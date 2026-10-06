/**
 * ScamTrap Bharat - WhatsApp Node Bridge
 * Connects Phone 1 via WhatsApp Web to autonomously interact with scammers.
 */

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const path = require('path');
const fs = require('fs');

const API_BASE = 'http://localhost:8050/api/honeypot';
let lastScammerPhone = null;

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', (qr) => {
    console.log('[WhatsApp Bridge] Scan this QR Code to connect Phone 1:');
    qrcode.generate(qr, { small: true });

    // Inform backend of QR code
    axios.post(`${API_BASE}/wa-status`, {
        connected: false,
        qr_code: qr
    }).catch(() => {});
});

client.on('ready', () => {
    console.log('>>> [WhatsApp Bridge] Honeypot Node is CONNECTED and Online!');
    const myNumber = client.info.wid.user;

    axios.post(`${API_BASE}/wa-status`, {
        connected: true,
        phone_number: `+${myNumber}`
    }).catch(() => {});
});

client.on('message', async (msg) => {
    try {
        const fromNumber = msg.from.split('@')[0];
        const bodyText = msg.body.trim();

        // Check if user texted 'trap' to themselves
        if (msg.fromMe || msg.to === msg.from) {
            if (bodyText.toLowerCase() === 'trap' && lastScammerPhone) {
                console.log(`[WhatsApp Bridge] 'trap' command activated for latest scammer: ${lastScammerPhone}`);
                await axios.post(`${API_BASE}/toggle-trap`, {
                    phone_number: `+${lastScammerPhone}`,
                    is_active: true
                });
                return;
            }
        }

        // Record last scammer number
        lastScammerPhone = fromNumber;

        // Check backend if trap is active for this sender
        const statusResp = await axios.get(`${API_BASE}/status`);
        const trapActiveMap = statusResp.data.trap_active_numbers || {};
        const isTrapActive = trapActiveMap[`+${fromNumber}`] || trapActiveMap[fromNumber];

        if (isTrapActive) {
            console.log(`[WhatsApp Bridge] Intercepted scammer message from +${fromNumber}: "${bodyText}"`);
            
            // Forward message to backend AI Decoy Engine
            const replyResp = await axios.post(`${API_BASE}/incoming`, {
                case_id: 'CASE-2026-1001',
                sender_role: 'scammer',
                message_text: bodyText,
                sender_phone: `+${fromNumber}`
            });

            const decoyText = replyResp.data.decoy_response;
            if (decoyText) {
                // Simulate human typing delay (2-4 seconds)
                setTimeout(async () => {
                    await client.sendMessage(msg.from, decoyText);
                    console.log(`[WhatsApp Bridge] AI Decoy replied to +${fromNumber}: "${decoyText}"`);
                }, 2500);
            }
        }
    } catch (err) {
        console.error('[WhatsApp Bridge Error]:', err.message);
    }
});

// Periodic outbox poller for sending generated baits/messages
setInterval(async () => {
    try {
        const resp = await axios.get(`${API_BASE}/outbox`);
        const queue = resp.data.outbox || [];
        for (const item of queue) {
            const targetChat = `${item.to_phone.replace('+', '').replace(/\s+/g, '')}@c.us`;
            if (item.media_path && fs.existsSync(item.media_path)) {
                const media = MessageMedia.fromFilePath(item.media_path);
                await client.sendMessage(targetChat, media, { caption: item.text });
            } else if (item.text) {
                await client.sendMessage(targetChat, item.text);
            }
        }
    } catch (e) {
        // Backend might be offline
    }
}, 3000);

client.initialize();
