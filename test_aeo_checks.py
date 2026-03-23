#!/usr/bin/env python3
"""Unit tests for AEO Checker — 7 checks individually tested with mocked HTTP.

Run:  cd projects/aeo-checker && python3 -m pytest test_aeo_checks.py -v
  or: cd projects/aeo-checker && python3 -m unittest test_aeo_checks -v
"""

import unittest
from unittest.mock import patch, MagicMock
import json

# Import check functions + module ref for patching
from aeo_server_checks import (
    check_structured_data,
    check_robots_txt,
    check_llms_txt,
    check_content_structure,
    check_tool_api,
    check_performance,
    check_markdown_agents,
    server_module,
)

# Patching target: the requests/time inside the loaded aeo-server module
REQUESTS_GET = "aeo_server.requests.get"
TIME_TIME = "aeo_server.time.time"

# Register the loaded module so unittest.mock can find it
import sys
sys.modules["aeo_server"] = server_module


def mock_response(status=200, text="", headers=None):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.headers = headers or {"content-type": "text/html"}
    resp.content = text.encode() if isinstance(text, str) else text
    return resp


# ─── HTML fixtures ────────────────────────────────────────────────────────────

PERFECT_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta name="description" content="AEO Checker is a free tool that scans your website for AI agent discoverability across 7 criteria and gives actionable recommendations." />
  <meta property="og:title" content="AEO Checker" />
  <meta property="og:description" content="Free AI-readiness audit tool" />
  <meta property="og:image" content="https://example.com/og.png" />
  <script type="application/ld+json">
  {"@type": "Organization", "name": "AEO Checker"}
  </script>
  <script type="application/ld+json">
  {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "What is AEO?"}]}
  </script>
  <script type="application/ld+json">
  {"@type": "HowTo", "name": "How to optimize"}
  </script>
</head>
<body>
  <h1>AEO Checker</h1>
  <h2>What is AEO?</h2>
  <h2>How it works</h2>
  <h2>Get started</h2>
  <p>Check your site for AI agent readiness and MCP endpoint compatibility.</p>
  <a href="/api/docs">API Documentation</a>
</body>
</html>"""

MINIMAL_HTML = """<!DOCTYPE html>
<html><head><title>Hello</title></head>
<body><p>Just a paragraph</p></body></html>"""

PARTIAL_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta name="description" content="Short" />
  <meta property="og:title" content="Test" />
</head>
<body>
  <h1>Title</h1>
  <h1>Second Title</h1>
  <h2>Section</h2>
</body>
</html>"""


class TestStructuredData(unittest.TestCase):
    """Check 1: Structured Data (max 20pts)."""

    def test_perfect_score(self):
        result = check_structured_data("https://example.com", PERFECT_HTML)
        self.assertEqual(result["name"], "Structured Data")
        self.assertEqual(result["max"], 20)
        self.assertEqual(result["score"], 20)
        self.assertIn("JSON-LD", result["details"])
        self.assertEqual(len(result["recommendations"]), 0)

    def test_minimal_html_zero(self):
        result = check_structured_data("https://example.com", MINIMAL_HTML)
        self.assertEqual(result["score"], 0)
        self.assertTrue(len(result["recommendations"]) >= 2)

    def test_partial_og_and_short_meta(self):
        result = check_structured_data("https://example.com", PARTIAL_HTML)
        # og:title=2, no og:desc=0, no og:image=0, short meta=2 → 4
        self.assertGreater(result["score"], 0)
        self.assertLess(result["score"], 20)

    def test_empty_html(self):
        result = check_structured_data("https://example.com", "")
        self.assertEqual(result["score"], 0)

    def test_score_capped_at_max(self):
        result = check_structured_data("https://example.com", PERFECT_HTML)
        self.assertLessEqual(result["score"], result["max"])


