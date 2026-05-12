'use strict';

const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

const S = {
  ws: null,
  reconnectTimer: null,
  authBlocked: false,
  agentOnline: false,
  mode: 'command',
  session: null,
  entries: new Map(),
  confirmPayload: null,
  confirmAsked: new Set(),
  lightboxSrc: '',
  lightboxLabel: '',
};

const $ = id => document.getElementById(id);
const els = {
  app: $('app'),
  gate: $('gate'),
  gateMessage: $('gate-message'),
  userLabel: $('user-label'),
  badge: $('agent-badge'),
  badgeLabel: $('badge-label'),
  metricCpu: $('metric-cpu'),
  metricRam: $('metric-ram'),
  metricBattery: $('metric-battery'),
  metricAgent: $('metric-agent'),
  input: $('prompt-input'),
  send: $('btn-send'),
  clear: $('btn-clear'),
  refresh: $('btn-refresh'),
  history: $('history'),
  empty: $('empty-state'),
  toast: $('toast'),
  confirm: $('confirm'),
  confirmText: $('confirm-text'),
  confirmCancel: $('btn-confirm-cancel'),
  confirmOk: $('btn-confirm-ok'),
  lightbox: $('lightbox'),
  lightboxImg: $('lightbox-img'),
  lightboxLabel: $('lightbox-label'),
  lightboxClose: $('btn-lb-close'),
  lightboxBackdrop: $('lightbox-backdrop'),
  download: $('btn-download'),
};

initTelegram();
bindUi();
connect();

function initTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  try {
    tg.setHeaderColor('#171b23');
    tg.setBackgroundColor('#0f1117');
    tg.disableVerticalSwipes && tg.disableVerticalSwipes();
  } catch (err) {
    console.debug(err);
  }
  if (tg.MainButton) {
    tg.MainButton.setText('Yuborish');
    tg.MainButton.onClick(submit);
  }
  if (tg.onEvent) {
    tg.onEvent('themeChanged', applyTelegramTheme);
  }
  applyTelegramTheme();
}

function applyTelegramTheme() {
  if (!tg || !tg.themeParams) return;
  const p = tg.themeParams;
  const root = document.documentElement;
  if (p.bg_color && tg.colorScheme === 'light') {
    root.style.setProperty('--bg', p.bg_color);
  }
  if (p.text_color && tg.colorScheme === 'light') {
    root.style.setProperty('--text', p.text_color);
  }
}

function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const initData = tg && tg.initData ? tg.initData : '';
  const qs = initData ? `?init_data=${encodeURIComponent(initData)}` : '';
  return `${proto}://${location.host}/ws/client${qs}`;
}

function connect() {
  if (S.authBlocked) return;
  if (S.ws && S.ws.readyState < WebSocket.CLOSING) return;

  S.ws = new WebSocket(wsUrl());
  S.ws.onopen = () => {
    clearTimeout(S.reconnectTimer);
    wsSend({ type: 'get_status' });
  };
  S.ws.onmessage = event => {
    try {
      dispatch(JSON.parse(event.data));
    } catch (err) {
      console.error(err);
    }
  };
  S.ws.onclose = () => {
    setAgentOnline(false);
    if (!S.authBlocked) {
      S.reconnectTimer = setTimeout(connect, 2500);
    }
  };
  S.ws.onerror = () => {
    try { S.ws.close(); } catch (err) { console.debug(err); }
  };
}

function wsSend(payload) {
  if (!S.ws || S.ws.readyState !== WebSocket.OPEN) {
    toast('Server bilan aloqa yo\'q.', true);
    return false;
  }
  S.ws.send(JSON.stringify(payload));
  return true;
}

