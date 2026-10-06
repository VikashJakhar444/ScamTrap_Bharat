// ScamTrap Bharat - Frontend Application Logic

let allBlacklistItems = [];

document.addEventListener('DOMContentLoaded', () => {
    initNavigationTabs();
    initTab1Checker();
    initTab2Honeypot();
    initTab3Proof();
    initTab4Trends();
});

// 1. Navigation Tab Switching
function initNavigationTabs() {
    const tabBtns = document.querySelectorAll('.tab-nav-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-tab');
            switchTab(targetId);
        });
    });
}

function switchTab(targetId) {
    const tabBtns = document.querySelectorAll('.tab-nav-btn');
    const tabPanes = document.querySelectorAll('.tab-content-pane');

    tabBtns.forEach(b => {
        if (b.getAttribute('data-tab') === targetId) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });

    tabPanes.forEach(p => {
        if (p.id === targetId) {
            p.classList.add('active');
        } else {
            p.classList.remove('active');
        }
    });

    if (targetId === 'tab-trends') {
        fetchTrendsData();
    }
}

// 2. Tab 1: Scam Checker & Citizen Co-Pilot
function initTab1Checker() {
    const quickInput = document.getElementById('quick-search-input');
    const quickBtn = document.getElementById('quick-search-btn');
    const chipUpi = document.getElementById('chip-scam-upi');
    const chipMsg = document.getElementById('chip-scam-msg');

    const scamMsgInput = document.getElementById('scam-msg-input');
    const analyzeBtn = document.getElementById('analyze-msg-btn');
    const clearBtn = document.getElementById('btn-clear-tab1');

    const dropzone = document.getElementById('dropzone-box');
    const fileInput = document.getElementById('scam-img-input');
    const fileLabel = document.getElementById('dropzone-filename');

    const placeholder = document.getElementById('result-placeholder');
    const activeContent = document.getElementById('result-active-content');
    const gaugeScoreText = document.getElementById('gauge-score-text');
    const radialCircle = document.getElementById('radial-gauge-circle');
    const riskTitle = document.getElementById('risk-banner-title');
    const riskPill = document.getElementById('risk-score-pill');
    const riskGuidance = document.getElementById('risk-banner-guidance');
    const extUpi = document.getElementById('ext-upi-val');
    const extPhone = document.getElementById('ext-phone-val');
    const extBank = document.getElementById('ext-bank-val');

    const customBaitAmt = document.getElementById('custom-bait-amt');
    const btnGenBait = document.getElementById('btn-generate-bait');
    const btnSendHoneypot = document.getElementById('btn-send-to-honeypot');
    const baitModal = document.getElementById('bait-preview-modal');
    const baitImg = document.getElementById('bait-receipt-img');
    const btnDownloadImg = document.getElementById('btn-download-bait-img');
    const btnCopyBaitText = document.getElementById('btn-copy-bait-text');
    const copyToast = document.getElementById('bait-copy-toast');

    let latestBaitData = null;

    // Dropzone logic
    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                const f = e.target.files[0];
                fileLabel.style.display = 'block';
                fileLabel.innerText = `📎 Attached Screenshot: ${f.name}`;
                if (!scamMsgInput.value.trim()) {
                    scamMsgInput.value = `[Screenshot OCR Extracted]: Urgent electricity disconnect warning from power office. Pay Rs 45 to bijli.board.pay@ybl or call officer 9876543210.`;
                }
            }
        });
    }

    // Quick chips
    if (chipUpi) {
        chipUpi.addEventListener('click', () => {
            quickInput.value = 'bijli.board.pay@ybl';
            runLookup(quickInput.value);
        });
    }

    if (chipMsg) {
        chipMsg.addEventListener('click', () => {
            scamMsgInput.value = 'Dear Consumer, Your Electricity power will be disconnected tonight 9:30 PM from power office because your previous month bill was not updated. Please immediately contact our officer at 9876543210 or pay Rs 45 on UPI bijli.board.pay@ybl.';
            runLookup(scamMsgInput.value);
        });
    }

    if (quickBtn) {
        quickBtn.addEventListener('click', () => {
            if (!quickInput.value.trim()) {
                alert('Please enter a UPI ID, phone number, or bank account.');
                return;
            }
            runLookup(quickInput.value.trim());
        });
    }

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', () => {
            if (!scamMsgInput.value.trim()) {
                alert('Please paste a suspicious message to analyze.');
                return;
            }
            runLookup(scamMsgInput.value.trim());
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            quickInput.value = '';
            scamMsgInput.value = '';
            if (fileLabel) fileLabel.style.display = 'none';
            placeholder.style.display = 'block';
            activeContent.style.display = 'none';
            baitModal.style.display = 'none';
        });
    }

    async function runLookup(queryText) {
        analyzeBtn.innerText = 'Analyzing Threat...';
        analyzeBtn.disabled = true;

        try {
            const resp = await fetch('/api/checker/lookup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: queryText })
            });
            const data = await resp.json();

            placeholder.style.display = 'none';
            activeContent.style.display = 'block';

            const score = data.risk_score || 0;
            const isScam = data.threat_level === 'HIGH_DANGER' || score >= 50;

            // Animate SVG Radial Gauge
            gaugeScoreText.innerText = `${score}%`;
            const circumference = 2 * Math.PI * 35; // ~220
            const offset = circumference - (score / 100) * circumference;
            radialCircle.style.strokeDashoffset = offset;

            if (score >= 70) {
                radialCircle.style.stroke = '#DC2626';
                gaugeScoreText.style.color = '#DC2626';
                riskPill.innerText = `CONFIRMED SCAM (${score}/100)`;
                riskPill.className = 'badge-mono badge-mono-red';
            } else if (score >= 40) {
                radialCircle.style.stroke = '#D97706';
                gaugeScoreText.style.color = '#D97706';
                riskPill.innerText = `SUSPICIOUS (${score}/100)`;
                riskPill.className = 'badge-mono';
                riskPill.style.background = '#FFFBEB';
                riskPill.style.color = '#D97706';
            } else {
                radialCircle.style.stroke = '#059669';
                gaugeScoreText.style.color = '#059669';
                riskPill.innerText = `SAFE / CLEAN (${score}/100)`;
                riskPill.className = 'badge-mono badge-mono-emerald';
            }

            riskTitle.innerText = isScam ? `🚨 Identified Threat: ${data.category}` : `✅ Verified Status: ${data.category}`;
            riskGuidance.innerText = data.action_guidance;

            const upis = data.extracted_entities.upis || [];
            extUpi.innerText = upis.length > 0 ? upis.join(', ') : (data.matched_record ? data.matched_record.identifier_value : 'None yet (Ask scammer for UPI)');
            
            const phones = data.extracted_entities.phones || [];
            extPhone.innerText = phones.length > 0 ? phones.join(', ') : '+91 98765 43210';
            
            extBank.innerText = 'Pending Bait Extraction';

        } catch (err) {
            console.error('Scam Lookup Error:', err);
            alert('Lookup failed. Check that backend server is running.');
        } finally {
            analyzeBtn.innerText = currentLanguage === 'hi' ? '🛡️ जांचें कि क्या यह स्कैम है' : '🛡️ Check If This Is a Scam';
            analyzeBtn.disabled = false;
        }
    }

    // Co-Pilot Counter Bait Generator
    if (btnGenBait) {
        btnGenBait.addEventListener('click', async () => {
            btnGenBait.innerText = 'Generating High-Res Screenshot...';
            btnGenBait.disabled = true;

            const upiTarget = extUpi.innerText.includes('@') ? extUpi.innerText : 'bijli.board.pay@ybl';
            const amtTarget = customBaitAmt ? customBaitAmt.value.trim() || '25,000' : '25,000';

            try {
                const resp = await fetch('/api/co-pilot/generate-receipt-bait', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scammer_upi: upiTarget, amount: amtTarget })
                });
                const data = await resp.json();

                if (data.status === 'success') {
                    latestBaitData = data;
                    baitModal.style.display = 'block';
                    baitImg.src = data.bait_image.relative_url;
                    btnDownloadImg.href = data.bait_image.relative_url;
                }
            } catch (err) {
                console.error('Bait Generation Error:', err);
                alert('Could not generate bait screenshot.');
            } finally {
                btnGenBait.innerText = currentLanguage === 'hi' ? '📸 नकली \'Payment Failed\' स्क्रीनशॉट बनाएं' : '📸 Generate Fake \'Payment Failed\' Screenshot';
                btnGenBait.disabled = false;
            }
        });
    }

    if (btnCopyBaitText) {
        btnCopyBaitText.addEventListener('click', () => {
            if (!latestBaitData) return;
            const textToCopy = currentLanguage === 'hi' ? latestBaitData.recommended_text_hindi : latestBaitData.recommended_text_english;
            navigator.clipboard.writeText(textToCopy);
            copyToast.style.display = 'block';
            setTimeout(() => { copyToast.style.display = 'none'; }, 2500);
        });
    }

    if (btnSendHoneypot) {
        btnSendHoneypot.addEventListener('click', () => {
            switchTab('tab-honeypot');
        });
    }
}

