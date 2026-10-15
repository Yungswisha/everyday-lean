"""Find recipes with the Brave Search API and save them to discover.json.

Each search in discover-queries.txt is run through Brave; every result page is
fetched and its schema.org Recipe data (which most recipe sites publish) is
converted to TheMealDB's format, so the app's existing importer can use it.

Needs the BRAVE_API_KEY environment variable (a GitHub Actions secret).
Usage: python scripts/discover_recipes.py [--test-url URL]
"""
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), '..')
OUT = os.path.join(ROOT, 'discover.json')
QUERIES = os.path.join(ROOT, 'discover-queries.txt')
KEEP = 150            # newest recipes kept in discover.json
PER_QUERY = 10        # Brave results checked per search
UA = 'Mozilla/5.0 (compatible; EverydayLeanRecipeBot/1.0; personal meal planner)'

UNITS = (r'kg|kilograms?|g|grams?|ml|millilit(?:re|er)s?|l|lit(?:re|er)s?|tbsp|tablespoons?|tsp|teaspoons?'
         r'|pounds?|lbs?|ounces?|oz|cups?|cloves?|pieces?|whole|eggs?|cans?|tins?|bunch(?:es)?|handfuls?|pinch(?:es)?|slices?')
QTY = r'(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?|[½¼¾⅓⅔])(?:\s*[-–]\s*\d+(?:\.\d+)?)?'
MEASURE = re.compile(rf'^\s*({QTY})\s*({UNITS})?\.?\b\s*(?:of\s+)?(.*)$', re.I)


def brave(query, key):
    url = 'https://api.search.brave.com/res/v1/web/search?' + urllib.parse.urlencode(
        {'q': query, 'country': 'AU', 'search_lang': 'en', 'count': PER_QUERY, 'safesearch': 'strict'})
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'X-Subscription-Token': key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get('web', {}).get('results', [])


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(3_000_000).decode('utf8', 'replace')


def find_recipe(node):
    """Depth-first search of JSON-LD for an object whose @type includes Recipe."""
    if isinstance(node, list):
        for n in node:
            r = find_recipe(n)
            if r:
                return r
    elif isinstance(node, dict):
        t = node.get('@type')
        if t == 'Recipe' or (isinstance(t, list) and 'Recipe' in t):
            return node
        for k in ('@graph', 'mainEntity', 'itemListElement'):
            if k in node:
                r = find_recipe(node[k])
                if r:
                    return r
    return None


def text(v):
    if isinstance(v, list):
        v = v[0] if v else ''
    if isinstance(v, dict):
        v = v.get('url') or v.get('text') or v.get('name') or ''
    return html.unescape(re.sub(r'<[^>]+>', ' ', str(v or ''))).strip()


def steps(instr):
    out = []
    if isinstance(instr, str):
        out = [s for s in re.split(r'\r?\n+|(?<=\.)\s{2,}', html.unescape(re.sub(r'<[^>]+>', '\n', instr)))]
    elif isinstance(instr, list):
        for s in instr:
            if isinstance(s, dict) and s.get('@type') == 'HowToSection':
                out += steps(s.get('itemListElement', []))
            else:
                out.append(text(s))
    return [re.sub(r'\s+', ' ', s).strip() for s in out if s and s.strip()]


def to_number(qty):
    """'1 1/2' -> 1.5, '1/2' -> 0.5, '½' -> 0.5; ranges like '2-3' -> None."""
    qty = qty.replace('½', '1/2').replace('¼', '1/4').replace('¾', '3/4').replace('⅓', '1/3').replace('⅔', '2/3')
    if re.search(r'[-–]', qty):
        return None
    total = 0.0
    for part in qty.split():
        a, _, b = part.partition('/')
        total += float(a) / float(b) if b else float(a)
    return total


