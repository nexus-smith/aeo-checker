# Beesy AEO Scan Results — 2026-03-21

## beesy.me — 25/110 (Poor)

| Check | Score | Issue |
|-------|-------|-------|
| Structured Data | 5/20 | Meta desc OK, no JSON-LD, no OpenGraph |
| robots.txt AI Bots | 0/15 | **ALL AI bots BLOCKED** (GPTBot, ClaudeBot, PerplexityBot, Google-Extended) |
| llms.txt | 0/15 | Missing |
| Content Structure | 5/20 | H1 OK, no H2s, no FAQ schema |
| Tool/API | 0/15 | No ai-plugin.json, no OpenAPI |
| Performance | 15/15 | 254ms ⚡ (excellent) |
| Markdown for Agents | 0/10 | No content negotiation, no /crawl, no llms-full.txt |

**Key finding:** Beesy is actively blocking ALL AI agents via robots.txt. When someone asks ChatGPT or Claude "what's the best AI meeting tool?", Beesy is invisible.

### robots.txt Deep Dive
The robots.txt is **Cloudflare-managed** with two critical problems:
1. Every AI bot explicitly blocked: ClaudeBot, GPTBot, Google-Extended, Amazonbot, Applebot-Extended, Bytespider, CCBot, meta-externalagent
2. A catch-all `User-agent: * / Disallow: /` at the bottom → blocks EVERYTHING including Google Search
3. Content-Signal header says `search=yes` but the Disallow rule overrides it

**Source:** Likely from Cloudflare Dashboard → Security → Bots → "AI Scrapers" toggle. JC or David can turn it off in 30 seconds.

### Deliverables Prepared
- `beesy-llms-txt-draft.md` — Ready-to-upload llms.txt file for beesy.me
- Proposed robots.txt fix (allow search + AI discovery bots, block only training crawlers)
- Estimated impact: 25/110 → 70-80/110 with llms.txt + robots.txt + basic JSON-LD

## beesy.fr — 0/110 (Critical)

SSL error: `TLSV1_ALERT_INTERNAL_ERROR`. Page won't load at all.
This means beesy.fr is completely unreachable by both humans and AI agents.

## What This Means for David

1. **Beesy is invisible to AI agents.** When prospects ask AI assistants about meeting productivity tools, Beesy won't be recommended.
2. **Quick wins available:** Just unblocking AI bots in robots.txt would improve the score significantly. Adding JSON-LD + llms.txt = 70+ score achievable in a few hours.
3. **beesy.fr is broken** — SSL certificate issue means the French domain is completely down.
4. **Agents B2B angle:** If David is selling AI agent solutions to enterprises, his own product should be agent-ready. It's a credibility issue.

## Draft Message for David (send when timing is right)

Subject: J'ai scanné beesy.me — il y a un truc à régler

Salut David,

J'ai scanné beesy.me avec l'outil AEO Checker dont je t'ai parlé. Résultat : 25/110 (Poor).

Le problème principal : le robots.txt de Beesy bloque TOUS les assistants IA — ChatGPT, Claude, Perplexity, tout. Concrètement, quand quelqu'un demande à ChatGPT "quel outil pour gérer mes réunions ?", Beesy est invisible. L'IA ne peut même pas lire le site.

En plus, beesy.fr (le domaine français) a un problème de certificat SSL — le site ne charge pas du tout, ni pour les humains ni pour les machines.

La bonne nouvelle : c'est facile à corriger. Modifier le robots.txt + ajouter quelques balises structurées = on peut passer de 25 à 70+ en quelques heures. Et vu que tu vends des solutions IA aux entreprises, c'est important que ton propre produit soit visible par les IA.

Tu veux que je prépare les corrections ?

— Nexus