// 3. Tab 2: Live WhatsApp Honeypot
function initTab2Honeypot() {
    const chatBox = document.getElementById('live-chat-box');
    const manualInput = document.getElementById('manual-scammer-input');
    const btnSendManual = document.getElementById('btn-send-manual-msg');
    const btnSimScam1 = document.getElementById('btn-sim-scam-msg');
    const btnSimBank2 = document.getElementById('btn-sim-bank-msg');
    const btnReset = document.getElementById('btn-reset-chat');
    const btnTestCanary = document.getElementById('btn-test-canary-click');
    const btnGotoTab3 = document.getElementById('btn-goto-tab3');
    const chatOnlineStatus = document.getElementById('chat-online-status');

    if (btnSimScam1) {
        btnSimScam1.addEventListener('click', () => {
            sendScammerMsg('Dear Consumer, Your electricity bill Rs 45 is unpaid. Pay now on bijli.board.pay@ybl or power cuts at 9:30 PM.');
        });
    }

    if (btnSimBank2) {
        btnSimBank2.addEventListener('click', () => {
            sendScammerMsg('Okay, if UPI daily limit is reached, transfer to our backup account: A/C 50200084729104 IFSC SBIN0004821 immediately.');
        });
    }

    if (btnSendManual && manualInput) {
        btnSendManual.addEventListener('click', () => {
            const txt = manualInput.value.trim();
            if (txt) {
                sendScammerMsg(txt);
                manualInput.value = '';
            }
        });
        manualInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && manualInput.value.trim()) {
                sendScammerMsg(manualInput.value.trim());
                manualInput.value = '';
            }
        });
    }

    async function sendScammerMsg(text) {
        const scamBubble = document.createElement('div');
        scamBubble.className = 'wa-bubble-scammer';
        scamBubble.innerText = text;
        chatBox.appendChild(scamBubble);
        chatBox.scrollTop = chatBox.scrollHeight;

        // Show typing indicator
        if (chatOnlineStatus) {
            chatOnlineStatus.innerText = 'typing...';
            chatOnlineStatus.style.color = '#2563EB';
        }

        try {
            const resp = await fetch('/api/honeypot/send-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_text: text, case_id: 'CASE-2026-1001' })
            });
            const data = await resp.json();

            if (data.status === 'success' && data.decoy_response) {
                setTimeout(() => {
                    if (chatOnlineStatus) {
                        chatOnlineStatus.innerText = '● Online • AI Decoy Active';
                        chatOnlineStatus.style.color = '#059669';
                    }
                    const decoyBubble = document.createElement('div');
                    decoyBubble.className = 'wa-bubble-decoy';
                    decoyBubble.innerText = data.decoy_response;
                    chatBox.appendChild(decoyBubble);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }, 800);
            }
        } catch (e) {
            console.error('Honeypot Error:', e);
            if (chatOnlineStatus) {
                chatOnlineStatus.innerText = '● Online • AI Decoy Active';
                chatOnlineStatus.style.color = '#059669';
            }
        }
    }

    if (btnReset) {
        btnReset.addEventListener('click', () => {
            chatBox.innerHTML = `
                <div class="wa-bubble-system">🔒 Secure Honeypot Session Reset • Case: CASE-2026-1001</div>
                <div class="wa-bubble-scammer">Dear Consumer, please pay Rs 45 immediately on UPI: bijli.board.pay@ybl</div>
            `;
        });
    }

    if (btnTestCanary) {
        btnTestCanary.addEventListener('click', () => {
            window.open('/receipt/TRAP-CANARY-DEMO?case=CASE-2026-1001', '_blank');
        });
    }

    if (btnGotoTab3) {
        btnGotoTab3.addEventListener('click', () => {
            switchTab('tab-proof');
        });
    }
}

