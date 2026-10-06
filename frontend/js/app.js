// ScamTrap Bharat Frontend Application Logic

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initChecker();
    initCoPilotBait();
    initHoneypotChat();
    initDossierDownload();
    fetchScamRadarSummary();
});

// 1. Tab Switching Logic
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add('active');
            }

            if (targetId === 'tab4') {
                fetchScamRadarSummary();
            }
        });
    });
}

// 2. Scam Checker & Heuristics
function initChecker() {
    const input = document.getElementById('checkerInput');
    const btnCheck = document.getElementById('btnRunCheck');
    const btnClear = document.getElementById('btnClearCheck');
    const resultBox = document.getElementById('checkerResultBox');
    const coPilotSection = document.getElementById('coPilotBaitSection');

    const sample1 = document.getElementById('sample1');
    const sample2 = document.getElementById('sample2');
    const sample3 = document.getElementById('sample3');

    if (sample1) {
        sample1.addEventListener('click', () => {
            input.value = "Dear Consumer, Your Electricity power will be disconnected tonight 9:30 PM from power office because your previous month bill was not updated. Please immediately contact our officer at 9876543210 or pay Rs 45 on UPI bijli.board.pay@ybl.";
            runScamCheck();
        });
    }

    if (sample2) {
        sample2.addEventListener('click', () => {
            input.value = "Dear SBI Customer, Your YONO NetBanking account has been blocked due to pending KYC verification. Please click here or transfer to sbi.kyc.update@okaxis to re-verify within 2 hours.";
            runScamCheck();
        });
    }

    if (sample3) {
        sample3.addEventListener('click', () => {
            input.value = "Hello mom, I reached the office safely and will be home by 7 PM today.";
            runScamCheck();
        });
    }

    if (btnClear) {
        btnClear.addEventListener('click', () => {
            input.value = "";
            resultBox.style.display = "none";
            coPilotSection.style.display = "none";
        });
    }

    if (btnCheck) {
        btnCheck.addEventListener('click', runScamCheck);
    }

    async function runScamCheck() {
        const query = input.value.trim();
        if (!query) {
            alert("Please enter a phone number, UPI ID, or paste a message to analyze.");
            return;
        }

        btnCheck.innerText = "Analyzing Threat...";
        btnCheck.disabled = true;

        try {
            const resp = await fetch('/api/checker/lookup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });
            const data = await resp.json();

            renderCheckResult(data);
        } catch (err) {
            console.error("Check Error:", err);
            alert("Could not complete scam check. Please ensure backend server is running.");
        } finally {
            btnCheck.innerText = currentLanguage === 'hi' ? "खतरे की जांच करें" : "Check Threat Level";
            btnCheck.disabled = false;
        }
    }

    function renderCheckResult(data) {
        resultBox.style.display = "block";
        const isDanger = data.threat_level === 'HIGH_DANGER' || data.risk_score >= 60;
        resultBox.className = `result-card ${isDanger ? 'danger' : 'clean'}`;

        let extractedList = [];
        if (data.extracted_entities.upis && data.extracted_entities.upis.length > 0) {
            extractedList.push(`<strong>Extracted UPI:</strong> ${data.extracted_entities.upis.join(', ')}`);
        }
        if (data.extracted_entities.phones && data.extracted_entities.phones.length > 0) {
            extractedList.push(`<strong>Contact Phone:</strong> ${data.extracted_entities.phones.join(', ')}`);
        }

        resultBox.innerHTML = `
            <div class="result-title">
                ${isDanger ? '🚨 HIGH THREAT SCAM DETECTED' : '✅ NO ACTIVE THREAT DETECTED'} 
                <span style="font-size: 0.85rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 9999px; background: ${isDanger ? '#fee2e2' : '#dcfce7'}; color: ${isDanger ? '#dc2626' : '#166534'};">
                    Risk Score: ${data.risk_score}/100
                </span>
            </div>
            <div style="margin-top: 0.5rem; font-size: 0.9rem; font-weight: 600; color: #1e293b;">
                Category: <span style="color: ${isDanger ? '#b91c1c' : '#047857'};">${data.category}</span>
            </div>
            <p style="margin-top: 0.4rem; font-size: 0.88rem; color: #334155; line-height: 1.5;">
                ${data.action_guidance}
            </p>
            ${extractedList.length > 0 ? `
                <div style="margin-top: 0.6rem; padding: 0.6rem; background: rgba(255,255,255,0.7); border-radius: 6px; font-size: 0.85rem;">
                    ${extractedList.join(' | ')}
                </div>
            ` : ''}
        `;

        if (data.counter_bait_available) {
            coPilotSection.style.display = "block";
        } else {
            coPilotSection.style.display = "none";
        }
    }
}

// 3. Citizen Co-Pilot Counter Bait Generator
function initCoPilotBait() {
    const btnGen = document.getElementById('btnGenerateBait');
    const baitOutput = document.getElementById('baitOutputContainer');
    const baitImg = document.getElementById('baitImageDisplay');
    const baitText = document.getElementById('baitRecommendedText');
    const btnCopy = document.getElementById('btnCopyBaitText');

    if (btnGen) {
        btnGen.addEventListener('click', async () => {
            btnGen.innerText = "Generating Synthetic Limit Receipt...";
            btnGen.disabled = true;

            try {
                const resp = await fetch('/api/co-pilot/generate-receipt-bait', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scammer_upi: "bijli.board.pay@ybl", amount: "450.00" })
                });
                const data = await resp.json();

                if (data.status === 'success') {
                    baitOutput.style.display = "block";
                    baitImg.src = data.bait_image.relative_url;
                    baitText.innerText = currentLanguage === 'hi' ? data.recommended_text_hindi : data.recommended_text_english;
                }
            } catch (err) {
                console.error("Bait Gen Error:", err);
                alert("Failed to generate counter-bait.");
            } finally {
                btnGen.innerText = currentLanguage === 'hi' ? "UPI लिमिट स्क्रीनशॉट बेट बनाएं" : "Generate UPI Limit Counter-Bait";
                btnGen.disabled = false;
            }
        });
    }

    if (btnCopy) {
        btnCopy.addEventListener('click', () => {
            navigator.clipboard.writeText(baitText.innerText);
            btnCopy.innerText = "✓ Copied to Clipboard!";
            setTimeout(() => {
                btnCopy.innerText = "📋 Copy Text to Clipboard";
            }, 2000);
        });
    }
}

