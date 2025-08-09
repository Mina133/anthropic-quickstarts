// Use same-origin proxy to the API to avoid CORS/host issues
const API_BASE = (window.API_BASE || '/api');

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const text = await res.text();
  const ct = res.headers.get('content-type') || '';
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
  }
  if (ct.includes('application/json')) {
    try { return JSON.parse(text); } catch (e) { throw new Error(`Invalid JSON: ${text.slice(0,200)}`); }
  }
  throw new Error(`Non-JSON response: ${text.slice(0, 200)}`);
}

const createSessionBtn = document.getElementById('createSessionBtn');
const sessionIdEl = document.getElementById('sessionId');
const messagesEl = document.getElementById('messages');
const streamList = document.getElementById('streamList');
const sendBtn = document.getElementById('sendBtn');
const userInput = document.getElementById('userInput');
const sessionList = document.getElementById('sessionList');
const refreshSessionsBtn = document.getElementById('refreshSessions');
const vncFrame = document.getElementById('vncFrame');
const vncContainer = document.getElementById('vncContainer');
const vncWidthInput = document.getElementById('vncWidth');
const vncHeightInput = document.getElementById('vncHeight');
const lockAspectInput = document.getElementById('lockAspect');
const fitToggle = document.getElementById('fitToggle');
const vncStatus = document.getElementById('vncStatus');
const vncReconnect = document.getElementById('vncReconnect');
const novncNewTab = document.getElementById('novncNewTab');

let currentSessionId = null;
let ws = null;
let vncUrl = 'http://localhost:6080/vnc.html?autoconnect=true&resize=scale&host=localhost&port=6080&path=websockify';
let aspectRatio = 1024/768;

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = `${role}: ${text}`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendStreamBubble(kind, text, at) {
  const item = document.createElement('div');
  item.className = 'tl-item';
  const time = document.createElement('div');
  time.className = 'tl-time';
  time.textContent = at ? new Date(at).toLocaleTimeString() : '';
  const bubble = document.createElement('div');
  bubble.className = `tl-bubble ${kind}`;
  bubble.textContent = text;
  item.appendChild(time);
  item.appendChild(bubble);
  streamList.appendChild(item);
  streamList.scrollTop = streamList.scrollHeight;
}

async function createSession() {
  if (currentSessionId) {
    try { await fetch(`${API_BASE}/sessions/${currentSessionId}/archive`, { method: 'POST' }); } catch (e) {}
  }
  const data = await fetchJson(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
  });
  currentSessionId = data.id;
  sessionIdEl.textContent = `Session: ${currentSessionId}`;
  // Use per-session novnc port if present
  const vm = data.metadata_json?.vm;
  if (vm?.novnc_port) {
    vncUrl = `http://localhost:${vm.novnc_port}/vnc.html?autoconnect=true&resize=scale`;
  }
  // reset UI before connecting
  messagesEl.innerHTML = '';
  streamList.innerHTML = '';
  connectWebSocket();
  ensureVncFrame();
  await loadSessions();
}

