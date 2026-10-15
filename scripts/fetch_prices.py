"""Build prices.json for the app's Shop tab (Live / feed prices).

The app keys prices as '<food>|<unit>' and reads the price as AUD per 100 g
('g'), per 100 mL ('ml') or per item ('each').

Usage: python scripts/fetch_prices.py [output path] [--only key1,key2] [--stores iga,coles]
"""
import datetime as dt
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from catalog import CATALOG, entry  # noqa: E402
from stores import STORES, Blocked  # noqa: E402

CANDIDATES = 8  # how many matching products to consider per search


def matches(product, rule):
    n = (product['name'] or '').lower()
    dept = product.get('dept') or ''
    return (all(w in n for w in rule.get('need', []))
            and not any(w in n for w in rule.get('avoid', []))
            and (not rule.get('dept') or not dept or any(d in dept for d in rule['dept']))
            and not any(d in dept for d in rule.get('not_dept', [])))


def pack_count(name, size):
    text = f'{name or ""} {size or ""}'.lower()
    if 'dozen' in text:
        return 12
    m = re.search(r'(\d+)\s*(?:pack|pk|pc|pcs|piece|pieces|x\b)|\bx\s*(\d+)\b|(\d+)\s*(?:eggs|wraps|slices|each)', text)
    if m:
        n = int(next(g for g in m.groups() if g))
        return n if 1 < n <= 60 else None
    return None


def prices_for(product, rule):
    """Return {'g': per100g, 'ml': per100ml, 'each': per item} for one product."""
    up, basis = product['unit_price'], product['unit_basis']
    out = {}
    if basis in ('100g', '100ml'):
        out['g'] = out['ml'] = up  # treat 1 g ~ 1 mL; close enough for groceries
    count = pack_count(product['name'], product['size'])
    if count and product['price']:
        out['each'] = product['price'] / count
    elif basis == 'each':
        out['each'] = up
    elif 'g' in out and rule.get('each_g'):
        out['each'] = out['g'] * rule['each_g'] / 100
    if 'g' not in out and 'each' in out and rule.get('each_g'):
        out['g'] = out['ml'] = out['each'] / rule['each_g'] * 100
    f = rule.get('factor', 1)
    for unit in ('g', 'ml'):
        if unit in out:
            out[unit] *= f
    return out


def best(products, rule):
    """Cheapest matching product for each unit, from the most relevant results."""
    picked = {}
    for p in [p for p in products if matches(p, rule)][:CANDIDATES]:
        for unit, price in prices_for(p, rule).items():
            if price > 0 and (unit not in picked or price < picked[unit][0]):
                picked[unit] = (price, p)
    return picked


def main():
    args, only = sys.argv[1:], None
    if '--only' in args:
        i = args.index('--only')
        only = set(args[i + 1].split(','))
        del args[i:i + 2]
    stores = STORES
    if '--stores' in args:  # e.g. --stores iga
        i = args.index('--stores')
        wanted = set(args[i + 1].split(','))
        stores = [S for S in STORES if S.id in wanted]
        del args[i:i + 2]
    out_path = args[0] if args else os.path.join(os.path.dirname(__file__), '..', 'prices.json')

    try:
        with open(out_path, encoding='utf8') as fh:
            previous = json.load(fh)
    except (OSError, ValueError):
        previous = {'items': []}

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    items, status = [], {}
    for Store in stores:
        fresh, failed, err = {}, 0, None
        try:
            store = Store()
        except Exception as e:  # store unreachable or blocking us
            store, err = None, f'{type(e).__name__}: {e}'
        for ref, rule in CATALOG.items():
            if store is None or 'alias' in rule or rule.get('skip') or (only and ref not in only):
                continue
            try:
                picked = best(store.search(rule['q']), rule)
            except Blocked as e:
                err = str(e)
                break  # respect the block: no more requests to this store this run
            except Exception as e:
                failed += 1
                err = f'{type(e).__name__}: {e}'
                picked = {}
            for unit, (price, p) in picked.items():
                fresh[f'{ref}|{unit}'] = {'storeId': Store.id, 'key': f'{ref}|{unit}', 'price': round(price, 4),
                                          'product': p['name'], 'shelfPrice': p['price'], 'size': p['size'],
                                          'checkedAt': now}
            time.sleep(Store.delay)
        # Items not found this run keep their last good price.
        kept = {i['key']: i for i in previous.get('items', [])
                if i.get('storeId') == Store.id and i['key'] not in fresh}
        merged = {**kept, **fresh}
        # Aliases (e.g. 'thigh' -> 'chickenthigh') reuse the same prices.
        for ref, rule in CATALOG.items():
            if 'alias' in rule:
                target = entry(ref)
                tref = next(k for k, v in CATALOG.items() if v is target)
                for k, i in list(merged.items()):
                    if k.startswith(tref + '|'):
                        nk = ref + '|' + k.split('|')[1]
                        merged[nk] = dict(i, key=nk)
        items += merged.values()
        status[Store.id] = {'ok': bool(fresh), 'updated': len(fresh), 'keptPrevious': len(kept),
                            'failedSearches': failed, 'error': err}
        print(Store.id, status[Store.id], flush=True)

    for Store in STORES:
        if Store not in stores:
            items += [i for i in previous.get('items', []) if i.get('storeId') == Store.id]
            if Store.id in previous.get('stores', {}):
                status[Store.id] = previous['stores'][Store.id]

    if not any(s['ok'] for s in status.values()):
        print('No store returned prices; leaving prices.json unchanged.')
        sys.exit(1)

    snapshot = {'version': 1, 'updatedAt': now,
                'note': 'AUD per 100 g (|g), per 100 mL (|ml) or per item (|each). Prices may vary based on location.',
                'stores': status, 'items': items}
    with open(out_path, 'w', encoding='utf8') as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=1)
    print(f'Wrote {len(items)} prices to {out_path}')


if __name__ == '__main__':
    main()