// 4. Honeypot Chat Console
function initHoneypotChat() {
    const chatBox = document.getElementById('honeypotChatBox');
    const input = document.getElementById('honeypotInput');
    const btnSend = document.getElementById('btnSendHoneypot');

    if (btnSend && input) {
        btnSend.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Append scammer message immediately
        const scammerBubble = document.createElement('div');
        scammerBubble.className = 'chat-bubble scammer';
        scammerBubble.innerText = text;
        chatBox.appendChild(scammerBubble);
        input.value = "";
        chatBox.scrollTop = chatBox.scrollHeight;

        btnSend.disabled = true;

        try {
            const resp = await fetch('/api/honeypot/send-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_text: text, case_id: 'CASE-2026-1001' })
            });
            const data = await resp.json();

            if (data.status === 'success' && data.decoy_response) {
                setTimeout(() => {
                    const decoyBubble = document.createElement('div');
                    decoyBubble.className = 'chat-bubble decoy';
                    decoyBubble.innerText = data.decoy_response;
                    chatBox.appendChild(decoyBubble);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }, 600);
            }
        } catch (err) {
            console.error("Chat Error:", err);
        } finally {
            btnSend.disabled = false;
        }
    }
}

// 5. Scammer Dossier & PDF Export
function initDossierDownload() {
    const btnDownload = document.getElementById('btnDownloadDossier');
    const statusDiv = document.getElementById('pdfDownloadStatus');

    if (btnDownload) {
        btnDownload.addEventListener('click', async () => {
            btnDownload.innerText = "Generating Official 1930 PDF...";
            btnDownload.disabled = true;
            statusDiv.innerText = "Compiling trapped mule accounts, forensics & chat logs...";

            try {
                const resp = await fetch('/api/reports/generate-dossier', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ case_id: 'CASE-2026-1001' })
                });
                const data = await resp.json();

                if (data.status === 'success' && data.file) {
                    statusDiv.innerHTML = `✅ Dossier Generated: <a href="${data.file.relative_url}" target="_blank" style="color: #2563eb; font-weight: 700; text-decoration: underline;">Click here to Open / Download PDF</a>`;
                    window.open(data.file.relative_url, '_blank');
                }
            } catch (err) {
                console.error("PDF Gen Error:", err);
                statusDiv.innerText = "Failed to generate PDF dossier.";
            } finally {
                btnDownload.innerText = currentLanguage === 'hi' ? "📥 आधिकारिक 1930 सबूत डोजियर (PDF) डाउनलोड करें" : "📥 Download Official 1930 Evidence Dossier (PDF)";
                btnDownload.disabled = false;
            }
        });
    }
}

// 6. Scam Radar Live Summary
async function fetchScamRadarSummary() {
    try {
        const resp = await fetch('/api/reports/summary');
        const result = await resp.json();

        if (result.status === 'success' && result.data) {
            const d = result.data;
            const statBlacklisted = document.getElementById('statBlacklisted');
            const statReports = document.getElementById('statReports');
            const statTrapped = document.getElementById('statTrapped');

            if (statBlacklisted) statBlacklisted.innerText = d.total_blacklisted_accounts;
            if (statReports) statReports.innerText = d.total_citizen_reports;
            if (statTrapped) statTrapped.innerText = d.scammer_mules_neutralized;

            // Render Blacklist Table
            const tbody = document.getElementById('blacklistTableBody');
            if (tbody && d.blacklist) {
                tbody.innerHTML = d.blacklist.map(item => `
                    <tr>
                        <td style="font-weight: 700; color: #0f172a; font-family: monospace;">${item.identifier_value}</td>
                        <td><span class="badge-pill badge-${item.identifier_type.toLowerCase()}">${item.identifier_type}</span></td>
                        <td>${item.scam_category}</td>
                        <td style="font-weight: 700; color: #dc2626;">${item.risk_score}/100</td>
                        <td><strong>${item.reports_count}</strong> reports</td>
                    </tr>
                `).join('');
            }
        }
    } catch (err) {
        console.error("Radar Summary Fetch Error:", err);
    }
}
