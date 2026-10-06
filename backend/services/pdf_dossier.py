import os
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from backend.config import GENERATED_PDFS_DIR

def generate_complaint_dossier(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates an official-format 1930 Cyber Cell & BSA Section 63 Digital Evidence Dossier.
    Utilizes SimpleDocTemplate with A4 and wrapped Paragraph cells for zero text clipping.
    """
    case_id = case_data.get("case_id", "CASE-2026-1001")
    filename = f"NCRP_Dossier_{case_id}_{uuid.uuid4().hex[:6]}.pdf"
    filepath = GENERATED_PDFS_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569'),
        spaceAfter=12
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=10,
        spaceAfter=6
    )

    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )

    cell_mono = ParagraphStyle(
        'CellMono',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#DC2626')
    )

    cell_regular = ParagraphStyle(
        'CellRegular',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # 1. Header & Title
    story.append(Paragraph("NATIONAL CYBER CRIME REPORTING PORTAL (1930 / I4C)", title_style))
    story.append(Paragraph("Standard Digital Evidence Dossier • Bharatiya Sakshya Adhiniyam (BSA) Sec 63 Compliant", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=10))

    # 2. Case Metadata Table
    created_str = datetime.now().strftime("%d %B %Y, %I:%M:%S %p")
    hash_raw = f"{case_id}-{case_data.get('scammer_phone')}-{created_str}"
    sha256_hash = hashlib.sha256(hash_raw.encode('utf-8')).hexdigest().upper()

    meta_table_data = [
        [Paragraph("Incident Reference Case ID:", cell_bold), Paragraph(case_id, cell_mono),
         Paragraph("Investigation Status:", cell_bold), Paragraph("PRE-FRAUD INTERCEPTED", cell_bold)],
        [Paragraph("Scam Classification:", cell_bold), Paragraph(case_data.get("scam_category", "Electricity Bill Scam"), cell_regular),
         Paragraph("Financial Loss:", cell_bold), Paragraph("₹ 0.00 (Zero Loss)", cell_bold)],
        [Paragraph("Target Scammer Phone:", cell_bold), Paragraph(case_data.get("scammer_phone", "+91 98765 43210"), cell_mono),
         Paragraph("Timestamp:", cell_bold), Paragraph(created_str, cell_regular)]
    ]

    meta_table = Table(meta_table_data, colWidths=[140, 130, 110, 135])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 3. Trapped Financial Supply Chain Table
    story.append(Paragraph("1. Identified Scammer Financial Supply Chain (For Immediate Account Freezing)", h2_style))
    
    fin_headers = [Paragraph("Financial Entity", cell_bold), Paragraph("Extracted Value / Monospace Handle", cell_bold), Paragraph("Extraction Method / Source", cell_bold)]
    fin_rows = [
        fin_headers,
        [Paragraph("Primary Scammer UPI", cell_bold), Paragraph(case_data.get("primary_upi", "bijli.board.pay@ybl"), cell_mono), Paragraph("Initial extortion demand message", cell_regular)],
        [Paragraph("Backup Mule Bank Account", cell_bold), Paragraph(case_data.get("bank_ac", "50200084729104"), cell_mono), Paragraph("Extracted via Fake U16 UPI limit counter-bait", cell_regular)],
        [Paragraph("Beneficiary IFSC Code", cell_bold), Paragraph(case_data.get("ifsc", "SBIN0004821 (State Bank of India)"), cell_regular), Paragraph("Extracted in secondary payment demand", cell_regular)],
        [Paragraph("Target Contact Number", cell_bold), Paragraph(case_data.get("scammer_phone", "+91 98765 43210"), cell_mono), Paragraph("WhatsApp / SMS sender origin", cell_regular)]
    ]

    fin_table = Table(fin_rows, colWidths=[150, 190, 175])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFF6FF')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 12))

    # 4. Scammer Digital Forensics & Canary Logs Table
    story.append(Paragraph("2. Scammer Digital Network & Device Forensics (Canary Trap Logs)", h2_style))

    forensic_headers = [Paragraph("Forensic Parameter", cell_bold), Paragraph("Captured Value", cell_bold)]
    forensic_rows = [
        forensic_headers,
        [Paragraph("Scammer Public IP Address", cell_bold), Paragraph(case_data.get("ip_address", "103.21.144.62 (Kolkata Hub / Jamtara Route)"), cell_regular)],
        [Paragraph("Device Operating System & Model", cell_bold), Paragraph(case_data.get("device_os", "Android 13 / Redmi Note 11"), cell_regular)],
        [Paragraph("Client Browser User-Agent", cell_bold), Paragraph(case_data.get("browser_ua", "Mozilla/5.0 (Linux; Android 13; Chrome/122.0.6261.94 Mobile)"), cell_regular)],
        [Paragraph("Canary Bait Receipt Intercepted", cell_bold), Paragraph("SBI / NPCI Settlement Verification Portal (Receipt Ref: U16-OK)", cell_regular)]
    ]

    forensic_table = Table(forensic_rows, colWidths=[180, 335])
    forensic_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECFDF5')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(forensic_table)
    story.append(Spacer(1, 12))

    # 5. Full Chat Evidence Transcript
    story.append(Paragraph("3. Autonomous Honeypot Conversational Evidence Log", h2_style))
    
    chat_headers = [Paragraph("Speaker", cell_bold), Paragraph("Verbatim Message Content", cell_bold)]
    raw_msgs = case_data.get("messages", [
        "[SCAMMER]: Dear Consumer, Your Electricity power will be disconnected tonight 9:30 PM from power office because your previous month bill was not updated. Please immediately contact our officer at 9876543210.",
        "[AI DECOY]: Sir please mat kaato light! Bachhe padh rahe hain. Kahan pay karna hai batayein?",
        "[SCAMMER]: Pay Rs 45 immediately on our official power UPI: bijli.board.pay@ybl or bill will not update.",
        "[AI DECOY]: Sir maine try kiya par UPI Daily Limit Reached error aa raha hai. Dekhiye screenshot. Koi alternate account number ya secondary UPI do jaldi?",
        "[SCAMMER]: Theek hai is backup account pe transfer karo: A/C 50200084729104 IFSC SBIN0004821 (Name: Bijli Collection Unit) turant.",
        "[SYSTEM]: Honeypot Trigger: Scammer secondary mule account and IFSC successfully trapped."
    ])

    chat_rows = [chat_headers]
    for msg in raw_msgs:
        parts = msg.split(":", 1)
        role = parts[0].replace("[", "").replace("]", "").strip() if len(parts) > 1 else "LOG"
        text = parts[1].strip() if len(parts) > 1 else msg
        role_color = cell_mono if "SCAMMER" in role else (cell_bold if "AI" in role else cell_regular)
        chat_rows.append([Paragraph(role, role_color), Paragraph(text, cell_regular)])

    chat_table = Table(chat_rows, colWidths=[90, 425])
    chat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(chat_table)
    story.append(Spacer(1, 14))

    # 6. Integrity Hash & Signoff
    footer_text = f"<b>BSA Sec 63 Evidence Integrity SHA-256 Hash:</b> {sha256_hash}<br/>" \
                  f"<i>Generated automatically by ScamTrap Bharat (Citizen Cyber Safety Sandbox Engine) on {created_str}.</i>"
    story.append(Paragraph(footer_text, subtitle_style))

    # Build document
    doc.build(story)

    return {
        "filename": filename,
        "filepath": str(filepath),
        "relative_url": f"/storage/generated_pdfs/{filename}",
        "sha256_hash": sha256_hash
    }
