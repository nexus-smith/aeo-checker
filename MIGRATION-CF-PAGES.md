# Migration AEO Check: Netlify → Cloudflare Pages

*Created: 2026-03-16 23:36 — à exécuter dès que David ne fixe pas Netlify*

## Why

Netlify free tier paused the ENTIRE site (503). Google can't crawl, indexation blocked.
Cloudflare Pages: free tier is more generous (500 deploys/month, unlimited bandwidth, unlimited sites).

## What Needs to Migrate

### Static files (easy)
- `public/` folder — 18 HTML files (homepage, pricing, 13 blogs, robots.txt, sitemap.xml, llms.txt)
- No build step needed — pure static HTML

### Serverless functions (needs adaptation)
- `netlify/functions/check.js` — AEO scan API endpoint (18KB)
- `netlify/functions/badge.js` — SVG badge generator (1.7KB)
- Netlify Functions → Cloudflare Workers syntax (minor changes)
- Key difference: Cloudflare Workers use `export default { async fetch(request) }` vs Netlify's `exports.handler`

### Redirects
- `/api/check` → function
- `/api/badge/:score` → function
- Netlify `_redirects` or `netlify.toml` → Cloudflare `_redirects` file (same format mostly)

### DNS/Domain
- Current: `aeo-check.netlify.app` (subdomain)
- CF Pages: `aeo-check.pages.dev` (new subdomain)
- Update all internal refs (sitemap canonical URLs, og:url, etc.)
- Old Netlify URLs will 503 — no redirect possible while site is paused

## Step-by-Step Plan

### 1. Create Cloudflare Account
- Use nexus.smith@proton.me or nexus.smiths@gmail.com
- Free plan is sufficient

### 2. Create CF Pages Project
```bash
# Install wrangler CLI
npm install -g wrangler

# Login
wrangler login

# Create pages project
wrangler pages project create aeo-check

# Deploy static files
wrangler pages deploy public/
```

### 3. Adapt Functions
Create `functions/` directory at project root (CF Pages convention):

```
functions/
  api/
    check.js    ← adapted from netlify/functions/check.js
    badge/
      [score].js ← adapted from netlify/functions/badge.js
```

CF Pages function format:
```javascript
export async function onRequest(context) {
  const { request, params } = context;
  // ... logic from Netlify handler
  return new Response(body, { headers, status });
}
```

### 4. Update URLs
- sitemap.xml: change all `aeo-check.netlify.app` → `aeo-check.pages.dev`
- All HTML canonical URLs
- All og:url meta tags
- GoatCounter still works (tracking by page path, not domain)

### 5. Resubmit to Google
- Update Search Console property URL
- Resubmit sitemap
- Request indexing for key pages

### 6. Update References
- `TOOLS.md` — Netlify token/deploy info
- `TODO.md` — deploy commands
- dang.ai backlink still points to netlify URL (can't change)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Functions don't work on CF | API broken | Test locally first with `wrangler pages dev` |
| Old URLs dead (netlify) | Lost backlinks | Can't fix while Netlify paused. Accept loss. |
| Google re-crawl delay | Days without indexation | Request indexing immediately via Search Console |
| CF free tier limits | Unlikely | 500 deploys/month, unlimited bandwidth |

## Decision Criteria

**Migrate IF:**
- David silent >24h after 503 alert (deadline: Mar 17 15:08)
- OR David says "go ahead"

**Don't migrate IF:**
- David adds payment method to Netlify (fixes everything instantly)
- David upgrades Netlify plan

## Estimated Time
- Static migration: 15 min
- Function adaptation: 30-45 min  
- URL updates: 15 min
- Total: ~1h with testing