function dispatch(msg) {
  switch (msg.type) {
    case 'init':
      S.session = msg.session || null;
      if (S.session) els.userLabel.textContent = S.session.display_name || 'Mini App';
      setAgentOnline(!!msg.agent_connected);
      renderStatus(msg.system);
      clearHistoryDom();
      (msg.history || []).forEach(upsertEntry);
      break;
    case 'auth_error':
      S.authBlocked = true;
      showGate(msg.message || 'Telegram sessiya tekshirilmadi.');
      break;
    case 'agent_status':
      setAgentOnline(!!msg.connected);
      break;
    case 'status_snapshot':
      renderStatus(msg.status);
      break;
    case 'new_prompt':
      upsertEntry(msg.prompt);
      scrollHistory();
      break;
    case 'history_updated':
      upsertEntry(msg.entry);
      maybeAskConfirm(msg.entry);
      scrollHistory();
      break;
    case 'prompt_sent':
      patchEntryStatus(msg.prompt_id, msg.ok ? 'sent' : 'error');
      break;
    case 'screenshot':
      appendScreenshot(msg.prompt_id, msg.kind, msg.image_b64, msg.taken_at);
      break;
    case 'history_cleared':
      clearHistoryDom();
      break;
    case 'error':
      toast(msg.message || 'Xatolik yuz berdi.', true);
      break;
  }
}

function bindUi() {
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => setMode(btn.dataset.mode));
  });

  document.querySelectorAll('.quick-action').forEach(btn => {
    btn.addEventListener('click', () => {
      const params = readJson(btn.dataset.params);
      const payload = {
        action: btn.dataset.action,
        label: btn.dataset.label || btn.textContent.trim(),
        params,
        text: '',
      };
      if (btn.dataset.confirm === 'true') {
        openConfirm(payload);
      } else {
        sendCommand(payload);
      }
    });
  });

  els.input.addEventListener('input', () => {
    autosizeInput();
    syncSendState();
  });

  els.input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  });

  els.send.addEventListener('click', submit);
  els.refresh.addEventListener('click', () => wsSend({ type: 'get_status' }));
  els.clear.addEventListener('click', () => openConfirm({
    label: 'Tarixni tozalash',
    clearHistory: true,
  }));

  els.confirmCancel.addEventListener('click', closeConfirm);
  els.confirmOk.addEventListener('click', () => {
    const payload = S.confirmPayload;
    closeConfirm();
    if (!payload) return;
    if (payload.clearHistory) {
      wsSend({ type: 'clear_history' });
    } else {
      sendCommand(payload, true);
    }
  });
  document.querySelector('[data-close="confirm"]').addEventListener('click', closeConfirm);

  els.lightboxClose.addEventListener('click', closeLightbox);
  els.lightboxBackdrop.addEventListener('click', closeLightbox);
  els.download.addEventListener('click', downloadLightbox);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      if (!els.lightbox.hidden) closeLightbox();
      if (!els.confirm.hidden) closeConfirm();
    }
  });
}

