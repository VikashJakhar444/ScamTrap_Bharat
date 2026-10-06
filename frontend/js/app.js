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
  threads: [],
  summary: null,
  blacklist: [],
  selectedCase: CASE_ID,
  latestBait: null,
  lastVerdict: null
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
  loadHoneypotStatus();
  loadThreads();
  loadEvidence();
  checkHealth();
});

function cacheDom() {
  [
    'desktop-tablist', 'mobile-tablist', 'hamburger-btn', 'toast-region',
    'quick-search-input', 'quick-search-btn', 'chip-scam-upi', 'chip-scam-msg',
    'scam-msg-input', 'analyze-msg-btn', 'btn-clear-tab1',
    'dropzone-box', 'scam-img-input', 'dropzone-filename',
    'result-side-card', 'result-placeholder', 'result-loading', 'result-active-content',
    'gauge-score-text', 'radial-gauge-circle', 'risk-score-pill',
    'risk-banner-box', 'risk-banner-icon', 'risk-banner-title', 'risk-banner-guidance',
    'ext-upi-val', 'ext-phone-val', 'ext-bank-val',
    'custom-bait-amt', 'btn-generate-bait', 'btn-send-to-honeypot',
    'bait-preview-modal', 'bait-receipt-img', 'btn-download-bait-img',
    'btn-copy-bait-text', 'bait-copy-toast',
    'wa-conn-badge', 'wa-conn-text', 'node-phone', 'node-persona', 'node-mode',
    'thread-list', 'live-chat-box', 'manual-scammer-input', 'btn-send-manual-msg',
    'btn-sim-scam-msg', 'btn-sim-bank-msg', 'btn-reset-chat',
    'btn-refresh-status', 'btn-test-canary-click', 'btn-goto-tab3',
    'chat-online-status', 'trap-progress-list',
    'stat-engaged', 'stat-mules',
    'banner-case-id', 'banner-hash', 'ev-upi-list', 'ev-bank-list',
    'ev-device', 'ev-transcript',
    'kpi-reports', 'kpi-blacklisted', 'kpi-cases', 'kpi-resolved',
    'blacklist-search-input', 'trends-blacklist-tbody', 'blacklist-count',
    'category-bars',
    'analyze-label', 'bait-label', 'chat-status-text'
  ].forEach((id) => { ui[id] = document.getElementById(id); });
}

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

function switchTab(targetId) {
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
  if (targetId === 'tab-honeypot') { loadHoneypotStatus(); loadThreads(); }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function initGlobalHandlers() {
  document.querySelectorAll('[data-goto-tab]').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      switchTab(el.dataset.gotoTab);
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
    const value = ui['scam-msg-input'].value.trim();
    if (!value) { toast(t('t1_empty_note'), 'info'); ui['scam-msg-input'].focus(); return; }
    runLookup(value);
  });

  ui['btn-clear-tab1'].addEventListener('click', () => {
    quick.value = '';
    ui['scam-msg-input'].value = '';
    ui['dropzone-filename'].classList.add('is-hidden');
    ui['scam-img-input'].value = '';
    ui['result-placeholder'].classList.remove('is-hidden');
    ui['result-loading'].classList.add('is-hidden');
    ui['result-active-content'].classList.add('is-hidden');
    ui['bait-preview-modal'].classList.add('is-hidden');
    state.latestBait = null;
  });

  // Dropzone — click, keyboard and drag/drop.
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

  function handleFile(file) {
    if (!file) return;
    const label = ui['dropzone-filename'];
    label.textContent = `Attached: ${file.name}`;
    label.classList.remove('is-hidden');
    if (!ui['scam-msg-input'].value.trim()) {
      ui['scam-msg-input'].value =
        '[From screenshot] Urgent: your power connection is due for disconnection today. Pay Rs 45 to bijli.board.pay@ybl or call 9876543210.';
    }
  }

  ui['btn-generate-bait'].addEventListener('click', generateBait);
  ui['btn-copy-bait-text'].addEventListener('click', copyBaitReply);
  ui['btn-send-to-honeypot'].addEventListener('click', () => switchTab('tab-honeypot'));
}

