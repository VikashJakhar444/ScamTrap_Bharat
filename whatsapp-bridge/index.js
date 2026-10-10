/**
 * ScamTrap Bharat · WhatsApp Bridge (Mode 2 / Cloud AI Node)
 *
 * Responsibilities
 *  - Owns the real WhatsApp session (LocalAuth, persisted under ./.wwebjs_auth)
 *  - Shows a QR code in the console AND pushes it to the Python backend so the
 *    browser can render it
 *  - Forwards every inbound message to the Python backend webhook
 *  - Sends outbound replies with a human typing delay so the scammer never
 *    sees bot-like behaviour
 *
 * The backend is the single source of truth for the reply itself; this file
 * only moves bytes and simulates a human.
 */

const fs = require('fs');
const path = require('path');
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const QRCode = require('qrcode');
require('qrcode-terminal');

// --------------------------------------------------------------------------- #
// Config (env first, .env file second, safe defaults last)
// --------------------------------------------------------------------------- #
function loadEnvFile() {
  const p = path.join(__dirname, '.env');
  if (!fs.existsSync(p)) return;
  for (const line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/i);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2];
  }
}
loadEnvFile();
// Also read the project root .env so both processes share one token.
(function readRootEnv() {
  const p = path.join(__dirname, '..', '.env');
  if (!fs.existsSync(p)) return;
  for (const line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/i);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2];
  }
})();

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8050';
const BRIDGE_PORT = parseInt(process.env.BRIDGE_PORT || '3000', 10);
const BRIDGE_TOKEN = process.env.BRIDGE_TOKEN || '';

// Human typing simulation (average realistic WhatsApp reply behaviour)
const READ_DELAY_MIN_MS = 2000;
const READ_DELAY_MAX_MS = 6000;
const TYPING_CPS = 14;           // characters per second a normal person types
const TYPING_JITTER = 0.4;       // +/- 40 %
const MAX_AUTO_RETRY = 3;

const log = (...a) => console.log(`[bridge ${new Date().toISOString()}]`, ...a);

// --------------------------------------------------------------------------- #
// WhatsApp client
// --------------------------------------------------------------------------- #
const { Client, LocalAuth } = require('whatsapp-web.js');

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: path.join(__dirname, '.wwebjs_auth') }),
  puppeteer: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  },
});

let connected = false;
let linkedPhone = null;
let currentQrData = null;
let currentQrPng = null;

// --------------------------------------------------------------------------- #
// Backend helpers
// --------------------------------------------------------------------------- */
async function pushStatus(extra = {}) {
  try {
    await axios.post(
      `${BACKEND}/api/honeypot/wa-status`,
      {
        connected,
        qr_data: currentQrData,
        qr_code: currentQrPng,
        phone_number: linkedPhone,
        ...extra,
      },
      { timeout: 4000 }
    );
  } catch (e) {
    log('status push failed:', e.message);
  }
}

async function forwardInbound(from, body, wamid) {
  try {
    const res = await axios.post(
      `${BACKEND}/api/honeypot/webhook`,
      { from, text: body, wamid },
      { headers: { 'x-bridge-token': BRIDGE_TOKEN }, timeout: 45000 }
    );
    log('webhook ->', res.data.status, res.data.reason || '');
    return res.data;
  } catch (e) {
    log('webhook failed:', e.message);
    return null;
  }
}

// --------------------------------------------------------------------------- #
// Human timing
// --------------------------------------------------------------------------- */
function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function humanDelayFor(text) {
  const read = READ_DELAY_MIN_MS + Math.random() * (READ_DELAY_MAX_MS - READ_DELAY_MIN_MS);
  const typing = ((text || '').length / TYPING_CPS) * 1000;
  const jitter = 1 + (Math.random() * 2 - 1) * TYPING_JITTER;
  return Math.round(read + typing * jitter);
}

// --------------------------------------------------------------------------- #
// WhatsApp events
// --------------------------------------------------------------------------- */
client.on('qr', (qr) => {
  currentQrData = qr;
  currentQrPng = null;
  connected = false;
  log('Scan this QR with WhatsApp (Linked Devices):');
  QRCode.toString(qr, { type: 'terminal', small: true }, (err, ascii) => {
    if (!err) console.log(ascii);
  });
  QRCode.toDataURL(qr, { width: 320 }, (err, url) => {
    if (!err) currentQrPng = url;
    pushStatus();
  });
});

