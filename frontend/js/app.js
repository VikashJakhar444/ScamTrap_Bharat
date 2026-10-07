/* ==========================================================================
   ScamTrap Bharat — application logic
   Tabs · toasts · checker · honeypot · evidence · trends
   ========================================================================== */

const CASE_ID = 'CASE-2026-1001';
const CIRCUMFERENCE = 2 * Math.PI * 35;

const ui = {};

/** State kept so language switches can re-render dynamic panels. */
const state = {
  evidence: null,
  summary: null,
  blacklist: [],
  selectedCase: CASE_ID,
  activeCaseId: CASE_ID,
  originalMessage: '',
  lastSuggestion: '',
  handoverDone: false,
  baitAmount: '',
  latestBait: null,
  lastVerdict: null,   // normalised shape consumed by renderVerdict()
  lastReport: null     // raw /api/checker/analyze* response (layers, principles)
};

/* --------------------------------------------------------------------------
   Boot
   -------------------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  cacheDom();
  initTabs();
  initChecker();
  initHoneypot();
  initEvidence();
  initTrends();
  initGlobalHandlers();
  renderTargetBar();
  loadEvidence();
  checkHealth();
});

function cacheDom() {
  [
    'desktop-tablist', 'mobile-tablist', 'hamburger-btn', 'toast-region',
    'quick-search-input', 'quick-search-btn', 'chip-scam-upi', 'chip-scam-msg',
    'scam-msg-input', 'analyze-msg-btn', 'btn-clear-tab1',
    'dropzone-box', 'scam-img-input',
    'attach-audio-btn', 'attach-qr-btn', 'attach-status',
    'scam-audio-input', 'qr-row', 'qr-payload-input', 'qr-analyze-btn',
    'result-side-card', 'result-placeholder', 'result-loading', 'result-active-content',
    'verdict-meta', 'meta-model', 'meta-input', 'meta-case',
    'principles-panel', 'principles-list',
    'layers-panel',
    'gauge-score-text', 'radial-gauge-circle', 'risk-score-pill',
    'risk-banner-box', 'risk-banner-icon', 'risk-banner-title', 'risk-banner-guidance',
    'ext-upi-val', 'ext-phone-val', 'ext-bank-val',
    'custom-bait-amt', 'custom-bait-name', 'btn-generate-bait', 'btn-send-to-honeypot',
    'bait-preview-modal', 'bait-receipt-img', 'btn-download-bait-img',
    'btn-copy-bait-text', 'bait-copy-toast',
    'btn-refresh-status', 'btn-test-canary-click', 'btn-goto-tab3',
    'trap-note',
    'm1-attached',
    'm1-suggested', 'm1-scammer-input', 'btn-m1-generate', 'm1-thread',
    'm1-thread-empty', 'm1-foot', 'm1-provider', 'm1-attached', 'm1-gate-note',
    'btn-m1-copy', 'btn-m1-copy-out', 'case-briefing', 'brief-toggle',
    'brief-body', 'brief-meta', 'brief-msg', 'brief-msg-wrap', 'brief-facts', 'brief-chev',
    'case-evidence', 'case-evidence-items', 'brief-action-wrap', 'brief-action',
    'brief-score-pill', 'brief-score-pill-n', 'brief-score-pill-t', 'brief-more',
    'brief-principles', 'brief-principles-wrap', 'brief-layers', 'brief-layers-wrap',
    'brief-reports', 'brief-reports-wrap', 'btn-m1-receipt-dl', 'btn-m1-receipt-copy',
    'btn-m1-use', 'btn-m1-receipt', 'copilot-receipt-box',
    'copilot-receipt-empty', 'copilot-receipt-img',
    'cloud-form', 'm2-relation', 'm2-name', 'm2-excuse', 'm2-custom',
    'm2-custom-wrap', 'btn-m2-deploy', 'cloud-terminal', 'cloud-chat-box',
    'cloud-case-chip', 'cloud-status-text', 'cloud-node-name',
    'm2-scammer-input', 'btn-m2-send', 'btn-m2-sim', 'btn-m2-reset',
    'banner-case-id', 'banner-hash', 'ev-upi-list', 'ev-bank-list',
    'ev-device', 'ev-transcript',
    'kpi-reports', 'kpi-blacklisted', 'kpi-cases', 'kpi-resolved',
    'blacklist-search-input', 'trends-blacklist-tbody', 'blacklist-count',
    'category-bars',
    'analyze-label', 'bait-label', 'chat-status-text'
  ].forEach((id) => { ui[id] = document.getElementById(id); });
}

/* Cache immediately: i18n.js (loaded first) fires i18n:changed from its own
   DOMContentLoaded listener, which runs before ours — the panels below must
   already resolve. The DOM is parsed; the script tag sits at the end of body. */
cacheDom();

/* --------------------------------------------------------------------------
   Toasts (replace every alert())
   -------------------------------------------------------------------------- */
function toast(message, type = 'info', duration = 4200) {
  if (!ui['toast-region']) return;

  const icon = type === 'error' ? '#i-alert' : type === 'success' ? '#i-check' : '#i-info';
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.innerHTML = `<svg aria-hidden="true"><use href="${icon}"></use></svg><span></span>`;
  el.querySelector('span').textContent = message;

  ui['toast-region'].appendChild(el);
  const remove = () => {
    el.classList.add('is-leaving');
    setTimeout(() => el.remove(), 220);
  };
  setTimeout(remove, duration);
  el.addEventListener('click', remove);
}

function toastFromError(err, fallbackKey = 'toast_error_generic') {
  console.error(err);
  const isNetwork = err instanceof TypeError || (err && err.message && /fetch|network/i.test(err.message));
  toast(isNetwork ? t('toast_error_network') : t(fallbackKey), 'error');
}

/* --------------------------------------------------------------------------
   Tabs
   -------------------------------------------------------------------------- */
function initTabs() {
  document.querySelectorAll('[role="tab"]').forEach((tab) => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    tab.addEventListener('keydown', (e) => {
      const keys = ['ArrowRight', 'ArrowLeft', 'Home', 'End'];
      if (!keys.includes(e.key)) return;
      e.preventDefault();
      const tabs = Array.from(document.querySelectorAll('#desktop-tablist [role="tab"]'));
      const i = tabs.indexOf(tab);
      let next = i;
      if (e.key === 'ArrowRight') next = (i + 1) % tabs.length;
      if (e.key === 'ArrowLeft') next = (i - 1 + tabs.length) % tabs.length;
      if (e.key === 'Home') next = 0;
      if (e.key === 'End') next = tabs.length - 1;
      tabs[next].focus();
      switchTab(tabs[next].dataset.tab);
    });
  });

  ui['hamburger-btn'].addEventListener('click', () => {
    const open = ui['mobile-tablist'].classList.toggle('is-open');
    ui['hamburger-btn'].setAttribute('aria-expanded', String(open));
  });
}

function switchTab(targetId, scrollEl) {
  document.querySelectorAll('[role="tab"]').forEach((tab) => {
    const active = tab.dataset.tab === targetId;
    tab.setAttribute('aria-selected', String(active));
    if (tab.closest('[role="tablist"]')) tab.tabIndex = active ? 0 : -1;
  });

  document.querySelectorAll('.tab-content-pane').forEach((pane) => {
    pane.classList.toggle('is-active', pane.id === targetId);
  });

  ui['mobile-tablist'].classList.remove('is-open');
  ui['hamburger-btn'].setAttribute('aria-expanded', 'false');

  if (targetId === 'tab-trends') loadSummary();
  if (targetId === 'tab-proof') loadEvidence();
  if (targetId === 'tab-honeypot') {
    renderTargetBar();
    syncCoPilotPanel();
    seedThread();
    syncCaseGate();
  }

  scrollToPane(scrollEl || document.getElementById(targetId));
}

/** Eased window scroll driven by rAF, so it animates regardless of
 *  browser smooth-scroll settings. Returns true if it started animating. */
function smoothScrollTo(target) {
  const dest = Math.max(0, Math.round(target));
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const root = document.documentElement;
  const start = Math.round(window.pageYOffset);
  const dist = dest - start;

  if (reduce || Math.abs(dist) < 2) {
    window.scrollTo(0, dest);
    return false;
  }

  const duration = Math.min(900, Math.max(320, Math.abs(dist) * 0.42));
  const t0 = performance.now();
  const prevBehaviour = root.style.scrollBehavior;
  root.style.scrollBehavior = 'auto'; // stop CSS smooth-scroll from doubling up

  const easeInOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

  const step = (now) => {
    const p = Math.min(1, (now - t0) / duration);
    window.scrollTo(0, start + dist * easeInOut(p));
    if (p < 1) {
      requestAnimationFrame(step);
    } else {
      window.scrollTo(0, dest);
      root.style.scrollBehavior = prevBehaviour;
    }
  };
  requestAnimationFrame(step);
  return true;
}

