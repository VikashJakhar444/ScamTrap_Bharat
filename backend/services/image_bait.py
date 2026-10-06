import os
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from backend.config import GENERATED_BAITS_DIR

def _get_font(size: int, bold: bool = False):
    """Safely loads Windows TrueType font or falls back to PIL default font."""
    font_paths = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def generate_upi_limit_receipt(scammer_upi: str = "bijli.board.pay@ybl", amount: str = "25,000") -> Dict[str, Any]:
    """
    Generates a crisp 600x960 Google Pay / PhonePe style Payment Failed screenshot.
    Includes NPCI U16 Daily Limit Exceeded warning box and asks for alternate account/IFSC.
    """
    width, height = 600, 960
    image = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(image)

    # Fonts
    font_title = _get_font(26, bold=True)
    font_subtitle = _get_font(16, bold=False)
    font_amount = _get_font(34, bold=True)
    font_bold_md = _get_font(15, bold=True)
    font_regular_md = _get_font(14, bold=False)
    font_small = _get_font(12, bold=False)

    # 1. Header Bar
    draw.rectangle([(0, 0), (width, 60)], fill="#F8FAFC")
    draw.line([(0, 60), (width, 60)], fill="#E2E8F0", width=1)
    draw.text((24, 20), "NPCI Unified Payments Interface", fill="#64748B", font=font_small)
    draw.text((width - 120, 20), "REF: GPay/2026", fill="#64748B", font=font_small)

    # 2. Failure Icon Circle (Red #DC2626)
    center_x = width // 2
    icon_y = 130
    radius = 38
    draw.ellipse([(center_x - radius, icon_y - radius), (center_x + radius, icon_y + radius)], fill="#DC2626")
    
    # White 'X' icon
    draw.line([(center_x - 16, icon_y - 16), (center_x + 16, icon_y + 16)], fill="#FFFFFF", width=5)
    draw.line([(center_x + 16, icon_y - 16), (center_x - 16, icon_y + 16)], fill="#FFFFFF", width=5)

    # 3. Main Headline & Amount
    draw.text((center_x, 195), "Payment Failed", fill="#0F172A", font=font_title, anchor="mt")
    draw.text((center_x, 230), "Declined by Receiver's Bank Server", fill="#DC2626", font=font_subtitle, anchor="mt")
    
    clean_amt = amount.replace("₹", "").replace("Rs", "").strip()
    draw.text((center_x, 265), f"₹{clean_amt}.00", fill="#0F172A", font=font_amount, anchor="mt")

    # 4. Amber Warning Box: U16 DAILY LIMIT EXCEEDED
    warn_box_top = 325
    warn_box_bottom = 435
    draw.rectangle([(30, warn_box_top), (width - 30, warn_box_bottom)], fill="#FFFBEB", outline="#FDE68A", width=2)
    
    draw.text((45, warn_box_top + 12), "⚠️ NPCI ERROR: U16 (RECEIVER LIMIT EXCEEDED)", fill="#92400E", font=font_bold_md)
    err_desc = f"The receiver UPI ID ({scammer_upi}) has reached its daily receiving limit of ₹1,00,000. Transfer cannot be completed to this VPA today."
    # Wrap text simply
    draw.text((45, warn_box_top + 38), "The receiver UPI ID has reached its daily transaction limit.", fill="#B45309", font=font_regular_md)
    draw.text((45, warn_box_top + 60), "Please request beneficiary for alternate UPI ID or Bank A/C + IFSC.", fill="#92400E", font=font_bold_md)
    draw.text((45, warn_box_top + 82), "Money has NOT been deducted from your account.", fill="#78350F", font=font_small)

    # 5. Transaction Details Card
    card_top = 455
    card_bottom = 850
    draw.rectangle([(30, card_top), (width - 30, card_bottom)], fill="#FFFFFF", outline="#E2E8F0", width=1)
    
    # Card Header
    draw.rectangle([(30, card_top), (width - 30, card_top + 45)], fill="#F8FAFC")
    draw.text((45, card_top + 14), "TRANSACTION BREAKDOWN", fill="#475569", font=font_bold_md)
    draw.line([(30, card_top + 45), (width - 30, card_top + 45)], fill="#E2E8F0", width=1)

    cur_time = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
    txn_ref = f"UPI/2026/{uuid.uuid4().hex[:10].upper()}"

    details = [
        ("To Beneficiary UPI", scammer_upi),
        ("Debited From", "State Bank of India (•••• 4821)"),
        ("Sender Account", "Verified Citizen Account (Vikas Ji)"),
        ("Date & Time", cur_time),
        ("UPI Reference ID", txn_ref),
        ("NPCI Response Code", "U16_DAILY_INWARD_LIMIT_EXHAUSTED"),
        ("Advised Resolution", "Provide Secondary Bank A/C or Alternate VPA")
    ]

    y_pos = card_top + 60
    for label, val in details:
        draw.text((45, y_pos), label, fill="#64748B", font=font_small)
        # Highlight important values
        color_val = "#DC2626" if "U16" in val or "Advised" in label else "#0F172A"
        draw.text((45, y_pos + 18), str(val), fill=color_val, font=font_bold_md)
        draw.line([(45, y_pos + 42), (width - 45, y_pos + 42)], fill="#F1F5F9", width=1)
        y_pos += 52

    # 6. NPCI Security Footer
    draw.text((center_x, 880), "Secured by National Payments Corporation of India (NPCI)", fill="#94A3B8", font=font_small, anchor="mt")
    draw.text((center_x, 905), "🔒 256-Bit End-to-End Encrypted Banking Sandbox Verification", fill="#CBD5E1", font=font_small, anchor="mt")

    # Save to storage
    filename = f"upi_error_{uuid.uuid4().hex[:8]}.png"
    filepath = GENERATED_BAITS_DIR / filename
    image.save(filepath, "PNG", quality=95)

    return {
        "filename": filename,
        "filepath": str(filepath),
        "relative_url": f"/storage/generated_baits/{filename}",
        "txn_ref": txn_ref,
        "scammer_upi": scammer_upi,
        "amount": clean_amt
    }