client.on('ready', () => {
  connected = true;
  currentQrData = null;
  currentQrPng = null;
  log('WhatsApp session ready');
  pushStatus();
});

client.on('authenticated', () => log('authenticated'));
client.on('auth_failure', (m) => { log('auth failure:', m); connected = false; pushStatus(); });
client.on('disconnected', (r) => { log('disconnected:', r); connected = false; pushStatus(); });

client.on('message', async (msg) => {
  try {
    // Ignore groups, broadcasts, status and anything without text.
    if (msg.isStatus || msg.from.endsWith('@g.us') || msg.from.endsWith('@broadcast') ||
        msg.from.endsWith('@newsletter')) return;
    if (!msg.from.endsWith('@c.us')) return;
    const body = (msg.body || '').trim();
    if (!body) return;

    log(`inbound ${msg.from}: ${body.slice(0, 80)}`);
    const data = await forwardInbound(msg.from, body, msg.id && msg.id._serialized);
    // Auto-reply path: the backend already generated it and stored send_state=0.
    // We pick it up from the outbox rather than inventing anything here.
    if (data && data.status === 'Reply Delivered') {
      await deliverOutbox();
    }
  } catch (e) {
    log('inbound handler error:', e.message);
  }
});

// --------------------------------------------------------------------------- #
// Outbound
// --------------------------------------------------------------------------- */
async function sendWithHumanDelay(to, text, meta = {}) {
  const toJid = to.endsWith('@c.us') ? to : `${to}@c.us`;
  const delay = meta.delay_ms || humanDelayFor(text);
  try {
    const chat = await client.getChatById(toJid);
    await chat.sendStateTyping();
    await sleep(delay);
    await client.sendMessage(toJid, text);
    await chat.clearTyping();
    log(`sent to ${toJid} after ${delay}ms`);
    return true;
  } catch (e) {
    log('send failed:', e.message);
    return false;
  }
}

async function deliverOutbox() {
  let ids = [];
  try {
    const res = await axios.get(`${BACKEND}/api/honeypot/outbox`, {
      params: { pending: 1 },
      timeout: 6000,
    });
    const items = (res.data && res.data.outbox) || [];
    if (!items.length) return;
    for (const item of items) {
      const ok = await sendWithHumanDelay(item.to_phone, item.text);
      if (ok) ids.push(item.id);
    }
    if (ids.length) {
      await axios.post(`${BACKEND}/api/honeypot/sents`, { ids }, { timeout: 6000 });
    }
  } catch (e) {
    log('outbox delivery error:', e.message);
  }
}

// --------------------------------------------------------------------------- #
// Express (outbound API for the backend / UI)
// --------------------------------------------------------------------------- #
const app = express();
app.use(cors());
app.use(express.json({ limit: '1mb' }));

app.get('/status', (_req, res) => {
  res.json({ connected, phone: linkedPhone, has_qr: Boolean(currentQrData) });
});

app.post('/send', async (req, res) => {
  const { to, text } = req.body || {};
  if (!to || !text) return res.status(422).json({ error: 'to and text are required' });
  if (!connected) return res.status(503).json({ error: 'whatsapp not connected' });

  // Fire and forget so the caller is never blocked by the typing delay.
  const promise = sendWithHumanDelay(to, text).then((ok) => ({ ok }));
  // Keep a reference so Node does not GC a pending promise mid-flight.
  global.__pendingSends = (global.__pendingSends || []).filter((p) => p !== promise);
  global.__pendingSends.push(promise);
  res.json({ status: 'queued', to });
});

app.listen(BRIDGE_PORT, '127.0.0.1', () => {
  log(`bridge listening on http://127.0.0.1:${BRIDGE_PORT}`);
  log(`backend target: ${BACKEND}`);
});

// --------------------------------------------------------------------------- #
// Startup
// --------------------------------------------------------------------------- */
(async () => {
  log('initialising WhatsApp client (first run downloads Chromium, be patient)...');
  await client.initialize();
})();

// Periodic status heartbeat so the backend knows we are alive.
setInterval(pushStatus, 15000);
// Periodic outbox sweep so replies survive a restart.
setInterval(deliverOutbox, 10000);
