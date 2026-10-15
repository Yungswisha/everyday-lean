// Everyday Lean recipe search — Cloudflare Worker.
//
// GET /search?q=chicken+curry&offset=0
//   -> { results: [meal, ...], nextOffset: 1 | null }
//
// Searches the web with Brave (English, any country), skips sites whose
// robots.txt disallows us, reads each page's schema.org Recipe data and
// returns it in TheMealDB's shape so the app's importMeal() can use it.
// The Brave key is the BRAVE_API_KEY secret; it never reaches the browser.

const BOT = 'EverydayLeanBot';
const UA = `Mozilla/5.0 (compatible; ${BOT}/1.0; +https://yungswisha.github.io/everyday-lean/)`;
const ALLOWED_ORIGINS = ['https://yungswisha.github.io', 'http://127.0.0.1:8767', 'http://localhost:8767'];
const PER_PAGE = 15; // Brave results per search; each costs 2 subrequests (robots + page)

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const cors = {
      'Access-Control-Allow-Origin': ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
      'Access-Control-Allow-Methods': 'GET',
      Vary: 'Origin',
    };
    if (request.method === 'OPTIONS') return new Response(null, { headers: cors });

    const url = new URL(request.url);
    if (url.pathname !== '/search') return json({ error: 'Use /search?q=' }, 404, cors);
    const q = (url.searchParams.get('q') || '').trim().slice(0, 100);
    const offset = Math.min(Math.max(parseInt(url.searchParams.get('offset') || '0', 10) || 0, 0), 9);
    if (!q) return json({ error: 'Missing search' }, 400, cors);

    const cache = caches.default;
    const cacheKey = new Request(`https://cache.local/search?q=${encodeURIComponent(q.toLowerCase())}&offset=${offset}`);
    const hit = await cache.match(cacheKey);
    if (hit) return withHeaders(hit, cors);

    let web;
    try {
      web = await braveSearch(`${q} recipe`, offset, env.BRAVE_API_KEY);
    } catch (e) {
      return json({ error: 'Search failed: ' + e.message }, 502, cors);
    }
    const settled = await Promise.allSettled(web.results.map(r => recipeFrom(r)));
    const results = settled.filter(s => s.status === 'fulfilled' && s.value).map(s => s.value);
    const body = { results, nextOffset: web.more && offset < 9 ? offset + 1 : null };

    const res = json(body, 200, { 'Cache-Control': 'public, max-age=86400' });
    await cache.put(cacheKey, res.clone());
    return withHeaders(res, cors);
  },
};

function json(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

function withHeaders(res, headers) {
  const r = new Response(res.body, res);
  for (const [k, v] of Object.entries(headers)) r.headers.set(k, v);
  return r;
}

async function braveSearch(query, offset, key) {
  const u = new URL('https://api.search.brave.com/res/v1/web/search');
  u.search = new URLSearchParams({ q: query, search_lang: 'en', ui_lang: 'en-US', count: PER_PAGE, offset, safesearch: 'strict' });
  const r = await fetch(u, { headers: { Accept: 'application/json', 'X-Subscription-Token': key } });
  if (!r.ok) throw new Error('Brave HTTP ' + r.status);
  const d = await r.json();
  const results = (d.web?.results || []).filter(x => /^https?:\/\//.test(x.url) && (!x.language || x.language.startsWith('en')));
  return { results, more: !!d.query?.more_results_available };
}

// ---- robots.txt -----------------------------------------------------------

async function allowedByRobots(pageUrl) {
  const u = new URL(pageUrl);
  let text = '';
  try {
    const r = await fetch(`${u.origin}/robots.txt`, { headers: { 'User-Agent': UA }, cf: { cacheTtl: 86400, cacheEverything: true } });
    if (r.status >= 500) return false; // site unsure: treat as disallowed
    if (!r.ok) return true; // no robots.txt: crawling allowed
    text = await r.text();
  } catch {
    return false;
  }
  // Collect rules for our bot if named, otherwise for '*'.
  const groups = [];
  let current = null;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/#.*/, '').trim();
    const m = line.match(/^([A-Za-z-]+)\s*:\s*(.*)$/);
    if (!m) continue;
    const field = m[1].toLowerCase();
    const value = m[2].trim();
    if (field === 'user-agent') {
      if (!current || current.rules.length) groups.push((current = { agents: [], rules: [] }));
      current.agents.push(value.toLowerCase());
    } else if ((field === 'allow' || field === 'disallow') && current) {
      current.rules.push({ allow: field === 'allow', path: value });
    }
  }
  const mine = groups.filter(g => g.agents.some(a => a !== '*' && BOT.toLowerCase().includes(a)));
  const rules = (mine.length ? mine : groups.filter(g => g.agents.includes('*'))).flatMap(g => g.rules);
  const path = u.pathname + u.search;
  let best = null;
  for (const rule of rules) {
    if (!rule.path) continue; // 'Disallow:' (empty) allows everything
    const re = new RegExp('^' + rule.path.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\\\$$/, '$'));
    if (re.test(path) && (!best || rule.path.length > best.path.length || (rule.path.length === best.path.length && rule.allow))) best = rule;
  }
  return !best || best.allow;
}

// ---- Recipe extraction ----------------------------------------------------

