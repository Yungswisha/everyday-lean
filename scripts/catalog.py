"""How to find each app ingredient (FOODS key in index.html) at the supermarkets.

q        search query
need     every word must appear in the product name (lowercase)
avoid    product is skipped if its name contains any of these
factor   multiply the per-100 g/mL price by this (e.g. dry rice -> cooked rice);
         not applied to per-item prices
dept     product must be in a store department containing one of these words
         (set per group below, e.g. fresh produce only from Fruit & Veg)
not_dept product is skipped if its department contains any of these
each_g   typical weight of one item, used when a recipe counts items ("2 eggs")
         and the store only gives a weight price
skip     not priced (free or negligible)
"""

FRESH_AVOID = ['frozen', 'dried', 'canned', 'tin', 'juice', 'chips', 'baby food', 'muffin', 'bread',
               'cake', 'bar', 'ice cream', 'split', 'smoothie', 'yoghurt', 'custard', 'chopped',
               'sliced', 'diced', 'puree', 'sauce', 'snack', 'pouch', 'lollies', 'flavour']

CATALOG = {
    # Protein
    'rawturkey':     {'q': 'turkey mince', 'need': ['turkey', 'mince']},
    'rawbeef':       {'q': 'lean beef mince', 'need': ['beef', 'mince'], 'avoid': ['wagyu', 'angus', 'pork', 'lamb', 'chicken']},
    'chickenraw':    {'q': 'chicken breast fillets', 'need': ['chicken', 'breast'], 'avoid': ['crumbed', 'marinated', 'cooked', 'roast', 'schnitzel', 'mince', 'kiev', 'tender']},
    'chickencooked': {'q': 'chicken breast fillets', 'need': ['chicken', 'breast'], 'avoid': ['crumbed', 'marinated', 'cooked', 'roast', 'schnitzel', 'mince', 'kiev', 'tender'], 'factor': 1.33},
    'chickenthigh':  {'q': 'chicken thigh fillets', 'need': ['chicken', 'thigh'], 'avoid': ['crumbed', 'marinated', 'cooked', 'roast', 'bone in', 'skin on', 'kebab']},
    'thigh':         {'alias': 'chickenthigh'},
    'prawns':        {'q': 'raw prawns', 'need': ['prawn'], 'avoid': ['cooked', 'crumbed', 'cutlet', 'dumpling', 'cracker', 'chips']},
    'salmonraw':     {'q': 'salmon fillets', 'need': ['salmon'], 'avoid': ['smoked', 'canned', 'tin', 'pouch', 'crumbed', 'mousse']},
    'fillet':        {'alias': 'salmonraw'},
    'salmontin':     {'q': 'canned pink salmon', 'need': ['salmon'], 'avoid': ['smoked', 'fillet', 'fresh', 'pouch flavour']},
    'tuna':          {'q': 'tuna in springwater', 'need': ['tuna'], 'avoid': ['steak', 'sashimi', 'flavour', 'chilli', 'lemon pepper', 'mayo', 'dog', 'cat', 'pet']},
    'sardines':      {'q': 'sardines in springwater', 'need': ['sardine'], 'avoid': ['dog', 'cat', 'pet']},
    'eggs':          {'q': 'free range eggs 12 pack', 'need': ['egg'], 'avoid': ['white', 'easter', 'chocolate', 'noodle', 'boiled', 'quail'], 'each_g': 58},
    'eggwhite':      {'q': 'liquid egg whites', 'need': ['egg', 'white']},
    'whey':          {'q': 'whey protein powder', 'need': ['whey', 'protein'], 'avoid': ['bar', 'ball', 'drink', 'shake 6', 'cookie', 'yoghurt', 'milk', 'shake', 'powder drink']},
    'cottage':       {'q': 'cottage cheese', 'need': ['cottage']},

    # Dairy
    'yoghurt0':      {'q': 'greek yoghurt no fat', 'need': ['yoghurt'], 'avoid': ['strawberry', 'vanilla', 'mango', 'honey', 'berry', 'pouch', 'kids', 'dip']},
    'yoghurtplain':  {'q': 'greek yoghurt natural', 'need': ['yoghurt'], 'avoid': ['strawberry', 'vanilla', 'mango', 'honey', 'berry', 'pouch', 'kids', 'dip']},
    'milk':          {'q': 'lite milk', 'need': ['milk'], 'avoid': ['chocolate', 'coconut', 'almond', 'oat', 'soy', 'powder', 'flavoured', 'condensed', 'evaporated', 'iced coffee']},

    # Grains and bread
    'oats':          {'q': 'rolled oats', 'need': ['oats'], 'avoid': ['sachet', 'bar', 'quick', 'flavour', 'honey']},
    'rice':          {'q': 'long grain white rice 5kg', 'need': ['rice'], 'avoid': ['microwave', 'cup', 'pouch', 'cake', 'cracker', 'noodle', 'flour', 'milk', 'pudding', 'basmati brown'], 'factor': 0.4},
    'pasta':         {'q': 'wholemeal pasta', 'need': ['whole'], 'avoid': ['bread', 'wrap', 'flour', 'cheese', 'sauce', 'roll', 'cracker', 'biscuit', 'muffin', 'oats', 'rice'], 'factor': 0.43},
    'bread':         {'q': 'wholemeal bread loaf', 'need': ['bread'], 'avoid': ['crumbs', 'garlic', 'roll', 'mix', 'flour'], 'each_g': 38},
    'wrap':          {'q': 'wholemeal wraps', 'need': ['wrap'], 'avoid': ['foil', 'cling', 'paper'], 'each_g': 62},
    'ricecake':      {'q': 'rice cakes', 'need': ['rice', 'cake'], 'avoid': ['mini', 'chocolate', 'flavour', 'caramel'], 'each_g': 9},
    'breadcrumb':    {'q': 'breadcrumbs', 'need': ['breadcrumb']},

    # Legumes
    'blackbeans':    {'q': 'black beans can', 'need': ['black', 'bean'], 'avoid': ['dried', 'sauce']},
    'kidneybeans':   {'q': 'red kidney beans can', 'need': ['kidney'], 'avoid': ['dried', 'chilli']},
    'chickpeas':     {'q': 'chickpeas can', 'need': ['chickpea'], 'avoid': ['dried', 'snack', 'roasted', 'chips', 'hummus']},
    'lentils':       {'q': 'brown lentils can', 'need': ['lentil'], 'avoid': ['dried', 'soup', 'chips']},
    'edamame':       {'q': 'frozen edamame', 'need': ['edamame']},

    # Produce
    'banana':        {'q': 'bananas', 'need': ['banana'], 'avoid': FRESH_AVOID + ['bread', 'lady finger', 'organic'], 'each_g': 120},
    'apple':         {'q': 'pink lady apples', 'need': ['apple'], 'avoid': FRESH_AVOID + ['sauce', 'pie', 'cider', 'kids', 'mini'], 'each_g': 180},
    'orange':        {'q': 'navel oranges', 'need': ['orange'], 'avoid': FRESH_AVOID + ['mandarin', 'bottle', 'drink', 'soft', 'soda', 'cordial'], 'each_g': 200},
    'kiwi':          {'q': 'kiwifruit', 'need': ['kiwi'], 'avoid': FRESH_AVOID, 'each_g': 85},
    'lime':          {'q': 'limes', 'need': ['lime'], 'avoid': FRESH_AVOID + ['leaves', 'cordial', 'pickle', 'salad', 'kit', 'water', 'sparkling', 'bag', 'earthie', 'soda', 'mineral'], 'each_g': 65},
    'lemonjuice':    {'q': 'lemons', 'need': ['lemon'], 'avoid': ['frozen', 'dried', 'tea', 'cordial', 'drink', 'myrtle'], 'factor': 2.5},
    'blueberries':   {'q': 'fresh blueberries', 'need': ['blueberr'], 'avoid': ['frozen', 'dried', 'muffin', 'yoghurt', 'jam', 'juice']},
    'berries':       {'q': 'frozen mixed berries', 'need': ['berr'], 'avoid': ['yoghurt', 'jam', 'juice', 'muffin']},
    'tomato':        {'q': 'tomatoes', 'need': ['tomato'], 'avoid': FRESH_AVOID + ['sauce', 'paste', 'sun dried', 'soup', 'diced', 'passata', 'cherry', 'truss'], 'each_g': 120},
    'capsicum':      {'q': 'red capsicum', 'need': ['capsicum'], 'avoid': FRESH_AVOID + ['strips', 'roasted'], 'each_g': 180},
    'zucchini':      {'q': 'zucchini', 'need': ['zucchini'], 'avoid': FRESH_AVOID + ['noodle', 'spiral', 'slice'], 'each_g': 200},
    'spinach':       {'q': 'baby spinach', 'need': ['spinach'], 'avoid': ['frozen', 'dip', 'ricotta', 'wrap', 'pasta']},
    'cucumber':      {'q': 'lebanese cucumber', 'need': ['cucumber'], 'avoid': FRESH_AVOID + ['pickle'], 'each_g': 150},
    'carrot':        {'q': 'carrots', 'need': ['carrot'], 'avoid': FRESH_AVOID + ['cake', 'baby', 'stick', 'shredded'], 'each_g': 120},
    'lettuce':       {'q': 'cos lettuce', 'need': ['lettuce'], 'avoid': ['wrap', 'salad kit'], 'each_g': 400},
    'onion':         {'q': 'brown onions', 'need': ['onion'], 'avoid': FRESH_AVOID + ['spring', 'red', 'fried', 'soup', 'rings', 'powder', 'flakes'], 'each_g': 150},
    'redonion':      {'q': 'red onions', 'need': ['red', 'onion'], 'avoid': FRESH_AVOID + ['powder', 'pickled'], 'each_g': 150},
    'garlic':        {'q': 'garlic bulb', 'need': ['garlic'], 'avoid': ['bread', 'paste', 'crushed', 'chopped', 'dip', 'peeled', 'roasted', 'black', 'powder', 'salt', 'sauce', 'naan', 'minced', 'jar', 'aioli'], 'each_g': 5},
    'ginger':        {'q': 'fresh ginger', 'need': ['ginger'], 'avoid': ['ale', 'beer', 'paste', 'crushed', 'powder', 'nut', 'biscuit', 'tea', 'crystallised', 'minced', 'jar', 'bread', 'shot', 'diffuser', 'aroma', 'oil', 'juice', 'cold pressed', 'kombucha']},
    'mushrooms':     {'q': 'cup mushrooms', 'need': ['mushroom'], 'avoid': ['canned', 'dried', 'soup', 'sauce', 'risotto', 'baking', 'tart']},
    'broccoli':      {'q': 'broccoli', 'need': ['broccoli'], 'avoid': FRESH_AVOID + ['rice', 'slaw', 'soup'], 'each_g': 350},
    'cauliflower':   {'q': 'cauliflower', 'need': ['cauliflower'], 'avoid': FRESH_AVOID + ['rice', 'cheese', 'pizza', 'mash', 'half', 'pea', 'carrot', 'corn', 'birds eye'], 'each_g': 1000},
    'beansgreen':    {'q': 'green beans', 'need': ['bean'], 'avoid': FRESH_AVOID + ['baked', 'kidney', 'coffee', 'jelly', 'black', 'cannellini', 'four', 'broad']},
    'peas':          {'q': 'frozen peas', 'need': ['peas'], 'avoid': ['snow', 'sugar snap', 'wasabi', 'split', 'chick']},
    'corn':          {'q': 'corn kernels can', 'need': ['corn'], 'avoid': ['chips', 'flour', 'flakes', 'starch', 'cream', 'baby', 'pop', 'tortilla', 'cob', 'chicken']},
    'mixedveg':      {'q': 'frozen mixed vegetables', 'need': ['veg'], 'avoid': ['chips', 'pie', 'soup', 'stock', 'dumpling', 'pastie']},
    'potato':        {'q': 'washed potatoes', 'need': ['potato'], 'avoid': FRESH_AVOID + ['sweet', 'salad', 'mash', 'wedges', 'gems', 'hash', 'crisps', 'gnocchi', 'bake'], 'each_g': 200},
    'sweetpotato':   {'q': 'sweet potato', 'need': ['sweet', 'potato'], 'avoid': FRESH_AVOID + ['fries', 'wedges', 'mash'], 'each_g': 400},

    # Pantry and condiments
    'oliveoil':      {'q': 'extra virgin olive oil', 'need': ['olive', 'oil'], 'avoid': ['spray', 'tuna', 'sardine', 'olives', 'bread']},
    'sesameoil':     {'q': 'sesame oil', 'need': ['sesame', 'oil'], 'avoid': ['spray', 'dressing', 'tuna', 'salmon', 'sardine', 'noodle']},
    'soy':           {'q': 'salt reduced soy sauce', 'need': ['soy'], 'avoid': ['milk', 'bean', 'chips', 'nuts']},
    'honey':         {'q': 'honey', 'need': ['honey'], 'avoid': ['soy', 'mustard', 'cereal', 'chicken', 'yoghurt', 'oats', 'nut', 'roasted', 'bar', 'puffs', 'ham', 'glaze']},
    'mustard':       {'q': 'dijon mustard', 'need': ['mustard'], 'avoid': ['powder', 'honey mustard chicken', 'seeds']},
    'salsa':         {'q': 'tomato salsa', 'need': ['salsa'], 'avoid': ['chips', 'seasoning', 'verde']},
    'passata':       {'q': 'tomato passata', 'need': ['passata']},
    'coconutm':      {'q': 'light coconut milk', 'need': ['coconut', 'milk'], 'avoid': ['powder', 'drink', 'yoghurt', 'chocolate', 'ice']},
    'peanutbutter':  {'q': 'peanut butter', 'need': ['peanut', 'butter'], 'avoid': ['cookie', 'bar', 'chocolate', 'ball', 'cups', 'protein', 'dog', 'bliss']},
    'chias':         {'q': 'chia seeds', 'need': ['chia'], 'avoid': ['pudding', 'bar', 'drink', 'bread', 'snap']},
    'almonds':       {'q': 'raw almonds', 'need': ['almond'], 'avoid': ['milk', 'chocolate', 'meal', 'flaked', 'slivered', 'butter', 'bar', 'biscuit', 'smoked', 'salted', 'roasted', 'yoghurt', 'cluster', 'cake']},

    # Not priced
    'water':         {'skip': True},
    'ice':           {'skip': True},
    'seasoning':     {'skip': True},
}


