// Internationalization (i18n) Module for English & Hindi Toggle

const translations = {
    en: {
        app_title: "ScamTrap Bharat",
        app_subtitle: "Citizen Cyber Safety & Active Scam Account Hunter",
        sandbox_badge: "🔒 100% Local Safe Sandbox (Zero External Data Sharing)",
        lang_toggle_btn: "🌐 हिंदी (Switch to Hindi)",
        
        // Navigation Tabs
        tab_checker: "🔍 Check a Scam & Co-Pilot",
        tab_honeypot: "🤖 Live WhatsApp Honeypot",
        tab_dossier: "📄 Scammer Proof & Police PDF",
        tab_radar: "📊 Bharat Scam Radar",

        // Tab 1: Scam Checker
        checker_title: "Check Suspicious UPI ID, Phone Number or Message",
        checker_desc: "Enter any phone number, UPI ID, or paste a full WhatsApp message. Our local engine checks the scam registry and extracts financial threat patterns.",
        input_placeholder: "e.g. 9876543210, bijli.board.pay@ybl, or paste: 'Dear Consumer your electricity power will be disconnected tonight...'",
        btn_check: "Check Threat Level",
        btn_clear: "Clear",
        quick_test_label: "Quick Sample Tests:",
        sample_electricity: "⚡ Electricity Bill Scam",
        sample_kyc: "🏦 Bank KYC Block Scam",
        sample_clean: "✅ Genuine Clean Number",
        
        // Co-Pilot Counter Bait Card
        copilot_title: "Citizen Counter-Bait Co-Pilot",
        copilot_desc: "Generate a realistic 'UPI Daily Limit Reached' screenshot to send the scammer, tricking them into revealing their secondary bank account or alternate UPI ID.",
        btn_gen_bait: "Generate UPI Limit Counter-Bait",
        
        // Tab 2: Live WhatsApp Honeypot
        honeypot_title: "Autonomous 2-Phone WhatsApp Trap Node",
        honeypot_desc: "Connects a dedicated honeypot mobile to automatically chat with scammers in natural Hinglish. Traps secondary accounts without risking any citizen money.",
        honeypot_status_active: "Active Node: Online (Standby)",
        honeypot_persona_label: "Active AI Decoy Persona: 'Vikas Ji' (Elderly Retired Citizen)",
        btn_start_trap: "Start Live AI Trap",
        honeypot_chat_header: "Simulated Honeypot WhatsApp Conversation",
        input_scammer_msg_placeholder: "Type message as scammer (e.g. 'Pay Rs 45 now or power will cut')...",
        btn_send_scammer: "Send as Scammer",
        
        // Tab 3: Scammer Proof & Police PDF
        dossier_title: "Scammer Digital Evidence & 1930 Cyber Cell Dossier",
        dossier_desc: "Directly export verified scammer UPI IDs, Bank Accounts, IFSC codes, and device forensics ready for immediate freezing by Cyber Police.",
        mule_accounts_heading: "Trapped Scam Accounts & Financial Identifiers",
        device_forensics_heading: "Captured Scammer Device & Network Audit",
        btn_download_pdf: "📥 Download Official 1930 Evidence Dossier (PDF)",

        // Tab 4: Bharat Scam Radar
        radar_title: "Bharat Scam Radar & Active Defense Matrix",
        radar_desc: "Real-time statistics from your local sandbox and comparison of how ScamTrap Bharat stops fraud before money is lost.",
        stat_blacklisted: "Blacklisted Scam Identifiers",
        stat_reports: "Total Citizen Reports Analyzed",
        stat_trapped: "Mule Bank Accounts Trapped",
        stat_loss: "Citizen Financial Loss",
        table_heading: "Live Public Scam Blacklist (SQLite Database)",
        matrix_heading: "Why ScamTrap Bharat is Different (Comparison Matrix)"
    },
    hi: {
        app_title: "स्कैमट्रैप भारत",
        app_subtitle: "नागरिक साइबर सुरक्षा एवं सक्रिय स्कैम खाता हंटर",
        sandbox_badge: "🔒 100% स्थानीय सुरक्षित सैंडबॉक्स (कोई बाहरी डेटा साझा नहीं)",
        lang_toggle_btn: "🌐 English (स्विच करें)",
        
        // Navigation Tabs
        tab_checker: "🔍 स्कैम की जांच एवं को-पायलट",
        tab_honeypot: "🤖 लाइव व्हाट्सएप हनीपॉट",
        tab_dossier: "📄 स्कैमर सबूत एवं पुलिस PDF",
        tab_radar: "📊 भारत स्कैम रडार",

        // Tab 1: Scam Checker
        checker_title: "संदिग्ध UPI ID, फोन नंबर या मैसेज की तुरंत जांच करें",
        checker_desc: "कोई भी फोन नंबर, UPI ID दर्ज करें या पूरा व्हाट्सएप मैसेज पेस्ट करें। हमारा सिस्टम स्कैम डेटाबेस में जांच कर वित्तीय धोखाधड़ी की पहचान करता है।",
        input_placeholder: "जैसे: 9876543210, bijli.board.pay@ybl, या पेस्ट करें: 'Dear Consumer your electricity power will be disconnected tonight...'",
        btn_check: "खतरे की जांच करें",
        btn_clear: "साफ़ करें",
        quick_test_label: "त्वरित परीक्षण नमूने:",
        sample_electricity: "⚡ बिजली बिल स्कैम",
        sample_kyc: "🏦 बैंक KYC ब्लॉक स्कैम",
        sample_clean: "✅ सुरक्षित नंबर",
        
        // Co-Pilot Counter Bait Card
        copilot_title: "नागरिक काउंटर-बेट को-पायलट",
        copilot_desc: "स्कैमर को भेजने के लिए असली जैसा 'UPI Daily Limit Reached' स्क्रीनशॉट बनाएं, जिससे वह अपना दूसरा बैकअप बैंक खाता या वैकल्पिक UPI ID बता दे।",
        btn_gen_bait: "UPI लिमिट स्क्रीनशॉट बेट बनाएं",
        
        // Tab 2: Live WhatsApp Honeypot
        honeypot_title: "स्वायत्त 2-फ़ोन व्हाट्सएप ट्रैप नोड",
        honeypot_desc: "स्कैमर्स से स्वचालित रूप से स्वाभाविक हिंग्लिश में चैट करने के लिए समर्पित हनीपॉट फोन जोड़ता है और नागरिक का ₹1 गंवाए बिना उनके बैंक खाते पकड़ता है।",
        honeypot_status_active: "सक्रिय नोड: ऑनलाइन (तैयार)",
        honeypot_persona_label: "सक्रिय AI डिकॉय: 'विकास जी' (वरिष्ठ नागरिक)",
        btn_start_trap: "लाइव AI ट्रैप शुरू करें",
        honeypot_chat_header: "सिम्युलेटेड हनीपॉट व्हाट्सएप बातचीत",
        input_scammer_msg_placeholder: "स्कैमर के रूप में मैसेज लिखें (जैसे: 'तुरंत 45 रुपये भरें वरना बिजली कटेगी')...",
        btn_send_scammer: "स्कैमर की ओर से भेजें",
        
        // Tab 3: Scammer Proof & Police PDF
        dossier_title: "स्कैमर डिजिटल सबूत एवं 1930 साइबर सेल डोजियर",
        dossier_desc: "साइबर पुलिस द्वारा तुरंत खाते फ्रीज कराने के लिए सत्यापित स्कैमर UPI ID, बैंक खाते, IFSC और डिवाइस डिजिटल सबूत सीधे डाउनलोड करें।",
        mule_accounts_heading: "पकड़े गए स्कैम बैंक खाते एवं UPI IDs",
        device_forensics_heading: "पकड़ा गया स्कैमर डिवाइस व नेटवर्क ऑडिट",
        btn_download_pdf: "📥 आधिकारिक 1930 सबूत डोजियर (PDF) डाउनलोड करें",

        // Tab 4: Bharat Scam Radar
        radar_title: "भारत स्कैम रडार एवं सक्रिय सुरक्षा मैट्रिक्स",
        radar_desc: "स्थानीय डेटाबेस से लाइव आंकड़े और तुलना कि स्कैमट्रैप भारत पैसे डूबने से पहले ही धोखाधड़ी को कैसे रोकता है।",
        stat_blacklisted: "ब्लैकलिस्टेड स्कैम खाते",
        stat_reports: "विश्लेषण की गई नागरिक रिपोर्टें",
        stat_trapped: "पकड़े गए बैकअप बैंक खाते",
        stat_loss: "नागरिक वित्तीय नुकसान",
        table_heading: "लाइव पब्लिक स्कैम ब्लैकलिस्ट (SQLite डेटाबेस)",
        matrix_heading: "स्कैमट्रैप भारत दूसरों से अलग क्यों है (तुलना चार्ट)"
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
                el.innerText = t[key];
            }
        }
    });

    const langBtn = document.getElementById('langToggleBtn');
    if (langBtn) {
        langBtn.innerText = t.lang_toggle_btn;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    applyTranslations();
    const btn = document.getElementById('langToggleBtn');
    if (btn) {
        btn.addEventListener('click', toggleLanguage);
    }
});
