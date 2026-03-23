const express = require('express');
const cheerio = require('cheerio');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const USER_AGENT = 'AEOChecker/1.0 (AI Discoverability Scanner)';
const FETCH_TIMEOUT = 8000;

// ─── Helper: Fetch with timeout ──────────────────────────────────────────────
async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        ...(options.headers || {}),
      },
    });
    clearTimeout(timer);
    return res;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

// ─── Check 1: Structured Data (0-20pts) ──────────────────────────────────────
async function checkStructuredData(url, html) {
  let score = 0;
  const details = [];
  const recommendations = [];

  const $ = cheerio.load(html);

  // JSON-LD (up to 10pts)
  const jsonldScripts = $('script[type="application/ld+json"]');
  const jsonldCount = jsonldScripts.length;
  if (jsonldCount > 0) {
    score += 10;
    details.push(`${jsonldCount} JSON-LD schema(s) found`);

    // Bonus: check for rich schema types (up to 2 bonus within cap)
    let richTypes = [];
    jsonldScripts.each((_, el) => {
      try {
        const data = JSON.parse($(el).html());
        const types = [].concat(data['@type'] || []);
        richTypes = richTypes.concat(types);
      } catch {}
    });
    if (richTypes.length > 0) {
      details.push(`Types: ${richTypes.slice(0, 5).join(', ')}`);
    }
  } else {
    recommendations.push('Add JSON-LD structured data (Schema.org). AI agents rely on it to understand your content type and extract key facts.');
  }

  // OpenGraph (up to 5pts)
  const ogTitle = $('meta[property="og:title"]').attr('content');
  const ogDesc = $('meta[property="og:description"]').attr('content');
  const ogImage = $('meta[property="og:image"]').attr('content');
  const ogScore = (ogTitle ? 2 : 0) + (ogDesc ? 2 : 0) + (ogImage ? 1 : 0);
  score += ogScore;
  if (ogScore >= 4) {
    details.push('OpenGraph tags complete');
  } else if (ogScore > 0) {
    details.push(`OpenGraph partial (${ogScore}/5)`);
    if (!ogTitle) recommendations.push('Add og:title for better AI/social context.');
    if (!ogDesc) recommendations.push('Add og:description — AI agents use this for page summaries.');
  } else {
    recommendations.push('Add OpenGraph meta tags (og:title, og:description, og:image). They help AI parse your page intent.');
  }

  // Meta description (up to 5pts)
  const metaDesc = $('meta[name="description"]').attr('content');
  if (metaDesc && metaDesc.length > 50) {
    score += 5;
    details.push(`Meta description: ${metaDesc.length} chars`);
  } else if (metaDesc) {
    score += 2;
    details.push('Meta description too short (<50 chars)');
    recommendations.push('Expand your meta description to 120–160 chars. AI agents use it as the primary page summary.');
  } else {
    recommendations.push('Add a meta description. It is the single most important signal for AI answer engines.');
  }

  score = Math.min(score, 20);

  return {
    name: 'Structured Data',
    score,
    max: 20,
    icon: '🧱',
    details: details.join(' · '),
    recommendations,
  };
}

