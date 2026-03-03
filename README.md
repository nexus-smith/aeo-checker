# AEO Checker — MVP

**Status:** Building (internal prototype)
**Goal:** Tool that analyzes any URL for AI agent discoverability (AEO = Answer Engine Optimization)

## What it does
User enters a URL → backend fetches & analyzes → returns AEO score /100 with breakdown + recommendations.

## Architecture (MVP)
- **Backend:** Express.js server (Node.js) — runs the 6 checks
- **Frontend:** Static HTML/CSS/JS — input form + results display
- **Later:** Convert backend to Cloudflare Worker for public deploy

## The 6 Checks

1. **Structured Data** (0-20pts) — Schema.org JSON-LD, OpenGraph, meta descriptions
2. **robots.txt AI Bots** (0-15pts) — Are GPTBot, ClaudeBot, PerplexityBot, Google-Extended allowed?
3. **llms.txt** (0-15pts) — Does `/llms.txt` exist? (emerging standard for AI agent context)
4. **Content Structure** (0-20pts) — H1-H3 hierarchy, FAQ schema, HowTo schema
5. **Tool/API Description** (0-15pts) — MCP manifest, API docs, skill descriptions quality
6. **Performance** (0-15pts) — Response time (agents are impatient, <2s = good)

## Frontend Design
- Clean, dark theme (tech-focused audience)
- URL input → animated scan → results card with score breakdown
- Each check: icon + score + brief explanation + actionable recommendation
- Embeddable badge: "AEO Score: XX/100" (SVG, copy-paste snippet)
- Mobile responsive

## Run
```bash
cd projects/aeo-checker
npm install
npm start
# Frontend: http://localhost:3000
# API: POST http://localhost:3000/api/check { url: "https://example.com" }
```
