const cheerio = require('cheerio');
const fetch = require('node-fetch');

const USER_AGENT = 'AEOChecker/1.0 (AI Discoverability Scanner)';
const FETCH_TIMEOUT = 8000;

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

  const jsonldScripts = $('script[type="application/ld+json"]');
  const jsonldCount = jsonldScripts.length;
  if (jsonldCount > 0) {
    score += 10;
    details.push(`${jsonldCount} JSON-LD schema(s) found`);
    let richTypes = [];
    jsonldScripts.each((_, el) => {
      try {
        const data = JSON.parse($(el).html());
        const types = [].concat(data['@type'] || []);
        richTypes = richTypes.concat(types);
      } catch {}
    });
    if (richTypes.length > 0) details.push(`Types: ${richTypes.slice(0, 5).join(', ')}`);
  } else {
    recommendations.push('Add JSON-LD structured data (Schema.org). AI agents rely on it to understand your content type and extract key facts.');
  }

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

  return { name: 'Structured Data', score: Math.min(score, 20), max: 20, icon: '🧱', details: details.join(' · '), recommendations };
}

// ─── Check 2: robots.txt AI Bots (0-15pts) ───────────────────────────────────
async function checkRobotsTxt(baseUrl) {
  const bots = ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended'];
  let score = 0;
  const details = [];
  const recommendations = [];
  let robotsText = '';

  try {
    const res = await fetchWithTimeout(`${baseUrl}/robots.txt`);
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

  const lines = robotsText.split('\n').map(l => l.trim());
  let currentAgent = null;
  const agentRules = {};

  for (const line of lines) {
    if (line.toLowerCase().startsWith('user-agent:')) {
      currentAgent = line.substring('user-agent:'.length).trim();
      if (!agentRules[currentAgent]) agentRules[currentAgent] = { disallowAll: false };
    } else if (line.toLowerCase().startsWith('disallow:')) {
      const path = line.substring('disallow:'.length).trim();
      if (path === '/' && currentAgent) agentRules[currentAgent].disallowAll = true;
    }
  }

  const wildcardBlock = agentRules['*'] && agentRules['*'].disallowAll;

  for (const bot of bots) {
    const botBlocked = (agentRules[bot] && agentRules[bot].disallowAll) || (wildcardBlock && !(agentRules[bot]));
    const mentioned = robotsText.toLowerCase().includes(bot.toLowerCase());

    if (botBlocked) {
      details.push(`${bot}: ❌ blocked`);
      recommendations.push(`${bot} is blocked in robots.txt. Remove the Disallow: / rule for ${bot}.`);
    } else if (mentioned) {
      score += 4;
      details.push(`${bot}: ✅ allowed`);
    } else {
      if (wildcardBlock) {
        details.push(`${bot}: ⚠️ blocked by wildcard`);
      } else {
        score += 2;
        details.push(`${bot}: ⚠️ not explicitly listed`);
        recommendations.push(`Explicitly allow ${bot} in robots.txt for max indexation by AI crawlers.`);
      }
    }
  }

  return { name: 'robots.txt AI Bots', score: Math.min(score, 15), max: 15, icon: '🤖', details: details.join(' · '), recommendations };
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
      if (length > 500) { score = 15; details = `llms.txt exists (${length} chars) — comprehensive`; }
      else if (length > 100) { score = 10; details = `llms.txt exists (${length} chars) — could be expanded`; recommendations.push('Your llms.txt exists but is short. Add more context: product description, key features, use cases. Target 500+ chars.'); }
      else if (length > 0) { score = 5; details = `llms.txt exists but minimal (${length} chars)`; recommendations.push('Your llms.txt is nearly empty. Fill it with structured context for AI agents.'); }
    } else if (res.status === 404) {
      details = 'No llms.txt found (404)';
      recommendations.push('Create /llms.txt — the emerging standard for AI agent context. Include: company description, product features, key URLs, use cases.');
    } else {
      details = `HTTP ${res.status}`;
      recommendations.push(`llms.txt returned HTTP ${res.status}. Fix the endpoint to return a 200.`);
    }
  } catch {
    details = 'Could not fetch llms.txt';
    recommendations.push('Create /llms.txt with context about your product for AI agents.');
  }

  return { name: 'llms.txt', score, max: 15, icon: '📄', details, recommendations };
}