// ─── Check 2: robots.txt AI Bots (0-15pts) ───────────────────────────────────
async function checkRobotsTxt(baseUrl) {
  const bots = ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended'];
  let score = 0;
  const details = [];
  const recommendations = [];
  let robotsText = '';

  try {
    const robotsUrl = `${baseUrl}/robots.txt`;
    const res = await fetchWithTimeout(robotsUrl);
    if (res.ok) {
      robotsText = await res.text();
    } else {
      recommendations.push(`robots.txt not found (HTTP ${res.status}). Create one and explicitly allow AI bots.`);
      return { name: 'robots.txt AI Bots', score: 0, max: 15, icon: '🤖', details: 'No robots.txt found', recommendations };
    }
  } catch (err) {
    recommendations.push('Could not fetch robots.txt. Ensure it exists and is accessible.');
    return { name: 'robots.txt AI Bots', score: 0, max: 15, icon: '🤖', details: `Fetch error: ${err.message}`, recommendations };
  }

  // Parse robots.txt to find disallow rules per bot
  const lines = robotsText.split('\n').map(l => l.trim());
  const botStatus = {};

  // Check global disallow first
  let currentAgent = null;
  let globalDisallowAll = false;
  const agentRules = {}; // agent -> { disallowAll: bool }

  for (const line of lines) {
    if (line.toLowerCase().startsWith('user-agent:')) {
      currentAgent = line.substring('user-agent:'.length).trim();
      if (!agentRules[currentAgent]) agentRules[currentAgent] = { disallowAll: false };
    } else if (line.toLowerCase().startsWith('disallow:')) {
      const path = line.substring('disallow:'.length).trim();
      if (path === '/' && currentAgent) {
        agentRules[currentAgent].disallowAll = true;
      }
    }
  }

  const wildcardBlock = agentRules['*'] && agentRules['*'].disallowAll;

  for (const bot of bots) {
    const botBlocked = (agentRules[bot] && agentRules[bot].disallowAll) || (wildcardBlock && !(agentRules[bot]));
    const mentioned = robotsText.toLowerCase().includes(bot.toLowerCase());

    if (botBlocked) {
      details.push(`${bot}: ❌ blocked`);
      recommendations.push(`${bot} is blocked in robots.txt. AI indexers can't crawl your content — remove the Disallow: / rule for ${bot}.`);
    } else if (mentioned) {
      score += 4; // explicitly allowed
      details.push(`${bot}: ✅ allowed`);
    } else {
      // Not mentioned — inherits wildcard. If wildcard blocks, bot is blocked.
      if (wildcardBlock) {
        score += 0;
        details.push(`${bot}: ⚠️ blocked by wildcard`);
      } else {
        score += 2; // not mentioned, not blocked — partial credit
        details.push(`${bot}: ⚠️ not explicitly listed`);
        recommendations.push(`Explicitly allow ${bot} in robots.txt for clarity and max indexation by AI crawlers.`);
      }
    }
  }

  score = Math.min(score, 15);

  return {
    name: 'robots.txt AI Bots',
    score,
    max: 15,
    icon: '🤖',
    details: details.join(' · '),
    recommendations,
  };
}

// ─── Check 3: llms.txt (0-15pts) ─────────────────────────────────────────────
async function checkLlmsTxt(baseUrl) {
  const recommendations = [];
  let score = 0;
  let details = '';

  try {
    const res = await fetchWithTimeout(`${baseUrl}/llms.txt`);
    if (res.ok) {
      const text = await res.text();
      const length = text.trim().length;

      if (length > 500) {
        score = 15;
        details = `llms.txt exists (${length} chars) — comprehensive`;
      } else if (length > 100) {
        score = 10;
        details = `llms.txt exists (${length} chars) — could be expanded`;
        recommendations.push('Your llms.txt exists but is short. Add more context: product description, key features, use cases, links to key pages. Target 500+ chars.');
      } else if (length > 0) {
        score = 5;
        details = `llms.txt exists but minimal (${length} chars)`;
        recommendations.push('Your llms.txt exists but is nearly empty. Fill it with structured context for AI agents: what your product does, who it\'s for, key capabilities.');
      }
    } else if (res.status === 404) {
      score = 0;
      details = 'No llms.txt found (404)';
      recommendations.push('Create /llms.txt — the emerging standard for AI agent context. Include: company description, product features, key URLs, use cases, and contact info for AI access.');
    } else {
      details = `HTTP ${res.status}`;
      recommendations.push(`llms.txt returned HTTP ${res.status}. Fix the endpoint to return a 200 with your AI context.`);
    }
  } catch (err) {
    details = `Could not fetch llms.txt`;
    recommendations.push('Create /llms.txt with context about your product for AI agents to consume.');
  }

  return {
    name: 'llms.txt',
    score,
    max: 15,
    icon: '📄',
    details,
    recommendations,
  };
}

