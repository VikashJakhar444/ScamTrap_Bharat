// Internationalization (i18n) Module for English & Hindi Toggle

const translations = {
    en: {
        app_title: "ScamTrap Bharat",
        app_subtitle: "National Citizen Cyber Defense & Pre-Fraud Interception Portal",
        sandbox_badge: "Local Safe Sandbox (100% Offline Integrity)",
        lang_toggle_btn: "🌐 हिंदी में देखें",
        
        // Navigation Tabs
        tab_checker: "🔍 1. Check a Scam",
        tab_honeypot: "🤖 2. Trap Scammer (Live AI)",
        tab_proof: "📄 3. Scammer Proof & Police PDF",
        tab_trends: "📊 4. Scam Trends & Why Us",

        // Tab 1: Check a Scam
        card1_heading: "Check Any Suspicious Message, UPI ID, or Phone Number",
        card1_desc: "Verify suspicious payment demands before sending ₹1. Our active engine cross-references verified scam registries and analyzes financial threat patterns.",
        quick_search_label: "Check a UPI ID, Phone Number, or Bank Account",
        quick_search_placeholder: "e.g., bijli.board.pay@ybl or 9876543210",
        btn_quick_search: "🔍 Check Database",
        chip_test_upi: "Test Scam UPI: bijli.board.pay@ybl",
        chip_test_msg: "Test Scam Msg: Electricity Bill Disconnect",
        
        paste_msg_label: "Paste a Suspicious WhatsApp / SMS Message",
        paste_msg_placeholder: "Paste the message asking for urgent payment, KYC update, or electricity bill...",
        attach_screenshot_btn: "📷 Attach Scam Screenshot (Optional)",
        btn_analyze_msg: "🛡️ Check If This Is a Scam",
        
        card2_heading: "Instant Safety Result & Citizen Co-Pilot",
        placeholder_result: "Enter a UPI ID or message on the left to check its threat level.",
        
        copilot_box_heading: "💡 Want to Expose Their Backup Bank Account Safely?",
        copilot_box_desc: "Generate a realistic 'NPCI U16 UPI Daily Limit Reached' error screenshot. When sent to the scammer, they greedily reveal their secondary backup bank account!",
        btn_gen_bait: "📸 Generate Fake 'Payment Failed' Screenshot",
        btn_send_honeypot: "🤖 Hand Over to Live AI Honeypot (Tab 2)",

        // Tab 2: Trap Scammer
        tab2_title: "Live 2-Phone Autonomous WhatsApp Trap Node",
        tab2_desc: "Connect Phone 1 via WhatsApp Web QR code to autonomously engage scammers in natural Hinglish and safely capture their secondary mule accounts.",
        wa_conn_title: "WhatsApp Node Connection",
        wa_status_standby: "Standby — Scan QR to Link Phone 1",
        wa_threads_title: "Active Scammer Threads",
        btn_start_trap: "🎯 Start AI Trap",
        btn_trap_active: "🛑 AI Trap Active",
        wa_tip: "💡 Tip: On Phone 1, you can also text 'trap' to yourself to activate the AI on the latest scammer!",
        
        chat_header_title: "Live WhatsApp Conversation",
        chat_status_decoy: "🤖 Citizen AI Decoy Active",
        btn_reset_chat: "🔄 Reset Chat",
        btn_send_msg_1st_upi: "⚡ Test Electricity Threat + UPI",
        btn_send_2nd_bank: "🏦 Test 2nd Backup Bank A/C",
        btn_test_scammer_click: "🔗 Test Scammer Clicking Trap Link",
        btn_go_to_tab3: "📄 View Full Police Report (Go to Tab 3) →",

        // Tab 3: Proof & Police PDF
        tab3_banner_title: "Official Cybercrime Complaint Evidence File (NCRP 1930 Format)",
        btn_download_1930_pdf: "📥 Download 1930 Police Report PDF",
        card_upi_title: "💳 Scammer's UPI IDs",
        card_bank_title: "🏦 Scammer's Bank Accounts & IFSC",
        card_device_title: "🌐 Scammer's Network IP & Device Info",
        card_chat_title: "💬 Complete Chat & Visual Bait Log",

        // Tab 4: Scam Trends
        kpi_attempts: "Total Scam Attempts Blocked",
        kpi_blacklisted: "Scammer UPI IDs Blacklisted",
        kpi_mules: "Mule Bank Accounts Exposed",
        kpi_saved: "Est. Citizen Money Saved",
        table_blacklist_title: "Public Blacklisted UPI & Phone Directory",
        chart_category_title: "Scam Category Breakdown",
        table_matrix_title: "🏆 Why ScamTrap Bharat is Different from Existing Tools"
    },
    hi: {
        app_title: "स्कैमट्रैप भारत",
        app_subtitle: "राष्ट्रीय नागरिक साइबर सुरक्षा एवं प्री-फ्रॉड इंटरसेप्शन पोर्टल",
        sandbox_badge: "सुरक्षित सैंडबॉक्स मोड (100% स्थानीय सुरक्षा)",
        lang_toggle_btn: "🌐 View in English",
        
        // Navigation Tabs
        tab_checker: "🔍 1. स्कैम की जांच करें",
        tab_honeypot: "🤖 2. स्कैमर को ट्रैप करें (लाइव AI)",
        tab_proof: "📄 3. स्कैमर सबूत एवं पुलिस PDF",
        tab_trends: "📊 4. स्कैम रुझान एवं तुलना",

        // Tab 1: Check a Scam
        card1_heading: "संदिग्ध मैसेज, UPI ID या फोन नंबर की तुरंत जांच करें",
        card1_desc: "₹1 भी भेजने से पहले संदिग्ध मांग की जांच करें। हमारा एक्टिव इंजन ज्ञात स्कैम रिकॉर्ड और वित्तीय धोखाधड़ी पैटर्न की पहचान करता है।",
        quick_search_label: "UPI ID, फोन नंबर या बैंक खाता दर्ज करें",
        quick_search_placeholder: "जैसे: bijli.board.pay@ybl या 9876543210",
        btn_quick_search: "🔍 डेटाबेस में खोजें",
        chip_test_upi: "परीक्षण स्कैम UPI: bijli.board.pay@ybl",
        chip_test_msg: "परीक्षण स्कैम संदेश: बिजली बिल कनेक्शन",
        
        paste_msg_label: "संदिग्ध व्हाट्सएप / SMS मैसेज पेस्ट करें",
        paste_msg_placeholder: "बिजली बिल, बैंक KYC या तत्काल भुगतान मांगने वाला मैसेज यहां पेस्ट करें...",
        attach_screenshot_btn: "📷 स्कैम का स्क्रीनशॉट संलग्न करें (वैकल्पिक)",
        btn_analyze_msg: "🛡️ जांचें कि क्या यह स्कैम है",
        
        card2_heading: "त्वरित सुरक्षा परिणाम एवं नागरिक को-पायलट",
        placeholder_result: "खतरे की जांच के लिए बाईं ओर UPI ID या संदेश दर्ज करें।",
        
        copilot_box_heading: "💡 क्या आप उनका दूसरा बैकअप बैंक खाता सुरक्षित पकड़ना चाहते हैं?",
        copilot_box_desc: "असली जैसा 'NPCI U16 UPI Daily Limit' स्क्रीनशॉट बनाएं। जब आप इसे भेजेंगे, तो स्कैमर अपना दूसरा बैकअप बैंक खाता बता देगा!",
        btn_gen_bait: "📸 नकली 'Payment Failed' स्क्रीनशॉट बनाएं",
        btn_send_honeypot: "🤖 लाइव AI हनीपॉट को सौंपें (टैब 2)",

        // Tab 2: Trap Scammer
        tab2_title: "लाइव 2-फ़ोन स्वायत्त व्हाट्सएप ट्रैप नोड",
        tab2_desc: "स्कैमर्स से स्वाभाविक हिंग्लिश में बात करने और उनके बैकअप बैंक खाते सुरक्षित रूप से पकड़ने के लिए फोन 1 को जोड़ें।",
        wa_conn_title: "व्हाट्सएप नोड कनेक्शन",
        wa_status_standby: "तैयार — फोन 1 जोड़ने के लिए QR स्कैन करें",
        wa_threads_title: "सक्रिय स्कैमर चैट",
        btn_start_trap: "🎯 AI ट्रैप शुरू करें",
        btn_trap_active: "🛑 AI ट्रैप सक्रिय है",
        wa_tip: "💡 सलाह: फोन 1 पर आप खुद को 'trap' लिखकर भी अंतिम स्कैमर पर AI एक्टिवेट कर सकते हैं!",
        
        chat_header_title: "लाइव व्हाट्सएप बातचीत",
        chat_status_decoy: "🤖 नागरिक AI डिकॉय सक्रिय",
        btn_reset_chat: "🔄 चैट रीसेट करें",
        btn_send_msg_1st_upi: "⚡ बिजली बिल धमकी + UPI भेजें",
        btn_send_2nd_bank: "🏦 2nd बैकअप बैंक खाता भेजें",
        btn_test_scammer_click: "🔗 स्कैमर द्वारा लिंक क्लिक का परीक्षण करें",
        btn_go_to_tab3: "📄 पूरी पुलिस रिपोर्ट देखें (टैब 3 पर जाएं) →",

        // Tab 3: Proof & Police PDF
        tab3_banner_title: "आधिकारिक साइबर अपराध सबूत फ़ाइल (NCRP 1930 प्रारूप)",
        btn_download_1930_pdf: "📥 1930 पुलिस रिपोर्ट PDF डाउनलोड करें",
        card_upi_title: "💳 स्कैमर के UPI IDs",
        card_bank_title: "🏦 स्कैमर के बैंक खाते एवं IFSC",
        card_device_title: "🌐 स्कैमर का नेटवर्क IP व डिवाइस विवरण",
        card_chat_title: "💬 पूरी बातचीत एवं स्क्रीनशॉट लॉग",

        // Tab 4: Scam Trends
        kpi_attempts: "रोके गए कुल स्कैम प्रयास",
        kpi_blacklisted: "ब्लैकलिस्टेड स्कैमर UPI IDs",
        kpi_mules: "पकड़े गए बैकअप बैंक खाते",
        kpi_saved: "नागरिकों के बचाए गए अनुमानित पैसे",
        table_blacklist_title: "सार्वजनिक ब्लैकलिस्टेड UPI एवं फोन डायरेक्टरी",
        chart_category_title: "स्कैम श्रेणियों का विश्लेषण",
        table_matrix_title: "🏆 स्कैमट्रैप भारत दूसरों से अलग क्यों है"
    }
};

let currentLanguage = 'en';

function toggleLanguage() {
    currentLanguage = currentLanguage === 'en' ? 'hi' : 'en';
    applyTranslations();
}

function applyTranslations() {
    const t = translations[currentLanguage];
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) {
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = t[key];
            } else {
                // If element has a pulse dot child, preserve it
                const dot = el.querySelector('.pulse-dot');
                if (dot) {
                    el.childNodes.forEach(node => {
                        if (node.nodeType === Node.TEXT_NODE) {
                            node.textContent = ' ' + t[key];
                        }
                    });
                } else {
                    el.innerText = t[key];
                }
            }
        }
    });

    const langBtn = document.getElementById('lang-toggle-btn');
    if (langBtn) {
        langBtn.innerText = t.lang_toggle_btn;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    applyTranslations();
    const btn = document.getElementById('lang-toggle-btn');
    if (btn) {
        btn.addEventListener('click', toggleLanguage);
    }
});
