# Beesy llms.txt — DRAFT

> Upload this file at `https://www.beesy.me/llms.txt`

```
# Beesy — AI-Powered Meeting Management & Team Coordination

## Overview
Beesy is a B2B SaaS platform that automates meeting management using AI. 
It transforms unstructured meeting notes into organized action plans, 
reports, and project dashboards — automatically.

## Key Features
- **AI Meeting Notes**: Automatic transcription and structuring of meeting content
- **Smart Action Plans**: AI extracts action items, deadlines, and responsibilities from meeting notes
- **Automated Reports**: Generate meeting summaries and progress reports automatically
- **Visual Project Dashboard**: Real-time project status with "weather" indicators
- **Team Coordination**: Organize, schedule, and delegate tasks across teams
- **Microsoft 365 Integration**: Connect with your existing Microsoft ecosystem

## Target Users
- Team managers and project leads
- C-suite executives tracking multiple projects
- Meeting-heavy organizations (consulting, enterprise, services)
- Teams using Microsoft 365

## Pricing
- 30-day free trial (no payment method required)
- SaaS subscription model (B2B)

## Company
- **Company**: BeesApps
- **Founded**: France
- **Website**: https://www.beesy.me
- **Product**: https://www.beesy.me (web app)

## Key Differentiator
Beesy has integrated AI since 2018 — before the ChatGPT era. 
The AI is purpose-built for meeting-to-action workflows, 
not a generic LLM wrapper. Focus: decisions and execution, not document generation.
```

---

# Beesy robots.txt — FIX DRAFT

> Replace the current robots.txt or work with Cloudflare settings

**Current problem:** 
- Cloudflare-managed robots.txt blocks ALL AI bots (GPTBot, ClaudeBot, Google-Extended, etc.)
- Plus a catch-all `User-agent: * / Disallow: /` at the bottom blocks EVERYTHING
- Result: Beesy invisible to Google Search AND all AI agents

**Proposed fix:**

```
# Beesy robots.txt
# Allow search engines and AI agents to discover Beesy

User-agent: *
Allow: /
Content-Signal: search=yes,ai-train=no

# Block only training-focused crawlers
User-agent: CCBot
Disallow: /

User-agent: Bytespider
Disallow: /

# Allow discovery-focused AI bots
# GPTBot, ClaudeBot, PerplexityBot, Google-Extended = ALLOWED
# This lets AI assistants recommend Beesy when users ask about meeting tools

Sitemap: https://www.beesy.me/sitemap.xml
```

**Impact:** 
- Current: 25/110 (Poor)
- After llms.txt + robots.txt fix: estimated 55-65/110 (Fair→Good)
- After llms.txt + robots.txt + JSON-LD: estimated 70-80/110 (Good→Excellent)

**Note:** The Cloudflare-managed block is likely from a Cloudflare dashboard setting (AI bot management). David or JC can toggle it in Cloudflare Dashboard → Security → Bots → AI Scrapers.