DEPTS = {
    ('fruit', 'veg'): ['banana', 'apple', 'orange', 'kiwi', 'lime', 'lemonjuice', 'blueberries', 'tomato',
                       'capsicum', 'zucchini', 'spinach', 'cucumber', 'carrot', 'lettuce', 'onion', 'redonion',
                       'garlic', 'ginger', 'mushrooms', 'broccoli', 'cauliflower', 'beansgreen', 'potato',
                       'sweetpotato'],
    ('meat', 'seafood', 'poultry'): ['rawturkey', 'rawbeef', 'chickenraw', 'chickencooked', 'chickenthigh',
                                     'prawns', 'salmonraw'],
    ('frozen', 'freezer'): ['berries', 'peas', 'mixedveg', 'edamame'],
    ('pantry',): ['pasta', 'rice', 'oats', 'oliveoil', 'sesameoil', 'soy', 'blackbeans', 'kidneybeans',
                  'chickpeas', 'lentils', 'tuna', 'sardines', 'salmontin'],
}
for words, refs in DEPTS.items():
    for ref in refs:
        CATALOG[ref]['dept'] = list(words)
        if 'frozen' not in words:
            CATALOG[ref]['not_dept'] = ['frozen', 'freezer']  # e.g. IGA 'Frozen Vegetables'


def entry(ref):
    e = CATALOG.get(ref)
    while e and 'alias' in e:
        e = CATALOG.get(e['alias'])
    return e