// ─── Check 4: Content Structure (0-20pts) ────────────────────────────────────
async function checkContentStructure(url, html) {
  let score = 0;
  const details = [];
  const recommendations = [];

  const $ = cheerio.load(html);

  // H1 check (up to 5pts)
  const h1s = $('h1');
  if (h1s.length === 1) {
    score += 5;
    details.push(`H1: ✅ (1)`);
  } else if (h1s.length > 1) {
    score += 2;
    details.push(`H1: ⚠️ (${h1s.length} — should be 1)`);
    recommendations.push(`You have ${h1s.length} H1 tags. Use exactly one H1 per page — AI agents treat it as the primary topic signal.`);
  } else {
    details.push('H1: ❌ missing');
    recommendations.push('Add a single H1 tag that clearly describes the page topic. AI agents use it as the primary content anchor.');
  }

  // H2/H3 structure (up to 5pts)
  const h2s = $('h2').length;
  const h3s = $('h3').length;
  if (h2s >= 3) {
    score += 5;
    details.push(`H2-H3: ✅ (${h2s}×H2, ${h3s}×H3)`);
  } else if (h2s >= 1) {
    score += 3;
    details.push(`H2-H3: (${h2s}×H2, ${h3s}×H3)`);
    recommendations.push('Add more H2 sections to create clear content hierarchy. AI agents use heading structure to extract topic clusters.');
  } else {
    details.push('H2: ❌ none');
    recommendations.push('Structure your content with H2/H3 headings. This dramatically improves AI understanding and featured snippet potential.');
  }

  // FAQPage schema (up to 5pts)
  const jsonldScripts = $('script[type="application/ld+json"]');
  let hasFaq = false;
  let hasHowTo = false;
  jsonldScripts.each((_, el) => {
    try {
      const data = JSON.parse($(el).html());
      const types = [].concat(data['@type'] || []);
      if (types.includes('FAQPage')) hasFaq = true;
      if (types.includes('HowTo')) hasHowTo = true;
    } catch {}
  });

  if (hasFaq) {
    score += 5;
    details.push('FAQPage: ✅');
  } else {
    recommendations.push('Add FAQPage JSON-LD schema. AI answer engines heavily favor pages with structured Q&A — it\'s the fastest path to being quoted directly.');
  }

  if (hasHowTo) {
    score += 5;
    details.push('HowTo: ✅');
  } else {
    recommendations.push('Consider adding HowTo JSON-LD schema for step-by-step content. AI agents love procedural structure.');
  }

  score = Math.min(score, 20);

  return {
    name: 'Content Structure',
    score,
    max: 20,
    icon: '🏗️',
    details: details.join(' · '),
    recommendations,
  };
}

// ─── Check 5: Tool/API Description (0-15pts) ─────────────────────────────────
async function checkToolApiDescription(baseUrl, html) {
  let score = 0;
  const details = [];
  const recommendations = [];

  // Check /.well-known/ai-plugin.json
  let hasAiPlugin = false;
  try {
    const res = await fetchWithTimeout(`${baseUrl}/.well-known/ai-plugin.json`);
    if (res.ok) {
      hasAiPlugin = true;
      score += 7;
      details.push('ai-plugin.json: ✅');
    }
  } catch {}
  if (!hasAiPlugin) {
    details.push('ai-plugin.json: ❌');
    recommendations.push('Create /.well-known/ai-plugin.json — the standard manifest for AI tools/plugins. Enables ChatGPT plugins, Copilot integrations, and MCP discovery.');
  }

  // Check /openapi.json or /openapi.yaml or /api-docs
  let hasOpenApi = false;
  for (const path of ['/openapi.json', '/openapi.yaml', '/api-docs', '/swagger.json']) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`);
      if (res.ok) {
        hasOpenApi = true;
        score += 5;
        details.push(`OpenAPI (${path}): ✅`);
        break;
      }
    } catch {}
  }
  if (!hasOpenApi) {
    details.push('OpenAPI: ❌');
    recommendations.push('Publish an OpenAPI spec at /openapi.json. AI agents use it to understand your API capabilities and auto-integrate.');
  }

  // Check for MCP/API hints in HTML
  const $ = cheerio.load(html);
  const bodyText = $('body').text().toLowerCase();
  const hasMcpHints = bodyText.includes('mcp') || bodyText.includes('model context protocol') || bodyText.includes('ai agent') || bodyText.includes('api endpoint');
  const hasApiLink = $('a[href*="api"], a[href*="docs"], a[href*="developer"]').length > 0;

  if (hasMcpHints || hasApiLink) {
    score += 3;
    details.push('API/MCP mentions: ✅');
  } else {
    recommendations.push('Link to your API docs from your homepage. AI agents scan for API indicators to understand tool capabilities.');
  }

  score = Math.min(score, 15);

  return {
    name: 'Tool/API Description',
    score,
    max: 15,
    icon: '🔌',
    details: details.join(' · '),
    recommendations,
  };
}

// ─── Check 6: Performance (0-15pts) ──────────────────────────────────────────
async function checkPerformance(url) {
  const details = [];
  const recommendations = [];
  let score = 0;
  let responseTime = null;

  try {
    const start = Date.now();
    const res = await fetchWithTimeout(url, {});
    await res.text(); // consume body
    responseTime = Date.now() - start;

    if (responseTime < 1000) {
      score = 15;
      details.push(`Response: ${responseTime}ms ⚡ (<1s)`);
    } else if (responseTime < 2000) {
      score = 10;
      details.push(`Response: ${responseTime}ms ✅ (<2s)`);
    } else if (responseTime < 3000) {
      score = 5;
      details.push(`Response: ${responseTime}ms ⚠️ (<3s)`);
      recommendations.push(`Response time ${responseTime}ms is borderline. AI agents timeout fast — aim for <1s with caching and CDN.`);
    } else {
      score = 0;
      details.push(`Response: ${responseTime}ms 🐌 (>3s)`);
      recommendations.push(`Response time ${responseTime}ms is too slow. AI agents (and users) abandon slow pages. Optimize: use CDN, enable caching, reduce TTFB.`);
    }
  } catch (err) {
    details.push(`Error: ${err.message}`);
    recommendations.push('Page failed to load. Fix connectivity/uptime issues first — AI crawlers skip unreachable pages entirely.');
  }

  return {
    name: 'Performance',
    score,
    max: 15,
    icon: '⚡',
    details: details.join(' · '),
    recommendations,
    responseTime,
  };
}

// ─── POST /api/check ──────────────────────────────────────────────────────────
app.post('/api/check', async (req, res) => {
  let { url } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'url is required' });
  }

  // Normalize URL
  if (!/^https?:\/\//i.test(url)) {
    url = 'https://' + url;
  }

  let baseUrl;
  try {
    const parsed = new URL(url);
    baseUrl = `${parsed.protocol}//${parsed.host}`;
  } catch {
    return res.status(400).json({ error: 'Invalid URL' });
  }

  // Fetch main HTML once (reuse for multiple checks)
  let html = '';
  let fetchError = null;
  try {
    const res2 = await fetchWithTimeout(url);
    html = await res2.text();
  } catch (err) {
    fetchError = err.message;
  }

  const results = await Promise.allSettled([
    checkStructuredData(url, html),
    checkRobotsTxt(baseUrl),
    checkLlmsTxt(baseUrl),
    checkContentStructure(url, html),
    checkToolApiDescription(baseUrl, html),
    checkPerformance(url),
  ]);

  const checks = results.map((r, i) => {
    if (r.status === 'fulfilled') return r.value;
    return {
      name: ['Structured Data', 'robots.txt AI Bots', 'llms.txt', 'Content Structure', 'Tool/API Description', 'Performance'][i],
      score: 0,
      max: [20, 15, 15, 20, 15, 15][i],
      icon: ['🧱', '🤖', '📄', '🏗️', '🔌', '⚡'][i],
      details: `Error: ${r.reason?.message || 'Unknown'}`,
      recommendations: ['An error occurred during this check.'],
    };
  });

  const totalScore = checks.reduce((sum, c) => sum + c.score, 0);
  const maxScore = checks.reduce((sum, c) => sum + c.max, 0);

  // Grade
  let grade, gradeColor;
  if (totalScore >= 80) { grade = 'Excellent'; gradeColor = '#22c55e'; }
  else if (totalScore >= 60) { grade = 'Good'; gradeColor = '#84cc16'; }
  else if (totalScore >= 40) { grade = 'Fair'; gradeColor = '#eab308'; }
  else if (totalScore >= 20) { grade = 'Poor'; gradeColor = '#f97316'; }
  else { grade = 'Critical'; gradeColor = '#ef4444'; }

  res.json({
    url,
    baseUrl,
    totalScore,
    maxScore,
    grade,
    gradeColor,
    fetchError,
    checks,
    scannedAt: new Date().toISOString(),
  });
});