def split_ingredient(line):
    """'500g turkey mince' -> ('500g', 'turkey mince'); '2 cloves garlic, crushed' -> ('2 cloves', 'garlic')."""
    line = re.sub(r'\s+', ' ', html.unescape(line)).strip()
    prev = None
    while prev != line:  # drop notes like '(6oz)', innermost brackets first
        prev, line = line, re.sub(r'\s*\([^()]*\)', '', line)
    line = re.sub(r'[()]', '', line).strip()
    m = MEASURE.match(line)
    if not m:
        return '', line
    qty, unit, rest = m.group(1), m.group(2) or '', m.group(3)
    name = re.split(r',|\(|\bto serve\b', rest)[0].strip() or rest.strip()
    if re.fullmatch(r'pounds?|lbs?|ounces?|oz', unit, re.I):  # imperial -> grams
        amount = to_number(qty)
        if amount:
            grams = 453.6 if unit.lower()[0] in 'pl' else 28.35
            return f'{round(amount * grams)}g', name
    return f'{qty}{unit if unit.lower() in ("g", "kg", "ml", "l") else (" " + unit if unit else "")}'.strip(), name


def category(r):
    c = ' '.join(text(x) for x in (r.get('recipeCategory') if isinstance(r.get('recipeCategory'), list)
                                   else [r.get('recipeCategory')])).lower()
    return 'Breakfast' if 'breakfast' in c or 'brunch' in c else 'Dinner'


def to_meal(r, url, query):
    host = urllib.parse.urlparse(url).netloc.removeprefix('www.')
    meal = {
        'idDiscover': url, 'strMeal': text(r.get('name')) or 'Online recipe', 'strSource': url,
        'strMealThumb': text(r.get('image')), 'strCategory': category(r), 'strArea': host,
        'strInstructions': '\n'.join(steps(r.get('recipeInstructions'))),
        'site': host, 'query': query, 'description': text(r.get('description'))[:300],
        'serves': text(r.get('recipeYield')), 'totalTime': text(r.get('totalTime')),
    }
    ings = [text(i) for i in (r.get('recipeIngredient') or r.get('ingredients') or [])][:20]
    for j, line in enumerate(ings, 1):
        meal[f'strMeasure{j}'], meal[f'strIngredient{j}'] = split_ingredient(line)
    nut = r.get('nutrition') or {}
    if isinstance(nut, dict):
        meal['nutrition'] = {k: text(nut[k]) for k in ('calories', 'proteinContent', 'carbohydrateContent', 'fatContent') if nut.get(k)}
    return meal if ings and meal['strInstructions'] else None


def recipe_from_page(url, query=''):
    page = fetch(url)
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            r = find_recipe(json.loads(block.strip()))
        except ValueError:
            continue
        if r:
            return to_meal(r, url, query)
    return None


def main():
    if '--test-url' in sys.argv:
        print(json.dumps(recipe_from_page(sys.argv[sys.argv.index('--test-url') + 1]), indent=1, ensure_ascii=False))
        return
    key = os.environ.get('BRAVE_API_KEY')
    if not key:
        print('BRAVE_API_KEY is not set; skipping recipe discovery.')
        return
    queries = [q.strip() for q in open(QUERIES, encoding='utf8') if q.strip() and not q.startswith('#')]
    try:
        existing = json.load(open(OUT, encoding='utf8')).get('recipes', [])
    except (OSError, ValueError):
        existing = []
    seen = {m['strSource'] for m in existing}
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    found = []
    for q in queries:
        try:
            results = brave(q, key)
        except Exception as e:
            print(f'Brave search failed for {q!r}: {e}')
            continue
        added = 0
        for res in results:
            url = res.get('url', '')
            if not url.startswith('http') or url in seen:
                continue
            seen.add(url)
            try:
                meal = recipe_from_page(url, q)
            except Exception as e:
                print(f'  skip {url}: {type(e).__name__}')
                continue
            if meal:
                meal['strMealThumb'] = meal['strMealThumb'] or (res.get('thumbnail') or {}).get('src', '')
                meal['foundAt'] = now
                found.append(meal)
                added += 1
        print(f'{q!r}: {len(results)} results, {added} new recipes')
        time.sleep(1.1)  # Brave free plan allows 1 request per second
    recipes = (found + existing)[:KEEP]
    with open(OUT, 'w', encoding='utf8') as fh:
        json.dump({'version': 1, 'updatedAt': now, 'queries': queries, 'recipes': recipes}, fh, ensure_ascii=False, indent=1)
    print(f'Saved {len(recipes)} recipes ({len(found)} new) to discover.json')


if __name__ == '__main__':
    main()