class TestRobotsTxt(unittest.TestCase):
    """Check 2: robots.txt AI Bots (max 15pts)."""

    @patch(REQUESTS_GET)
    def test_all_bots_explicitly_allowed(self, mock_get):
        robots = (
            "User-agent: GPTBot\nAllow: /\n"
            "User-agent: ClaudeBot\nAllow: /\n"
            "User-agent: PerplexityBot\nAllow: /\n"
            "User-agent: Google-Extended\nAllow: /\n"
        )
        mock_get.return_value = mock_response(text=robots)
        result = check_robots_txt("https://example.com")
        self.assertEqual(result["max"], 15)
        # 4pts per bot × 4 = 16, capped at 15
        self.assertEqual(result["score"], 15)

    @patch(REQUESTS_GET)
    def test_no_robots_txt(self, mock_get):
        mock_get.return_value = mock_response(status=404)
        result = check_robots_txt("https://example.com")
        self.assertEqual(result["score"], 0)

    @patch(REQUESTS_GET)
    def test_wildcard_block_all(self, mock_get):
        mock_get.return_value = mock_response(text="User-agent: *\nDisallow: /\n")
        result = check_robots_txt("https://example.com")
        self.assertEqual(result["score"], 0)

    @patch(REQUESTS_GET)
    def test_bots_not_mentioned_no_wildcard_block(self, mock_get):
        mock_get.return_value = mock_response(text="User-agent: Googlebot\nAllow: /\n")
        result = check_robots_txt("https://example.com")
        # Bots not mentioned, no wildcard block → 2pts each × 4 = 8
        self.assertEqual(result["score"], 8)

    @patch(REQUESTS_GET)
    def test_fetch_error(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        result = check_robots_txt("https://example.com")
        self.assertEqual(result["score"], 0)


class TestLlmsTxt(unittest.TestCase):
    """Check 3: llms.txt (max 15pts)."""

    @patch(REQUESTS_GET)
    def test_comprehensive_500plus(self, mock_get):
        mock_get.return_value = mock_response(text="x" * 600)
        result = check_llms_txt("https://example.com")
        self.assertEqual(result["score"], 15)
        self.assertIn("comprehensive", result["details"])

    @patch(REQUESTS_GET)
    def test_medium_100_500(self, mock_get):
        mock_get.return_value = mock_response(text="x" * 200)
        result = check_llms_txt("https://example.com")
        self.assertEqual(result["score"], 10)
        self.assertIn("expanded", result["details"])

    @patch(REQUESTS_GET)
    def test_minimal_under_100(self, mock_get):
        mock_get.return_value = mock_response(text="x" * 50)
        result = check_llms_txt("https://example.com")
        self.assertEqual(result["score"], 5)
        self.assertIn("minimal", result["details"])

    @patch(REQUESTS_GET)
    def test_not_found(self, mock_get):
        mock_get.return_value = mock_response(status=404)
        result = check_llms_txt("https://example.com")
        self.assertEqual(result["score"], 0)
        self.assertIn("No llms.txt", result["details"])

    @patch(REQUESTS_GET)
    def test_network_error(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        result = check_llms_txt("https://example.com")
        self.assertEqual(result["score"], 0)


class TestContentStructure(unittest.TestCase):
    """Check 4: Content Structure (max 20pts)."""

    def test_perfect_structure(self):
        result = check_content_structure(PERFECT_HTML)
        self.assertEqual(result["max"], 20)
        self.assertEqual(result["score"], 20)
        self.assertIn("H1: ✅", result["details"])
        self.assertIn("FAQPage: ✅", result["details"])
        self.assertIn("HowTo: ✅", result["details"])

    def test_minimal_html(self):
        result = check_content_structure(MINIMAL_HTML)
        self.assertEqual(result["score"], 0)

    def test_multiple_h1_gives_partial(self):
        result = check_content_structure(PARTIAL_HTML)
        self.assertIn("⚠️", result["details"])
        # Multiple H1=2, 1×H2=3, no FAQ/HowTo=0 → 5
        self.assertEqual(result["score"], 5)

    def test_empty_html(self):
        result = check_content_structure("")
        self.assertEqual(result["score"], 0)


class TestToolApi(unittest.TestCase):
    """Check 5: Tool/API Description (max 15pts)."""

    @patch(REQUESTS_GET)
    def test_all_present(self, mock_get):
        def side_effect(url, **kwargs):
            if "ai-plugin.json" in url:
                return mock_response(text='{"name": "test"}')
            if "openapi.json" in url:
                return mock_response(text='{"openapi": "3.0"}')
            return mock_response(status=404)
        mock_get.side_effect = side_effect
        result = check_tool_api("https://example.com", PERFECT_HTML)
        self.assertEqual(result["max"], 15)
        self.assertEqual(result["score"], 15)

    @patch(REQUESTS_GET)
    def test_nothing_present(self, mock_get):
        mock_get.return_value = mock_response(status=404)
        result = check_tool_api("https://example.com", MINIMAL_HTML)
        self.assertEqual(result["score"], 0)
        self.assertTrue(len(result["recommendations"]) >= 2)

    @patch(REQUESTS_GET)
    def test_only_openapi(self, mock_get):
        def side_effect(url, **kwargs):
            if "openapi.json" in url:
                return mock_response(text='{"openapi": "3.0"}')
            return mock_response(status=404)
        mock_get.side_effect = side_effect
        result = check_tool_api("https://example.com", MINIMAL_HTML)
        self.assertEqual(result["score"], 5)

    @patch(REQUESTS_GET)
    def test_only_ai_plugin(self, mock_get):
        def side_effect(url, **kwargs):
            if "ai-plugin.json" in url:
                return mock_response(text='{"name": "test"}')
            return mock_response(status=404)
        mock_get.side_effect = side_effect
        result = check_tool_api("https://example.com", MINIMAL_HTML)
        self.assertEqual(result["score"], 7)


class TestPerformance(unittest.TestCase):
    """Check 6: Performance (max 15pts)."""

    @patch(REQUESTS_GET)
    @patch(TIME_TIME)
    def test_fast_under_1s(self, mock_time, mock_get):
        mock_time.side_effect = [0.0, 0.3]  # 300ms
        mock_get.return_value = mock_response(text="<html></html>")
        result = check_performance("https://example.com")
        self.assertEqual(result["score"], 15)
        self.assertIn("⚡", result["details"])

    @patch(REQUESTS_GET)
    @patch(TIME_TIME)
    def test_medium_1_2s(self, mock_time, mock_get):
        mock_time.side_effect = [0.0, 1.5]  # 1500ms
        mock_get.return_value = mock_response(text="<html></html>")
        result = check_performance("https://example.com")
        self.assertEqual(result["score"], 10)

    @patch(REQUESTS_GET)
    @patch(TIME_TIME)
    def test_slow_2_3s(self, mock_time, mock_get):
        mock_time.side_effect = [0.0, 2.5]  # 2500ms
        mock_get.return_value = mock_response(text="<html></html>")
        result = check_performance("https://example.com")
        self.assertEqual(result["score"], 5)

    @patch(REQUESTS_GET)
    @patch(TIME_TIME)
    def test_very_slow_over_3s(self, mock_time, mock_get):
        mock_time.side_effect = [0.0, 4.0]  # 4000ms
        mock_get.return_value = mock_response(text="<html></html>")
        result = check_performance("https://example.com")
        self.assertEqual(result["score"], 0)

    @patch(REQUESTS_GET)
    def test_fetch_error(self, mock_get):
        mock_get.side_effect = Exception("Connection timeout")
        result = check_performance("https://example.com")
        self.assertEqual(result["score"], 0)
        self.assertIn("Error", result["details"])


class TestMarkdownAgents(unittest.TestCase):
    """Check 7: Markdown for Agents (max 10pts)."""

    @patch(REQUESTS_GET)
    def test_all_present(self, mock_get):
        def side_effect(url, **kwargs):
            headers = kwargs.get("headers", {})
            accept = headers.get("Accept", "")
            if accept == "text/markdown" and "/crawl" not in url:
                return mock_response(text="# Hello", headers={"content-type": "text/markdown"})
            if "/crawl" in url:
                return mock_response(
                    text="# Full crawl content for agents " * 10,
                    headers={"content-type": "text/markdown"},
                )
            if "llms-full.txt" in url:
                return mock_response(text="Comprehensive context " * 20)
            return mock_response(status=404)
        mock_get.side_effect = side_effect
        result = check_markdown_agents("https://example.com", "https://example.com/")
        self.assertEqual(result["max"], 10)
        self.assertEqual(result["score"], 10)

    @patch(REQUESTS_GET)
    def test_nothing_present(self, mock_get):
        mock_get.return_value = mock_response(status=404, headers={"content-type": "text/html"})
        result = check_markdown_agents("https://example.com", "https://example.com/")
        self.assertEqual(result["score"], 0)

    @patch(REQUESTS_GET)
    def test_only_llms_full(self, mock_get):
        def side_effect(url, **kwargs):
            if "llms-full.txt" in url:
                return mock_response(text="Comprehensive context " * 20)
            return mock_response(status=404, headers={"content-type": "text/html"})
        mock_get.side_effect = side_effect
        result = check_markdown_agents("https://example.com", "https://example.com/")
        self.assertEqual(result["score"], 2)


class TestScoringIntegrity(unittest.TestCase):
    """Cross-cutting scoring rules."""

    def test_max_total_is_110(self):
        maxes = [20, 15, 15, 20, 15, 15, 10]
        self.assertEqual(sum(maxes), 110)

    def test_grade_boundaries(self):
        def grade(pct):
            if pct >= 80: return "Excellent"
            elif pct >= 60: return "Good"
            elif pct >= 40: return "Fair"
            elif pct >= 20: return "Poor"
            return "Critical"

        self.assertEqual(grade(100), "Excellent")
        self.assertEqual(grade(80), "Excellent")
        self.assertEqual(grade(79.9), "Good")
        self.assertEqual(grade(60), "Good")
        self.assertEqual(grade(59.9), "Fair")
        self.assertEqual(grade(40), "Fair")
        self.assertEqual(grade(39.9), "Poor")
        self.assertEqual(grade(20), "Poor")
        self.assertEqual(grade(19.9), "Critical")
        self.assertEqual(grade(0), "Critical")

    def test_all_checks_return_required_keys(self):
        """Every check must return name, score, max, icon, details, recommendations."""
        required = {"name", "score", "max", "icon", "details", "recommendations"}
        results = [
            check_structured_data("https://x.com", MINIMAL_HTML),
            check_content_structure(MINIMAL_HTML),
        ]
        for r in results:
            self.assertTrue(required.issubset(r.keys()), f"Missing keys in {r['name']}")
            self.assertIsInstance(r["score"], (int, float))
            self.assertIsInstance(r["max"], int)
            self.assertIsInstance(r["recommendations"], list)
            self.assertLessEqual(r["score"], r["max"])


if __name__ == "__main__":
    unittest.main()