/** Scrolls to a tab pane, clearing the sticky header. */
function scrollToPane(pane) {
  if (!pane) return false;
  const header = document.querySelector('.site-header');
  const offset = (header ? header.offsetHeight : 0) + 20;
  const top = pane.getBoundingClientRect().top + window.scrollY - offset;
  return smoothScrollTo(top);
}

function initGlobalHandlers() {
  document.querySelectorAll('[data-goto-tab]').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      switchTab(el.dataset.gotoTab, document.getElementById(el.dataset.gotoTab));
    });
  });

  document.querySelectorAll('[data-copy-target]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const target = document.getElementById(btn.dataset.copyTarget);
      const text = target ? target.innerText.trim() : '';
      if (!text) { toast(t('copy_nothing'), 'info'); return; }
      try {
        await navigator.clipboard.writeText(text);
        toast(t('copied_toast'), 'success', 2400);
      } catch (err) {
        toast(t('toast_error_generic'), 'error');
      }
    });
  });
}

async function checkHealth() {
  try {
    await fetch('/api/health');
  } catch (err) {
    console.warn('health check failed', err);
  }
}

/* --------------------------------------------------------------------------
   Tab 1 · Checker
   -------------------------------------------------------------------------- */
function initChecker() {
  const { 'quick-search-input': quick, 'quick-search-btn': quickBtn } = ui;

  quickBtn.addEventListener('click', () => {
    const value = quick.value.trim();
    if (!value) { toast(t('t1_empty_note'), 'info'); quick.focus(); return; }
    runLookup(value);
  });

  quick.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') quickBtn.click();
  });

  ui['chip-scam-upi'].addEventListener('click', () => {
    quick.value = 'bijli.board.pay@ybl';
    runLookup(quick.value);
  });

  ui['chip-scam-msg'].addEventListener('click', () => {
    ui['scam-msg-input'].value =
      'Dear Consumer, your electricity will be disconnected tonight 9:30 PM because last month bill was not updated. Contact officer 9876543210 or pay Rs 45 on UPI bijli.board.pay@ybl.';
    runLookup(ui['scam-msg-input'].value);
  });

  ui['analyze-msg-btn'].addEventListener('click', () => {
    const value = ui['scam-msg-input'].value.trim()
                  || ui['quick-search-input'].value.trim();
    if (!value) { toast(t('t1_empty_note'), 'info'); ui['scam-msg-input'].focus(); return; }
    runDeepAnalyze(value);
  });

  ui['btn-clear-tab1'].addEventListener('click', () => {
    quick.value = '';
    ui['scam-msg-input'].value = '';
    ui['scam-img-input'].value = '';
    if (ui['scam-audio-input']) ui['scam-audio-input'].value = '';
    if (ui['qr-payload-input']) ui['qr-payload-input'].value = '';
    if (ui['qr-row']) ui['qr-row'].classList.add('is-hidden');
    if (ui['attach-qr-btn']) ui['attach-qr-btn'].classList.remove('is-active');
    if (ui['attach-audio-btn']) ui['attach-audio-btn'].classList.remove('is-active');
    ui['dropzone-box'].classList.remove('is-active');
    if (ui['attach-status']) {
      ui['attach-status'].textContent = '';
      ui['attach-status'].classList.add('is-hidden');
    }
    state.lastVerdict = null;
    state.lastReport = null;
    ui['result-placeholder'].classList.remove('is-hidden');
    ui['result-loading'].classList.add('is-hidden');
    ui['result-active-content'].classList.add('is-hidden');
    ui['bait-preview-modal'].classList.add('is-hidden');
    if (ui['principles-panel']) ui['principles-panel'].classList.add('is-hidden');
    if (ui['layers-panel']) ui['layers-panel'].classList.add('is-hidden');
    if (ui['verdict-meta']) ui['verdict-meta'].classList.add('is-hidden');
    state.latestBait = null;
  });

  // Dropzone — click, keyboard and drag/drop (image → real OCR endpoint).
  const fileInput = ui['scam-img-input'];
  ui['dropzone-box'].addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => handleFile(fileInput.files && fileInput.files[0]));

  ['dragenter', 'dragover'].forEach((evt) =>
    ui['dropzone-box'].addEventListener(evt, (e) => {
      e.preventDefault();
      ui['dropzone-box'].classList.add('is-dragover');
    })
  );
  ['dragleave', 'drop'].forEach((evt) =>
    ui['dropzone-box'].addEventListener(evt, (e) => {
      e.preventDefault();
      ui['dropzone-box'].classList.remove('is-dragover');
    })
  );
  ui['dropzone-box'].addEventListener('drop', (e) => {
    if (e.dataTransfer && e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  });

  function setAttachStatus(text) {
    const el = ui['attach-status'];
    if (!el) return;
    el.textContent = text || '';
    el.classList.toggle('is-hidden', !text);
  }

  function handleFile(file) {
    if (!file) return;
    if (!/^image\//.test(file.type)) {
      toast(t('attach_wrong_type'), 'error');
      return;
    }
    setAttachStatus(`${t('attach_reading')} ${file.name}`);
    uploadAndAnalyze('/api/checker/analyze-image', file, 'IMAGE_OCR')
      .catch(() => setAttachStatus(''))
      .finally(() => { ui['dropzone-box'].classList.remove('is-active'); });
    ui['dropzone-box'].classList.add('is-active');
  }

  // ── Voice note → /api/checker/analyze-audio ──────────────────────────────
  const audioInput = ui['scam-audio-input'];
  ui['attach-audio-btn'].addEventListener('click', () => audioInput.click());
  audioInput.addEventListener('change', () => {
    const file = audioInput.files && audioInput.files[0];
    if (!file) return;
    if (!/^audio\//.test(file.type) && !/\.(mp3|wav|m4a|ogg|aac|opus)$/i.test(file.name)) {
      toast(t('attach_wrong_type'), 'error');
      return;
    }
    ui['attach-audio-btn'].classList.add('is-active');
    setAttachStatus(`${t('attach_reading')} ${file.name}`);
    uploadAndAnalyze('/api/checker/analyze-audio', file, 'VOICE_AUDIO')
      .catch(() => setAttachStatus(''))
      .finally(() => ui['attach-audio-btn'].classList.remove('is-active'));
  });

  // ── UPI QR payload → /api/checker/analyze-qr ─────────────────────────────
  ui['attach-qr-btn'].addEventListener('click', () => {
    const row = ui['qr-row'];
    const open = row.classList.toggle('is-hidden');
    ui['attach-qr-btn'].classList.toggle('is-active', !open);
    if (!open) ui['qr-payload-input'].focus();
  });
  const submitQr = () => {
    const payload = (ui['qr-payload-input'].value || '').trim();
    if (!payload) { toast(t('qr_empty'), 'info'); ui['qr-payload-input'].focus(); return; }
    setAttachStatus(t('attach_reading'));
    postJson('/api/checker/analyze-qr', { payload, lang: currentLanguage })
      .then((data) => { showAnalyzeResult(data); setAttachStatus(''); })
      .catch((err) => { setAttachStatus(''); toastFromError(err, 'toast_error_network'); });
  };
  ui['qr-analyze-btn'].addEventListener('click', submitQr);
  ui['qr-payload-input'].addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitQr();
  });

  ui['btn-generate-bait'].addEventListener('click', generateBait);
  ui['btn-copy-bait-text'].addEventListener('click', copyBaitReply);

  // ── Hand the finished case to Tab 2 (POST /api/honeypot/create-case) ─────
  ui['btn-send-to-honeypot'].addEventListener('click', handOverToHoneypot);
}

