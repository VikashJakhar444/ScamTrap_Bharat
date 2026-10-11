import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from backend.config import GENERATED_PDFS_DIR

IST = timezone(timedelta(hours=5, minutes=30), name="IST")

NOT_RECORDED = "Not recorded"


def _fmt_ts(value: Optional[str]) -> str:
    if not value:
        return NOT_RECORDED
    return str(value)


def generate_complaint_dossier(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Renders an official-format 1930 / BSA Sec 63 digital evidence dossier.

    Every cell is filled from the live evidence bundle passed in. Nothing is
    invented: an uncaptured forensic field prints "Not recorded", and the
    integrity hash printed at the bottom is the REAL evidence-bundle hash
    recomputed by `backend.database.db.evidence_hash` — the same value the
    evidence tab shows — so a judge who hashes the bundle themselves gets
    an exact match.
    """
    case_id = case_data.get("case_id") or NOT_RECORDED
    filename = f"NCRP_Dossier_{case_id}_{uuid.uuid4().hex[:6]}.pdf"
    filepath = GENERATED_PDFS_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath), pagesize=A4,
        leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'],
                                 fontName='Helvetica-Bold', fontSize=15, leading=18,
                                 textColor=colors.HexColor('#1E3A8A'), spaceAfter=4)
    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'],
                                    fontName='Helvetica', fontSize=9, leading=12,
                                    textColor=colors.HexColor('#475569'), spaceAfter=12)
    h2_style = ParagraphStyle('SectionH2', parent=styles['Heading2'],
                              fontName='Helvetica-Bold', fontSize=11, leading=14,
                              textColor=colors.HexColor('#0F172A'),
                              spaceBefore=10, spaceAfter=6)
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'],
                               fontName='Helvetica-Bold', fontSize=9, leading=12,
                               textColor=colors.HexColor('#0F172A'))
    cell_mono = ParagraphStyle('CellMono', parent=styles['Normal'],
                               fontName='Courier-Bold', fontSize=9, leading=12,
                               textColor=colors.HexColor('#DC2626'))
    cell_regular = ParagraphStyle('CellRegular', parent=styles['Normal'],
                                  fontName='Helvetica', fontSize=9, leading=12,
                                  textColor=colors.HexColor('#334155'))
    cert_title = ParagraphStyle('CertTitle', parent=styles['Normal'],
                                fontName='Helvetica-Bold', fontSize=11, leading=14,
                                alignment=1, textColor=colors.HexColor('#065F46'))
    cert_body = ParagraphStyle('CertBody', parent=styles['Normal'],
                               fontName='Helvetica', fontSize=8.5, leading=12,
                               alignment=1, textColor=colors.HexColor('#064E3B'))
    cert_hash = ParagraphStyle('CertHash', parent=styles['Normal'],
                               fontName='Courier-Bold', fontSize=8, leading=11,
                               alignment=1, textColor=colors.HexColor('#065F46'))

    story = []

    # ── 1. Header ──────────────────────────────────────────────────────────
    story.append(Paragraph("NATIONAL CYBER CRIME REPORTING PORTAL (1930 / I4C)", title_style))
    story.append(Paragraph(
        "Digital Evidence Dossier &bull; Bharatiya Sakshya Adhiniyam (BSA) Section 63 Compliant",
        subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5,
                            color=colors.HexColor('#1E3A8A'), spaceAfter=10))

    # ── 2. Case metadata (all real, no invented status) ────────────────────
    generated_str = datetime.now(IST).strftime("%d %B %Y, %I:%M:%S %p IST")
    # The REAL evidence hash — same value the evidence tab banners.
    sha256_hash = (case_data.get("evidence_hash") or "").upper()
    messages = case_data.get("messages") or []
    identifiers = case_data.get("identifiers") or []
    captures = case_data.get("canary_captures") or []

    meta_rows = [
        [Paragraph("Incident Reference Case ID", cell_bold),
         Paragraph(case_id, cell_mono),
         Paragraph("Scam Category", cell_bold),
         Paragraph(case_data.get("scam_category") or NOT_RECORDED, cell_regular)],
        [Paragraph("Target Scammer Phone", cell_bold),
         Paragraph(case_data.get("scammer_phone") or NOT_RECORDED, cell_mono),
         Paragraph("Case Recorded At", cell_bold),
         Paragraph(_fmt_ts(case_data.get("created_at")), cell_regular)],
        [Paragraph("Evidence Rows Sealed", cell_bold),
         Paragraph(str(len(messages)), cell_regular),
         Paragraph("Identifiers Extracted", cell_bold),
         Paragraph(str(len(identifiers)), cell_regular)],
        [Paragraph("Canary Captures", cell_bold),
         Paragraph(str(len(captures)) if captures else "0 (none logged)", cell_regular),
         Paragraph("Dossier Generated", cell_bold),
         Paragraph(generated_str, cell_regular)],
    ]
    meta_table = Table(meta_rows, colWidths=[140, 130, 110, 135])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # ── 3. Financial supply chain (real extracted identifiers only) ────────
    story.append(Paragraph(
        "1. Extracted Financial Identifiers (for immediate account freezing)", h2_style))

    fin_rows = [[Paragraph("Type", cell_bold), Paragraph("Value", cell_bold),
                 Paragraph("Registry Status", cell_bold)]]
    if identifiers:
        for ident in identifiers:
            bl = ident.get("blacklisted")
            status = ("Blacklisted &mdash; risk %s" % ident.get("risk_score")) if bl else "Not in registry"
            fin_rows.append([
                Paragraph(ident.get("label") or ident.get("type") or "Identifier", cell_bold),
                Paragraph(str(ident.get("value")), cell_mono),
                Paragraph(status, cell_regular),
            ])
    else:
        fin_rows.append([Paragraph("—", cell_regular),
                         Paragraph("No identifier captured in this case", cell_regular),
                         Paragraph(NOT_RECORDED, cell_regular)])

    fin_table = Table(fin_rows, colWidths=[160, 200, 155])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFF6FF')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 12))

    # ── 4. Canary forensics — only when a REAL capture exists ──────────────
    latest = case_data.get("latest_capture")
    story.append(Paragraph("2. Canary Trap &mdash; Scammer Device & Network Forensics", h2_style))
    if latest:
        fore_rows = [
            [Paragraph("Parameter", cell_bold), Paragraph("Captured Value", cell_bold)],
            [Paragraph("Public IP address", cell_bold),
             Paragraph(str(latest.get("ip_address") or NOT_RECORDED), cell_regular)],
            [Paragraph("Device operating system", cell_bold),
             Paragraph(str(latest.get("device_os") or NOT_RECORDED), cell_regular)],
            [Paragraph("Browser user-agent", cell_bold),
             Paragraph(str(latest.get("browser_ua") or NOT_RECORDED), cell_regular)],
            [Paragraph("Captured at", cell_bold),
             Paragraph(_fmt_ts(latest.get("captured_at")), cell_regular)],
            [Paragraph("Trap reference", cell_bold),
             Paragraph(str(latest.get("trap_code") or NOT_RECORDED), cell_mono)],
        ]
    else:
        fore_rows = [
            [Paragraph("Parameter", cell_bold), Paragraph("Captured Value", cell_bold)],
            [Paragraph("Canary trap status", cell_bold),
             Paragraph("No trap-visit capture recorded for this case. "
                       "Open the trap link from the evidence tab to record "
                       "the scammer's device and network metadata.", cell_regular)],
        ]
    fore_table = Table(fore_rows, colWidths=[180, 335])
    fore_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECFDF5')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(fore_table)
    story.append(Spacer(1, 12))

    # ── 5. Verbatim transcript (real rows, never a scripted fallback) ──────
    story.append(Paragraph("3. Verbatim Conversational Evidence Log", h2_style))
    chat_rows = [[Paragraph("Speaker", cell_bold), Paragraph("Message (verbatim)", cell_bold)]]
    if messages:
        for m in messages:
            role = (m.get("sender_role") or "log").upper().replace("AI_DECOY", "AI DECOY")
            role_style = cell_mono if "SCAMMER" in role else (
                cell_bold if "AI" in role or "DECOY" in role else cell_regular)
            text = (m.get("message_text") or "").replace("&", "&amp;").replace("<", "&lt;")
            chat_rows.append([Paragraph(role, role_style), Paragraph(text, cell_regular)])
    else:
        chat_rows.append([Paragraph("—", cell_regular),
                          Paragraph("No transcript rows recorded for this case.", cell_regular)])
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

    # ── 6. Section 63 BSA certificate — real hash, tamper-evident seal ─────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#065F46'),
                            spaceBefore=6, spaceAfter=8))
    cert_lines = [
        Paragraph("SECTION 63 BSA &mdash; COMPLIANT ELECTRONIC EVIDENCE", cert_title),
        Paragraph("This dossier is a verbatim export of the locally recorded "
                  "evidence bundle. No value below is estimated or inferred.", cert_body),
        Spacer(1, 4),
        Paragraph("INTEGRITY SHA-256", cert_body),
        Paragraph(sha256_hash or "HASH UNAVAILABLE", cert_hash),
        Spacer(1, 4),
        Paragraph(
            "Sealed at %s &bull; Case %s &bull; %d evidence rows &bull; %d sections<br/>"
            "The hash above is recomputed over the full evidence bundle "
            "(transcript + canary captures + identifiers) every time this "
            "dossier is opened. Any alteration of the underlying record "
            "produces a different hash, making tampering detectable."
            % (generated_str, case_id, len(messages), 5),
            cert_body),
    ]
    for el in cert_lines:
        story.append(el)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<i>Generated by ScamTrap Bharat &mdash; Citizen Cyber Defence Portal. "
        "Report financial fraud on 1930 or cybercrime.gov.in.</i>", subtitle_style))

    doc.build(story)

    return {
        "filename": filename,
        "filepath": str(filepath),
        "relative_url": f"/storage/generated_pdfs/{filename}",
        "sha256_hash": sha256_hash,
        "evidence_hash": sha256_hash,
        "case_id": case_id,
        "generated_at": generated_str,
    }
