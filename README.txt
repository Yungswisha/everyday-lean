EVERYDAY LEAN AU 2.2 — RECIPES & GROCERY PRICES

Use Everyday_Lean_AU_2_2.html for a standalone preview, or upload the extracted files in this ZIP to the root of a GitHub Pages repository. On iPhone, use Safari → Share → Add to Home Screen.

Includes 26 original recipes and editable ingredient quantities, seven-day planning, a shopping list, TheMealDB recipe discovery, and a three-retailer price comparison (Woolworths, Coles and IGA).

PRICING
Prices may vary based on location.
The Shop tab contains TWO STRICTLY SEPARATE price sources:
- Live / feed: read-only prices retrieved from a hosted prices.json or imported JSON snapshot; imported snapshots are explicitly labelled as such, and are NOT automatically verified live quotes.
- Entered prices: amounts you type in the app and maintain yourself. These never get overwritten by the feed or imported snapshot.

The app does NOT currently connect to a retailer live pricing API or automatically collect hourly quotes. To use a feed, a permitted external data provider must publish a prices.json in the same directory as index.html. Hit Shop → Check hosted price feed. Example price schema, values deliberately omitted:
{"version":1,"updatedAt":"2026-10-15T08:00:00Z","items":[{"storeId":"coles","key":"rawturkey|g","price":0}]}
The displayed reference unit is AUD per 100 g, per 100 mL, or per item; actual availability and unit conversions must be verified. The example zero is a format placeholder, not a real or estimated grocery price.

Australian measures: 1 cup 250 mL, tablespoon 20 mL, teaspoon 5 mL. Nutrition estimates are approximate; use product-label values when available. Recipes and edited prices are stored in your browser's local storage. Use Settings → Export all data to back up.

To upgrade a hosted v2.1 installation, replace its files at the same URL. The v2.2 app migrates locally entered legacy prices into Entered and prior imported snapshots into Feed; any previous retailer-specific entries are combined into one set per retailer.

Online recipe discovery uses TheMealDB test key; suitable production access may require a separate provider account. HTTPS hosting does not itself provide a backend, a search API, or a retailer feed.
