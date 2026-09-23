const $ = (selector, root = document) => root.querySelector(selector);
const labels = { unreviewed: 'Not reviewed', correct: 'Correct', revision: 'Needs revision', unsure: 'Unsure' };
const palette = [['#5b9987', '#e8f3ed'], ['#6c8cae', '#eaf0f8'], ['#b29a60', '#f8f1df']];
const state = { data: null, reviews: {}, category: 'all', facility: 'all', status: 'all', query: '' };
let storageKey, messageTimer;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
function safeUrl(value) {
  if (!value) return '';
  try { const url = new URL(value, location.href); return ['http:', 'https:'].includes(url.protocol) ? url.href : ''; } catch { return ''; }
}
function toast(text, persistent = false) {
  $('#message').textContent = text; $('#message').hidden = false;
  clearTimeout(messageTimer);
  if (!persistent) messageTimer = setTimeout(() => { $('#message').hidden = true; }, 6000);
}
function entries() { return state.data.papers.flatMap(p => p.scenarios.map(s => ({ paper: p, scenario: s }))); }
function verdict(id) { return state.reviews[id]?.status || 'unreviewed'; }
function persist() {
  try { localStorage.setItem(storageKey, JSON.stringify(state.reviews)); return true; }
  catch { toast('Browser storage is unavailable. Export your reviews before leaving this page.', true); return false; }
}
function updateProgress() {
  const total = entries().length;
  const done = entries().filter(({ scenario }) => verdict(scenario.id) !== 'unreviewed').length;
  $('#reviewed-count').textContent = `${done} / ${total}`;
  $('#progress').max = total || 1; $('#progress').value = done;
  $('#export').disabled = !Object.keys(state.reviews).length;
}
function evidenceHTML(items = []) {
  return items.map(e => {
    const image = safeUrl(e.image), source = safeUrl(e.url);
    return `<div class="evidence-card"><div class="evidence-label"><strong>${esc(e.label || 'Source evidence')}</strong>${image ? '<span>Click to enlarge ↗</span>' : ''}</div>${image ? `<button class="evidence-open" data-image="${esc(image)}" data-caption="${esc(e.caption)}" data-label="${esc(e.label)}" aria-label="Enlarge ${esc(e.label || 'source evidence')}"><img src="${esc(image)}" alt="${esc(e.caption || e.label)}" loading="lazy"></button>` : ''}${e.caption ? `<p>${esc(e.caption)}</p>` : ''}${source ? `<p><a href="${esc(source)}" target="_blank" rel="noopener noreferrer">Open source ↗</a></p>` : ''}</div>`;
  }).join('');
}
function scenarioHTML(s, paper) {
  const review = state.reviews[s.id] || {}, current = verdict(s.id);
  const total = s.rubric.reduce((sum, r) => sum + r.points, 0);
  return `<details class="scenario" id="scenario-${esc(s.id)}" data-id="${esc(s.id)}" data-verdict="${current}"><summary><span class="scenario-id">${esc(s.id)}</span><span class="scenario-title">${esc(s.title)}</span><span class="edge">${esc(s.edge)}</span><span class="verdict-badge">${labels[current]}</span><span class="chevron" aria-hidden="true"></span></summary><div class="scenario-body"><div class="section-heading"><h3>Scenario details</h3><a class="permalink" href="#scenario-${encodeURIComponent(s.id)}">Link to scenario ↗</a></div><div class="content-grid"><div><section class="content-section"><h4>Model prompt</h4><div class="prompt-box"><p>${esc(s.prompt)}</p></div></section><section class="content-section"><h4>Source evidence</h4>${s.evidence?.length ? evidenceHTML(s.evidence) : '<p class="paper-source">No source evidence attached.</p>'}</section></div><section class="content-section"><h4>Reference answer</h4><div class="truth-box"><dl>${Object.entries(s.groundTruth).map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(value)}</dd>`).join('')}</dl></div></section></div><section class="content-section"><div class="section-heading"><h3>Scoring rubric</h3><span class="badge">${total} points total</span></div><div class="table-scroll" tabindex="0" aria-label="Scoring rubric"><table><thead><tr><th scope="col">Criterion</th><th scope="col">Reference answer / scoring criteria</th><th scope="col">Points</th></tr></thead><tbody>${s.rubric.map(r => `<tr><td>${esc(r.criterion)}</td><td>${esc(r.answer)}</td><td>${r.points}</td></tr>`).join('')}</tbody></table></div></section><section class="review-form" aria-label="Review ${esc(s.id)}"><div class="review-top"><h3>Your review</h3><button class="text-button clear-review" type="button">Clear review</button></div><div class="review-actions" role="group" aria-label="Verdict for ${esc(s.id)}">${[['correct', '✓'], ['revision', '✎'], ['unsure', '?']].map(([status, icon]) => `<button class="verdict-button" type="button" data-status="${status}" aria-pressed="${status === current}">${icon} ${labels[status]}</button>`).join('')}</div><label for="comment-${esc(s.id)}">Comments or suggested corrections</label><textarea id="comment-${esc(s.id)}" maxlength="12000" placeholder="Describe any issues with the prompt, answer, rubric, or evidence…">${esc(review.comment || '')}</textarea><div class="review-bottom"><span class="save-state">${review.updatedAt ? 'Saved in this browser' : 'Only saved in this browser'}</span><a class="issue-link" href="${esc(issueUrl(s, paper))}" target="_blank" rel="noopener noreferrer">Open GitHub issue ↗</a></div></section></div></details>`;
}
function issueUrl(s, p) {
  const url = new URL('https://github.com/rteehas/spectral_agent_bench/issues/new');
  url.searchParams.set('title', `[Review] ${s.id}: ${s.title}`);
  const comment = state.reviews[s.id]?.comment || 'Describe your correction here.';
  url.searchParams.set('body', `Scenario: ${s.id}\nPaper: ${p.title}\nDataset: ${state.data.datasetId}\n${p.doi ? `DOI: ${p.doi}\n` : ''}Verdict: ${labels[verdict(s.id)]}\n\n${comment.slice(0, 1200)}${comment.length > 1200 ? '\n\n[Long comment truncated. Attach an exported review file for the full text.]' : ''}`);
  return url.href;
}
function matches(p, s) {
  return (state.category === 'all' || p.category === state.category) && (state.facility === 'all' || p.facility === state.facility) && (state.status === 'all' || verdict(s.id) === state.status) && (!state.query || [p.title, p.authors, p.doi, p.category, p.facility, s.id, s.title, s.edge, s.prompt, ...Object.values(s.groundTruth)].join(' ').toLowerCase().includes(state.query));
}
function render() {
  const open = new Set([...document.querySelectorAll('details[open][id]')].map(d => d.id));
  let count = 0, papers = 0;
  $('#papers').innerHTML = state.data.papers.map((p, index) => {
    const scenarios = p.scenarios.filter(s => matches(p, s));
    if (!scenarios.length) return '';
    count += scenarios.length; papers++;
    const colors = palette[index % palette.length];
    const doi = p.doi ? `https://doi.org/${encodeURI(p.doi)}` : '', pdf = safeUrl(p.pdf);
    return `<details class="paper" id="paper-${esc(p.id)}" style="--paper-accent:${colors[0]};--badge-bg:${colors[1]}"><summary><span class="paper-heading"><span class="paper-title">${esc(p.title)}</span><span class="paper-meta"><span class="badge category">${esc(p.category)}</span><span class="badge facility">${esc(p.facility)}</span><span>${esc(p.authors)}</span>${p.doi ? `<span>DOI: ${esc(p.doi)}</span>` : ''}</span></span><span class="paper-count">${scenarios.length} ${scenarios.length === 1 ? 'scenario' : 'scenarios'}</span><span class="chevron" aria-hidden="true"></span></summary><div class="paper-body"><div class="paper-source">${doi ? `<a href="${esc(doi)}" target="_blank" rel="noopener noreferrer">View publication ↗</a>` : 'No publication linked'}${pdf ? ` · <a href="${esc(pdf)}" target="_blank" rel="noopener noreferrer">Open paper PDF ↗</a>` : ''}${state.data.demo ? ' · Demonstration examples only' : ''}</div>${p.evidence?.length ? `<details class="source-evidence"><summary>Key paper evidence</summary>${evidenceHTML(p.evidence)}</details>` : ''}${scenarios.map(s => scenarioHTML(s, p)).join('')}</div></details>`;
  }).join('') || `<div class="empty"><strong>${entries().length ? 'No matching scenarios' : 'No examples published yet'}</strong>${entries().length ? 'Try another search or reset your filters.' : 'Benchmark examples will appear here when they are added.'}</div>`;
  for (const id of open) { const el = document.getElementById(id); if (el) el.open = true; }
  $('#results').textContent = `${count} ${count === 1 ? 'scenario' : 'scenarios'} across ${papers} ${papers === 1 ? 'paper' : 'papers'}`;
  document.querySelectorAll('.chip').forEach(b => b.setAttribute('aria-pressed', b.dataset.category === state.category));
  updateProgress();
}
function updateReview(el, patch) {
  const id = el.dataset.id;
  const review = { status: 'unreviewed', comment: '', ...state.reviews[id], ...patch, updatedAt: new Date().toISOString() };
  if (review.status === 'unreviewed' && !review.comment) delete state.reviews[id];
  else state.reviews[id] = review;
  const saved = persist();
  el.dataset.verdict = review.status;
  $('.verdict-badge', el).textContent = labels[review.status];
  el.querySelectorAll('[data-status]').forEach(b => b.setAttribute('aria-pressed', b.dataset.status === review.status));
  $('.save-state', el).textContent = saved ? 'Saved in this browser' : 'Not saved — export before leaving';
  const item = entries().find(e => e.scenario.id === id);
  $('.issue-link', el).href = issueUrl(item.scenario, item.paper);
  updateProgress();
  // Defer status-filter removal until focus leaves the scenario, so a verdict never interrupts a comment.
  if (state.status !== 'all') el.dataset.pendingFilter = 'true';
}
function focusHash() {
  let id; try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
  if (!id.startsWith('scenario-')) return;
  let el = document.getElementById(id);
  if (!el && entries().some(({scenario}) => `scenario-${scenario.id}` === id)) { resetFilters(); el = document.getElementById(id); }
  if (el) { el.closest('.paper').open = true; el.open = true; el.scrollIntoView({ block: 'start' }); $('summary', el).focus({ preventScroll: true }); }
}
function resetFilters() { state.category = state.facility = state.status = 'all'; state.query = ''; $('#search').value = ''; $('#status').value = $('#facility').value = 'all'; render(); }
function validateReviews(reviews) {
  if (!reviews || typeof reviews !== 'object' || Array.isArray(reviews)) throw new Error('The file does not contain a valid reviews object.');
  const allowed = new Set(entries().map(e => e.scenario.id)), result = {};
  for (const [id, r] of Object.entries(reviews)) {
    if (!allowed.has(id)) throw new Error(`Unknown scenario: ${id}. Import a file for this dataset.`);
    if (!r || !Object.hasOwn(labels, r.status) || typeof r.comment !== 'string' || r.comment.length > 12000 || typeof r.updatedAt !== 'string' || !Number.isFinite(Date.parse(r.updatedAt))) throw new Error(`Invalid review for ${id}.`);
    result[id] = { status: r.status, comment: r.comment, updatedAt: r.updatedAt };
  }
  return result;
}
$('#search').addEventListener('input', e => { state.query = e.target.value.trim().toLowerCase(); render(); });
$('#facility').addEventListener('change', e => { state.facility = e.target.value; render(); });
$('#status').addEventListener('change', e => { state.status = e.target.value; render(); });
$('#categories').addEventListener('click', e => { const b = e.target.closest('[data-category]'); if (b) { state.category = b.dataset.category; render(); } });
$('#reset').addEventListener('click', resetFilters);
$('#expand').addEventListener('click', () => document.querySelectorAll('.paper').forEach(p => p.open = true));
$('#collapse').addEventListener('click', () => document.querySelectorAll('#papers details').forEach(p => p.open = false));
$('#papers').addEventListener('input', e => { if (e.target.matches('textarea')) updateReview(e.target.closest('.scenario'), { comment: e.target.value }); });
$('#papers').addEventListener('focusout', e => { const el = e.target.closest('.scenario'); if (el?.dataset.pendingFilter && !el.contains(e.relatedTarget)) render(); });
$('#papers').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  const el = b.closest('.scenario');
  if (b.dataset.status) updateReview(el, { status: b.dataset.status });
  if (b.classList.contains('clear-review')) { $('textarea', el).value = ''; updateReview(el, { status: 'unreviewed', comment: '' }); }
  if (b.dataset.image) {
    $('#evidence-image').src = b.dataset.image; $('#evidence-image').alt = b.dataset.caption || b.dataset.label;
    $('#evidence-title').textContent = b.dataset.label; $('#evidence-caption').textContent = b.dataset.caption;
    $('#evidence-dialog').showModal();
  }
});
$('#close-evidence').addEventListener('click', () => $('#evidence-dialog').close());
$('#papers').addEventListener('error', e => { if (e.target.tagName === 'IMG') { e.target.hidden = true; const note = document.createElement('p'); note.textContent = 'Evidence image unavailable. Please check the source link.'; e.target.parentElement.replaceWith(note); } }, true);
$('#export').addEventListener('click', () => {
  const data = { schemaVersion: 1, datasetId: state.data.datasetId, exportedAt: new Date().toISOString(), reviews: state.reviews };
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = `spectral-reviews-${state.data.datasetId}-${new Date().toISOString().slice(0, 10)}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast('Review file downloaded. Send it to the benchmark maintainer to share your feedback.');
});
$('#import').addEventListener('click', () => $('#import-file').click());
$('#import-file').addEventListener('change', async e => {
  try {
    const file = e.target.files[0]; if (!file) return;
    if (file.size > 5_000_000) throw new Error('Review files must be smaller than 5 MB.');
    const data = JSON.parse(await file.text());
    if (data.schemaVersion !== 1 || data.datasetId !== state.data.datasetId) throw new Error('This review file belongs to a different dataset or unsupported version.');
    const incoming = validateReviews(data.reviews); let added = 0;
    for (const [id, review] of Object.entries(incoming)) {
      if (!state.reviews[id] || Date.parse(review.updatedAt) > Date.parse(state.reviews[id].updatedAt)) { state.reviews[id] = review; added++; }
    }
    const saved = persist(); render(); if (saved) toast(`Imported ${added} reviews. More recent local reviews were kept.`);
  } catch (err) { toast(`Could not import: ${err.message}`, true); }
  finally { e.target.value = ''; }
});
window.addEventListener('hashchange', focusHash);
async function init() {
  try {
    const response = await fetch('data/benchmark.json');
    if (!response.ok) throw new Error(`Dataset request failed (${response.status}).`);
    state.data = await response.json();
    if (state.data.schemaVersion !== 1 || !Array.isArray(state.data.papers)) throw new Error('Unsupported dataset format.');
    storageKey = `spectral-agent-bench:reviews:${state.data.datasetId}`;
    try { const stored = localStorage.getItem(storageKey); if (stored) state.reviews = validateReviews(JSON.parse(stored)); }
    catch { toast('Saved reviews could not be loaded. Existing storage has not been changed.', true); }
    $('#demo-notice').hidden = !state.data.demo;
    const categories = [...new Set(state.data.papers.map(p => p.category))], facilities = [...new Set(state.data.papers.map(p => p.facility))];
    $('#scenario-count').textContent = entries().length; $('#paper-count').textContent = state.data.papers.length; $('#category-count').textContent = categories.length; $('#facility-count').textContent = facilities.length;
    $('#categories').innerHTML = `<button class="chip" data-category="all" aria-pressed="true">All categories<span>${entries().length}</span></button>` + categories.map(c => `<button class="chip" data-category="${esc(c)}" aria-pressed="false">${esc(c)}<span>${entries().filter(e => e.paper.category === c).length}</span></button>`).join('');
    $('#facility').innerHTML += facilities.map(f => `<option value="${esc(f)}">${esc(f)}</option>`).join('');
    render(); focusHash();
    // Progressive enhancement for browsers that support the WebMCP proposal.
    if (navigator.modelContext?.registerTool) {
      navigator.modelContext.registerTool({ name: 'filter_benchmark_scenarios', description: 'Filter the visible benchmark scenarios by text and review status. Does not submit or modify reviews.', inputSchema: { type: 'object', properties: { query: { type: 'string' }, status: { type: 'string', enum: ['all', ...Object.keys(labels)] } }, additionalProperties: false }, execute: async ({ query = '', status = 'all' }) => { state.query = String(query).trim().toLowerCase(); state.status = Object.hasOwn(labels, status) ? status : 'all'; $('#search').value = query; $('#status').value = state.status; render(); return { content: [{ type: 'text', text: $('#results').textContent }] }; } });
    }
  } catch (err) {
    $('#papers').innerHTML = '<div class="empty error"><strong>Examples could not be loaded</strong>Reload the page. If the problem persists, ask the maintainer to check the benchmark data file.</div>';
    $('#results').textContent = 'Dataset unavailable'; $('#import').disabled = true; console.error(err);
  }
}
init();