function setMode(mode) {
  S.mode = mode === 'claude' ? 'claude' : 'command';
  document.querySelectorAll('.mode-btn').forEach(btn => {
    const active = btn.dataset.mode === S.mode;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  els.input.placeholder = S.mode === 'claude'
    ? 'Claude prompt yozing...'
    : 'Buyruq yozing...';
  syncSendState();
}

function submit() {
  const text = els.input.value.trim();
  if (!text) return;
  if (!S.agentOnline) {
    toast('Local agent offline.', true);
    return;
  }

  if (S.mode === 'claude') {
    wsSend({ type: 'send_prompt', text });
  } else {
    sendCommand({ text, label: text });
  }

  haptic('impact');
  els.input.value = '';
  autosizeInput();
  syncSendState();
  els.input.focus();
}

function sendCommand(payload, confirmed) {
  if (!S.agentOnline) {
    toast('Local agent offline.', true);
    return;
  }
  wsSend({
    type: 'run_command',
    text: payload.text || '',
    action: payload.action || '',
    label: payload.label || payload.text || payload.action,
    params: payload.params || {},
    confirmed: !!confirmed,
  });
  haptic(confirmed ? 'notification' : 'selection');
}

function setAgentOnline(online) {
  S.agentOnline = online;
  els.badge.classList.toggle('online', online);
  els.badge.classList.toggle('offline', !online);
  els.badgeLabel.textContent = online ? 'online' : 'offline';
  els.metricAgent.textContent = online ? 'online' : 'offline';
  document.querySelectorAll('.quick-action').forEach(btn => {
    btn.disabled = !online;
  });
  syncSendState();
}

function syncSendState() {
  const enabled = S.agentOnline && !!els.input.value.trim();
  els.send.disabled = !enabled;
  if (tg && tg.MainButton) {
    if (enabled) {
      tg.MainButton.setText(S.mode === 'claude' ? 'Prompt yuborish' : 'Buyruq yuborish');
      tg.MainButton.show();
    } else {
      tg.MainButton.hide();
    }
  }
}

function renderStatus(status) {
  if (!status) return;
  setMetric(els.metricCpu, status.cpu == null ? '--' : `${status.cpu}%`);
  setMetric(els.metricRam, status.ram == null ? '--' : `${status.ram}%`);
  if (status.battery == null) {
    setMetric(els.metricBattery, '--');
  } else {
    setMetric(els.metricBattery, `${status.battery}%${status.charging ? '+' : ''}`);
  }
  if (S.agentOnline && status.hostname) {
    els.metricAgent.textContent = status.hostname;
  }
}

function setMetric(node, value) {
  node.textContent = value;
}

function upsertEntry(rawEntry) {
  if (!rawEntry || !rawEntry.id) return;
  const entry = normalizeEntry(rawEntry);
  const current = S.entries.get(entry.id) || { screenshots: [] };
  current.entry = entry;
  S.entries.set(entry.id, current);

  const card = buildEntryCard(entry, current.screenshots);
  const old = document.getElementById(`entry-${entry.id}`);
  if (old) {
    old.replaceWith(card);
  } else {
    els.empty.hidden = true;
    els.history.appendChild(card);
  }
}

function normalizeEntry(entry) {
  return {
    id: entry.id,
    kind: entry.kind || 'claude',
    text: entry.text || '',
    status: entry.status || 'queued',
    result: entry.result || '',
    action: entry.action || '',
    data: entry.data || {},
    created_at: entry.created_at || new Date().toISOString(),
  };
}

function buildEntryCard(entry, screenshots) {
  const card = create('article', 'history-card');
  card.id = `entry-${entry.id}`;

  const head = create('div', 'entry-head');
  const title = create('div', 'entry-title');
  title.append(
    create('span', 'entry-kind', entry.kind === 'claude' ? 'Claude' : 'Buyruq'),
    create('span', 'entry-time', fmtTime(entry.created_at))
  );
  head.append(title, create('span', `entry-status ${entry.status}`, statusLabel(entry.status)));

  const body = create('div', 'entry-body');
  body.appendChild(create('div', 'entry-text', entry.text));
  if (entry.result) {
    body.appendChild(create('div', 'entry-result', entry.result));
  }

  card.append(head, body);

  if (entry.kind === 'claude') {
    const actions = create('div', 'entry-actions');
    actions.append(
      entryAction('Tekshirish', entry.id, 'check'),
      entryAction('Natija', entry.id, 'result')
    );
    card.appendChild(actions);
  }

  const images = [];
  if (entry.data && entry.data.image_b64) {
    images.push({
      kind: entry.data.kind || 'result',
      b64: entry.data.image_b64,
      takenAt: entry.completed_at || new Date().toISOString(),
    });
  }
  images.push(...screenshots);
  if (images.length) {
    const media = create('div', 'media-grid');
    media.id = `media-${entry.id}`;
    images.forEach((shot, index) => media.appendChild(shotNode(shot, index)));
    card.appendChild(media);
  }

  return card;
}

function entryAction(label, id, kind) {
  const btn = create('button', 'entry-action');
  btn.type = 'button';
  btn.append(icon(kind === 'check' ? 'eye' : 'check'), document.createTextNode(label));
  btn.addEventListener('click', () => {
    if (!S.agentOnline) {
      toast('Local agent offline.', true);
      return;
    }
    wsSend({ type: 'screenshot', prompt_id: id, kind });
  });
  return btn;
}

function shotNode(shot, index) {
  const wrap = create('div', 'shot');
  const src = `data:image/png;base64,${shot.b64}`;
  const btn = document.createElement('button');
  btn.type = 'button';
  const img = document.createElement('img');
  img.src = src;
  img.alt = shot.kind || 'screenshot';
  img.loading = 'lazy';
  btn.appendChild(img);
  btn.addEventListener('click', () => openLightbox(src, `${shot.kind || 'screenshot'} ${fmtTime(shot.takenAt)}`));
  const cap = create('div', 'shot-caption');
  cap.append(
    create('span', '', shot.kind === 'check' ? 'Tekshirish' : shot.kind === 'screen' ? 'Skrinshot' : 'Natija'),
    create('span', '', `${fmtTime(shot.takenAt)}${index ? ` #${index + 1}` : ''}`)
  );
  wrap.append(btn, cap);
  return wrap;
}

function appendScreenshot(id, kind, b64, takenAt) {
  if (!id || !b64) {
    toast('Skrinshot kelmadi.', true);
    return;
  }
  const current = S.entries.get(id);
  if (!current) return;
  current.screenshots.push({ kind, b64, takenAt });
  upsertEntry(current.entry);
  scrollHistory();
}

function patchEntryStatus(id, status) {
  const current = S.entries.get(id);
  if (!current) return;
  current.entry.status = status;
  upsertEntry(current.entry);
}

function maybeAskConfirm(entry) {
  if (!entry || !entry.data || !entry.data.needs_confirm || S.confirmAsked.has(entry.id)) {
    return;
  }
  S.confirmAsked.add(entry.id);
  openConfirm({
    action: entry.data.action || entry.action,
    label: entry.text,
    text: entry.text,
  });
}

function openConfirm(payload) {
  S.confirmPayload = payload;
  els.confirmText.textContent = payload.clearHistory
    ? 'Tarix tozalansinmi?'
    : `${payload.label || 'Buyruq'} bajarilsinmi?`;
  els.confirm.hidden = false;
  haptic('warning');
}

function closeConfirm() {
  els.confirm.hidden = true;
  S.confirmPayload = null;
}

function openLightbox(src, label) {
  S.lightboxSrc = src;
  S.lightboxLabel = label;
  els.lightboxImg.src = src;
  els.lightboxLabel.textContent = label;
  els.lightbox.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  els.lightbox.hidden = true;
  els.lightboxImg.src = '';
  document.body.style.overflow = '';
}

function downloadLightbox() {
  if (!S.lightboxSrc) return;
  const a = document.createElement('a');
  a.href = S.lightboxSrc;
  a.download = `ghost-${Date.now()}.png`;
  a.click();
}

function clearHistoryDom() {
  S.entries.clear();
  S.confirmAsked.clear();
  Array.from(els.history.querySelectorAll('.history-card')).forEach(node => node.remove());
  els.empty.hidden = false;
}

function autosizeInput() {
  els.input.style.height = 'auto';
  els.input.style.height = `${Math.min(els.input.scrollHeight, 132)}px`;
}

function showGate(message) {
  els.gateMessage.textContent = message;
  els.gate.hidden = false;
}

function scrollHistory() {
  requestAnimationFrame(() => {
    const scroller = $('content');
    scroller.scrollTop = scroller.scrollHeight;
  });
}

function toast(message, error) {
  els.toast.textContent = message;
  els.toast.className = `show${error ? ' error' : ''}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    els.toast.className = '';
  }, 3200);
}

function haptic(kind) {
  try {
    if (!tg || !tg.HapticFeedback) return;
    if (kind === 'notification' || kind === 'warning') {
      tg.HapticFeedback.notificationOccurred(kind === 'warning' ? 'warning' : 'success');
    } else if (kind === 'impact') {
      tg.HapticFeedback.impactOccurred('light');
    } else {
      tg.HapticFeedback.selectionChanged();
    }
  } catch (err) {
    console.debug(err);
  }
}

function readJson(value) {
  if (!value) return {};
  try {
    return JSON.parse(value);
  } catch (err) {
    console.debug(err);
    return {};
  }
}

function fmtTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (err) {
    return '';
  }
}

function statusLabel(status) {
  const labels = {
    queued: 'kutilmoqda',
    sent: 'yuborildi',
    done: 'bajarildi',
    error: 'xato',
  };
  return labels[status] || status || 'kutilmoqda';
}

function create(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function icon(name) {
  const span = document.createElement('span');
  span.innerHTML = icons[name] || icons.check;
  return span.firstElementChild;
}

const icons = {
  eye: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
  check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>',
};