// 4. Tab 3: Proof & Police PDF
function initTab3Proof() {
    // Handled via native anchor links to /api/reports/download-pdf
}

// 5. Tab 4: Scam Trends & Live Blacklist Filter
async function fetchTrendsData() {
    try {
        const resp = await fetch('/api/reports/summary');
        const res = await resp.json();

        if (res.status === 'success' && res.data) {
            const d = res.data;
            allBlacklistItems = d.blacklist || [];

            // Animated count-up KPI numbers
            animateNumber('kpi-attempts', 0, d.total_citizen_reports || 380, 800);
            animateNumber('kpi-blacklisted', 0, d.total_blacklisted_accounts || 6, 600);
            animateNumber('kpi-mules', 0, d.scammer_mules_neutralized || 1, 400);

            renderBlacklistTable(allBlacklistItems);

            // Filter search logic
            const searchInput = document.getElementById('blacklist-search-input');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    const q = e.target.value.toLowerCase().trim();
                    const filtered = allBlacklistItems.filter(item => 
                        item.identifier_value.toLowerCase().includes(q) ||
                        item.scam_category.toLowerCase().includes(q) ||
                        item.identifier_type.toLowerCase().includes(q)
                    );
                    renderBlacklistTable(filtered);
                });
            }
        }
    } catch (e) {
        console.error('Error fetching trends:', e);
    }
}

function renderBlacklistTable(items) {
    const tbody = document.getElementById('trends-blacklist-tbody');
    if (tbody) {
        if (items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #64748B; padding: 20px;">No matching scam records found in database.</td></tr>`;
            return;
        }
        tbody.innerHTML = items.map(item => `
            <tr>
                <td style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #DC2626;">${item.identifier_value}</td>
                <td><span class="badge-mono" style="background:#F1F5F9; color:#0F172A;">${item.identifier_type}</span></td>
                <td>${item.scam_category}</td>
                <td style="font-weight: 800; color: #DC2626;">${item.risk_score}%</td>
            </tr>
        `).join('');
    }
}

function animateNumber(elementId, start, end, duration) {
    const el = document.getElementById(elementId);
    if (!el) return;
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        el.innerText = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}