async function recipeFrom(result) {
  if (!(await allowedByRobots(result.url))) return null;
  const r = await fetch(result.url, { headers: { 'User-Agent': UA, Accept: 'text/html', 'Accept-Language': 'en' }, redirect: 'follow' });
  if (!r.ok || !(r.headers.get('content-type') || '').includes('html')) return null;

  // HTMLRewriter streams the page and only hands us the bits we need.
  let lang = '';
  const blocks = []; // text of each <script type="application/ld+json">
  await new HTMLRewriter()
    .on('html', { element(el) { lang = (el.getAttribute('lang') || '').toLowerCase(); } })
    .on('script[type="application/ld+json"]', {
      element() { blocks.push(''); },
      text(t) { blocks[blocks.length - 1] += t.text; },
    })
    .transform(r)
    .arrayBuffer();
  if (lang && !lang.startsWith('en')) return null;

  for (const block of blocks) {
    let recipe;
    try { recipe = findRecipe(JSON.parse(block)); } catch { continue; }
    if (!recipe) continue;
    const inLang = text(recipe.inLanguage).toLowerCase();
    if (inLang && !inLang.startsWith('en')) return null;
    return toMeal(recipe, result.url, result);
  }
  return null;
}

function findRecipe(node) {
  if (Array.isArray(node)) {
    for (const n of node) { const r = findRecipe(n); if (r) return r; }
  } else if (node && typeof node === 'object') {
    const t = node['@type'];
    if (t === 'Recipe' || (Array.isArray(t) && t.includes('Recipe'))) return node;
    for (const k of ['@graph', 'mainEntity', 'itemListElement']) {
      if (k in node) { const r = findRecipe(node[k]); if (r) return r; }
    }
  }
  return null;
}

function decode(s) {
  return s.replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n)).replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCharCode(parseInt(n, 16)))
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#039;|&apos;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ');
}

function text(v) {
  if (Array.isArray(v)) v = v[0] ?? '';
  if (v && typeof v === 'object') v = v.url || v.text || v.name || '';
  return decode(String(v ?? '').replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
}

function steps(instr) {
  if (typeof instr === 'string') return decode(instr.replace(/<[^>]+>/g, '\n')).split(/\r?\n+/).map(s => s.trim()).filter(Boolean);
  if (!Array.isArray(instr)) return [];
  return instr.flatMap(s => (s && s['@type'] === 'HowToSection' ? steps(s.itemListElement || []) : [text(s)])).filter(Boolean);
}

const QTY = String.raw`(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?|[½¼¾⅓⅔])(?:\s*[-–]\s*\d+(?:\.\d+)?)?`;
const UNITS = String.raw`kg|kilograms?|g|grams?|ml|millilit(?:re|er)s?|l|lit(?:re|er)s?|tbsp|tablespoons?|tsp|teaspoons?|pounds?|lbs?|ounces?|oz|cups?|cloves?|pieces?|whole|eggs?|cans?|tins?|bunch(?:es)?|handfuls?|pinch(?:es)?|slices?`;
const MEASURE = new RegExp(String.raw`^\s*(${QTY})\s*(${UNITS})?\.?\b\s*(?:of\s+)?(.*)$`, 'i');

function toNumber(q) {
  q = q.replace('½', '1/2').replace('¼', '1/4').replace('¾', '3/4').replace('⅓', '1/3').replace('⅔', '2/3');
  if (/[-–]/.test(q)) return null;
  return q.split(/\s+/).reduce((t, p) => { const [a, b] = p.split('/'); return t + (b ? +a / +b : +a); }, 0);
}

// '500g turkey mince' -> ['500g', 'turkey mince']; '1 lb beef' -> ['454g', 'beef']
function splitIngredient(line) {
  let s = decode(line).replace(/\s+/g, ' ').trim();
  let prev;
  do { prev = s; s = s.replace(/\s*\([^()]*\)/g, ''); } while (s !== prev); // drop '(6oz)' notes
  s = s.replace(/[()]/g, '').trim();
  const m = s.match(MEASURE);
  if (!m) return ['', s];
  const [, qty, unit = '', rest] = m;
  const name = (rest.split(/,|\bto serve\b/)[0] || rest).trim();
  if (/^(pounds?|lbs?|ounces?|oz)$/i.test(unit)) {
    const n = toNumber(qty);
    if (n) return [`${Math.round(n * (/^[pl]/i.test(unit) ? 453.6 : 28.35))}g`, name];
  }
  const metric = /^(g|kg|ml|l)$/i.test(unit);
  return [`${qty}${metric ? unit : unit ? ' ' + unit : ''}`.trim(), name];
}

function toMeal(r, url, result) {
  const host = new URL(url).hostname.replace(/^www\./, '');
  const cats = [].concat(r.recipeCategory || []).map(text).join(' ').toLowerCase();
  const meal = {
    strMeal: text(r.name) || result.title || 'Online recipe',
    strSource: url,
    strMealThumb: text(r.image) || result.thumbnail?.src || '',
    strCategory: /breakfast|brunch/.test(cats) ? 'Breakfast' : 'Dinner',
    strArea: host,
    strInstructions: steps(r.recipeInstructions).join('\n'),
    site: host,
    totalTime: text(r.totalTime).replace(/^PT/i, '').toLowerCase(),
    serves: text(r.recipeYield),
  };
  const ings = [].concat(r.recipeIngredient || r.ingredients || []).map(text).filter(Boolean).slice(0, 20);
  ings.forEach((line, i) => { [meal[`strMeasure${i + 1}`], meal[`strIngredient${i + 1}`]] = splitIngredient(line); });
  return ings.length && meal.strInstructions ? meal : null;
}
