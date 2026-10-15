// Everyday Lean add-on: daily recipe finds and automatic price feed.
// Data comes from discover.json and prices.json, which a GitHub Action
// refreshes every day. Loaded after the main app script in index.html:
//   <script src="./discover.js"></script>
(function () {
  const FEED_SEEN = 'everyday-lean-feed-applied-at';
  const finds = { list: null, updatedAt: null, error: null, filter: '', shown: 12 };

  async function loadFinds() {
    try {
      const r = await fetch('./discover.json?cache=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) throw Error(r.status === 404 ? 'No recipe finds yet' : 'HTTP ' + r.status);
      const d = await r.json();
      finds.list = Array.isArray(d.recipes) ? d.recipes : [];
      finds.updatedAt = d.updatedAt || null;
    } catch (e) {
      finds.list = [];
      finds.error = e.message;
    }
    if (state.page === 'explore') render();
  }

  // Apply a newer hosted prices.json automatically, once per new snapshot.
  async function autoPrices() {
    if (location.protocol === 'file:') return;
    try {
      const r = await fetch('./prices.json?cache=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) return;
      const snap = await r.json();
      let seen = null;
      try { seen = localStorage.getItem(FEED_SEEN); } catch (e) {}
      if (!snap.updatedAt || snap.updatedAt === seen) return;
      await applyPriceSnapshot(snap, 'hosted');
      try { localStorage.setItem(FEED_SEEN, snap.updatedAt); } catch (e) {}
    } catch (e) { /* offline or no feed yet: entered prices still work */ }
  }

  function card(m, i) {
    const img = m.strMealThumb ? `<img src="${escAttr(m.strMealThumb)}" alt="" loading="lazy" style="width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:10px;background:var(--leaf)">` : '';
    const meta = [m.site, m.totalTime && m.totalTime.replace(/^PT/, '').toLowerCase(), m.serves && 'serves ' + m.serves].filter(Boolean).join(' · ');
    return `<div class="linkbox">${img}<strong style="display:block;margin-top:8px">${safe(m.strMeal)}</strong>
      <p class="muted" style="font-size:12px;margin-top:4px">${safe(meta)}</p>
      ${m.description ? `<p style="font-size:12px;margin-top:6px">${safe(m.description.slice(0, 140))}${m.description.length > 140 ? '…' : ''}</p>` : ''}
      <div class="bar m12"><button class="btn tiny" data-find-import="${i}">+ Import</button>
      <a class="btn secondary tiny" href="${escAttr(m.strSource)}" target="_blank" rel="noopener noreferrer">Open ↗</a></div></div>`;
  }

  function renderFinds() {
    if (finds.list === null) return `<div class="card pad mb12"><h3>Fresh recipe finds</h3><p class="muted m8">Loading…</p></div>`;
    if (!finds.list.length) return `<div class="card pad mb12"><h3>Fresh recipe finds</h3><p class="muted m8" style="font-size:12px">${safe(finds.error || 'No recipes found yet.')} New finds are added daily.</p></div>`;
    const f = finds.filter.toLowerCase();
    const matches = finds.list.map((m, i) => [m, i]).filter(([m]) => !f || (m.strMeal + ' ' + m.site + ' ' + (m.description || '')).toLowerCase().includes(f));
    const when = finds.updatedAt ? new Date(finds.updatedAt).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' }) : '';
    return `<div class="card pad mb12"><div class="row between wraprow"><div><h3>Fresh recipe finds</h3>
      <p class="muted m8" style="font-size:12px">Found daily with Brave Search${when ? ' · updated ' + safe(when) : ''}. Import makes an editable copy — check the amounts before cooking.</p></div>
      <span class="pill">${finds.list.length} recipes</span></div>
      <input class="input m12" id="findFilter" placeholder="Filter finds — e.g. chicken, salmon, breakfast" value="${escAttr(finds.filter)}" autocomplete="off">
      <div class="link-grid m12">${matches.slice(0, finds.shown).map(([m, i]) => card(m, i)).join('') || '<p class="muted">No finds match that filter.</p>'}</div>
      ${matches.length > finds.shown ? `<button class="btn secondary m12" data-find-more>Show more (${matches.length - finds.shown})</button>` : ''}</div>`;
  }

  const baseExplore = renderExplore;
  renderExplore = function () {
    const html = baseExplore();
    const at = html.indexOf('<div class="card pad">');  // put finds above the TheMealDB search card
    return at < 0 ? html + renderFinds() : html.slice(0, at) + renderFinds() + html.slice(at);
  };

  document.addEventListener('click', e => {
    const imp = e.target.closest('[data-find-import]');
    if (imp) {
      const m = finds.list[+imp.dataset.findImport];
      if (!m) return;
      importMeal(m);
      const r = data.recipes[0];  // importMeal puts the new recipe first
      r.origin = m.site || 'Online recipe';
      r.note = `Imported from ${m.site || 'the web'}. Convert and verify any missing metric measures.`;
      save(); render();
      return;
    }
    if (e.target.closest('[data-find-more]')) { finds.shown += 12; render(); }
  });

  document.addEventListener('input', e => {
    if (e.target.id !== 'findFilter') return;
    finds.filter = e.target.value;
    finds.shown = 12;
    const pos = e.target.selectionStart;
    render();
    const box = document.getElementById('findFilter');
    if (box) { box.focus(); box.setSelectionRange(pos, pos); }
  });

  loadFinds();
  autoPrices();
})();
