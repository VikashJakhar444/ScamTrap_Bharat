/* ==========================================================================
   ScamTrap Bharat — i18n (English / हिंदी)
   - Every visible string carries data-i18n; inputs get their placeholder set.
   - t(key) exposes the same table to app.js for dynamic strings.
   ========================================================================== */

const translations = {
  en: {
    brand_name: 'ScamTrap Bharat',
    brand_tag: 'Citizen Cyber Defence Portal',
    status_local_db: 'Local database',
    lang_toggle: 'हिंदी',

    nav_checker: 'Check a scam',
    nav_honeypot: 'Trap the scammer',
    nav_proof: 'Evidence & PDF',
    nav_trends: 'Trends & compare',

    hero_eyebrow: 'Pre-fraud interception, not post-fraud alerts',
    hero_title: 'Catch the scammer before the money moves.',
    hero_lede:
      'Paste a suspicious message or UPI ID to score it against a live scam registry. Then let an AI decoy keep the scammer talking until they hand over their backup bank account — and export the whole transcript as a 1930-format complaint.',
    hero_cta_primary: 'Check a message now',
    hero_cta_secondary: 'Open live honeypot',
    trust_1: 'Records stay in a local SQLite file',
    trust_2: 'Evidence hash recomputed on every read',
    trust_3: 'English & हिंदी interface',

    pipe_title: 'How a case runs',
    pipe_live: 'Live',
    pipe_1_title: '1 · Score the message',
    pipe_1_note: 'Regex + keyword engine extracts UPI, phone, IFSC and bank account, then checks the registry.',
    pipe_2_title: '2 · Send a counter-bait',
    pipe_2_note: 'A “daily limit reached” receipt pushes the scammer toward a second, backup account.',
    pipe_3_title: '3 · Export the dossier',
    pipe_3_note: 'Transcript, identifiers and canary captures compile into a downloadable complaint PDF.',

    t1_num: 'Step 01',
    t1_title: 'Check a suspicious message',
    t1_desc: 'Runs against the local blacklist of UPI handles, phone numbers, IFSC codes and mule accounts. Nothing is sent anywhere.',
    t1_db_badge: 'SQLite registry',

    label_quick_lookup: 'Quick lookup',
    ph_quick_lookup: 'bijli.board.pay@ybl or 9876543210',
    btn_lookup: 'Check registry',
    chip_upi: 'Try a flagged UPI',
    chip_msg: 'Try an electricity-bill message',

    label_paste: 'Paste the full message',
    ph_paste: 'Paste the WhatsApp or SMS text asking for an urgent payment, KYC update or bill clearance…',
    dropzone_hint: 'Drop a screenshot, or ',
    dropzone_browse: 'browse files',
    dropzone_help: 'Optional. If a file is chosen and the box above is empty, sample text is filled in for the demo.',
    paste_helper: 'Image text is not OCR’d locally — type or paste what you see.',
    btn_clear: 'Clear',
    btn_analyze: 'Check if this is a scam',

    t1_result_title: 'Verdict & counter-bait',
    t1_result_desc: 'Risk score, matched registry record and the next safe move.',
    t1_empty_title: 'Nothing checked yet',
    t1_empty_note: 'Enter a UPI ID or paste a message on the left.',
    t1_loading: 'Querying registry…',

    gauge_caption: 'Risk score',
    pill_pending: 'Awaiting',
    pill_scam: 'Confirmed scam',
    pill_suspicious: 'Suspicious',
    pill_safe: 'No threat found',

    extracted_title: 'Extracted identifiers',
    lbl_upi: 'UPI handles',
    lbl_phone: 'Phone numbers',
    lbl_bank: 'Bank account / IFSC',
    ident_none: 'None found',
    ident_pending: 'Not extracted yet',

    copilot_title: 'Expose their backup account',
    copilot_desc:
      'Generate a realistic “NPCI U16 daily limit reached” receipt. Sent back to the scammer, it usually makes them reveal a second bank account they did not intend to share.',
    lbl_bait_amount: 'Amount',
    btn_gen_bait: 'Generate payment-failed screenshot',
    btn_to_honeypot: 'Hand over to the AI decoy',
    bait_title: 'Generated counter-bait receipt',
    btn_dl_img: 'Download image',
    btn_copy_reply: 'Copy ready reply',
    bait_copied: 'Copied — includes the tracking trap link.',

    verdict_threat: 'Identified threat',
    verdict_clean: 'No active threat matched',
    btn_generating: 'Generating…',
    btn_analyzing: 'Checking…',
    btn_generating_bait: 'Rendering screenshot…',

    t2_num: 'Step 02',
    t2_title: 'Run the AI decoy',
    t2_desc: 'Replies are generated locally and stored with the case. The WhatsApp bridge is optional — the console below runs without a phone.',
    btn_refresh: 'Refresh status',
    t2_node_title: 'Bridge node',
    t2_node_checking: 'Checking…',
    t2_node_online: 'Bridge connected',
    t2_node_standby: 'Standby · no phone linked',
    lbl_node_phone: 'Decoy number',
    lbl_node_persona: 'Persona',
    lbl_node_mode: 'Mode',
    t2_node_help: 'To link a real phone: open WhatsApp → Linked devices → Link a device, then scan the QR served by the bridge.',
    t2_threads_title: 'Active cases',
    t2_threads_empty: 'No cases yet. Run a check in step 1 first.',
    t2_tip: 'Tip: type “trap” in the box below to switch the decoy into extraction mode for the newest case.',
    t2_progress_title: 'Trap progress',
    prog_1: 'Scam demand received',
    prog_2: 'Primary UPI extracted',
    prog_3: 'Counter-bait sent',
    prog_4: 'Backup bank account captured',
    t2_stats_title: 'Session totals',
    stat_engaged: 'Cases engaged',
    stat_mules: 'Backup A/C exposed',
    btn_canary: 'Open the trap link',
    btn_go_evidence: 'Open evidence dossier',

    chat_name: 'Citizen decoy console',
    chat_status: 'Online · decoy active',
    chat_typing: 'Decoy is typing…',
    chat_boot: 'Secure session ready',
    btn_reset_chat: 'Reset',
    btn_sim_bill: 'Send bill threat',
    btn_sim_bank: 'Send backup A/C',
    lbl_manual_msg: 'Message to send as the scammer',
    ph_manual_msg: 'Type a message to send as the scammer…',
    btn_send: 'Send',
    btn_sending: 'Sending…',
    trap_keyword_ack: 'Decoy switched to extraction mode for the newest case.',

    t3_num: 'Step 03',
    t3_title: 'Evidence dossier',
    t3_desc: 'Everything below is read back from the local database. Fields that have not actually been captured show as pending rather than a placeholder value.',
    t3_eyebrow: 'Cybercrime complaint evidence file · NCRP 1930 format',
    btn_dl_pdf: 'Download 1930 complaint PDF',
    t3_upi_title: 'UPI handles',
    t3_bank_title: 'Bank accounts & IFSC',
    t3_device_title: 'Canary capture (device & network)',
    t3_device_note: 'Populated only when the trap link is opened. Until then this panel stays pending.',
    t3_chat_title: 'Full transcript',
    btn_copy: 'Copy',
    ev_pending: 'Awaiting capture',
    ev_none: 'Nothing recorded yet',
    ev_none_note: 'Run a check in step 1 to populate this panel.',
    ev_reports: 'reports',
    ev_blacklisted: 'Blacklisted',
    ev_not_listed: 'Not in registry',
    ev_captures: 'captures recorded',
    ev_role_scammer: 'SCAMMER',
    ev_role_ai_decoy: 'DECOY',
    ev_role_system: 'SYSTEM',
    copied_toast: 'Copied to clipboard.',
    copy_nothing: 'Nothing to copy yet.',

    t4_num: 'Reference',
    t4_title: 'Registry trends & comparison',
    t4_desc: 'Counts are aggregated live from the blacklist table each time this tab opens.',
    kpi_reports: 'Citizen reports logged',
    kpi_blacklisted: 'Identifiers blacklisted',
    kpi_cases: 'Cases opened',
    kpi_resolved: 'Cases resolved',
    t4_blacklist_title: 'Public blacklist directory',
    lbl_filter: 'Filter the blacklist',
    ph_filter: 'Filter by value, type or category…',
    th_identifier: 'Identifier',
    th_type: 'Type',
    th_category: 'Category',
    th_risk: 'Risk',
    th_loading: 'Loading registry…',
    th_empty: 'No matching records',
    t4_chart_title: 'Category breakdown',
    chart_empty: 'No categories in the registry yet.',
    t4_compare_title: 'Where this differs from existing tools',
    t4_compare_desc: 'Comparison against consumer-facing alternatives available in India.',
    th_capability: 'Capability',
    th_sanchar: 'Sanchar Saathi',
    th_voicebots: 'Voice bots',
    th_ours: 'This tool',

    cmp_r1: 'Works on WhatsApp & UPI text scams',
    cmp_r2: 'Flags a UPI handle before money is sent',
    cmp_r3: 'Coaxes out a second backup account',
    cmp_r4: 'Logs the link-clicker’s IP & device',
    cmp_r5: 'One-click complaint PDF in 1930 format',
    cmp_r6: 'Evidence hash recomputed per read',
    cmp_yes: 'Yes',
    cmp_no: 'No',
    cmp_sms: 'SMS only',
    cmp_imei: 'IMEI only',
    cmp_ref: 'Reference no.',

    footer_blurb:
      'A citizen-facing cyber-safety workbench: score a suspicious message, run an AI decoy against the scammer, and export a complaint-ready evidence file. All records live in a local SQLite database.',
    footer_screens: 'Screens',
    footer_resources: 'Resources',
    footer_status: 'Status',
    footer_legal: 'Educational sandbox. Always report fraud on the official 1930 portal.',
    link_ncrp: 'cybercrime.gov.in',
    link_1930: 'Helpline 1930',
    link_apidocs: 'API documentation',
    link_sanchar: 'Sanchar Saathi',
    link_health: 'Service health',
    link_storage: 'storage/scamtrap.db',
    link_sandbox: 'No outbound reporting',

    toast_error_network: 'Could not reach the local server. Is the backend running?',
    toast_error_generic: 'Something went wrong. Check the browser console for details.',
    toast_bait_failed: 'Could not generate the receipt image.',
    toast_bait_empty: 'Generate the screenshot first, then copy the reply.',
    doc_title: 'ScamTrap Bharat — Check a scam, trap the scammer, file the report'
  },

  hi: {
    brand_name: 'स्कैमट्रैप भारत',
    brand_tag: 'नागरिक साइबर सुरक्षा पोर्टल',
    status_local_db: 'स्थानीय डेटाबेस',
    lang_toggle: 'English',

    nav_checker: 'स्कैम जाँचें',
    nav_honeypot: 'स्कैमर फँसाएँ',
    nav_proof: 'सबूत व PDF',
    nav_trends: 'रुझान व तुलना',

    hero_eyebrow: 'धोखाधड़ी से पहले रोकथाम, बाद की चेतावनी नहीं',
    hero_title: 'पैसे हिलने से पहले स्कैमर को पकड़ें।',
    hero_lede:
      'संदिग्ध मैसेज या UPI ID पेस्ट करें और उसे लाइव स्कैम रजिस्ट्री से जाँचें। फिर AI डिकॉय स्कैमर से तब तक बात करता रहेगा जब तक वह अपना बैकअप बैंक खाता न बता दे — और पूरी बातचीत को 1930 प्रारूप की शिकायत के रूप में निर्यात करें।',
    hero_cta_primary: 'अभी मैसेज जाँचें',
    hero_cta_secondary: 'लाइव हनीपॉट खोलें',
    trust_1: 'रिकॉर्ड स्थानीय SQLite फ़ाइल में रहते हैं',
    trust_2: 'हर बार पढ़ने पर सबूत हैश दोबारा बनता है',
    trust_3: 'अंग्रेज़ी व हिंदी इंटरफ़ेस',

    pipe_title: 'केस कैसे चलता है',
    pipe_live: 'लाइव',
    pipe_1_title: '1 · मैसेज को आँकें',
    pipe_1_note: 'रेगेक्स + कीवर्ड इंजन UPI, फोन, IFSC और बैंक खाता निकालकर रजिस्ट्री से मिलान करता है।',
    pipe_2_title: '2 · काउंटर-बेट भेजें',
    pipe_2_note: '“डेली लिमिट पूरी” वाली रसीद स्कैमर को दूसरे बैकअप खाते की ओर धकेलती है।',
    pipe_3_title: '3 · डोसियर निर्यात करें',
    pipe_3_note: 'बातचीत, पहचान और कैनरी कैप्चर को डाउनलोड करने योग्य शिकायत PDF में संकलित किया जाता है।',

    t1_num: 'चरण 01',
    t1_title: 'संदिग्ध मैसेज जाँचें',
    t1_desc: 'यह स्थानीय ब्लैकलिस्ट — UPI हैंडल, फोन नंबर, IFSC कोड और म्यूल खातों — के विरुद्ध चलता है। कुछ भी बाहर नहीं भेजा जाता।',
    t1_db_badge: 'SQLite रजिस्ट्री',

    label_quick_lookup: 'त्वरित खोज',
    ph_quick_lookup: 'bijli.board.pay@ybl या 9876543210',
    btn_lookup: 'रजिस्ट्री जाँचें',
    chip_upi: 'फ्लैग किया UPI आज़माएँ',
    chip_msg: 'बिजली बिल वाला मैसेज आज़माएँ',

    label_paste: 'पूरा मैसेज पेस्ट करें',
    ph_paste: 'तत्काल भुगतान, KYC अपडेट या बिल भरने को कहने वाला WhatsApp/SMS टेक्स्ट यहाँ पेस्ट करें…',
    dropzone_hint: 'स्क्रीनशॉट यहाँ छोड़ें, या ',
    dropzone_browse: 'फ़ाइल चुनें',
    dropzone_help: 'वैकल्पिक। फ़ाइल चुनने पर और ऊपर का बॉक्स खाली हो तो डेमो के लिए नमूना टेक्स्ट भर दिया जाता है।',
    paste_helper: 'तस्वीर का टेक्स्ट स्थानीय रूप से OCR नहीं होता — जो दिखे वह टाइप या पेस्ट करें।',
    btn_clear: 'साफ़ करें',
    btn_analyze: 'जाँचें कि यह स्कैम है या नहीं',

    t1_result_title: 'निर्णय व काउंटर-बेट',
    t1_result_desc: 'जोखिम स्कोर, मिला रजिस्ट्री रिकॉर्ड और अगला सुरक्षित कदम।',
    t1_empty_title: 'अभी कुछ जाँचा नहीं गया',
    t1_empty_note: 'बाईं ओर UPI ID दर्ज करें या मैसेज पेस्ट करें।',
    t1_loading: 'रजिस्ट्री से पूछा जा रहा है…',

    gauge_caption: 'जोखिम स्कोर',
    pill_pending: 'प्रतीक्षा में',
    pill_scam: 'पुष्ट स्कैम',
    pill_suspicious: 'संदिग्ध',
    pill_safe: 'कोई खतरा नहीं',

    extracted_title: 'निकाले गए पहचान-तत्व',
    lbl_upi: 'UPI हैंडल',
    lbl_phone: 'फोन नंबर',
    lbl_bank: 'बैंक खाता / IFSC',
    ident_none: 'कुछ नहीं मिला',
    ident_pending: 'अभी निकाला नहीं गया',

    copilot_title: 'उनका बैकअप खाता उजागर करें',
    copilot_desc:
      'असली जैसी “NPCI U16 डेली लिमिट पहुँच गई” रसीद बनाएँ। स्कैमर को भेजने पर वह आमतौर पर वह दूसरा बैंक खाता बता देता है जो वह बताना नहीं चाहता था।',
    lbl_bait_amount: 'राशि',
    btn_gen_bait: 'पेमेंट फ़ेल स्क्रीनशॉट बनाएँ',
    btn_to_honeypot: 'AI डिकॉय को सौंपें',
    bait_title: 'बनाया गया काउंटर-बेट रसीद',
    btn_dl_img: 'चित्र डाउनलोड करें',
    btn_copy_reply: 'तैयार जवाब कॉपी करें',
    bait_copied: 'कॉपी हो गया — ट्रैकिंग ट्रैप लिंक शामिल है।',

    verdict_threat: 'पहचाना गया खतरा',
    verdict_clean: 'कोई सक्रिय खतरा मेल नहीं खाया',
    btn_generating: 'बनाया जा रहा है…',
    btn_analyzing: 'जाँच रहे हैं…',
    btn_generating_bait: 'स्क्रीनशॉट बन रहा है…',

    t2_num: 'चरण 02',
    t2_title: 'AI डिकॉय चलाएँ',
    t2_desc: 'जवाब स्थानीय रूप से बनते हैं और केस के साथ सहेजे जाते हैं। WhatsApp ब्रिज वैकल्पिक है — नीचे का कंसोल बिना फोन भी चलता है।',
    btn_refresh: 'स्थिति ताज़ा करें',
    t2_node_title: 'ब्रिज नोड',
    t2_node_checking: 'जाँच रहे हैं…',
    t2_node_online: 'ब्रिज जुड़ा हुआ',
    t2_node_standby: 'स्टैंडबाय · फोन जुड़ा नहीं',
    lbl_node_phone: 'डिकॉय नंबर',
    lbl_node_persona: 'व्यक्तित्व',
    lbl_node_mode: 'मोड',
    t2_node_help: 'असली फोन जोड़ने के लिए: WhatsApp खोलें → लिंक किए डिवाइस → डिवाइस लिंक करें, फिर ब्रिज का QR स्कैन करें।',
    t2_threads_title: 'सक्रिय केस',
    t2_threads_empty: 'अभी कोई केस नहीं। पहले चरण 1 से जाँच करें।',
    t2_tip: 'सुझाव: नीचे दिए बॉक्स में “trap” लिखकर डिकॉय को नए केस के लिए एक्सट्रैक्शन मोड में डालें।',
    t2_progress_title: 'ट्रैप प्रगति',
    prog_1: 'स्कैम की माँग मिली',
    prog_2: 'मुख्य UPI निकाला गया',
    prog_3: 'काउंटर-बेट भेजा गया',
    prog_4: 'बैकअप बैंक खाता पकड़ा गया',
    t2_stats_title: 'सत्र कुल',
    stat_engaged: 'जुड़े गए केस',
    stat_mules: 'बेनकाब बैकअप खाते',
    btn_canary: 'ट्रैप लिंक खोलें',
    btn_go_evidence: 'सबूत डोसियर खोलें',

    chat_name: 'नागरिक डिकॉय कंसोल',
    chat_status: 'ऑनलाइन · डिकॉय सक्रिय',
    chat_typing: 'डिकॉय लिख रहा है…',
    chat_boot: 'सुरक्षित सत्र तैयार',
    btn_reset_chat: 'रीसेट',
    btn_sim_bill: 'बिल धमकी भेजें',
    btn_sim_bank: 'बैकअप खाता भेजें',
    lbl_manual_msg: 'स्कैमर के रूप में भेजा जाने वाला संदेश',
    ph_manual_msg: 'स्कैमर के रूप में भेजने के लिए मैसेज लिखें…',
    btn_send: 'भेजें',
    btn_sending: 'भेज रहे हैं…',
    trap_keyword_ack: 'डिकॉय नए केस के लिए एक्सट्रैक्शन मोड में आ गया।',

    t3_num: 'चरण 03',
    t3_title: 'सबूत डोसियर',
    t3_desc: 'नीचे का हर कुछ स्थानीय डेटाबेस से पढ़ा गया है। जो वास्तव में कैप्चर नहीं हुआ वह नमूना मान के बजाय “प्रतीक्षा में” दिखाया जाता है।',
    t3_eyebrow: 'साइबर अपराध शिकायत सबूत फ़ाइल · NCRP 1930 प्रारूप',
    btn_dl_pdf: '1930 शिकायत PDF डाउनलोड करें',
    t3_upi_title: 'UPI हैंडल',
    t3_bank_title: 'बैंक खाते व IFSC',
    t3_device_title: 'कैनरी कैप्चर (डिवाइस व नेटवर्क)',
    t3_device_note: 'यह तभी भरा जाता है जब ट्रैप लिंक खोला जाए। तब तक यह पैनल प्रतीक्षा में रहता है।',
    t3_chat_title: 'पूरी बातचीत',
    btn_copy: 'कॉपी',
    ev_pending: 'कैप्चर की प्रतीक्षा',
    ev_none: 'अभी कुछ दर्ज नहीं',
    ev_none_note: 'यह पैनल भरने के लिए चरण 1 से जाँच करें।',
    ev_reports: 'रिपोर्ट',
    ev_blacklisted: 'ब्लैकलिस्टेड',
    ev_not_listed: 'रजिस्ट्री में नहीं',
    ev_captures: 'कैप्चर दर्ज',
    ev_role_scammer: 'स्कैमर',
    ev_role_ai_decoy: 'डिकॉय',
    ev_role_system: 'सिस्टम',
    copied_toast: 'क्लिपबोर्ड पर कॉपी हो गया।',
    copy_nothing: 'अभी कॉपी करने को कुछ नहीं।',

    t4_num: 'संदर्भ',
    t4_title: 'रजिस्ट्री रुझान व तुलना',
    t4_desc: 'हर बार यह टैब खोलने पर गिनती ब्लैकलिस्ट तालिका से सीधे जोड़ी जाती है।',
    kpi_reports: 'दर्ज नागरिक रिपोर्ट',
    kpi_blacklisted: 'ब्लैकलिस्टेड पहचान-तत्व',
    kpi_cases: 'खोले गए केस',
    kpi_resolved: 'हल किए गए केस',
    t4_blacklist_title: 'सार्वजनिक ब्लैकलिस्ट डायरेक्टरी',
    lbl_filter: 'ब्लैकलिस्ट छानें',
    ph_filter: 'मान, प्रकार या श्रेणी से छानें…',
    th_identifier: 'पहचान-तत्व',
    th_type: 'प्रकार',
    th_category: 'श्रेणी',
    th_risk: 'जोखिम',
    th_loading: 'रजिस्ट्री लोड हो रही है…',
    th_empty: 'कोई मेल नहीं खाया',
    t4_chart_title: 'श्रेणी विश्लेषण',
    chart_empty: 'रजिस्ट्री में अभी कोई श्रेणी नहीं।',
    t4_compare_title: 'यह मौजूदा टूल्स से कहाँ अलग है',
    t4_compare_desc: 'भारत में उपलब्ध उपभोक्ता-उपकरणों से तुलना।',
    th_capability: 'क्षमता',
    th_sanchar: 'संचार साथी',
    th_voicebots: 'वॉइस बॉट',
    th_ours: 'यह टूल',

    cmp_r1: 'WhatsApp व UPI टेक्स्ट स्कैम पर काम करता है',
    cmp_r2: 'पैसे जाने से पहले UPI हैंडल फ्लैग करता है',
    cmp_r3: 'दूसरा बैकअप खाता निकलवाता है',
    cmp_r4: 'लिंक खोलने वाले का IP व डिवाइस दर्ज करता है',
    cmp_r5: '1930 प्रारूप में एक-क्लिक शिकायत PDF',
    cmp_r6: 'हर पढ़ने पर सबूत हैश दोबारा बनता है',
    cmp_yes: 'हाँ',
    cmp_no: 'नहीं',
    cmp_sms: 'केवल SMS',
    cmp_imei: 'केवल IMEI',
    cmp_ref: 'संदर्भ नं.',

    footer_blurb:
      'नागरिकों के लिए साइबर-सुरक्षा कार्यक्षेत्र: संदिग्ध मैसेज को आँकें, स्कैमर के विरुद्ध AI डिकॉय चलाएँ, और शिकायत-योग्य सबूत फ़ाइल निर्यात करें। सारा रिकॉर्ड स्थानीय SQLite डेटाबेस में रहता है।',
    footer_screens: 'स्क्रीन',
    footer_resources: 'संसाधन',
    footer_status: 'स्थिति',
    footer_legal: 'शैक्षिक सैंडबॉक्स। धोखाधड़ी की शिकायत हमेशा आधिकारिक 1930 पोर्टल पर करें।',
    link_ncrp: 'cybercrime.gov.in',
    link_1930: 'हेल्पलाइन 1930',
    link_apidocs: 'API दस्तावेज़ीकरण',
    link_sanchar: 'संचार साथी',
    link_health: 'सेवा स्वास्थ्य',
    link_storage: 'storage/scamtrap.db',
    link_sandbox: 'कोई बाहरी रिपोर्टिंग नहीं',

    toast_error_network: 'स्थानीय सर्वर से संपर्क नहीं हुआ। क्या बैकएंड चल रहा है?',
    toast_error_generic: 'कुछ गड़बड़ हुई। विवरण के लिए ब्राउज़र कंसोल देखें।',
    toast_bait_failed: 'रसीद चित्र बनाया नहीं जा सका।',
    toast_bait_empty: 'पहले स्क्रीनशॉट बनाएँ, फिर जवाब कॉपी करें।',
    doc_title: 'स्कैमट्रैप भारत — स्कैम जाँचें, स्कैमर फँसाएँ, शिकायत दर्ज करें'
  }
};

let currentLanguage = 'en';

/** Returns a translated string; falls back to the key itself. */
function t(key) {
  const table = translations[currentLanguage] || translations.en;
  return table[key] !== undefined ? table[key] : (translations.en[key] !== undefined ? translations.en[key] : key);
}

function toggleLanguage() {
  currentLanguage = currentLanguage === 'en' ? 'hi' : 'en';
  applyTranslations();
}

function applyTranslations() {
  const isPlaceholderField = (el) => el.tagName === 'INPUT' || el.tagName === 'TEXTAREA';

  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const value = t(el.getAttribute('data-i18n'));
    if (isPlaceholderField(el)) {
      el.placeholder = value;
    } else {
      el.textContent = value;
    }
  });

  // Controls whose visible text is hidden by CSS still need a spoken name.
  document.querySelectorAll('[data-i18n-aria]').forEach((el) => {
    el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria')));
  });

  document.documentElement.lang = currentLanguage;
  document.title = t('doc_title');

  // Re-render anything the app built dynamically.
  document.dispatchEvent(new CustomEvent('i18n:changed', { detail: { lang: currentLanguage } }));
}

document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
  const btn = document.getElementById('lang-toggle-btn');
  if (btn) btn.addEventListener('click', toggleLanguage);
});