function connectWebSocket() {
  if (!currentSessionId) return;
  if (ws) ws.close();
  const url = API_BASE.replace('http', 'ws') + `/sessions/${currentSessionId}/stream`;
  ws = new WebSocket(url);
  ws.onopen = () => appendStreamBubble('api', '[connected]');
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      const t = msg.type;
      if (t === 'user_message') {
        const content = msg.message?.content || '';
        addMessage('user', content);
        appendStreamBubble('user', content, msg.at);
      } else if (t === 'assistant_block') {
        const block = msg.data;
        if (block?.type === 'text' && block.text) {
          addMessage('assistant', block.text);
        }
        appendStreamBubble('assistant', JSON.stringify(block).slice(0, 500), msg.at);
      } else if (t === 'assistant_message') {
        appendStreamBubble('assistant', '[assistant_message]', msg.at);
      } else if (t === 'tool_result') {
        // Render tool result; if image present, show below stream area
        appendStreamBubble('tool', `${msg.tool_use_id || ''}\n${(msg.data?.output || '').slice(0,800)}`, msg.at);
        if (msg.data?.base64_image) {
          const img = document.createElement('img');
          img.src = `data:image/png;base64,${msg.data.base64_image}`;
          img.style.maxWidth = '100%';
          img.style.border = '1px solid #333';
          const item = document.createElement('div');
          item.className = 'tl-item';
          const time = document.createElement('div');
          time.className = 'tl-time';
          time.textContent = msg.at ? new Date(msg.at).toLocaleTimeString() : '';
          const bubble = document.createElement('div');
          bubble.className = 'tl-bubble tool';
          bubble.appendChild(img);
          item.appendChild(time);
          item.appendChild(bubble);
          streamList.appendChild(item);
          streamList.scrollTop = streamList.scrollHeight;
        }
      } else if (t === 'api') {
        appendStreamBubble('api', `${msg.data?.request?.method || ''} ${msg.data?.request?.url || ''} -> ${msg.data?.response?.status || ''}`, msg.at);
      } else if (t === 'assistant_done') {
        appendStreamBubble('assistant', '[assistant_done]', msg.at);
      } else {
        appendStreamBubble('api', JSON.stringify(msg));
      }
    } catch (e) {
      appendStreamBubble('api', ev.data);
    }
  };
  ws.onclose = () => appendStreamBubble('api', '[disconnected]');
}

async function ensureVncFrame() {
  // Using same-origin proxy at /novnc/, no need to fetch API info
  if (vncFrame && vncFrame.src !== vncUrl) {
    vncFrame.src = vncUrl;
  }
  if (novncNewTab) {
    novncNewTab.href = vncUrl;
  }
  // Apply initial size
  setVncSize(parseInt(vncWidthInput.value, 10), parseInt(vncHeightInput.value, 10), false);
}