/** Shared POST helper so every input mode resolves to the same response shape. */
async function postJson(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Uploads a file to one of the multipart investigation endpoints. */
async function uploadAndAnalyze(url, file, inputType) {
  const analyzeBtn = ui['analyze-msg-btn'];
  const analyzeLabel = ui['analyze-label'];
  beginBusy();

  try {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('lang', currentLanguage);
    const res = await fetch(url, { method: 'POST', body: fd });
    if (!res.ok) {
      let detail = '';
      try { detail = (await res.json()).detail || ''; } catch (e) { /* ignore */ }
      throw new Error(detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    showAnalyzeResult(data);
    return data;
  } catch (err) {
    endBusy();
    ui['result-loading'].classList.add('is-hidden');
    ui['result-placeholder'].classList.remove('is-hidden');
    toast(err && err.message && !/^HTTP /.test(err.message)
      ? err.message : t('toast_error_network'), 'error');
    throw err;
  } finally {
    ui['result-side-card'].setAttribute('aria-busy', 'false');
    analyzeBtn.disabled = false;
    analyzeLabel.setAttribute('data-i18n', 'btn_analyze');
    analyzeLabel.textContent = t('btn_analyze');
  }
}

function beginBusy() {
  ui['result-placeholder'].classList.add('is-hidden');
  ui['result-active-content'].classList.add('is-hidden');
  ui['result-loading'].classList.remove('is-hidden');
  ui['result-side-card'].setAttribute('aria-busy', 'true');
  ui['analyze-msg-btn'].disabled = true;
}

function endBusy() {
  ui['result-side-card'].setAttribute('aria-busy', 'false');
  ui['analyze-msg-btn'].disabled = false;
  ui['analyze-label'].setAttribute('data-i18n', 'btn_analyze');
  ui['analyze-label'].textContent = t('btn_analyze');
}

/**
 * Single funnel for every `/analyze*` response: hides loading, stores the
 * verdict, then renders gauge → banner → principles → layers → identifiers.
 */
function showAnalyzeResult(data) {
  ui['result-loading'].classList.add('is-hidden');
  ui['result-active-content'].classList.remove('is-hidden');
  state.lastReport = data;

  const normalized = {
    risk_score: data.final_score,
    threat_level: data.threat_level,
    category: data.primary_category,
    reports_count: (data.blacklist_hits || []).length,
    action_guidance: data.citizen_action,
    extracted_entities: {
      upis: (data.extracted_entities || {}).upis || [],
      phones: (data.extracted_entities || {}).phones || [],
      bank_accounts: (data.extracted_entities || {}).bank_accounts || [],
      ifsc_codes: (data.extracted_entities || {}).ifsc_codes || [],
    },
    counter_bait_available: data.counter_bait_available,
  };
  state.lastVerdict = normalized;
  state.originalMessage = (ui['scam-msg-input'].value || '').trim() || state.originalMessage;
  syncBaitAmount();
  state.targetCategory = normalized.category || state.targetCategory;
  state.targetPhone = (normalized.extracted_entities.phones || [])[0] || state.targetPhone;

  renderVerdict(normalized);
  renderMeta(data);
  renderPrinciples(data);
  renderLayers(data);
  endBusy();
}

/** Provenance chips: which engine answered, on what, under which case id. */
function renderMeta(data) {
  const wrap = ui['verdict-meta'];
  if (!wrap) return;
  const model = data.ai_source === 'local_nli'
    ? (data.model ? `${t('meta_local_ai')} · ${data.model}` : t('meta_local_ai'))
    : (data.ai_source && data.ai_source !== 'local_engine'
      ? `Gemini · ${data.ai_source}`
      : t('meta_local'));
  const parts = [
    [ui['meta-model'], model],
    [ui['meta-input'], data.input_type || 'TEXT'],
    [ui['meta-case'], data.case_id || data.investigation_id || '—'],
  ];
  parts.forEach(([el, value]) => {
    if (el) el.querySelector('.verdict-meta__val').textContent = value;
  });
  wrap.classList.remove('is-hidden');
}

/** 4-Principle Cognitive AI Detective breakdown (spec §4). */
function renderPrinciples(data) {
  const panel = ui['principles-panel'];
  const list = ui['principles-list'];
  if (!panel || !list) return;

  const rows = (data.principles || []).filter((p) => p && p.name);
  if (!rows.length) { panel.classList.add('is-hidden'); return; }

  list.innerHTML = rows.map((p, i) => {
    const score = Number(p.score) || 0;
    const total = rows.reduce((s, r) => s + (Number(r.score) || 0), 0) || 100;
    const pct = Math.max(0, Math.min(100, Math.round((score / total) * 100)));
    const findings = (p.findings || []).filter(Boolean);
    const weight = i === 0 ? 'high' : (i < 3 ? 'mid' : 'low');
    const items = findings.length
      ? findings.map((f) => `<li>${escapeHtml(f)}</li>`).join('')
      : `<li>${escapeHtml(t('principle_no_signal'))}</li>`;
    return `
    <div class="principle-item" data-weight="${weight}">
      <div class="principle-head">
        <span class="principle-name">${escapeHtml(p.name)}</span>
        <span class="principle-pts">${pct}%</span>
      </div>
      <div class="principle-bar-wrap">
        <span class="principle-bar" style="width:0%" data-w="${pct}"></span>
      </div>
      <ul class="principle-findings${findings.length ? '' : ' is-empty'}">${items}</ul>
    </div>`;
  }).join('');

  panel.classList.remove('is-hidden');

  // Animate the bars in on the next frame so the width transition plays.
  requestAnimationFrame(() => {
    list.querySelectorAll('.principle-bar').forEach((bar) => {
      bar.style.width = `${bar.dataset.w}%`;
    });
  });
}

/** Hands the current investigation to Tab 2 so the decoy can pick it up. */
async function handOverToHoneypot() {
  const entities = (state.lastVerdict && state.lastVerdict.extracted_entities) || {};
  const btn = ui['btn-send-to-honeypot'];
  btn.disabled = true;
  try {
    const payload = {
      scammer_phone: (entities.phones || [])[0] || null,
      scammer_upi: (entities.upis || [])[0] || null,
      scam_category: (state.lastReport && (state.lastReport.scam_category
        || state.lastReport.primary_category))
        || (state.lastVerdict && state.lastVerdict.category)
        || 'General Suspicious',
      context: (ui['scam-msg-input'].value || '').trim().slice(0, 500) || null,
    };
    const res = await postJson('/api/honeypot/create-case', payload);
    const newCase = (res && res.case_id) || state.activeCaseId;
    if (newCase !== state.activeCaseId) state.copilotHistory = [];
    state.originalMessage = (ui['scam-msg-input'].value || '').trim() || state.originalMessage;
    syncBaitAmount();
    state.lastSuggestion = '';
    state.handoverDone = true;
    state.activeCaseId = newCase;
    state.selectedCase = (res && res.case_id) || state.selectedCase;
    state.targetPhone = (res && res.scammer_phone) || state.targetPhone;
    state.targetCategory = (res && res.scam_category) || state.targetCategory;
    renderTargetBar();
    seedThread();
    toast(t('handover_done'), 'success');
    switchTab('tab-honeypot');
  } catch (err) {
    toastFromError(err, 'toast_error_network');
  } finally {
    btn.disabled = false;
  }
}

/** Quick registry lookup — used by the top search bar only */
async function runLookup(queryText) {
  const analyzeBtn = ui['analyze-msg-btn'];
  const analyzeLabel = ui['analyze-label'];

  ui['result-placeholder'].classList.add('is-hidden');
  ui['result-active-content'].classList.add('is-hidden');
  ui['result-loading'].classList.remove('is-hidden');
  ui['result-side-card'].setAttribute('aria-busy', 'true');
  analyzeBtn.disabled = true;

  try {
    const res = await fetch('/api/checker/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: queryText, lang: currentLanguage })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    ui['result-loading'].classList.add('is-hidden');
    ui['result-active-content'].classList.remove('is-hidden');
    state.lastVerdict = data;
    state.lastReport = null;
    state.targetCategory = data.category || state.targetCategory;
    state.targetPhone = ((data.extracted_entities || {}).phones || [])[0] || state.targetPhone;
    renderVerdict(data);
    renderMeta({ input_type: 'IDENTIFIER_LOOKUP', ai_source: 'local_engine',
                 case_id: t('meta_quick') });
    // Quick lookup is a single registry hit — no layer/principle sweep to show.
    ui['principles-panel'].classList.add('is-hidden');
    ui['layers-panel'].classList.add('is-hidden');
  } catch (err) {
    ui['result-loading'].classList.add('is-hidden');
    ui['result-placeholder'].classList.remove('is-hidden');
    toastFromError(err, 'toast_error_network');
  } finally {
    ui['result-side-card'].setAttribute('aria-busy', 'false');
    analyzeBtn.disabled = false;
    analyzeLabel.setAttribute('data-i18n', 'btn_analyze');
    analyzeLabel.textContent = t('btn_analyze');
  }
}

/** Full investigation — de-obfuscation → 5 OSINT layers → 4-principle detective */
async function runDeepAnalyze(queryText) {
  const analyzeLabel = ui['analyze-label'];

  beginBusy();
  analyzeLabel.removeAttribute('data-i18n');
  analyzeLabel.textContent = t('btn_analyze_busy');

  try {
    const data = await postJson('/api/checker/analyze', {
      query: queryText, lang: currentLanguage, input_type: 'TEXT',
    });
    showAnalyzeResult(data);
  } catch (err) {
    ui['result-loading'].classList.add('is-hidden');
    ui['result-placeholder'].classList.remove('is-hidden');
    toastFromError(err, 'toast_error_network');
  } finally {
    endBusy();
  }
}

function renderVerdict(data) {
  const score = Number(data.risk_score) || 0;

  ui['gauge-score-text'].textContent = `${score}%`;
  ui['radial-gauge-circle'].style.strokeDashoffset = String(CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE);

  const pill = ui['risk-score-pill'];
  const box = ui['risk-banner-box'];
  const title = ui['risk-banner-title'];
  const guidance = ui['risk-banner-guidance'];
  const iconUse = ui['risk-banner-icon'].querySelector('use');

  pill.removeAttribute('data-i18n');

  if (score >= 70) {
    ui['radial-gauge-circle'].style.stroke = 'var(--red-600)';
    ui['gauge-score-text'].style.color = 'var(--red-600)';
    pill.className = 'badge badge--red';
    pill.textContent = `${t('pill_scam')} · ${score}/100`;
    box.className = 'alert-box alert-box-danger';
    iconUse.setAttribute('href', '#i-alert');
  } else if (score >= 40) {
    ui['radial-gauge-circle'].style.stroke = 'var(--amber-600)';
    ui['gauge-score-text'].style.color = 'var(--amber-600)';
    pill.className = 'badge badge--amber';
    pill.textContent = `${t('pill_suspicious')} · ${score}/100`;
    box.className = 'alert-box alert-box-warn';
    iconUse.setAttribute('href', '#i-alert');
  } else {
    ui['radial-gauge-circle'].style.stroke = 'var(--emerald-600)';
    ui['gauge-score-text'].style.color = 'var(--emerald-600)';
    pill.className = 'badge badge--emerald';
    pill.textContent = `${t('pill_safe')} · ${score}/100`;
    box.className = 'alert-box alert-box-safe';
    iconUse.setAttribute('href', '#i-check');
  }

  const isThreat = data.threat_level === 'HIGH_DANGER' || score >= 50;
  title.textContent = `${isThreat ? t('verdict_threat') : t('verdict_clean')}: ${data.category}`;
  guidance.textContent = data.action_guidance || '';

  const entities = data.extracted_entities || {};
  setText('ext-upi-val', (entities.upis || []).join(', '), t('ident_none'));
  setText('ext-phone-val', (entities.phones || []).join(', '), t('ident_none'));

  const banks = [].concat(entities.bank_accounts || [], entities.ifsc_codes || []);
  setText('ext-bank-val', banks.join(', '), t('ident_pending'));
}

function setText(id, value, fallback) {
  const el = ui[id];
  if (!el) return;
  el.textContent = value && value.trim() ? value : fallback;
  el.classList.toggle('badge-mono-red', id === 'ext-upi-val' && Boolean(value));
}

/** Renders the 5-layer breakdown panel */
function renderLayers(data) {
  const panel = document.getElementById('layers-panel');
  const list = document.getElementById('layers-list');
  const dlBtn = document.getElementById('btn-dl-forensic-log');
  if (!panel || !list) return;

  const layers = data.layers || [];
  if (!layers.length) { panel.classList.add('is-hidden'); return; }

  const LAYER_ICONS = ['#i-search', '#i-database', '#i-activity', '#i-sparkles', '#i-lock'];
  const scoreColor = (s) => s >= 70 ? '#ef4444' : s >= 40 ? '#f59e0b' : '#10b981';

  list.innerHTML = layers.map((layer, idx) => {
    const score = layer.score || 0;
    const color = scoreColor(score);
    const flagsHtml = (layer.flags || []).map(f =>
      `<li class="layer-flag">${f.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</li>`
    ).join('');
    return `
    <details class="layer-item" data-score="${score}">
      <summary class="layer-summary">
        <span class="layer-icon" style="color:${color}">
          <svg aria-hidden="true"><use href="${LAYER_ICONS[idx] || '#i-checks'}"></use></svg>
        </span>
        <span class="layer-info">
          <span class="layer-name">${layer.name}</span>
          <span class="layer-score" style="color:${color}">${score}/100</span>
        </span>
        <span class="layer-bar-wrap">
          <span class="layer-bar" style="width:${score}%;background:${color}"></span>
        </span>
      </summary>
      <ul class="layer-flags-list">${flagsHtml || '<li class="layer-flag muted">No flags raised</li>'}</ul>
    </details>`;
  }).join('');

  panel.classList.remove('is-hidden');

  // Forensic log download button
  if (dlBtn && data.forensic_log_url) {
    dlBtn.href = data.forensic_log_url;
    dlBtn.download = `ScamTrap_${data.case_id}_forensic.log`;
    dlBtn.classList.remove('is-hidden');
  }
}

async function generateBait() {
  const btn = ui['btn-generate-bait'];
  const label = ui['bait-label'];
  const upiTarget = ui['ext-upi-val'].textContent.includes('@')
    ? ui['ext-upi-val'].textContent.split(',')[0].trim()
    : 'bijli.board.pay@ybl';
  const amount = ui['custom-bait-amt'].value.trim() || '25,000';
  const senderName = (ui['custom-bait-name'] && ui['custom-bait-name'].value.trim()) || '';

  btn.disabled = true;
  label.removeAttribute('data-i18n');
  label.textContent = t('btn_generating_bait');

  try {
    const res = await fetch('/api/co-pilot/generate-receipt-bait', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scammer_upi: upiTarget, amount, sender_name: senderName, case_id: CASE_ID })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.status !== 'success') throw new Error('bad status');

    state.latestBait = data;
    applyBaitToPanel(data, true);
    ui['bait-receipt-img'].src = data.bait_image.relative_url;
    ui['bait-receipt-img'].alt = `Payment failed receipt for ${upiTarget}`;
    ui['btn-download-bait-img'].href = data.bait_image.relative_url;
    ui['bait-preview-modal'].classList.remove('is-hidden');
    ui['bait-copy-toast'].classList.add('is-hidden');
    ui['bait-preview-modal'].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (err) {
    toastFromError(err, 'toast_bait_failed');
  } finally {
    btn.disabled = false;
    label.setAttribute('data-i18n', 'btn_gen_bait');
    label.textContent = t('btn_gen_bait');
  }
}

async function copyBaitReply() {
  if (!state.latestBait) { toast(t('toast_bait_empty'), 'info'); return; }
  const text = currentLanguage === 'hi'
    ? state.latestBait.recommended_text_hindi
    : state.latestBait.recommended_text_english;
  try {
    await navigator.clipboard.writeText(text);
    ui['bait-copy-toast'].classList.remove('is-hidden');
    setTimeout(() => ui['bait-copy-toast'].classList.add('is-hidden'), 3200);
  } catch (err) {
    toast(t('toast_error_generic'), 'error');
  }
}

/* --------------------------------------------------------------------------
   Tab 2 · Honeypot
   -------------------------------------------------------------------------- */
function initHoneypot() {
  // Accordion — one panel open at a time (spec D).
  document.querySelectorAll('#strategy-acc .acc__btn').forEach((btn) => {
    btn.addEventListener('click', () => toggleAccordion(btn));
  });

  // Mode 1 · Co-Pilot ------------------------------------------------------
  ui['btn-m1-receipt'].addEventListener('click', generateCoPilotReceipt);
  ui['btn-m1-copy'].addEventListener('click', () => copyToClipboard(ui['m1-suggested'].value));
  ui['btn-m1-copy-out'].addEventListener('click', () => copyToClipboard(state.lastSuggestion));
  ui['btn-m1-use'].addEventListener('click', () => {
    if (!state.lastSuggestion) return;
    ui['m1-suggested'].value = state.lastSuggestion;
    ui['m1-suggested'].dataset.dirty = '1';
    ui['m1-suggested'].focus();
  });
  const toggleBrief = () => {
    const open = ui['brief-toggle'].getAttribute('aria-expanded') === 'true';
    const next = String(!open);
    ui['brief-toggle'].setAttribute('aria-expanded', next);
    if (ui['brief-chev']) ui['brief-chev'].setAttribute('aria-expanded', next);
    ui['brief-body'].classList.toggle('is-collapsed', open);
  };
  if (ui['brief-toggle']) ui['brief-toggle'].addEventListener('click', toggleBrief);
  if (ui['brief-chev']) ui['brief-chev'].addEventListener('click', toggleBrief);
  ui['m1-scammer-input'].addEventListener('keydown', (e) => {
    if (e.key === 'Enter') generateNextReply();
  });
  ui['btn-m1-generate'].addEventListener('click', generateNextReply);
  ui['btn-m1-receipt-dl'].addEventListener('click', () => {
    const img = ui['copilot-receipt-img'];
    if (!img || !img.src || img.hidden) { toast(t('t2_m1_img_empty'), 'error'); return; }
    const link = document.createElement('a');
    link.href = img.src;
    link.download = `receipt_${String(state.activeCaseId || 'case').replace(/[^A-Za-z0-9-]/g, '')}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  });
  ui['btn-m1-receipt-copy'].addEventListener('click', () => {
    const text = (ui['m1-suggested'] && ui['m1-suggested'].value.trim()) || state.lastSuggestion;
    if (!text) { toast(t('t2_m1_img_empty'), 'error'); return; }
    copyToClipboard(text);
  });

  // Mode 2 · Cloud AI node -------------------------------------------------
  ui['m2-excuse'].addEventListener('change', () => {
    ui['m2-custom-wrap'].hidden = ui['m2-excuse'].value !== 'custom';
    if (ui['m2-excuse'].value === 'custom') ui['m2-custom'].focus();
  });
  ui['cloud-form'].addEventListener('submit', (e) => { e.preventDefault(); deployCloudNode(); });
  ui['btn-m2-send'].addEventListener('click', sendCloudMessage);
  ui['m2-scammer-input'].addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendCloudMessage();
  });
  ui['btn-m2-sim'].addEventListener('click', () => {
    ui['m2-scammer-input'].value = t('t2_m2_sim_text');
    sendCloudMessage();
  });
  ui['btn-m2-reset'].addEventListener('click', resetCloudNode);

  // Chrome -----------------------------------------------------------------
  ui['btn-refresh-status'].addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    try { await loadEvidence(); } catch (err) { console.error(err); }
    renderTargetBar();
    syncCoPilotPanel();
    seedThread();
    syncCaseGate();
    toast(t('t2_refreshed'), 'success');
    btn.disabled = false;
  });
  ui['btn-test-canary-click'].addEventListener('click', () => {
    const trap = state.trapUrl || (state.latestBait && state.latestBait.trap_url);
    if (!trap) return;
    const caseId = state.activeCaseId || state.selectedCase || CASE_ID;
    const url = trap.includes('case=') ? trap : `${trap}?case=${encodeURIComponent(caseId)}`;
    window.open(url, '_blank', 'noopener');
    setTimeout(loadEvidence, 1500);
  });
  ui['btn-goto-tab3'].addEventListener('click', () => switchTab('tab-proof'));
}

function toggleAccordion(btn) {
  const item = btn.closest('.acc__item');
  const panel = document.getElementById(btn.getAttribute('aria-controls'));
  const isOpen = btn.getAttribute('aria-expanded') === 'true';

  document.querySelectorAll('#strategy-acc .acc__btn').forEach((b) => {
    b.setAttribute('aria-expanded', 'false');
    b.closest('.acc__item').classList.remove('is-open');
    const p = document.getElementById(b.getAttribute('aria-controls'));
    if (p) p.hidden = true;
  });

  if (!isOpen) {
    btn.setAttribute('aria-expanded', 'true');
    item.classList.add('is-open');
    if (panel) panel.hidden = false;
  }
}

/** Everything the old target bar showed now lives in the briefing card. */
function renderTargetBar() {
  renderBriefing();
  renderEvidenceStrip();
  syncCaseGate();
}

/**
 * The Step 1 hand-over card: original message, verdict facts, extracted
 * identifiers and the action Step 1 recommended - the same panel both modes
 * read from, so nothing the engine already learned is lost.
 */
function renderBriefing() {
  const card = ui['case-briefing'];
  if (!card) return;

  const report = state.lastReport || {};
  const verdict = state.lastVerdict || {};
  const original = state.originalMessage || report.raw_input
    || (ui['scam-msg-input'] && ui['scam-msg-input'].value.trim()) || '';
  const category = verdict.category || report.primary_category || state.targetCategory || '';
  const hasAnything = original || verdict.risk_score || category || verdict.action_guidance
    || (report.principles || []).length;
  card.classList.toggle('is-hidden', !hasAnything);

  if (ui['brief-msg-wrap']) {
    ui['brief-msg-wrap'].classList.toggle('is-hidden', !original);
    if (original && ui['brief-msg']) ui['brief-msg'].textContent = original;
  }

  const entities = verdict.extracted_entities || report.extracted_entities || {};
  const facts = [];
  if (category) facts.push([t('t2_lbl_category'), category]);
  const amount = state.baitAmount || detectAmount(original);
  if (amount) facts.push([t('t2_brief_amount'), `\u20b9${amount}`]);
  const phone = (entities.phones || [])[0] || state.targetPhone;
  if (phone && !/^(UNSPECIFIED|unknown|n\/a|-)$/i.test(phone)) facts.push([t('t2_lbl_phone'), phone]);
  if (verdict.reports_count) facts.push([t('t2_ev_reports'), String(verdict.reports_count)]);
  const summary = report.citizen_summary || '';
  if (summary) facts.push([t('t2_brief_summary'), summary]);
  const caseId = state.activeCaseId || state.selectedCase || report.case_id;
  if (caseId) facts.push([t('t2_lbl_case'), caseId]);

  if (ui['brief-facts']) {
    ui['brief-facts'].innerHTML = facts.map(([k, v]) => `<div class="brief__fact">
      <span class="brief__fact-k">${escapeHtml(k)}</span>
      <span class="brief__fact-v">${escapeHtml(v)}</span></div>`).join('');
    ui['brief-facts'].classList.toggle('is-hidden', !facts.length);
  }

  if (ui['brief-score-pill']) {
    const has = verdict.risk_score != null;
    ui['brief-score-pill'].classList.toggle('is-hidden', !has);
    if (has) {
      const level = String(verdict.threat_level || '');
      const tone = /HIGH/.test(level) ? 'high' : (/MODERATE|MEDIUM/.test(level) ? 'mid' : 'low');
      ui['brief-score-pill-n'].textContent = `${verdict.risk_score}%`;
      ui['brief-score-pill-t'].textContent = level.replace(/_/g, ' ');
      ui['brief-score-pill'].className = `brief__pill brief__pill--${tone}`;
    }
  }

  const guidance = verdict.action_guidance || report.citizen_action || '';
  if (ui['brief-action-wrap']) {
    ui['brief-action-wrap'].classList.toggle('is-hidden', !guidance);
    if (guidance && ui['brief-action']) ui['brief-action'].textContent = guidance;
  }

  if (ui['brief-meta']) {
    const bits = [category, amount ? `\u20b9${amount}` : '', report.input_type];
    ui['brief-meta'].textContent = bits.filter(Boolean).join('  \u00b7  ') || '\u2014';
  }

  const principles = (report.principles || []).filter((p) => p && p.name);
  if (ui['brief-principles-wrap']) {
    ui['brief-principles-wrap'].classList.toggle('is-hidden', !principles.length);
    ui['brief-principles'].innerHTML = principles.map((p) => {
      const findings = (p.findings || []).filter(Boolean).slice(0, 2);
      return `<li class="brief__li"><span class="brief__li-k">${escapeHtml(p.name)}</span>
        <span class="brief__li-s mono">${escapeHtml(String(p.score == null ? '' : p.score))}</span>
        ${findings.map((f) => `<span class="brief__li-f">${escapeHtml(f)}</span>`).join('')}</li>`;
    }).join('');
  }

  const layers = (report.layers || []).filter(Boolean);
  if (ui['brief-layers-wrap']) {
    ui['brief-layers-wrap'].classList.toggle('is-hidden', !layers.length);
    ui['brief-layers'].innerHTML = layers.map((l) => `<li class="brief__li">
      <span class="brief__li-k">${escapeHtml(l.name || l.title || l.layer || '')}</span>
      <span class="brief__li-s mono">${escapeHtml(String(l.score == null ? '' : l.score))}</span>
      <span class="brief__li-f">${escapeHtml(l.evidence && l.evidence.summary ? l.evidence.summary : '')}</span>
      </li>`).join('');
  }

  const hits = (report.blacklist_hits || []).filter(Boolean);
  if (ui['brief-reports-wrap']) {
    ui['brief-reports-wrap'].classList.toggle('is-hidden', !hits.length);
    ui['brief-reports'].innerHTML = hits.slice(0, 6).map((h) => {
      const label = typeof h === 'string' ? h
        : (h.value || h.identifier || h.reason || h.source || h.name || JSON.stringify(h));
      const kind = typeof h === 'string' ? '' : (h.type || h.category || '');
      return `<li class="brief__li"><span class="brief__li-k">${escapeHtml(label)}</span>
        ${kind ? `<span class="brief__li-s mono">${escapeHtml(kind)}</span>` : ''}</li>`;
    }).join('');
  }

  if (ui['brief-more']) {
    ui['brief-more'].classList.toggle('is-hidden', !(principles.length || layers.length || hits.length));
  }
}

/** Everything Step 1 found that is still useful while you chat (click = copy). */
function renderEvidenceStrip() {
  const wrap = ui['case-evidence'];
  const box = ui['case-evidence-items'];
  if (!wrap || !box) return;

  const verdict = state.lastVerdict || {};
  const ent = verdict.extracted_entities || {};
  const items = [];
  (ent.upis || []).slice(0, 2).forEach((v) => items.push(['UPI', v]));
  (ent.phones || []).slice(0, 2).forEach((v) => items.push(['Phone', v]));
  (ent.bank_accounts || []).slice(0, 2).forEach((v) => items.push(['A/C', v]));
  (ent.ifsc_codes || []).slice(0, 2).forEach((v) => items.push(['IFSC', v]));
  if (verdict.reports_count) items.push([t('t2_ev_reports'), String(verdict.reports_count)]);

  wrap.classList.toggle('is-hidden', !items.length);
  box.innerHTML = items.map(([k, val]) => `<button type="button" class="ev-chip"
      data-value="${escapeHtml(val)}"><span class="ev-chip__k">${escapeHtml(k)}</span>
      <span class="ev-chip__v mono">${escapeHtml(val)}</span></button>`).join('');
  box.querySelectorAll('.ev-chip').forEach((btn) => {
    btn.addEventListener('click', () => copyToClipboard(btn.dataset.value));
  });
}

/** Pulls the figure the scammer is demanding out of their own message. */
function detectAmount(text) {
  const raw = String(text || '');
  if (!raw) return '';
  const tagged = raw.match(/(?:\u20b9|rs\.?|inr)\s*([\d][\d,]{0,12})/i);
  const bare = raw.match(/\b(\d{1,3}(?:,\d{2,3})+|\d{2,6})\b/);
  const digits = (tagged ? tagged[1] : (bare ? bare[1] : '')).replace(/[^\d]/g, '');
  if (!digits || Number(digits) < 1) return '';
  return Number(digits).toLocaleString('en-IN');
}

function syncBaitAmount() {
  const found = detectAmount(state.originalMessage)
    || detectAmount(state.lastReport && state.lastReport.raw_input);
  if (found) {
    state.baitAmount = found;
    if (ui['custom-bait-amt']) ui['custom-bait-amt'].value = found;
  }
  return state.baitAmount || (ui['custom-bait-amt'] && ui['custom-bait-amt'].value) || '499';
}

/** Rebuilds the Mode 1 thread from history (or seeds it with the Tab 1 message). */
function seedThread() {
  const box = ui['m1-thread'];
  if (!box) return;
  box.querySelectorAll('.m1__b').forEach((el) => el.remove());
  const history = state.copilotHistory || [];
  if (history.length) {
    history.forEach((m) => appendThread(m.role, m.text, { quiet: true }));
  } else if (state.originalMessage) {
    state.copilotHistory = [{ role: 'scammer', text: state.originalMessage }];
    appendThread('scammer', state.originalMessage, { quiet: true });
  }
  const empty = ui['m1-thread-empty'];
  if (empty) empty.hidden = box.querySelectorAll('.m1__b').length > 0;
}

/** One bubble in the Mode 1 transcript. `ai` bubbles carry a copy action. */
function appendThread(role, text, meta) {
  const box = ui['m1-thread'];
  if (!box || !text) return;
  const empty = ui['m1-thread-empty'];
  if (empty) empty.hidden = true;

  const isMe = role === 'ai';
  const row = document.createElement('div');
  row.className = `m1__b ${isMe ? 'm1__b--me' : 'm1__b--them'}`;
  row.innerHTML = `<span class="m1__who">${escapeHtml(isMe ? t('t2_who_you') : t('t2_who_them'))}</span>`;

  const bubble = document.createElement('div');
  bubble.className = 'm1__bubble';
  bubble.textContent = text;
  row.appendChild(bubble);

  if (isMe) {
    const bar = document.createElement('div');
    bar.className = 'm1__bbar';
    const copy = document.createElement('button');
    copy.type = 'button';
    copy.className = 'm1__bact';
    copy.innerHTML = `<svg aria-hidden="true"><use href="#i-copy"></use></svg><span>${escapeHtml(t('btn_copy'))}</span>`;
    copy.addEventListener('click', () => copyToClipboard(text));
    bar.appendChild(copy);
    if (meta && meta.attached) {
      const chip = document.createElement('span');
      chip.className = 'chip chip--emerald';
      chip.textContent = t('t2_attached');
      bar.appendChild(chip);
    }
    row.appendChild(bar);
  }

  box.appendChild(row);
  box.scrollTop = box.scrollHeight;
}

/** Copies a Tab 1 generated receipt into Mode 1 so step 1 is never empty. */
function applyBaitToPanel(data, force) {
  if (!data || !data.bait_image) return;
  const ta = ui['m1-suggested'];
  if (!force && ta && ta.dataset.dirty === '1') return;
  const src = data.bait_image.relative_url || data.bait_image.filepath;
  if (src && ui['copilot-receipt-img']) {
    ui['copilot-receipt-img'].src = src;
    ui['copilot-receipt-img'].hidden = false;
    if (ui['copilot-receipt-empty']) ui['copilot-receipt-empty'].hidden = true;
  }
  if (ta) {
    const text = currentLanguage === 'hi'
      ? data.recommended_text_hindi
      : data.recommended_text_english;
    if (text) { ta.value = text; ta.dataset.dirty = '1'; }
  }
}

function syncCoPilotPanel() {
  if (state.latestBait) applyBaitToPanel(state.latestBait, false);
}

async function copyToClipboard(text) {
  const value = String(text || '').trim();
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    toast(t('btn_copy'), 'success');
  } catch (err) {
    console.error(err);
    toast(t('toast_error_generic'), 'error');
  }
}

/** Mode 1 · step 1 — the U16 failure PNG that gets sent as the "screenshot". */
async function ensureReceipt() {
  const img = ui['copilot-receipt-img'];
  if (img && !img.hidden && img.src) return;
  await generateCoPilotReceipt();
}

async function generateCoPilotReceipt() {
  const btn = ui['btn-m1-receipt'];
  const label = btn.querySelector('span');
  const prevLabel = label ? label.textContent : '';
  btn.disabled = true;
  if (label) label.textContent = t('btn_sending');

  const entities = (state.lastVerdict && state.lastVerdict.extracted_entities) || {};
  const upi = (entities.upis || [])[0] || 'bijli.board.pay@ybl';
  const amount = syncBaitAmount();
  const sender = (ui['custom-bait-name'] && ui['custom-bait-name'].value) || 'Rahul Sharma';

  try {
    const res = await postJson('/api/co-pilot/generate-receipt-bait', {
      scammer_upi: upi, amount, sender_name: sender, case_id: CASE_ID
    });
    const src = `/api/co-pilot/fake-receipt?upi=${encodeURIComponent(upi)}`
      + `&amount=${encodeURIComponent(amount)}&sender_name=${encodeURIComponent(sender)}`;
    applyBaitToPanel({
      bait_image: { relative_url: src },
      recommended_text_hindi: res && res.recommended_text_hindi,
      recommended_text_english: res && res.recommended_text_english
    }, true);
    state.trapUrl = (res && res.trap_url) || state.trapUrl;
  } catch (err) {
    state.cloudCaseId = null;
    ui['cloud-terminal'].hidden = true;
    toastFromError(err, 'toast_error_network');
  } finally {
    btn.disabled = false;
    if (label) label.textContent = prevLabel;
  }
}

/** Mode 1 · step 3 - one more exchange, fed by the whole Step 1 brief. */
function buildCaseContext() {
  const verdict = state.lastVerdict || {};
  const report = state.lastReport || {};
  return {
    original_message: state.originalMessage
      || (ui['scam-msg-input'] && ui['scam-msg-input'].value.trim())
      || (state.baitContext || ''),
    primary_category: verdict.category || report.primary_category || state.targetCategory || '',
    threat_level: verdict.threat_level || report.threat_level || '',
    risk_score: verdict.risk_score != null ? verdict.risk_score : report.final_score,
    reports_count: verdict.reports_count || (report.blacklist_hits || []).length,
    action_guidance: verdict.action_guidance || report.citizen_action || '',
    amount: state.baitAmount || detectAmount(state.originalMessage || '') || '',
    entities: verdict.extracted_entities || report.extracted_entities || {},
  };
}

function syncCaseGate() {
  const ready = !!state.handoverDone;
  const note = ui['m1-gate-note'];
  if (note) note.classList.toggle('is-hidden', ready);
  const input = ui['m1-scammer-input'];
  if (input) {
    input.disabled = !ready;
    input.placeholder = ready ? t('ph_m1_scammer') : t('t2_need_case');
  }
  const btn = ui['btn-m1-generate'];
  if (btn) btn.disabled = !ready;
}

async function generateNextReply() {
  if (!state.handoverDone) {
    toast(t('t2_need_case'), 'error');
    switchTab('tab-checker');
    return;
  }
  const input = ui['m1-scammer-input'];
  const text = input.value.trim();
  if (!text) { input.focus(); return; }

  const btn = ui['btn-m1-generate'];
  btn.disabled = true;
  appendThread('scammer', text);

  try {
    const res = await postJson('/api/co-pilot/next-reply', {
      scam_category: state.targetCategory
        || (state.lastVerdict && state.lastVerdict.category)
        || 'General Suspicious',
      chat_history: state.copilotHistory || [],
      scammer_new_message: text,
      case_context: buildCaseContext()
    });
    const reply = (res && res.suggested_reply) || '';
    const sendImage = Boolean(res && res.send_image);
    state.copilotHistory = (state.copilotHistory || []).concat([
      { role: 'scammer', text },
      { role: 'ai', text: reply }
    ]);
    state.lastSuggestion = reply;
    appendThread('ai', reply, { attached: sendImage });

    if (ui['m1-suggested']) {
      ui['m1-suggested'].value = reply;
      ui['m1-suggested'].dataset.dirty = '1';
    }
    if (ui['m1-provider']) {
      const secs = res && res.elapsed_ms ? `${(res.elapsed_ms / 1000).toFixed(1)}s` : '';
      ui['m1-provider'].textContent = [t('t2_ai_drafted'), secs].filter(Boolean).join(' · ');
    }
    if (ui['m1-attached']) ui['m1-attached'].classList.toggle('is-hidden', !sendImage);
    if (ui['m1-foot']) ui['m1-foot'].hidden = false;
    if (sendImage) {
      try { await ensureReceipt(); } catch (err) { console.error(err); }
    }
    input.value = '';
    input.focus();
  } catch (err) {
    state.copilotHistory = (state.copilotHistory || []).filter((m) => m.text !== text);
    const box = ui['m1-thread'];
    if (box) {
      const last = box.lastElementChild;
      if (last && last.classList.contains('m1__b--them')) last.remove();
    }
    if (ui['m1-thread-empty'] && box && !box.querySelector('.m1__b')) {
      ui['m1-thread-empty'].hidden = false;
    }
    toastFromError(err, 'toast_error_network');
  } finally {
    btn.disabled = false;
  }
}

/** Mode 2 · boots the autonomous decoy and opens its WhatsApp terminal. */
async function deployCloudNode() {
  const excuseValue = ui['m2-excuse'].value;
  const excuse = excuseValue === 'custom'
    ? ui['m2-custom'].value.trim()
    : t(`t2_exc_${excuseValue === 'battery' ? 'battery' : 'market'}`);
  if (!excuse) {
    toast(t('t2_m2_err'), 'error');
    ui['m2-custom'].focus();
    return;
  }

  const btn = ui['btn-m2-deploy'];
  const label = btn.querySelector('span');
  const prevLabel = label ? label.textContent : '';
  btn.disabled = true;
  if (label) label.textContent = t('btn_sending');

  state.cloudCaseId = 'DEPLOYING';
  ui['cloud-terminal'].hidden = false;
  ui['cloud-chat-box'].innerHTML = '';
  cloudAppendSystem(t('t2_cloud_deploying'));
  setCloudStatus(t('t2_cloud_deploying'));

  try {
    const res = await postJson('/api/honeypot/init-cloud', {
      scammer_phone: state.targetPhone || 'UNKNOWN',
      relation: ui['m2-relation'].value,
      fake_name: ui['m2-name'].value.trim(),
      excuse,
      scam_category: state.targetCategory || 'General Suspicious',
      context: (ui['scam-msg-input'] && ui['scam-msg-input'].value.trim().slice(0, 500)) || null,
      case_context: buildCaseContext()
    });

    state.cloudCaseId = res.case_id;
    state.cloudHistory = res.chat_history || [];
    ui['cloud-case-chip'].textContent = res.case_id;
    renderCloudHistory();
    setCloudStatus(t('t2_cloud_ready'));
    toast(res.case_id, 'success');
    ui['m2-scammer-input'].focus();
  } catch (err) {
    toastFromError(err, 'toast_error_network');
  } finally {
    btn.disabled = false;
    if (label) label.textContent = prevLabel;
  }
}

function setCloudStatus(text) {
  const el = ui['cloud-status-text'];
  if (!el) return;
  el.textContent = text;
  el.removeAttribute('data-i18n');
}

function cloudTyping(on) {
  const box = ui['cloud-chat-box'];
  if (on) {
    const el = document.createElement('div');
    el.className = 'wa-typing-indicator cloud-typing';
    el.innerHTML = '<i></i><i></i><i></i>';
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
    return el;
  }
  return null;
}

function cloudAppend(className, text, time) {
  const box = ui['cloud-chat-box'];
  const el = document.createElement('div');
  el.className = className;
  const body = document.createElement('div');
  body.textContent = text;
  const meta = document.createElement('div');
  meta.className = 'wa-bubble-meta';
  meta.innerHTML = `<span>${escapeHtml(time || nowTime())}</span><svg aria-hidden="true"><use href="#i-checks"></use></svg>`;
  el.appendChild(body);
  el.appendChild(meta);
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function cloudAppendImage(url) {
  const box = ui['cloud-chat-box'];
  const el = document.createElement('div');
  el.className = 'wa-bubble-image';
  const img = document.createElement('img');
  img.src = url;
  img.alt = t('t2_m1_step1');
  img.loading = 'lazy';
  el.appendChild(img);
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function cloudAppendSystem(text) {
  const box = ui['cloud-chat-box'];
  const el = document.createElement('div');
  el.className = 'wa-bubble-system';
  el.textContent = text;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function renderCloudHistory() {
  const box = ui['cloud-chat-box'];
  if (!box) return;
  box.innerHTML = '';
  const rows = state.cloudHistory || [];
  if (!rows.length) {
    cloudAppendSystem(t('t2_cloud_boot'));
    return;
  }
  rows.forEach((row) => {
    const role = row.sender_role || 'scammer';
    if (role === 'scammer') cloudAppend('wa-bubble-scammer', row.message_text, row.timestamp);
    else cloudAppend('wa-bubble-decoy', row.message_text, row.timestamp);
    if (Number(row.send_image) === 1) {
      cloudAppendImage(`/api/co-pilot/fake-receipt?case=${encodeURIComponent(state.cloudCaseId || '')}`);
    }
  });
}

/** One scammer turn in, one in-character decoy turn out. */
async function sendCloudMessage() {
  const input = ui['m2-scammer-input'];
  const text = input.value.trim();
  if (!text || !state.cloudCaseId || state.cloudCaseId === 'DEPLOYING') return;

  input.value = '';
  cloudAppend('wa-bubble-scammer', text);
  setCloudStatus(t('t2_cloud_typing'));
  const typing = cloudTyping(true);

  try {
    const res = await postJson('/api/honeypot/chat-message', {
      case_id: state.cloudCaseId,
      scammer_message: text
    });
    typing.remove();
    cloudAppend('wa-bubble-decoy', res.ai_reply);
    if (res.send_image && res.image_url) cloudAppendImage(res.image_url);
    state.cloudHistory = res.chat_history || state.cloudHistory;
    setCloudStatus(t('t2_cloud_ready'));
    input.focus();
  } catch (err) {
    typing.remove();
    setCloudStatus(t('toast_error_network'));
    toastFromError(err, 'toast_error_network');
  }
}

function resetCloudNode() {
  state.cloudHistory = [];
  ui['cloud-chat-box'].innerHTML = '';
  cloudAppendSystem(t('t2_cloud_boot'));
  setCloudStatus(t('t2_cloud_offline'));
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/* --------------------------------------------------------------------------
   Tab 3 · Evidence
   -------------------------------------------------------------------------- */
function initEvidence() {
  const link = document.getElementById('btn-download-pdf-main');
  if (link) link.href = `/api/reports/download-pdf?case_id=${CASE_ID}`;
  const banner = ui['banner-case-id'];
  if (banner) banner.textContent = CASE_ID;
}

async function loadEvidence() {
  const caseId = state.selectedCase || CASE_ID;
  try {
    const res = await fetch(`/api/reports/case-evidence?case_id=${encodeURIComponent(caseId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    state.evidence = payload.data;
    renderEvidence();
  } catch (err) {
    if (err && /HTTP 404/.test(String(err.message))) {
      state.evidence = null;
      renderEvidence();
      return;
    }
    console.error(err);
  }
}

function renderEvidence() {
  const ev = state.evidence;

  if (!ev) {
    ui['banner-case-id'].textContent = CASE_ID;
    ui['banner-hash'].textContent = 'SHA-256: —';
    ui['ev-upi-list'].innerHTML = emptyNote(t('ev_none'), t('ev_none_note'));
    ui['ev-bank-list'].innerHTML = emptyNote(t('ev_none'), t('ev_none_note'));
    ui['ev-device'].innerHTML = emptyNote(t('ev_none'), t('ev_none_note'));
    ui['ev-transcript'].innerHTML = emptyNote(t('ev_none'), t('ev_none_note'));
    renderProgress([], []);
    return;
  }

  ui['banner-case-id'].textContent = ev.case_id;
  ui['banner-hash'].textContent = `SHA-256: ${ev.evidence_hash || '—'}`;

  const byType = (types) => (ev.identifiers || []).filter((i) => types.includes(i.type));

  ui['ev-upi-list'].innerHTML = identBlock(byType(['UPI', 'PHONE']));
  ui['ev-bank-list'].innerHTML = identBlock(byType(['BANK_AC', 'IFSC']));

  const captures = ev.canary_captures || [];
  ui['ev-device'].innerHTML = captures.length
    ? `<div class="kv-list">${captures.map((c) => `
        <div class="kv">
          <span class="kv__k">${escapeHtml(c.ip_address)}</span>
          <span class="kv__v">${escapeHtml(c.device_os)}</span>
        </div>`).join('')}
        <div class="kv">
          <span class="kv__k">User agent</span>
          <span class="kv__v text-xs mono">${escapeHtml(captures[0].browser_ua || '')}</span>
        </div>
        <div class="kv">
          <span class="kv__k">${escapeHtml(t('ev_captures'))}</span>
          <span class="kv__v">${ev.capture_count}</span>
        </div>
      </div>`
    : `<div class="alert-box alert-box-warn">
         <div class="alert-box__title"><svg aria-hidden="true"><use href="#i-clock"></use></svg><span>${escapeHtml(t('ev_pending'))}</span></div>
         <p class="alert-box__body">${escapeHtml(t('t3_device_note'))}</p>
       </div>`;

  const messages = ev.messages || [];
  ui['ev-transcript'].innerHTML = messages.length
    ? messages.map((m) => {
        const roleKey = m.sender_role === 'scammer' ? 'ev_role_scammer'
          : m.sender_role === 'ai_decoy' ? 'ev_role_ai_decoy' : 'ev_role_system';
        const tone = m.sender_role === 'scammer' ? 'u-red'
          : m.sender_role === 'ai_decoy' ? 'u-emerald' : 'muted';
        const time = String(m.timestamp || '').slice(11, 16);
        return `<div class="transcript-row">
          <div class="transcript-row__meta ${tone}">${escapeHtml(t(roleKey))}${time ? ` · ${escapeHtml(time)}` : ''}</div>
          <div class="transcript-row__text">${escapeHtml(m.message_text)}</div>
        </div>`;
      }).join('')
    : emptyNote(t('ev_none'), t('ev_none_note'));

  renderProgress(messages, ev.identifiers || []);
}

function identBlock(items) {
  if (!items.length) return emptyNote(t('ev_none'), t('ev_none_note'));
  return items.map((i) => {
    const badge = i.blacklisted
      ? `<span class="badge badge--red">${escapeHtml(t('ev_blacklisted'))} · ${i.risk_score}</span>`
      : `<span class="badge">${escapeHtml(t('ev_not_listed'))}</span>`;
    return `<div class="ident-row">
      <div class="grow">
        <div class="ident-row__label">${escapeHtml(i.label || i.type)}</div>
        <span class="badge-mono ${i.blacklisted ? 'badge-mono-red' : ''}">${escapeHtml(i.value)}</span>
        ${i.reports_count ? `<div class="ident-row__meta">${i.reports_count} ${escapeHtml(t('ev_reports'))} · ${escapeHtml(i.scam_category || '')}</div>` : ''}
      </div>
      ${badge}
    </div>`;
  }).join('');
}

function emptyNote(title, note) {
  return `<div class="empty-state empty-state--sm">
    <div class="empty-state__title">${escapeHtml(title)}</div>
    <div class="empty-state__note">${escapeHtml(note)}</div>
  </div>`;
}

function renderProgress(messages, identifiers) {
  const scamCount = messages.filter((m) => m.sender_role === 'scammer').length;
  const decoyCount = messages.filter((m) => m.sender_role === 'ai_decoy').length;
  const baitSent = messages.some((m) =>
    m.sender_role === 'ai_decoy' && /(limit|u16|error)/i.test(m.message_text || ''));
  const hasUpi = identifiers.some((i) => i.type === 'UPI');
  const hasBank = identifiers.some((i) => i.type === 'BANK_AC');

  const steps = [
    [scamCount > 0, 'prog_1'],
    [hasUpi, 'prog_2'],
    [baitSent || decoyCount >= 2, 'prog_3'],
    [hasBank, 'prog_4']
  ];

  const box = ui['trap-progress-list'];
  if (!box) return;
  box.innerHTML = steps.map(([done, key]) => `
    <li class="${done ? 'is-done' : 'is-todo'}">
      <svg aria-hidden="true"><use href="${done ? '#i-check' : '#i-minus'}"></use></svg>
      <span>${escapeHtml(t(key))}</span>
    </li>`).join('');
}

function renderProgressFromMessages(messages) {
  renderProgress(
    messages.map((m) => ({ sender_role: m.sender_role, message_text: m.message_text })),
    (state.evidence && state.evidence.identifiers) || []
  );
}

/* --------------------------------------------------------------------------
   Tab 4 · Trends
   -------------------------------------------------------------------------- */
function initTrends() {
  ui['blacklist-search-input'].addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    const filtered = state.blacklist.filter((item) =>
      String(item.identifier_value).toLowerCase().includes(q) ||
      String(item.scam_category).toLowerCase().includes(q) ||
      String(item.identifier_type).toLowerCase().includes(q)
    );
    renderBlacklist(filtered);
  });
}

async function loadSummary() {
  try {
    const res = await fetch('/api/reports/summary');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    state.summary = payload.data || {};
    state.blacklist = state.summary.blacklist || [];
    renderSummary();
  } catch (err) {
    console.error(err);
    ui['trends-blacklist-tbody'].innerHTML =
      `<tr><td colspan="4" class="u-red">${escapeHtml(t('toast_error_network'))}</td></tr>`;
  }
}

function renderSummary() {
  const s = state.summary;
  if (!s) return;

  animateNumber(ui['kpi-reports'], Number(s.total_citizen_reports) || 0);
  animateNumber(ui['kpi-blacklisted'], Number(s.total_blacklisted_accounts) || 0);
  animateNumber(ui['kpi-cases'], Number(s.active_traps_count) || 0);
  animateNumber(ui['kpi-resolved'], Number(s.scammer_mules_neutralized) || 0);

  renderBlacklist(state.blacklist);
  renderCategoryBars(s.categories || []);
}

function renderBlacklist(items) {
  const tbody = ui['trends-blacklist-tbody'];
  ui['blacklist-count'].textContent = String(items.length);

  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="muted">${escapeHtml(t('th_empty'))}</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map((item) => `
    <tr>
      <td class="cell-id">${escapeHtml(item.identifier_value)}</td>
      <td><span class="badge">${escapeHtml(item.identifier_type)}</span></td>
      <td>${escapeHtml(item.scam_category)}</td>
      <td class="cell-num cell-risk">${item.risk_score}%</td>
    </tr>`).join('');
}

const BAR_COLORS = ['#DC2626', '#2563EB', '#D97706', '#059669', '#0F2C59', '#7C3AED'];

function renderCategoryBars(categories) {
  const box = ui['category-bars'];
  if (!categories.length) {
    box.innerHTML = `<div class="empty-state empty-state--sm">
      <div class="empty-state__title">${escapeHtml(t('chart_empty'))}</div></div>`;
    return;
  }

  const total = categories.reduce((sum, c) => sum + (Number(c.count) || 0), 0) || 1;
  const ordered = categories.slice(0, 6);
  const remainder = categories.slice(6);
  if (remainder.length) {
    ordered.push({
      scam_category: t('th_category'),
      count: remainder.reduce((s, c) => s + (Number(c.count) || 0), 0)
    });
  }

  box.innerHTML = ordered.map((c, idx) => {
    const pct = Math.round(((Number(c.count) || 0) / total) * 100);
    const color = BAR_COLORS[idx % BAR_COLORS.length];
    return `<div class="bar-row">
      <div class="bar-row__head">
        <span class="bar-row__label"><span class="bar-row__dot" style="background:${color}"></span>${escapeHtml(c.scam_category)}</span>
        <span class="bar-row__pct">${pct}%</span>
      </div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
    </div>`;
  }).join('');
}

function animateNumber(el, end, duration = 700) {
  if (!el) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    el.textContent = String(end);
    return;
  }
  let startTs = null;
  const step = (ts) => {
    if (startTs === null) startTs = ts;
    const p = Math.min((ts - startTs) / duration, 1);
    el.textContent = String(Math.round(p * end));
    if (p < 1) window.requestAnimationFrame(step);
  };
  window.requestAnimationFrame(step);
}

/* --------------------------------------------------------------------------
   Re-render on language change
   -------------------------------------------------------------------------- */
document.addEventListener('i18n:changed', () => {
  // Re-render whatever dynamic panel currently has data, exactly once.
  if (state.evidence) renderEvidence();
  else renderProgress([], []);

  if (state.summary) renderSummary();
  if (state.lastVerdict) renderVerdict(state.lastVerdict);
  if (state.lastReport) {
    renderMeta(state.lastReport);
    renderPrinciples(state.lastReport);
    renderLayers(state.lastReport);
  }

  if (ui['analyze-label']) {
    ui['analyze-label'].setAttribute('data-i18n', 'btn_analyze');
    ui['analyze-label'].textContent = t('btn_analyze');
  }
  if (ui['bait-label'] && !ui['btn-generate-bait'].disabled) {
    ui['bait-label'].setAttribute('data-i18n', 'btn_gen_bait');
    ui['bait-label'].textContent = t('btn_gen_bait');
  }
  if (ui['t2-node-chip-text'] && ui['t2-node-chip-text'].hasAttribute('data-i18n')) {
    ui['t2-node-chip-text'].textContent = t('t2_node_checking');
  }
  renderTargetBar();
});

/* --------------------------------------------------------------------------
   Helpers
   -------------------------------------------------------------------------- */
function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function truncate(value, max) {
  const s = String(value || '');
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}
