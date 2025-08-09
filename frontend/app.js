const API_BASE = (window.API_BASE || 'http://localhost:8000');

const createSessionBtn = document.getElementById('createSessionBtn');
const sessionIdEl = document.getElementById('sessionId');
const messagesEl = document.getElementById('messages');
const streamOutEl = document.getElementById('streamOut');
const sendBtn = document.getElementById('sendBtn');
const userInput = document.getElementById('userInput');
const vncFrame = document.getElementById('vncFrame');

let currentSessionId = null;
let ws = null;
let vncUrl = 'http://localhost:6080/vnc.html?autoconnect=true';

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = `${role}: ${text}`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendStream(text) {
  streamOutEl.textContent += text + '\n';
  streamOutEl.scrollTop = streamOutEl.scrollHeight;
}

async function createSession() {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  });
  const data = await res.json();
  currentSessionId = data.id;
  sessionIdEl.textContent = `Session: ${currentSessionId}`;
  connectWebSocket();
  ensureVncFrame();
}

function connectWebSocket() {
  if (!currentSessionId) return;
  if (ws) ws.close();
  const url = API_BASE.replace('http', 'ws') + `/sessions/${currentSessionId}/stream`;
  ws = new WebSocket(url);
  ws.onopen = () => appendStream('[connected]');
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'user_message') {
        addMessage('user', msg.message.content);
      } else if (msg.type === 'content_block_delta' || msg.type === 'message_delta' || msg.type === 'event') {
        appendStream(JSON.stringify(msg));
      } else {
        appendStream(JSON.stringify(msg));
      }
    } catch (e) {
      appendStream(ev.data);
    }
  };
  ws.onclose = () => appendStream('[disconnected]');
}

async function ensureVncFrame() {
  try {
    const res = await fetch(`${API_BASE}/vnc/info`);
    if (res.ok) {
      const data = await res.json();
      if (data && data.novnc_url) {
        vncUrl = data.novnc_url + (data.novnc_url.includes('?') ? '&' : '?') + 'autoconnect=true';
      }
    }
  } catch (e) {
    // ignore, fallback to default vncUrl
  }
  if (vncFrame && vncFrame.src !== vncUrl) {
    vncFrame.src = vncUrl;
  }
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

// Initialize VNC iframe on load
ensureVncFrame();