async function runLookup(queryText) {
  const analyzeBtn = ui['analyze-msg-btn'];
  const analyzeLabel = ui['analyze-label'];

  ui['result-placeholder'].classList.add('is-hidden');
  ui['result-active-content'].classList.add('is-hidden');
  ui['result-loading'].classList.remove('is-hidden');
  ui['result-side-card'].setAttribute('aria-busy', 'true');

  analyzeBtn.disabled = true;
  analyzeLabel.removeAttribute('data-i18n');
  analyzeLabel.textContent = t('btn_analyzing');

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
    renderVerdict(data);
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

async function generateBait() {
  const btn = ui['btn-generate-bait'];
  const label = ui['bait-label'];
  const upiTarget = ui['ext-upi-val'].textContent.includes('@')
    ? ui['ext-upi-val'].textContent.split(',')[0].trim()
    : 'bijli.board.pay@ybl';
  const amount = ui['custom-bait-amt'].value.trim() || '25,000';

  btn.disabled = true;
  label.removeAttribute('data-i18n');
  label.textContent = t('btn_generating_bait');

  try {
    const res = await fetch('/api/co-pilot/generate-receipt-bait', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scammer_upi: upiTarget, amount, case_id: CASE_ID })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.status !== 'success') throw new Error('bad status');

    state.latestBait = data;
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
  ui['btn-refresh-status'].addEventListener('click', () => {
    loadHoneypotStatus();
    loadThreads();
    loadEvidence();
  });

  ui['btn-sim-scam-msg'].addEventListener('click', () => {
    sendMessage('Dear Consumer, your electricity bill of Rs 45 is unpaid. Pay now on bijli.board.pay@ybl or power is cut at 9:30 PM.');
  });

  ui['btn-sim-bank-msg'].addEventListener('click', () => {
    sendMessage('If the UPI daily limit is reached, transfer to our backup account: A/C 50200084729104 IFSC SBIN0004821 immediately.');
  });

  const submit = () => {
    const value = ui['manual-scammer-input'].value.trim();
    if (!value) return;
    if (/^trap$/i.test(value)) {
      toast(t('trap_keyword_ack'), 'success');
      ui['manual-scammer-input'].value = '';
      return;
    }
    sendMessage(value);
    ui['manual-scammer-input'].value = '';
  };

  ui['btn-send-manual-msg'].addEventListener('click', submit);
  ui['manual-scammer-input'].addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submit();
  });

  ui['btn-reset-chat'].addEventListener('click', () => {
    ui['live-chat-box'].innerHTML = '';
    appendSystem(t('chat_boot'));
  });

  ui['btn-test-canary-click'].addEventListener('click', () => {
    window.open(`/receipt/TRAP-WEB-DEMO?case=${state.selectedCase}`, '_blank', 'noopener');
    setTimeout(loadEvidence, 1200);
  });

  ui['btn-goto-tab3'].addEventListener('click', () => switchTab('tab-proof'));
}

async function loadHoneypotStatus() {
  try {
    const res = await fetch('/api/honeypot/status');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const connected = Boolean(data.whatsapp_connected);
    ui['wa-conn-badge'].className = `badge ${connected ? 'badge--emerald' : 'badge--amber'} badge--block mt-3`;
    ui['wa-conn-text'].removeAttribute('data-i18n');
    ui['wa-conn-text'].textContent = connected
      ? `${t('t2_node_online')} · ${data.virtual_phone_number || ''}`
      : t('t2_node_standby');

    ui['node-phone'].textContent = data.virtual_phone_number || '—';
    ui['node-persona'].textContent = data.active_persona || '—';
    ui['node-mode'].textContent = data.mode || '—';

    ui['stat-engaged'].textContent = String(data.scammers_engaged_total ?? 0);
    ui['stat-mules'].textContent = String(data.mules_extracted_total ?? 0);
  } catch (err) {
    ui['wa-conn-text'].textContent = t('toast_error_network');
    ui['wa-conn-badge'].className = 'badge badge--red badge--block mt-3';
    console.error(err);
  }
}

