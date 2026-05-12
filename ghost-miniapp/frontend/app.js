'use strict';
/*  GHOST Claude Bridge ─ */

const WS_URL = (() => {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}/ws/client`;
})();

const SS_TIMEOUT_MS = 20000;

const S = {
  ws: null, online: false,
  prompts: new Map(), ssTimers: new Map(),
  reconnTimer: null, lbSrc: '', lbLabel: '',
};

const $ = id => document.getElementById(id);
const $chat    = $('chat');
const $empty   = $('empty-state');
const $input   = $('prompt-input');
const $btnSend = $('btn-send');
const $btnClear= $('btn-clear');
const $badge   = $('agent-badge');
const $badgeLbl= $('badge-label');
const $lightbox= $('lightbox');
const $lbImg   = $('lightbox-img');
const $lbLabel = $('lightbox-label');
const $lbClose = $('btn-lb-close');
const $lbDl    = $('btn-download');
const $toast   = $('toast');

if (window.Telegram && window.Telegram.WebApp) {
  const tg = Telegram.WebApp;
  tg.ready(); tg.expand();
  tg.setHeaderColor('#13131a');
  tg.setBackgroundColor('#0d0d12');
}

function connect() {
  if (S.ws && S.ws.readyState < WebSocket.CLOSING) return;
  S.ws = new WebSocket(WS_URL);
  S.ws.onopen = () => clearTimeout(S.reconnTimer);
  S.ws.onmessage = function(e) {
    try { dispatch(JSON.parse(e.data)); } catch(err) { console.error(err); }
  };
  S.ws.onclose = () => {
    setOnline(false);
    S.reconnTimer = setTimeout(connect, 3000);
  };
  S.ws.onerror = () => S.ws.close();
}

function wsSend(obj) {
  if (S.ws && S.ws.readyState === WebSocket.OPEN)
    S.ws.send(JSON.stringify(obj));
}

function dispatch(msg) {
  switch (msg.type) {
    case 'init':
      setOnline(msg.agent_connected);
      if (msg.history && msg.history.length) {
        msg.history.forEach(function(p) { renderCard(p, false); });
        scrollEnd();
      }
      break;
    case 'agent_status': setOnline(msg.connected); break;
    case 'new_prompt':   renderCard(msg.prompt, true); break;
    case 'prompt_sent':
      setStatus(msg.prompt_id, msg.ok ? 'sent' : 'error', msg.ok ? 'yuborildi' : 'xato');
      break;
    case 'screenshot':
      appendScreenshot(msg.prompt_id, msg.kind, msg.image_b64, msg.taken_at);
      break;
    case 'history_cleared': clearChat(); break;
    case 'error': toast(msg.message, true); break;
  }
}

function setOnline(v) {
  S.online = v;
  $badge.className = v ? 'online' : 'badge-offline';
  $badgeLbl.textContent = v ? 'online' : 'offline';
  $btnSend.disabled = !v;
}

function renderCard(prompt, scroll) {
  if (S.prompts.has(prompt.id)) return;
  $empty.style.display = 'none';

  var card = document.createElement('article');
  card.className = 'prompt-card';
  card.id = 'card-' + prompt.id;
  card.innerHTML =
    '<div class="card-head">' +
      '<div class="card-avatar">&#10022;</div>' +
      '<div class="card-body">' +
        '<div class="card-text">' + esc(prompt.text) + '</div>' +
        '<div class="card-meta">' +
          '<span class="card-time">' + fmtTime(prompt.created_at) + '</span>' +
          '<span class="card-status pending" id="st-' + prompt.id + '">' +
            '<span class="spin-icon"></span> yuborilmoqda' +
          '</span>' +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div class="card-actions">' +
      '<button class="action-btn check" data-pid="' + prompt.id + '" data-kind="check">' +
        iconEye() + ' Tekshirish' +
      '</button>' +
      '<button class="action-btn result" data-pid="' + prompt.id + '" data-kind="result">' +
        iconCheck() + ' Natija' +
      '</button>' +
    '</div>' +
    '<div class="card-screenshots" id="ss-' + prompt.id + '"></div>';

  $chat.appendChild(card);
  S.prompts.set(prompt.id, { el: card, screenshots: [] });
  if (scroll) scrollEnd();
}

function setStatus(pid, cls, text) {
  var el = document.getElementById('st-' + pid);
  if (el) { el.className = 'card-status ' + cls; el.textContent = text; }
}

function requestScreenshot(pid, kind) {
  var card = document.getElementById('card-' + pid);
  if (!card) return;
  var btn = card.querySelector('.action-btn[data-kind="' + kind + '"]');
  if (btn) btn.classList.add('loading');
  wsSend({ type: 'screenshot', prompt_id: pid, kind: kind });
  var key = pid + kind;
  clearTimeout(S.ssTimers.get(key));
  S.ssTimers.set(key, setTimeout(function() {
    if (btn) btn.classList.remove('loading');
    S.ssTimers.delete(key);
  }, SS_TIMEOUT_MS));
}

function appendScreenshot(pid, kind, b64, takenAt) {
  var container = document.getElementById('ss-' + pid);
  if (!container) return;
  var card = document.getElementById('card-' + pid);
  var btn  = card && card.querySelector('.action-btn[data-kind="' + kind + '"]');
  if (btn) btn.classList.remove('loading');
  var key = pid + kind;
  clearTimeout(S.ssTimers.get(key));
  S.ssTimers.delete(key);

  var src   = 'data:image/png;base64,' + b64;
  var label = kind === 'check' ? 'Tekshirish' : 'Natija';
  var time  = fmtTime(takenAt);
  var entry = S.prompts.get(pid);
  var count = entry ? entry.screenshots.filter(function(s){ return s.kind === kind; }).length + 1 : 1;

  var item = document.createElement('div');
  item.className = 'ss-item';
  item.innerHTML =
    '<div class="ss-meta">' +
      '<span class="ss-badge ' + kind + '">' + label + '</span>' +
      '<span class="ss-time">' + time + '</span>' +
      (count > 1 ? '<span class="ss-count">#' + count + '</span>' : '') +
    '</div>' +
    '<img class="ss-img" alt="' + label + '" loading="lazy" />';

  var img = item.querySelector('.ss-img');
  img.src = src;
  img.addEventListener('click', function() { openLightbox(src, label + ' \u00b7 ' + time); });

  container.appendChild(item);
  if (entry) entry.screenshots.push({ kind: kind, b64: b64, takenAt: takenAt });
  scrollEnd();
}

function openLightbox(src, label) {
  S.lbSrc = src; S.lbLabel = label;
  $lbImg.src = src;
  $lbLabel.textContent = label;
  $lightbox.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  $lightbox.hidden = true;
  $lbImg.src = '';
  document.body.style.overflow = '';
}

$lbClose.addEventListener('click', closeLightbox);
document.getElementById('lightbox-backdrop').addEventListener('click', closeLightbox);
$lbDl.addEventListener('click', function() {
  var a = document.createElement('a');
  a.href = S.lbSrc;
  a.download = 'ghost-' + Date.now() + '.png';
  a.click();
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && !$lightbox.hidden) closeLightbox();
});

$input.addEventListener('input', function() {
  $input.style.height = 'auto';
  $input.style.height = Math.min($input.scrollHeight, 130) + 'px';
  $btnSend.disabled = !S.online || !$input.value.trim();
});

$input.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
});

$btnSend.addEventListener('click', submit);

function submit() {
  var text = $input.value.trim();
  if (!text || !S.online) return;
  wsSend({ type: 'send_prompt', text: text });
  $input.value = '';
  $input.style.height = 'auto';
  $btnSend.disabled = true;
  $input.focus();
}

$chat.addEventListener('click', function(e) {
  var btn = e.target.closest('.action-btn');
  if (!btn) return;
  var pid = btn.dataset.pid, kind = btn.dataset.kind;
  if (pid && kind) requestScreenshot(pid, kind);
});

$btnClear.addEventListener('click', function() {
  if (!confirm("Barcha tarixni o'chirish?")) return;
  wsSend({ type: 'clear_history' });
});

function clearChat() {
  $chat.innerHTML = '';
  $chat.appendChild($empty);
  $empty.style.display = '';
  S.prompts.clear();
}

function scrollEnd() {
  requestAnimationFrame(function() { $chat.scrollTop = $chat.scrollHeight; });
}

function fmtTime(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
  catch(e) { return ''; }
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

var _toastTimer;
function toast(msg, isErr) {
  $toast.textContent = msg;
  $toast.className = 'show' + (isErr ? ' error' : '');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(function() { $toast.className = ''; }, 3000);
}

function iconEye() {
  return '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
}
function iconCheck() {
  return '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
}

connect();
$input.focus();
