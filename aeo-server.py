#!/usr/bin/env python3
"""AEO Checker — Lightweight Python backend.
Serves static files + /api/check endpoint.
Drop-in replacement for `python3 -m http.server`.
"""

import json, os, re, time, sys, logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

from collections import defaultdict
from datetime import datetime, timezone
import threading

# ── Structured Logging ────────────────────────────────────────────────────────
LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "aeo-server.log")

# Log to both stderr and file
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("aeo")

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
UA = "AEOChecker/1.0 (AI Discoverability Scanner)"
TIMEOUT = 8
CHECK_POOL = ThreadPoolExecutor(max_workers=7)  # one per check

# ── Scan History (persisted to disk) ──────────────────────────────────────────
HISTORY_MAX = 20
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan-history.json")
_history_lock = threading.Lock()
_scan_history = []  # [{domain, grade, gradeColor, score, maxScore, scannedAt}]

def _history_load():
    """Load history from disk on startup."""
    global _scan_history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                _scan_history = json.load(f)[:HISTORY_MAX]
            log.info("Loaded %d scans from history file", len(_scan_history))
    except Exception as e:
        log.warning("Failed to load history: %s", e)
        _scan_history = []

def _history_save():
    """Persist history to disk (called after each add)."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(_scan_history, f)
    except Exception as e:
        log.warning("Failed to save history: %s", e)

def _history_add(result):
    """Store a scan result in history (domain only, no PII)."""
    parsed = urlparse(result["url"])
    entry = {
        "domain": parsed.netloc,
        "grade": result["grade"],
        "gradeColor": result["gradeColor"],
        "score": result["totalScore"],
        "maxScore": result["maxScore"],
        "scannedAt": result["scannedAt"],
    }
    with _history_lock:
        _scan_history.insert(0, entry)
        if len(_scan_history) > HISTORY_MAX:
            _scan_history.pop()
        _history_save()

def _history_get():
    with _history_lock:
        return list(_scan_history)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
RATE_LIMIT = 10          # max scans per window
RATE_WINDOW = 60         # seconds
_rate_lock = threading.Lock()
_rate_buckets = defaultdict(list)  # ip -> [timestamps]

def _rate_check(ip):
    """Returns True if allowed, False if rate-limited."""
    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets[ip]
        # Prune old entries
        _rate_buckets[ip] = bucket = [t for t in bucket if now - t < RATE_WINDOW]
        if len(bucket) >= RATE_LIMIT:
            return False
        bucket.append(now)
        return True

# ── Checks ────────────────────────────────────────────────────────────────────

def fetch_page(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        return r.text, r.status_code
    except Exception as e:
        return "", 0

def check_structured_data(url, html):
    score, details, recs = 0, [], []
    soup = BeautifulSoup(html, "html.parser")

    jsonlds = soup.find_all("script", type="application/ld+json")
    if jsonlds:
        score += 10
        details.append(f"{len(jsonlds)} JSON-LD schema(s) found")
        types = []
        for s in jsonlds:
            try:
                d = json.loads(s.string or "")
                t = d.get("@type", [])
                types.extend(t if isinstance(t, list) else [t])
            except: pass
        if types:
            details.append(f"Types: {', '.join(types[:5])}")
    else:
        recs.append("Add JSON-LD structured data (Schema.org). AI agents rely on it to understand your content.")

    og_t = soup.find("meta", property="og:title")
    og_d = soup.find("meta", property="og:description")
    og_i = soup.find("meta", property="og:image")
    og_score = (2 if og_t else 0) + (2 if og_d else 0) + (1 if og_i else 0)
    score += og_score
    if og_score >= 4:
        details.append("OpenGraph tags complete")
    elif og_score > 0:
        details.append(f"OpenGraph partial ({og_score}/5)")
    else:
        recs.append("Add OpenGraph meta tags (og:title, og:description, og:image).")

    md = soup.find("meta", attrs={"name": "description"})
    md_c = md.get("content", "") if md else ""
    if md_c and len(md_c) > 50:
        score += 5
        details.append(f"Meta description: {len(md_c)} chars")
    elif md_c:
        score += 2
        details.append("Meta description too short")
        recs.append("Expand meta description to 120-160 chars.")
    else:
        recs.append("Add a meta description — the most important signal for AI answer engines.")

    return {"name": "Structured Data", "score": min(score, 20), "max": 20, "icon": "🧱",
            "details": " · ".join(details), "recommendations": recs}

def check_robots_txt(base_url):
    bots = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"]
    score, details, recs = 0, [], []
    try:
        r = requests.get(f"{base_url}/robots.txt", headers={"User-Agent": UA}, timeout=TIMEOUT)
        if r.status_code != 200:
            return {"name": "robots.txt AI Bots", "score": 0, "max": 15, "icon": "🤖",
                    "details": f"No robots.txt (HTTP {r.status_code})",
                    "recommendations": ["Create robots.txt and explicitly allow AI bots."]}
        text = r.text
    except:
        return {"name": "robots.txt AI Bots", "score": 0, "max": 15, "icon": "🤖",
                "details": "Fetch error", "recommendations": ["Ensure robots.txt is accessible."]}

    lines = text.split("\n")
    current_agent = None
    rules = {}
    for line in lines:
        l = line.strip().lower()
        if l.startswith("user-agent:"):
            current_agent = line.strip().split(":", 1)[1].strip()
            rules.setdefault(current_agent, {"block": False})
        elif l.startswith("disallow:") and current_agent:
            path = line.strip().split(":", 1)[1].strip()
            if path == "/":
                rules[current_agent]["block"] = True

    wildcard_block = rules.get("*", {}).get("block", False)
    for bot in bots:
        bot_rules = rules.get(bot, {})
        blocked = bot_rules.get("block", False) or (wildcard_block and bot not in rules)
        mentioned = bot.lower() in text.lower()
        if blocked:
            details.append(f"{bot}: ❌ blocked")
            recs.append(f"{bot} is blocked. Remove Disallow: / for {bot}.")
        elif mentioned:
            score += 4
            details.append(f"{bot}: ✅ allowed")
        else:
            score += 2 if not wildcard_block else 0
            details.append(f"{bot}: ⚠️ not listed")
            if not wildcard_block:
                recs.append(f"Explicitly allow {bot} in robots.txt.")

    return {"name": "robots.txt AI Bots", "score": min(score, 15), "max": 15, "icon": "🤖",
            "details": " · ".join(details), "recommendations": recs}

def check_llms_txt(base_url):
    recs = []
    try:
        r = requests.get(f"{base_url}/llms.txt", headers={"User-Agent": UA}, timeout=TIMEOUT)
        if r.status_code == 200:
            length = len(r.text.strip())
            if length > 500:
                return {"name": "llms.txt", "score": 15, "max": 15, "icon": "📄",
                        "details": f"llms.txt exists ({length} chars) — comprehensive", "recommendations": []}
            elif length > 100:
                return {"name": "llms.txt", "score": 10, "max": 15, "icon": "📄",
                        "details": f"llms.txt exists ({length} chars) — could be expanded",
                        "recommendations": ["Expand llms.txt to 500+ chars with more product context."]}
            else:
                return {"name": "llms.txt", "score": 5, "max": 15, "icon": "📄",
                        "details": f"llms.txt minimal ({length} chars)",
                        "recommendations": ["Fill llms.txt with structured context for AI agents."]}
        else:
            recs.append("Create /llms.txt — the emerging standard for AI agent context.")
    except:
        recs.append("Create /llms.txt with context about your product for AI agents.")
    return {"name": "llms.txt", "score": 0, "max": 15, "icon": "📄",
            "details": "No llms.txt found", "recommendations": recs}

def check_content_structure(html):
    score, details, recs = 0, [], []
    soup = BeautifulSoup(html, "html.parser")

    h1s = soup.find_all("h1")
    if len(h1s) == 1:
        score += 5; details.append("H1: ✅ (1)")
    elif len(h1s) > 1:
        score += 2; details.append(f"H1: ⚠️ ({len(h1s)})")
        recs.append(f"You have {len(h1s)} H1 tags. Use exactly one.")
    else:
        details.append("H1: ❌ missing"); recs.append("Add a single H1 tag.")

    h2s = len(soup.find_all("h2"))
    h3s = len(soup.find_all("h3"))
    if h2s >= 3:
        score += 5; details.append(f"H2-H3: ✅ ({h2s}×H2, {h3s}×H3)")
    elif h2s >= 1:
        score += 3; details.append(f"H2-H3: ({h2s}×H2, {h3s}×H3)")
    else:
        details.append("H2: ❌ none"); recs.append("Structure content with H2/H3 headings.")

    has_faq = has_howto = False
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(s.string or "")
            t = d.get("@type", [])
            types = t if isinstance(t, list) else [t]
            if "FAQPage" in types: has_faq = True
            if "HowTo" in types: has_howto = True
        except: pass
    if has_faq:
        score += 5; details.append("FAQPage: ✅")
    else:
        recs.append("Add FAQPage JSON-LD schema.")
    if has_howto:
        score += 5; details.append("HowTo: ✅")
    else:
        recs.append("Consider HowTo JSON-LD schema for step-by-step content.")

    return {"name": "Content Structure", "score": min(score, 20), "max": 20, "icon": "🏗️",
            "details": " · ".join(details), "recommendations": recs}

def check_tool_api(base_url, html):
    score, details, recs = 0, [], []

    has_plugin = False
    try:
        r = requests.get(f"{base_url}/.well-known/ai-plugin.json", headers={"User-Agent": UA}, timeout=TIMEOUT)
        if r.status_code == 200:
            has_plugin = True; score += 7; details.append("ai-plugin.json: ✅")
    except: pass
    if not has_plugin:
        details.append("ai-plugin.json: ❌")
        recs.append("Create /.well-known/ai-plugin.json — the standard manifest for AI tools.")

    has_openapi = False
    for p in ["/openapi.json", "/openapi.yaml", "/api-docs", "/swagger.json"]:
        try:
            r = requests.get(f"{base_url}{p}", headers={"User-Agent": UA}, timeout=TIMEOUT)
            if r.status_code == 200:
                has_openapi = True; score += 5; details.append(f"OpenAPI ({p}): ✅"); break
        except: pass
    if not has_openapi:
        details.append("OpenAPI: ❌")
        recs.append("Publish an OpenAPI spec at /openapi.json.")

    soup = BeautifulSoup(html, "html.parser")
    body_text = soup.get_text().lower()
    has_api_hints = any(kw in body_text for kw in ["mcp", "model context protocol", "ai agent", "api endpoint"])
    has_api_link = bool(soup.find("a", href=re.compile(r"api|docs|developer")))
    if has_api_hints or has_api_link:
        score += 3; details.append("API/MCP mentions: ✅")
    else:
        recs.append("Link to your API docs from your homepage.")

    return {"name": "Tool/API Description", "score": min(score, 15), "max": 15, "icon": "🔌",
            "details": " · ".join(details), "recommendations": recs}

def check_performance(url):
    details, recs = [], []
    try:
        start = time.time()
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        _ = r.text
        ms = int((time.time() - start) * 1000)
        if ms < 1000:
            return {"name": "Performance", "score": 15, "max": 15, "icon": "⚡",
                    "details": f"Response: {ms}ms ⚡ (<1s)", "recommendations": []}
        elif ms < 2000:
            return {"name": "Performance", "score": 10, "max": 15, "icon": "⚡",
                    "details": f"Response: {ms}ms ✅ (<2s)", "recommendations": []}
        elif ms < 3000:
            recs.append(f"Response {ms}ms is borderline. Aim for <1s.")
            return {"name": "Performance", "score": 5, "max": 15, "icon": "⚡",
                    "details": f"Response: {ms}ms ⚠️", "recommendations": recs}
        else:
            recs.append(f"Response {ms}ms is too slow. Use CDN/caching.")
            return {"name": "Performance", "score": 0, "max": 15, "icon": "⚡",
                    "details": f"Response: {ms}ms 🐌", "recommendations": recs}
    except Exception as e:
        return {"name": "Performance", "score": 0, "max": 15, "icon": "⚡",
                "details": f"Error: {e}", "recommendations": ["Page failed to load."]}

def check_markdown_agents(base_url, url):
    score, details, recs = 0, [], []

    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/markdown"}, timeout=TIMEOUT)
        ct = r.headers.get("content-type", "").lower()
        if "text/markdown" in ct or "text/x-markdown" in ct:
            score += 5; details.append("Markdown negotiation: ✅")
        else:
            details.append("Markdown negotiation: ❌")
            recs.append("Support Accept: text/markdown content negotiation for AI crawlers.")
    except:
        details.append("Markdown negotiation: ❌")

    try:
        r = requests.get(f"{base_url}/crawl", headers={"User-Agent": UA, "Accept": "text/markdown"}, timeout=TIMEOUT)
        ct = r.headers.get("content-type", "").lower()
        if r.status_code == 200 and len(r.text.strip()) > 50:
            score += 3; details.append(f"/crawl: ✅ ({len(r.text.strip())} chars)")
        else:
            details.append("/crawl: ❌")
    except:
        details.append("/crawl: ❌")
    if "/crawl" not in " ".join(details) or "❌" in " ".join(d for d in details if "/crawl" in d):
        recs.append("Consider adding a /crawl endpoint returning markdown content for AI agents.")

    try:
        r = requests.get(f"{base_url}/llms-full.txt", headers={"User-Agent": UA}, timeout=TIMEOUT)
        if r.status_code == 200 and len(r.text.strip()) > 100:
            score += 2; details.append(f"llms-full.txt: ✅ ({len(r.text.strip())} chars)")
        else:
            details.append("llms-full.txt: ❌")
    except:
        details.append("llms-full.txt: ❌")
    if "llms-full" not in " ".join(details) or "❌" in " ".join(d for d in details if "llms-full" in d):
        recs.append("Create /llms-full.txt with comprehensive product context.")

    return {"name": "Markdown for Agents", "score": min(score, 10), "max": 10, "icon": "📝",
            "details": " · ".join(details), "recommendations": recs}

def run_check(url):
    if not re.match(r"https?://", url):
        url = "https://" + url
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    html, status = fetch_page(url)
    fetch_error = None if status else "Could not fetch page"

    # Run all 7 checks in parallel (each may make its own HTTP requests)
    futures = {
        CHECK_POOL.submit(check_structured_data, url, html): 0,
        CHECK_POOL.submit(check_robots_txt, base_url): 1,
        CHECK_POOL.submit(check_llms_txt, base_url): 2,
        CHECK_POOL.submit(check_content_structure, html): 3,
        CHECK_POOL.submit(check_tool_api, base_url, html): 4,
        CHECK_POOL.submit(check_performance, url): 5,
        CHECK_POOL.submit(check_markdown_agents, base_url, url): 6,
    }
    checks = [None] * 7
    for future in as_completed(futures):
        idx = futures[future]
        try:
            checks[idx] = future.result(timeout=TIMEOUT + 5)
        except Exception as e:
            checks[idx] = {"name": f"Check {idx}", "score": 0, "max": 0,
                           "icon": "❓", "details": f"Error: {e}", "recommendations": []}

    total = sum(c["score"] for c in checks)
    mx = sum(c["max"] for c in checks)
    pct = (total / mx * 100) if mx else 0

    if pct >= 80: grade, color = "Excellent", "#22c55e"
    elif pct >= 60: grade, color = "Good", "#84cc16"
    elif pct >= 40: grade, color = "Fair", "#eab308"
    elif pct >= 20: grade, color = "Poor", "#f97316"
    else: grade, color = "Critical", "#ef4444"

    return {
        "url": url, "baseUrl": base_url,
        "totalScore": total, "maxScore": mx,
        "grade": grade, "gradeColor": color,
        "fetchError": fetch_error, "checks": checks,
        "scannedAt": datetime.now(timezone.utc).isoformat(),
    }

# ── HTTP Handler ──────────────────────────────────────────────────────────────

class AEOHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # History endpoint: /api/history
        if self.path == "/api/history":
            self._json(200, {"scans": _history_get()})
            return
        # Badge endpoint: /api/badge/<score>
        m = re.match(r"^/api/badge/(\d+)$", self.path)
        if m:
            score = max(0, min(110, int(m.group(1))))
            pct = round(score / 110 * 100)
            if pct >= 80: color = "#22c55e"
            elif pct >= 60: color = "#84cc16"
            elif pct >= 40: color = "#eab308"
            elif pct >= 20: color = "#f97316"
            else: color = "#ef4444"
            label, value = "AEO Score", f"{score}/110"
            lw, vw = 80, 60
            tw = lw + vw
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{tw}" height="20" role="img">
  <title>{label}: {value}</title>
  <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <clipPath id="r"><rect width="{tw}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)"><rect width="{lw}" height="20" fill="#555"/><rect x="{lw}" width="{vw}" height="20" fill="{color}"/><rect width="{tw}" height="20" fill="url(#s)"/></g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{lw//2}" y="15" fill="#010101" fill-opacity=".3">{label}</text><text x="{lw//2}" y="14">{label}</text>
    <text x="{lw+vw//2}" y="15" fill="#010101" fill-opacity=".3">{value}</text><text x="{lw+vw//2}" y="14">{value}</text>
  </g></svg>'''
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(svg.encode())
            return
        # Markdown content negotiation: if Accept: text/markdown, serve llms-full.txt
        accept = self.headers.get("Accept", "")
        if "text/markdown" in accept and (self.path == "/" or self.path == "/index.html"):
            try:
                with open("llms-full.txt", "r") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode())
                return
            except FileNotFoundError:
                pass

        # /crawl endpoint: return markdown content for AI crawlers
        if self.path == "/crawl":
            try:
                with open("llms-full.txt", "r") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode())
                return
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/check":
            client_ip = self.client_address[0]
            if not _rate_check(client_ip):
                self._json(429, {"error": "Rate limit exceeded. Max 10 scans per minute."})
                log.warning("RATE_LIMITED ip=%s", client_ip)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                url = data.get("url", "").strip()
            except:
                self._json(400, {"error": "Invalid JSON"})
                return
            if not url:
                self._json(400, {"error": "url is required"})
                return
            try:
                t0 = time.time()
                result = run_check(url)
                ms = int((time.time() - t0) * 1000)
                log.info("SCAN ip=%s url=%s grade=%s score=%d/%d ms=%d", client_ip, url, result['grade'], result['totalScore'], result['maxScore'], ms)
                _history_add(result)
                self._json(200, result)
            except Exception as e:
                log.error("SCAN_ERROR ip=%s url=%s error=%s", client_ip, url, e)
                self._json(500, {"error": str(e)})
        else:
            self._json(404, {"error": "Not found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        super().end_headers()

    def _json(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def log_message(self, format, *args):
        # Suppress noisy static file GET logs, only log non-200 or API paths
        msg = format % args
        if '"GET /' in msg and ' 200 ' in msg and '/api/' not in msg:
            return  # skip routine static file hits
        log.info("HTTP %s %s", self.address_string(), msg)

class ThreadingAEOServer(ThreadingMixIn, HTTPServer):
    """Handle each request in a new thread — prevents slow checks from blocking static files."""
    daemon_threads = True

if __name__ == "__main__":
    _history_load()
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy-static")
    os.chdir(static_dir)
    server = ThreadingAEOServer(("", PORT), AEOHandler)
    log.info("AEO Checker started port=%d pid=%d dir=%s history=%d", PORT, os.getpid(), static_dir, len(_scan_history))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
        server.shutdown()
