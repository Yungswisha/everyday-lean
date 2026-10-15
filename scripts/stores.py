"""Product search for Woolworths, Coles and IGA.

Each search returns a list of dicts:
  {name, price, size, unit_price, unit_basis, dept}
where unit_price is AUD per unit_basis ('100g', '100ml' or 'each') when the
store reports one, otherwise None. dept is the store's department/category
text in lowercase ('' if unknown).
"""
import json
import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/128.0 Safari/537.36')

# IGA prices differ by store; 52511 is the default online store.
IGA_STORE = '52511'


def _opener():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    op.addheaders = [('User-Agent', UA), ('Accept-Language', 'en-AU,en;q=0.9')]
    return op


def _get(op, url, data=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with op.open(req, timeout=timeout) as r:
        return r.read().decode('utf8', 'replace')


def normalise_unit(price, qty, unit):
    """Convert 'price per qty unit' to (price, basis) with basis 100g/100ml/each."""
    if price is None or not qty:
        return None, None
    u = (unit or '').strip().lower()
    if u in ('kg', 'kilogram'):
        return price / (qty * 10), '100g'
    if u in ('g', 'gm', 'gram'):
        return price / qty * 100, '100g'
    if u in ('l', 'litre', 'liter', 'lt'):
        return price / (qty * 10), '100ml'
    if u in ('ml', 'millilitre'):
        return price / qty * 100, '100ml'
    if u in ('ea', 'each', 'unit', 'pack', 'piece'):
        return price / qty, 'each'
    return None, None


def _parse_measure(text):
    """'1KG' -> (1, 'kg'); '100G' -> (100, 'g'); '1EA' -> (1, 'ea')."""
    m = re.match(r'\s*([\d.]+)\s*([a-zA-Z]+)', text or '')
    return (float(m.group(1)), m.group(2)) if m else (None, None)


class Blocked(Exception):
    """The store served a bot-check page; stop querying it for this run."""


class Woolworths:
    id = 'woolworths'
    delay = 0.6

    def __init__(self):
        self.op = _opener()
        _get(self.op, 'https://www.woolworths.com.au/')  # sets session cookies

    def search(self, query, n=12):
        body = json.dumps({
            'SearchTerm': query, 'PageSize': n, 'PageNumber': 1,
            'SortType': 'TraderRelevance',
            'Location': '/shop/search/products?searchTerm=' + urllib.parse.quote(query),
        }).encode()
        d = json.loads(_get(self.op, 'https://www.woolworths.com.au/apis/ui/Search/products',
                            data=body, headers={'Content-Type': 'application/json'}))
        out = []
        for group in d.get('Products') or []:
            for p in group.get('Products') or []:
                if not p.get('IsAvailable', True) or p.get('Price') is None:
                    continue
                qty, unit = _parse_measure(p.get('CupMeasure'))
                up, basis = normalise_unit(p.get('CupPrice'), qty, unit) if p.get('HasCupPrice') else (None, None)
                attrs = p.get('AdditionalAttributes') or {}
                dept = f"{attrs.get('piesdepartmentnamesjson') or ''} {attrs.get('sapdepartmentname') or ''}"
                out.append({'name': p.get('DisplayName') or p.get('Name'), 'price': p['Price'],
                            'size': p.get('PackageSize'), 'unit_price': up, 'unit_basis': basis,
                            'dept': dept.lower()})
        return out


class Coles:
    id = 'coles'
    delay = 10  # Coles rate-limits hard; go slowly

    def __init__(self):
        self.op = _opener()

    def search(self, query, n=12):
        html = _get(self.op, 'https://www.coles.com.au/search/products?q=' + urllib.parse.quote(query))
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            if 'Pardon Our Interruption' in html or 'incapsula' in html.lower():
                raise Blocked('Coles bot protection blocked the request')
            raise RuntimeError('Coles page had no product data')
        res = json.loads(m.group(1))['props']['pageProps']['searchResults']['results']
        out = []
        for p in res:
            if p.get('_type') != 'PRODUCT' or not p.get('pricing'):
                continue
            pr = p['pricing']
            unit = pr.get('unit') or {}
            up, basis = normalise_unit(unit.get('price'), unit.get('ofMeasureQuantity'), unit.get('ofMeasureUnits'))
            out.append({'name': ' '.join(x for x in (p.get('brand'), p.get('name')) if x),
                        'price': pr.get('now'), 'size': p.get('size'),
                        'unit_price': up, 'unit_basis': basis,
                        'dept': json.dumps(p.get('onlineHeirs') or []).lower()})
            if len(out) >= n:
                break
        return out


class IGA:
    id = 'iga'
    delay = 0.6

    def __init__(self):
        self.op = _opener()

    def search(self, query, n=12):
        url = (f'https://www.igashop.com.au/api/storefront/stores/{IGA_STORE}/search?'
               + urllib.parse.urlencode({'q': query, 'take': n}))
        d = json.loads(_get(self.op, url))
        out = []
        for p in d.get('items') or []:
            if not p.get('available', True) or p.get('priceNumeric') is None:
                continue
            up = basis = None
            m = re.match(r'\$([\d.]+)\s*/\s*([\d.]*)\s*([a-zA-Z]+)', p.get('pricePerUnit') or '')
            if m:
                up, basis = normalise_unit(float(m.group(1)), float(m.group(2) or 1), m.group(3))
            size = p.get('unitOfSize') or {}
            out.append({'name': p.get('name'), 'price': p['priceNumeric'],
                        'size': f"{size.get('size', '')}{size.get('abbreviation', '')}" or None,
                        'unit_price': up, 'unit_basis': basis,
                        'dept': ' '.join(c.get('categoryBreadcrumb', '') for c in p.get('categories') or []
                                         if isinstance(c, dict)).lower()})
        return out


STORES = [Woolworths, Coles, IGA]