async function loadThreads() {
  try {
    const res = await fetch('/api/honeypot/threads');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.threads = await res.json();
    renderThreads();
  } catch (err) {
    ui['thread-list'].innerHTML = `<div class="text-xs u-red">${escapeHtml(t('toast_error_network'))}</div>`;
    console.error(err);
  }
}

function renderThreads() {
  const list = ui['thread-list'];
  if (!state.threads.length) {
    list.innerHTML = `<div class="empty-state empty-state--sm">
      <div class="empty-state__title">${escapeHtml(t('t2_threads_empty'))}</div>
    </div>`;
    return;
  }

  list.innerHTML = state.threads.map((th) => {
    const selected = (th.case_id || '') === state.selectedCase;
    const statusClass = th.is_trap_active ? 'badge--emerald' : 'badge--amber';
    return `<button type="button" class="thread-item ${selected ? 'is-selected' : ''}" data-case="${escapeHtml(th.case_id || '')}">
      <span class="thread-item__body">
        <span class="thread-item__title mono">${escapeHtml(th.phone || '—')}</span>
        <span class="thread-item__sub">${escapeHtml(th.category || '')}</span>
        <span class="thread-item__sub">${escapeHtml(truncate(th.last_message || '', 54))}</span>
      </span>
      <span class="badge ${statusClass}">${th.is_trap_active ? 'ON' : 'OFF'}</span>
    </button>`;
  }).join('');

  list.querySelectorAll('.thread-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      state.selectedCase = btn.dataset.case || CASE_ID;
      renderThreads();
      loadEvidence();
      appendSystem(`${t('t2_threads_title')} · ${state.selectedCase}`);
    });
  });
}

async function sendMessage(text) {
  const box = ui['live-chat-box'];
  const status = ui['chat-status-text'];

  appendBubble('wa-bubble-scammer', text);

  status.removeAttribute('data-i18n');
  status.textContent = t('chat_typing');
  const typing = document.createElement('div');
  typing.className = 'wa-typing-indicator';
  typing.innerHTML = '<i></i><i></i><i></i>';
  box.appendChild(typing);
  box.scrollTop = box.scrollHeight;

  try {
    const res = await fetch('/api/honeypot/send-message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_text: text, case_id: state.selectedCase })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    typing.remove();
    if (data.decoy_response) appendBubble('wa-bubble-decoy', data.decoy_response);

    setChatStatus(t('chat_status'), false);
    renderProgressFromMessages(data.chat_history || []);
    loadEvidence();
    loadHoneypotStatus();
  } catch (err) {
    typing.remove();
    setChatStatus(t('toast_error_network'), true);
    toastFromError(err, 'toast_error_network');
  }
}

/** Keeps data-i18n in sync so a language switch updates the status label. */
function setChatStatus(text, sticky) {
  const el = ui['chat-status-text'];
  el.textContent = text;
  if (sticky) el.removeAttribute('data-i18n');
  else el.setAttribute('data-i18n', 'chat_status');
}

function appendBubble(className, text, time) {
  const box = ui['live-chat-box'];
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

function appendSystem(text) {
  const el = document.createElement('div');
  el.className = 'wa-bubble-system';
  el.textContent = text;
  ui['live-chat-box'].appendChild(el);
  ui['live-chat-box'].scrollTop = ui['live-chat-box'].scrollHeight;
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

  ui['trap-progress-list'].innerHTML = steps.map(([done, key]) => `
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
  if (state.threads.length) renderThreads();
  if (state.lastVerdict) renderVerdict(state.lastVerdict);

  if (ui['analyze-label']) {
    ui['analyze-label'].setAttribute('data-i18n', 'btn_analyze');
    ui['analyze-label'].textContent = t('btn_analyze');
  }
  if (ui['bait-label'] && !ui['btn-generate-bait'].disabled) {
    ui['bait-label'].setAttribute('data-i18n', 'btn_gen_bait');
    ui['bait-label'].textContent = t('btn_gen_bait');
  }
  if (ui['wa-conn-text'] && ui['wa-conn-text'].hasAttribute('data-i18n')) {
    ui['wa-conn-text'].textContent = t('t2_node_checking');
  }
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
