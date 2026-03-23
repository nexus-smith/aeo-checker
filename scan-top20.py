#!/usr/bin/env python3
"""Scan top 20 tech companies and output CSV."""
import json, requests, sys

SITES = [
    "stripe.com", "github.com", "notion.so", "linear.app", "vercel.com",
    "supabase.com", "openai.com", "anthropic.com", "cloudflare.com", "shopify.com",
    "slack.com", "zoom.us", "figma.com", "hubspot.com", "datadog.com",
    "twilio.com", "sentry.io", "atlassian.com", "gitlab.com", "hashicorp.com",
]

API = "http://localhost:8787/api/check"
results = []

print("domain,grade,score,max,pct")
for site in SITES:
    try:
        r = requests.post(API, json={"url": f"https://{site}"}, timeout=30)
        d = r.json()
        grade = d["grade"]
        score = d["totalScore"]
        mx = d["maxScore"]
        pct = round(score / mx * 100) if mx else 0
        print(f"{site},{grade},{score},{mx},{pct}%")
        results.append({"domain": site, "grade": grade, "score": score, "max": mx, "pct": pct,
                         "checks": {c["name"]: f"{c['score']}/{c['max']}" for c in d["checks"]}})
        sys.stderr.write(f"  {site} -> {grade} {score}/{mx}\n")
    except Exception as e:
        print(f"{site},ERROR,0,0,0%")
        sys.stderr.write(f"  {site} -> ERROR: {e}\n")

# Summary stats
scores = [r["score"] for r in results if r.get("grade") != "ERROR"]
if scores:
    avg = sum(scores) / len(scores)
    best = max(results, key=lambda x: x.get("score", 0))
    worst = min(results, key=lambda x: x.get("score", 999))
    sys.stderr.write(f"\n--- Summary ---\n")
    sys.stderr.write(f"Average: {avg:.1f}/110\n")
    sys.stderr.write(f"Best: {best['domain']} ({best['grade']} {best['score']}/110)\n")
    sys.stderr.write(f"Worst: {worst['domain']} ({worst['grade']} {worst['score']}/110)\n")

    from collections import Counter
    grades = Counter(r["grade"] for r in results)
    sys.stderr.write(f"Grades: {dict(grades)}\n")

# Write detailed JSON
outpath = "/Users/jarvis/.openclaw/workspace/projects/aeo-checker/research/top20-scans.json"
import os
os.makedirs(os.path.dirname(outpath), exist_ok=True)
with open(outpath, "w") as f:
    json.dump(results, f, indent=2)
sys.stderr.write(f"Detailed results: {outpath}\n")