// ─── Check 4: Content Structure (0-20pts) ────────────────────────────────────
async function checkContentStructure(url, html) {
  let score = 0;
  const details = [];
  const recommendations = [];
  const $ = cheerio.load(html);

  const h1s = $('h1');
  if (h1s.length === 1) { score += 5; details.push('H1: ✅ (1)'); }
  else if (h1s.length > 1) { score += 2; details.push(`H1: ⚠️ (${h1s.length})`); recommendations.push(`You have ${h1s.length} H1 tags. Use exactly one H1 per page.`); }
  else { details.push('H1: ❌ missing'); recommendations.push('Add a single H1 tag that clearly describes the page topic.'); }

  const h2s = $('h2').length;
  const h3s = $('h3').length;
  if (h2s >= 3) { score += 5; details.push(`H2-H3: ✅ (${h2s}×H2, ${h3s}×H3)`); }
  else if (h2s >= 1) { score += 3; details.push(`H2-H3: (${h2s}×H2, ${h3s}×H3)`); recommendations.push('Add more H2 sections for clear content hierarchy.'); }
  else { details.push('H2: ❌ none'); recommendations.push('Structure your content with H2/H3 headings for AI understanding.'); }

  const jsonldScripts = $('script[type="application/ld+json"]');
  let hasFaq = false, hasHowTo = false;
  jsonldScripts.each((_, el) => {
    try {
      const data = JSON.parse($(el).html());
      const types = [].concat(data['@type'] || []);
      if (types.includes('FAQPage')) hasFaq = true;
      if (types.includes('HowTo')) hasHowTo = true;
    } catch {}
  });

  if (hasFaq) { score += 5; details.push('FAQPage: ✅'); }
  else { recommendations.push('Add FAQPage JSON-LD schema. AI answer engines heavily favor structured Q&A.'); }
  if (hasHowTo) { score += 5; details.push('HowTo: ✅'); }
  else { recommendations.push('Consider adding HowTo JSON-LD schema for step-by-step content.'); }

  return { name: 'Content Structure', score: Math.min(score, 20), max: 20, icon: '🏗️', details: details.join(' · '), recommendations };
}

