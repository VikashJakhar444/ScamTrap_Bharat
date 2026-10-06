import os
import uuid
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from backend.config import GENERATED_BAITS_DIR

from typing import Dict, Any

def generate_upi_limit_receipt(scammer_upi: str = "bijli.board.pay@ybl", amount: str = "450.00") -> Dict[str, Any]:
    """Generates an authentic UPI payment limit error screenshot."""
    width, height = 750, 1334 # Standard smartphone aspect ratio
    image = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(image)
    
    # Header bar
    draw.rectangle([(0, 0), (width, 100)], fill="#F8F9FA")
    
    # Red Failure Icon Circle
    center_x, icon_y = width // 2, 240
    radius = 55
    draw.ellipse([(center_x - radius, icon_y - radius), (center_x + radius, icon_y + radius)], fill="#E53935")
    
    # Draw an 'X' mark inside circle
    draw.line([(center_x - 22, icon_y - 22), (center_x + 22, icon_y + 22)], fill="#FFFFFF", width=8)
    draw.line([(center_x + 22, icon_y - 22), (center_x - 22, icon_y + 22)], fill="#FFFFFF", width=8)
    
    # Title & Subtitle text
    try:
        font_large = ImageFont.load_default()
    except Exception:
        font_large = None

    # Error headline
    headline = "Payment Failed"
    draw.text((center_x - 70, icon_y + 80), headline, fill="#1A1A1A", font=font_large)
    
    # Error reason
    reason = "UPI Daily Transaction Limit Exceeded (U30)"
    draw.text((center_x - 140, icon_y + 115), reason, fill="#D32F2F", font=font_large)
    
    # Amount box
    draw.rectangle([(60, 430), (width - 60, 520)], fill="#F1F3F4", outline="#DADCE0", width=1)
    amt_text = f"Amount: Rs {amount}"
    draw.text((85, 465), amt_text, fill="#202124", font=font_large)
    
    # Details card
    card_top = 550
    draw.rectangle([(60, card_top), (width - 60, 950)], fill="#FFFFFF", outline="#E0E0E0", width=2)
    
    cur_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
    txn_ref = f"UPI/{uuid.uuid4().hex[:12].upper()}"
    
    details = [
        ("To UPI ID", scammer_upi),
        ("Debited From", "State Bank of India •••• 4192"),
        ("Date & Time", cur_time),
        ("UPI Reference ID", txn_ref),
        ("Bank Response", "Daily limit exhausted for user bank. Please use alternative A/C or IMPS.")
    ]
    
    y_offset = card_top + 30
    for label, val in details:
        draw.text((85, y_offset), f"{label}:", fill="#70757A", font=font_large)
        draw.text((85, y_offset + 25), str(val), fill="#202124", font=font_large)
        y_offset += 75
        
    # Footer Notice
    draw.text((center_x - 150, 1100), "National Payments Corporation of India (NPCI)", fill="#9AA0A6", font=font_large)
    
    filename = f"upi_error_{uuid.uuid4().hex[:8]}.png"
    filepath = GENERATED_BAITS_DIR / filename
    image.save(filepath, "PNG")
    
    return {
        "filename": filename,
        "filepath": str(filepath),
        "relative_url": f"/storage/generated_baits/{filename}",
        "txn_ref": txn_ref
    }
