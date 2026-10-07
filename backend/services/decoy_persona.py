import os
from typing import Dict, Any, List
from backend.config import GEMINI_API_KEY

SYSTEM_PROMPT = """You are 'Vikas Ji', a 52-year-old naive Indian middle-class citizen talking to a scammer over WhatsApp.
Your goal is to stay polite, scared, cooperative, and pretend you really want to pay/resolve the issue, but run into payment issues (e.g., 'UPI daily limit reached' or 'server error').
Ask the scammer for alternative payment options (like their secondary UPI ID, backup bank account number, IFSC code, or branch name).
Respond in natural, conversational Hinglish (Hindi + English). Keep answers short (1-2 sentences), realistic, and never reveal you are an AI or that this is a trap."""

def generate_decoy_reply(conversation_history: List[Dict[str, str]], scam_category: str = "Electricity Bill") -> str:
    """Generates an authentic decoy message response."""
    # If Gemini API key is configured and available
    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt_context = f"{SYSTEM_PROMPT}\nScam Context: {scam_category}\n\nChat History:\n"
            for msg in conversation_history:
                role = "Scammer" if msg.get("role") == "scammer" else "You (Vikas Ji)"
                prompt_context += f"{role}: {msg.get('text', '')}\n"
            prompt_context += "You (Vikas Ji): "
            
            response = model.generate_content(prompt_context)
            if response and response.text:
                return response.text.strip()
        except Exception:
            pass # Fallback to local rule-based engine
            
    # Local Rule-based conversational fallback engine
    last_msg = ""
    if conversation_history:
        last_msg = conversation_history[-1].get("text", "").lower()
        
    if "pay" in last_msg or "rs" in last_msg or "rupees" in last_msg or "upi" in last_msg:
        return "Sir maine Google Pay se try kiya par 'Bank Daily Limit Exceeded' aa raha hai. Kya aapka koi dusra Bank Account number ya backup UPI ID hai turant bhejiye?"
    elif "account" in last_msg or "ifsc" in last_msg:
        return "Theek hai sir note kar raha hoon. Account holder ka exact naam aur branch bhi bata dijiye taaki IMPS fail na ho?"
    elif "link" in last_msg or "click" in last_msg or "apk" in last_msg:
        return "Sir link open nahi ho raha, 'Invalid verification receipt' bol raha hai. Main aapko receipt ka screenshot bhej raha hoon, check kijiye?"
    else:
        return "Haanji sir please meri electricity/service mat band kijiyega. Kahan bhejna hai details bataiye main abhi karta hoon."
