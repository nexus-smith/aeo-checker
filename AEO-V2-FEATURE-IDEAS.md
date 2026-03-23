# AEO Checker v2 — Feature Ideas

*Brainstormed 2026-03-10. Based on competitive analysis, blog research, and market signals.*

---

## Current v1 (Landing Page Only)
- Static score display (e.g., "Your AEO Score: 46/100")
- Manual analysis (not automated)
- Blog content driving SEO

## v2 Feature Priorities

### P0 — Must Have (differentiators)

#### 1. Automated AEO Score Calculator
- User enters URL → automated scan → score + breakdown
- **Checks:** Schema.org markup, FAQ presence, structured data, meta descriptions, content structure, readability
- Why: Free tool = lead magnet. Every competitor charges for this. We give it free.
- Competitive edge: GenRankEngine charges for their "displacement check". We make basic check free.

#### 2. Schema.org Validation
- Detect existing schema types (Article, FAQPage, HowTo, Product, Organization)
- Flag missing schemas that AI engines look for
- Suggest specific schema additions with code snippets
- Why: Schema = #1 technical factor for AI citation. Nobody offers a free schema checker specifically for AI visibility.

#### 3. llms.txt Detection & Generator
- Check if site has `/llms.txt` (emerging standard, blog post already written)
- Generate optimized `llms.txt` content based on site analysis

#### 4. Cloudflare "Markdown for Agents" Check (NEW — 2026-03-11)
- Test if site responds to `Accept: text/markdown` header (Cloudflare's Markdown for Agents feature)
- Check if site serves clean markdown via content negotiation → means AI agents get structured content
- Flag sites NOT on Cloudflare: recommend llms.txt / structured data as alternative
- **Source:** Cloudflare changelog 2026-03-10, HN 262↑ + 106 comments. CF is building the "robots.txt for AI" infrastructure layer.
- **Blog idea:** "Cloudflare's Markdown for Agents: Is Your Site Ready for AI Crawlers?"
- Why: We wrote the blog "llms.txt: The New robots.txt" — this makes us the authority AND the tool.

### P1 — Should Have (value add)

#### 4. FAQ Presence Check
- Scan for FAQ sections on page
- Check if FAQPage schema matches visible FAQ content
- Suggest FAQ questions based on page topic (using AI)
- Why: FAQs = citation magnets for AI. Simple to check, high impact.

#### 5. Sitemap.xml Analysis
- Check sitemap exists, is valid, is submitted to Google
- Count pages, check for common errors
- Why: Basic but foundational. Many sites have broken sitemaps.

#### 6. Content Structure Score
- H1/H2/H3 hierarchy check
- Paragraph length analysis (AI prefers concise, scannable content)
- Key information placement (front-loaded vs buried)
- Why: Content structure directly affects AI citation probability.

#### 7. Competitive Displacement Report
- "Who is AI citing instead of you?" (inspired by GenRankEngine)
- User enters their URL + competitor URLs → compare AI visibility
- Shows which competitor gets cited and why
- Why: This is the killer feature GenRankEngine has. If we offer it free or at $99, we undercut them.

### P2 — Nice to Have (future)

#### 8. AI Citation Monitoring (Subscription Upsell)
- Weekly email: "Your brand was mentioned by ChatGPT X times this week"
- Track mentions across ChatGPT, Claude, Perplexity, Gemini
- Why: This is where subscription revenue lives. Audit = one-time, monitoring = recurring.
- Pricing: $19-$39/mo (undercut Otterly at $39/mo, match Atyla at €19/mo)

#### 9. Robots.txt AI Directives Check
- Check for AI-specific directives (GPTBot, ClaudeBot, PerplexityBot, etc.)
- Flag if site is accidentally blocking AI crawlers
- Suggest optimal robots.txt for AI visibility
- Why: Many sites block AI bots without knowing. Quick win.

#### 10. Multi-Page Batch Analysis
- Scan entire site (not just one page)
- Prioritized fix list across all pages
- Why: Enterprise value. Could be the $299 tier differentiator vs $99 single-page.

---

## Technical Stack Considerations

**For v2 MVP (P0 features):**
- Static HTML + client-side JS (keep it simple, no backend)
- Fetch URL via CORS proxy or serverless function
- Parse HTML client-side for schema, FAQ, structure
- Score algorithm = weighted checklist

**For monitoring (P2):**
- Needs backend (store user accounts, schedule checks)
- Options: Supabase (free tier), Cloudflare Workers, or simple cron + email
- This is where we'd need David's investment decision

---

## Revenue Model Options

| Model | Price | Audience | Revenue Type |
|-------|-------|----------|-------------|
| **Free Check** | $0 | Everyone | Lead gen |
| **Basic Report** | $99 one-time | SMBs, founders | One-time |
| **Pro Audit** | $299-$499 one-time | Growth companies | One-time |
| **Expert Audit** | $999-$2,499 one-time | Enterprise | One-time |
| **Monitoring** | $19-$39/mo | Ongoing users | Recurring |
| **Agency Plan** | $99-$199/mo (10+ sites) | Agencies | Recurring |

**Recommended path:** Free check (v2 MVP) → paid audit upsell → monitoring subscription later.

---

## Build Priority for David Discussion

1. **Quickest win:** Free automated checker (P0 items 1-3). Can build in ~1 week with coding agent.
2. **Biggest differentiator:** Competitive displacement report (P1 item 7). Complex but unique.
3. **Revenue unlock:** Monitoring subscription (P2 item 8). Needs backend investment.

*Decision needed from David: Build free tool first (growth) or paid features first (revenue)?*