async function sendMessage() {
  if (!currentSessionId) return;
  const text = userInput.value.trim();
  if (!text) return;
  userInput.value = '';
  await fetch(`${API_BASE}/sessions/${currentSessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: text })
  });
}

createSessionBtn.addEventListener('click', createSession);
sendBtn.addEventListener('click', sendMessage);
refreshSessionsBtn?.addEventListener('click', loadSessions);

// Initialize VNC iframe on load
ensureVncFrame();

function setVncSize(w, h, fromHeightChange) {
  if (!Number.isFinite(w) || !Number.isFinite(h)) return;
  if (fitToggle?.checked) {
    // In fit mode, we don't apply explicit pixel sizes; let CSS scale to container
    vncFrame.style.width = '100%';
    vncFrame.style.height = '100%';
    return;
  }
  if (lockAspectInput.checked) {
    if (fromHeightChange) {
      w = Math.round(h * aspectRatio);
    } else {
      h = Math.round(w / aspectRatio);
    }
  } else {
    aspectRatio = w / h;
  }
  vncFrame.style.width = w + 'px';
  vncFrame.style.height = h + 'px';
  vncWidthInput.value = w;
  vncHeightInput.value = h;
}

vncWidthInput?.addEventListener('input', () => {
  const w = parseInt(vncWidthInput.value, 10);
  const h = parseInt(vncHeightInput.value, 10);
  setVncSize(w, h, false);
});

vncHeightInput?.addEventListener('input', () => {
  const w = parseInt(vncWidthInput.value, 10);
  const h = parseInt(vncHeightInput.value, 10);
  setVncSize(w, h, true);
});

fitToggle?.addEventListener('change', () => {
  const container = document.getElementById('vncContainer');
  if (fitToggle.checked) {
    container.classList.add('fit');
  } else {
    container.classList.remove('fit');
  }
  const w = parseInt(vncWidthInput.value, 10);
  const h = parseInt(vncHeightInput.value, 10);
  setVncSize(w, h, false);
});

document.querySelectorAll('.preset').forEach(btn => {
  btn.addEventListener('click', () => {
    const w = parseInt(btn.getAttribute('data-w'), 10);
    const h = parseInt(btn.getAttribute('data-h'), 10);
    setVncSize(w, h, false);
  });
});

async function loadSessions() {
  try {
    const items = await fetchJson(`${API_BASE}/sessions`);
    renderSessionList(items);
  } catch (e) {
    appendStreamBubble('api', `[error] load sessions: ${e.message || e}`);
  }
}

function renderSessionList(items) {
  sessionList.innerHTML = '';
  items.forEach(s => {
    const el = document.createElement('div');
    el.className = 'session-item';
    const title = document.createElement('div');
    title.className = 'session-title';
    title.textContent = s.title || s.id;
    const meta = document.createElement('div');
    meta.className = 'session-meta';
    meta.textContent = `${s.status} • ${new Date(s.updated_at).toLocaleString()}`;
    el.appendChild(title);
    el.appendChild(meta);
    el.addEventListener('click', async () => {
      currentSessionId = s.id;
      sessionIdEl.textContent = `Session: ${currentSessionId}`;
      try {
        const detail = await fetchJson(`${API_BASE}/sessions/${s.id}`);
        const vm = detail.session?.metadata_json?.vm || s.metadata_json?.vm;
        if (vm?.novnc_port) {
          vncUrl = `http://localhost:${vm.novnc_port}/vnc.html?autoconnect=true&resize=scale`;
        }
        // render existing messages
        messagesEl.innerHTML = '';
        (detail.messages || []).forEach(m => {
          if (m.role === 'user' && m.content) addMessage('user', m.content);
          if (m.role === 'assistant' && m.content_json) {
            const textBlocks = (m.content_json || []).filter(b => b.type === 'text');
            textBlocks.forEach(b => addMessage('assistant', b.text || ''));
          }
        });
        // render stored events (if available)
        try {
          const events = await fetchJson(`${API_BASE}/sessions/${s.id}/events`);
          streamList.innerHTML = '';
          events.forEach(ev => {
            const t = ev.type;
            if (t === 'user_message') {
              appendStreamBubble('user', ev.message?.content || '', ev.at);
            } else if (t === 'assistant_block') {
              appendStreamBubble('assistant', JSON.stringify(ev.data).slice(0,500), ev.at);
            } else if (t === 'tool_result') {
              appendStreamBubble('tool', `${ev.tool_use_id || ''}\n${(ev.data?.output || '').slice(0,800)}`, ev.at);
              if (ev.data?.base64_image) {
                const img = document.createElement('img');
                img.src = `data:image/png;base64,${ev.data.base64_image}`;
                img.style.maxWidth = '100%';
                img.style.border = '1px solid #333';
                const item = document.createElement('div');
                item.className = 'tl-item';
                const time = document.createElement('div');
                time.className = 'tl-time';
                time.textContent = ev.at ? new Date(ev.at).toLocaleTimeString() : '';
                const bubble = document.createElement('div');
                bubble.className = 'tl-bubble tool';
                bubble.appendChild(img);
                item.appendChild(time);
                item.appendChild(bubble);
                streamList.appendChild(item);
              }
            } else if (t === 'api') {
              appendStreamBubble('api', `${ev.data?.request?.method || ''} ${ev.data?.request?.url || ''} -> ${ev.data?.response?.status || ''}`, ev.at);
            } else if (t === 'assistant_message') {
              appendStreamBubble('assistant', '[assistant_message]', ev.at);
            } else if (t === 'assistant_done') {
              appendStreamBubble('assistant', '[assistant_done]', ev.at);
            }
          });
        } catch (e) {
          // ignore if events backend not configured
          streamList.innerHTML = '';
        }
      } catch (e) {}
      connectWebSocket();
      ensureVncFrame();
    });
    sessionList.appendChild(el);
  });
}

// initial load
loadSessions();
// Monitor iframe connection state heuristically
function markVncOnline(online) {
  if (!vncStatus) return;
  vncStatus.textContent = online ? 'online' : 'offline';
  vncStatus.classList.toggle('online', online);
  vncStatus.classList.toggle('offline', !online);
}

vncFrame?.addEventListener('load', () => markVncOnline(true));
vncFrame?.addEventListener('error', () => markVncOnline(false));
vncReconnect?.addEventListener('click', () => {
  markVncOnline(false);
  vncFrame.src = vncUrl + `&t=${Date.now()}`;
});

// Optional: VM reset (disabled by default to avoid desktop instability)
async function resetVm() { /* intentionally no-op */ }