// ─── Check 5: Tool/API Description (0-15pts) ─────────────────────────────────
async function checkToolApiDescription(baseUrl, html) {
  let score = 0;
  const details = [];
  const recommendations = [];

  let hasAiPlugin = false;
  try {
    const res = await fetchWithTimeout(`${baseUrl}/.well-known/ai-plugin.json`);
    if (res.ok) { hasAiPlugin = true; score += 7; details.push('ai-plugin.json: ✅'); }
  } catch {}
  if (!hasAiPlugin) {
    details.push('ai-plugin.json: ❌');
    recommendations.push('Create /.well-known/ai-plugin.json — the standard manifest for AI tools/plugins.');
  }

  let hasOpenApi = false;
  for (const p of ['/openapi.json', '/openapi.yaml', '/api-docs', '/swagger.json']) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${p}`);
      if (res.ok) { hasOpenApi = true; score += 5; details.push(`OpenAPI (${p}): ✅`); break; }
    } catch {}
  }
  if (!hasOpenApi) {
    details.push('OpenAPI: ❌');
    recommendations.push('Publish an OpenAPI spec at /openapi.json for AI auto-integration.');
  }

  const $ = cheerio.load(html);
  const bodyText = $('body').text().toLowerCase();
  const hasMcpHints = bodyText.includes('mcp') || bodyText.includes('model context protocol') || bodyText.includes('ai agent') || bodyText.includes('api endpoint');
  const hasApiLink = $('a[href*="api"], a[href*="docs"], a[href*="developer"]').length > 0;
  if (hasMcpHints || hasApiLink) { score += 3; details.push('API/MCP mentions: ✅'); }
  else { recommendations.push('Link to your API docs from your homepage.'); }

  return { name: 'Tool/API Description', score: Math.min(score, 15), max: 15, icon: '🔌', details: details.join(' · '), recommendations };
}

// ─── Check 6: Performance (0-15pts) ──────────────────────────────────────────
async function checkPerformance(url) {
  const details = [];
  const recommendations = [];
  let score = 0;

  try {
    const start = Date.now();
    const res = await fetchWithTimeout(url, {});
    await res.text();
    const responseTime = Date.now() - start;

    if (responseTime < 1000) { score = 15; details.push(`Response: ${responseTime}ms ⚡ (<1s)`); }
    else if (responseTime < 2000) { score = 10; details.push(`Response: ${responseTime}ms ✅ (<2s)`); }
    else if (responseTime < 3000) { score = 5; details.push(`Response: ${responseTime}ms ⚠️ (<3s)`); recommendations.push(`Response time ${responseTime}ms is borderline. Aim for <1s.`); }
    else { details.push(`Response: ${responseTime}ms 🐌 (>3s)`); recommendations.push(`Response time ${responseTime}ms is too slow. Use CDN, caching.`); }
  } catch (err) {
    details.push(`Error: ${err.message}`);
    recommendations.push('Page failed to load. Fix connectivity issues first.');
  }

  return { name: 'Performance', score, max: 15, icon: '⚡', details: details.join(' · '), recommendations };
}

// ─── Check 7: Markdown for Agents (0-10pts) ──────────────────────────────────
async function checkMarkdownForAgents(baseUrl, url) {
  let score = 0;
  const details = [];
  const recommendations = [];

  // Test 1: Accept: text/markdown content negotiation (Cloudflare-style)
  let markdownNegotiation = false;
  try {
    const res = await fetchWithTimeout(url, {
      headers: {
        'Accept': 'text/markdown',
      },
    });
    const ct = (res.headers.get('content-type') || '').toLowerCase();
    if (ct.includes('text/markdown') || ct.includes('text/x-markdown')) {
      markdownNegotiation = true;
      score += 5;
      details.push('Markdown content negotiation: ✅');
    } else {
      details.push('Markdown content negotiation: ❌');
    }
  } catch {
    details.push('Markdown content negotiation: ❌ (fetch error)');
  }

  // Test 2: /crawl endpoint (Cloudflare docs-style)
  let hasCrawlEndpoint = false;
  try {
    const res = await fetchWithTimeout(`${baseUrl}/crawl`, {
      headers: { 'Accept': 'text/markdown' },
    });
    if (res.ok) {
      const ct = (res.headers.get('content-type') || '').toLowerCase();
      const text = await res.text();
      if ((ct.includes('text/markdown') || ct.includes('text/plain')) && text.length > 50) {
        hasCrawlEndpoint = true;
        score += 3;
        details.push(`/crawl endpoint: ✅ (${text.length} chars)`);
      }
    }
  } catch {}
  if (!hasCrawlEndpoint) {
    details.push('/crawl endpoint: ❌');
  }

  // Test 3: llms-full.txt (extended context for LLMs)
  let hasLlmsFullTxt = false;
  try {
    const res = await fetchWithTimeout(`${baseUrl}/llms-full.txt`);
    if (res.ok) {
      const text = await res.text();
      if (text.trim().length > 100) {
        hasLlmsFullTxt = true;
        score += 2;
        details.push(`llms-full.txt: ✅ (${text.trim().length} chars)`);
      }
    }
  } catch {}
  if (!hasLlmsFullTxt) {
    details.push('llms-full.txt: ❌');
  }

  // Recommendations
  if (!markdownNegotiation) {
    recommendations.push('Support Accept: text/markdown content negotiation. When AI crawlers request markdown, serve a clean markdown version of your page. Cloudflare recently enabled this — it\'s becoming a standard.');
  }
  if (!hasCrawlEndpoint) {
    recommendations.push('Consider adding a /crawl endpoint that returns your site content in markdown. This gives AI agents structured, clean content to index.');
  }
  if (!hasLlmsFullTxt) {
    recommendations.push('Create /llms-full.txt with comprehensive product context (expanded version of llms.txt). Useful for deep AI agent understanding.');
  }

  return { name: 'Markdown for Agents', score: Math.min(score, 10), max: 10, icon: '📝', details: details.join(' · '), recommendations };
}

// ─── Handler ──────────────────────────────────────────────────────────────────
exports.handler = async (event) => {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers, body: '' };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON' }) };
  }

  let { url } = body;
  if (!url) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'url is required' }) };
  }

  if (!/^https?:\/\//i.test(url)) url = 'https://' + url;

  let baseUrl;
  try {
    const parsed = new URL(url);
    baseUrl = `${parsed.protocol}//${parsed.host}`;
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid URL' }) };
  }

  let html = '';
  let fetchError = null;
  try {
    const res = await fetchWithTimeout(url);
    html = await res.text();
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
    checkMarkdownForAgents(baseUrl, url),
  ]);

  const checkMeta = [
    { name: 'Structured Data', max: 20, icon: '🧱' },
    { name: 'robots.txt AI Bots', max: 15, icon: '🤖' },
    { name: 'llms.txt', max: 15, icon: '📄' },
    { name: 'Content Structure', max: 20, icon: '🏗️' },
    { name: 'Tool/API Description', max: 15, icon: '🔌' },
    { name: 'Performance', max: 15, icon: '⚡' },
    { name: 'Markdown for Agents', max: 10, icon: '📝' },
  ];

  const checks = results.map((r, i) => {
    if (r.status === 'fulfilled') return r.value;
    return {
      name: checkMeta[i].name,
      score: 0,
      max: checkMeta[i].max,
      icon: checkMeta[i].icon,
      details: `Error: ${r.reason?.message || 'Unknown'}`,
      recommendations: ['An error occurred during this check.'],
    };
  });

  const totalScore = checks.reduce((sum, c) => sum + c.score, 0);
  const maxScore = checks.reduce((sum, c) => sum + c.max, 0);

  const pct = maxScore > 0 ? (totalScore / maxScore) * 100 : 0;
  let grade, gradeColor;
  if (pct >= 80) { grade = 'Excellent'; gradeColor = '#22c55e'; }
  else if (pct >= 60) { grade = 'Good'; gradeColor = '#84cc16'; }
  else if (pct >= 40) { grade = 'Fair'; gradeColor = '#eab308'; }
  else if (pct >= 20) { grade = 'Poor'; gradeColor = '#f97316'; }
  else { grade = 'Critical'; gradeColor = '#ef4444'; }

  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({
      url, baseUrl, totalScore, maxScore, grade, gradeColor, fetchError, checks,
      scannedAt: new Date().toISOString(),
    }),
  };
};