// ─── GET /api/badge/:score ────────────────────────────────────────────────────
app.get('/api/badge/:score', (req, res) => {
  const score = Math.max(0, Math.min(100, parseInt(req.params.score) || 0));

  let color;
  if (score >= 80) color = '#22c55e';
  else if (score >= 60) color = '#84cc16';
  else if (score >= 40) color = '#eab308';
  else if (score >= 20) color = '#f97316';
  else color = '#ef4444';

  const label = 'AEO Score';
  const value = `${score}/100`;
  const labelWidth = 80;
  const valueWidth = 60;
  const totalWidth = labelWidth + valueWidth;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${totalWidth}" height="20" role="img">
  <title>${label}: ${value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="${totalWidth}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="${labelWidth}" height="20" fill="#555"/>
    <rect x="${labelWidth}" width="${valueWidth}" height="20" fill="${color}"/>
    <rect width="${totalWidth}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="${labelWidth / 2}" y="15" fill="#010101" fill-opacity=".3">${label}</text>
    <text x="${labelWidth / 2}" y="14">${label}</text>
    <text x="${labelWidth + valueWidth / 2}" y="15" fill="#010101" fill-opacity=".3">${value}</text>
    <text x="${labelWidth + valueWidth / 2}" y="14">${value}</text>
  </g>
</svg>`;

  res.setHeader('Content-Type', 'image/svg+xml');
  res.setHeader('Cache-Control', 'public, max-age=3600');
  res.send(svg);
});

// ─── Start server ─────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 AEO Checker running at http://localhost:${PORT}`);
});
