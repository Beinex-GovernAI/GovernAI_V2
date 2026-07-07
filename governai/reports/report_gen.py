import os
import sys
import json
import uuid
from datetime import datetime, timezone

# Add the governai folder to the Python path so it can resolve database/services modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas as pdfcanvas

from database.db import SessionLocal
from services.ai_system_svc import get_system_by_id
from services.compliance_svc import get_compliance_score

# ─────────────────────────────────────────────────────────────
#  BRAND COLOURS  (unchanged)
# ─────────────────────────────────────────────────────────────
BRAND_DARK       = colors.HexColor("#0D1B2A")
BRAND_PRIMARY    = colors.HexColor("#1A3C5E")
BRAND_ACCENT     = colors.HexColor("#2563EB")
BRAND_LIGHT      = colors.HexColor("#E8F0FE")
BRAND_WHITE      = colors.HexColor("#FFFFFF")
BRAND_GRAY_DARK  = colors.HexColor("#374151")
BRAND_GRAY_MID   = colors.HexColor("#6B7280")
BRAND_GRAY_LIGHT = colors.HexColor("#F3F4F6")
BRAND_SUCCESS    = colors.HexColor("#059669")
BRAND_WARNING    = colors.HexColor("#D97706")
BRAND_DANGER     = colors.HexColor("#DC2626")
BRAND_ROW_ALT    = colors.HexColor("#F0F4FF")

PAGE_W, PAGE_H = A4

# Usable width inside left/right margins of 2 cm each
USABLE_W = PAGE_W - 4 * cm

# ─────────────────────────────────────────────────────────────
#  SPACING CONSTANTS  (consistent hierarchy throughout)
# ─────────────────────────────────────────────────────────────
SP_AFTER_HEADING   = 4    # pt  between heading and first paragraph
SP_AFTER_BODY      = 6    # pt  between paragraph and table
SP_AFTER_TABLE     = 10   # pt  between table/caption and next heading
SP_AFTER_CAPTION   = 10   # pt  after figure/table caption


# ─────────────────────────────────────────────────────────────
#  CUSTOM PAGE CANVAS  (header 14 mm + footer 12 mm)
# ─────────────────────────────────────────────────────────────
class GovernAICanvas(pdfcanvas.Canvas):
    """Persistent header bar + footer on every page, with correct total-page count."""

    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        self._saved_page_states = []
        # metadata injected externally before build()
        self._report_id   = ""
        self._system_name = ""
        self._gen_time    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self._draw_chrome(i + 1, total)
            super().showPage()
        super().save()

    def _draw_chrome(self, page_num: int, total: int):
        w, h = PAGE_W, PAGE_H
        HDR = 14 * mm      # header height (slightly reduced for more content space)
        FTR = 12 * mm      # footer height

        # ── Header ────────────────────────────────────────────
        self.setFillColor(BRAND_PRIMARY)
        self.rect(0, h - HDR, w, HDR, fill=1, stroke=0)

        # Accent line at header bottom
        self.setStrokeColor(BRAND_ACCENT)
        self.setLineWidth(1.5)
        self.line(0, h - HDR, w, h - HDR)

        # Left: logo word
        self.setFillColor(BRAND_WHITE)
        self.setFont("Helvetica-Bold", 8.5)
        self.drawString(18 * mm, h - 9 * mm, "GovernAI")

        # Left: subtitle
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#93C5FD"))
        self.drawString(18 * mm + 48, h - 9 * mm, "AI Governance & Audit Platform")

        # Right: doc label
        self.setFillColor(BRAND_WHITE)
        self.setFont("Helvetica", 7)
        self.drawRightString(w - 18 * mm, h - 9 * mm,
                             "CONFIDENTIAL — AI GOVERNANCE AUDIT REPORT")

        # ── Footer ────────────────────────────────────────────
        self.setFillColor(BRAND_GRAY_LIGHT)
        self.rect(0, 0, w, FTR, fill=1, stroke=0)

        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.5)
        self.line(0, FTR, w, FTR)

        # Footer left: generated + classification
        self.setFillColor(BRAND_GRAY_MID)
        self.setFont("Helvetica", 6.5)
        self.drawString(18 * mm, FTR - 4.5 * mm,
                        f"Generated: {self._gen_time}   |   CONFIDENTIAL — For Authorised Review Only")

        # Footer right: report ID + page
        self.setFont("Helvetica", 6.5)
        if self._report_id:
            self.drawRightString(w - 18 * mm, FTR - 4.5 * mm,
                                 f"Report ID: {self._report_id[:8].upper()}   |   "
                                 f"Page {page_num} of {total}")
        else:
            self.setFont("Helvetica-Bold", 6.5)
            self.drawRightString(w - 18 * mm, FTR - 4.5 * mm,
                                 f"Page {page_num} of {total}")


# ─────────────────────────────────────────────────────────────
#  STYLE SHEET
# ─────────────────────────────────────────────────────────────
def _build_styles():
    styles = {}

    # ── Cover page styles
    styles["cover_eyebrow"] = ParagraphStyle(
        "cover_eyebrow", fontName="Helvetica", fontSize=8,
        textColor=colors.HexColor("#94A3B8"), leading=12, alignment=TA_LEFT,
    )
    styles["cover_title"] = ParagraphStyle(
        "cover_title", fontName="Helvetica-Bold", fontSize=26,
        textColor=BRAND_WHITE, leading=32, alignment=TA_LEFT, spaceAfter=0,
    )
    styles["cover_system"] = ParagraphStyle(
        "cover_system", fontName="Helvetica", fontSize=14,
        textColor=colors.HexColor("#93C5FD"), leading=20, alignment=TA_LEFT,
    )
    styles["cover_kv_label"] = ParagraphStyle(
        "cover_kv_label", fontName="Helvetica-Bold", fontSize=7,
        textColor=colors.HexColor("#94A3B8"), leading=10, spaceAfter=1,
    )
    styles["cover_kv_value"] = ParagraphStyle(
        "cover_kv_value", fontName="Helvetica-Bold", fontSize=9,
        textColor=BRAND_WHITE, leading=12,
    )
    styles["cover_score_pct"] = ParagraphStyle(
        "cover_score_pct", fontName="Helvetica-Bold", fontSize=20,
        textColor=BRAND_WHITE, leading=24, alignment=TA_CENTER,
    )
    styles["cover_score_label"] = ParagraphStyle(
        "cover_score_label", fontName="Helvetica", fontSize=7,
        textColor=colors.HexColor("#94A3B8"), leading=10, alignment=TA_CENTER,
    )

    # ── Document body styles
    styles["section_heading"] = ParagraphStyle(
        "section_heading", fontName="Helvetica-Bold", fontSize=12,
        textColor=BRAND_PRIMARY, leading=16,
        spaceBefore=0, spaceAfter=SP_AFTER_HEADING,
    )
    styles["sub_heading"] = ParagraphStyle(
        "sub_heading", fontName="Helvetica-Bold", fontSize=9.5,
        textColor=BRAND_GRAY_DARK, leading=13,
        spaceBefore=6, spaceAfter=3,
    )
    styles["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=8.5,
        textColor=BRAND_GRAY_DARK, leading=13, spaceAfter=0, alignment=TA_JUSTIFY,
    )
    styles["body_bold"] = ParagraphStyle(
        "body_bold", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=BRAND_GRAY_DARK, leading=13,
    )
    styles["caption"] = ParagraphStyle(
        "caption", fontName="Helvetica-Oblique", fontSize=7.5,
        textColor=BRAND_GRAY_MID, leading=10,
        spaceAfter=SP_AFTER_CAPTION, alignment=TA_CENTER,
    )
    styles["kv_label"] = ParagraphStyle(
        "kv_label", fontName="Helvetica-Bold", fontSize=8,
        textColor=BRAND_GRAY_MID, leading=12,
    )
    styles["kv_value"] = ParagraphStyle(
        "kv_value", fontName="Helvetica", fontSize=9,
        textColor=BRAND_GRAY_DARK, leading=12,
    )
    styles["table_header"] = ParagraphStyle(
        "table_header", fontName="Helvetica-Bold", fontSize=8,
        textColor=BRAND_WHITE, leading=11, alignment=TA_LEFT,
    )
    styles["table_cell"] = ParagraphStyle(
        "table_cell", fontName="Helvetica", fontSize=8,
        textColor=BRAND_GRAY_DARK, leading=11, alignment=TA_LEFT,
    )
    styles["table_cell_center"] = ParagraphStyle(
        "table_cell_center", fontName="Helvetica", fontSize=8,
        textColor=BRAND_GRAY_DARK, leading=11, alignment=TA_CENTER,
    )
    styles["badge_ok"] = ParagraphStyle(
        "badge_ok", fontName="Helvetica-Bold", fontSize=8,
        textColor=BRAND_SUCCESS, alignment=TA_CENTER,
    )
    styles["badge_warn"] = ParagraphStyle(
        "badge_warn", fontName="Helvetica-Bold", fontSize=8,
        textColor=BRAND_WARNING, alignment=TA_CENTER,
    )
    styles["badge_err"] = ParagraphStyle(
        "badge_err", fontName="Helvetica-Bold", fontSize=8,
        textColor=BRAND_DANGER, alignment=TA_CENTER,
    )
    styles["badge_neutral"] = ParagraphStyle(
        "badge_neutral", fontName="Helvetica-Bold", fontSize=8,
        textColor=BRAND_GRAY_MID, alignment=TA_CENTER,
    )
    styles["toc_entry"] = ParagraphStyle(
        "toc_entry", fontName="Helvetica", fontSize=9,
        textColor=BRAND_GRAY_DARK, leading=16,
    )
    styles["toc_heading"] = ParagraphStyle(
        "toc_heading", fontName="Helvetica-Bold", fontSize=12,
        textColor=BRAND_PRIMARY, leading=16,
        spaceBefore=0, spaceAfter=8,
    )
    return styles


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _sp(pts: float):
    """Return a Spacer of the given height in points."""
    return Spacer(1, pts)


def _section_block(title: str, styles: dict):
    """Blue-accent rule + section heading, kept together."""
    return KeepTogether([
        HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT,
                   spaceBefore=0, spaceAfter=3),
        Paragraph(title.upper(), styles["section_heading"]),
    ])


def _risk_colour(tier: str):
    return {"High": BRAND_DANGER, "Prohibited": BRAND_DANGER,
            "Limited": BRAND_WARNING, "Minimal": BRAND_SUCCESS}.get(tier, BRAND_GRAY_MID)


def _status_colour(status: str):
    return {"Compliant": BRAND_SUCCESS, "At Risk": BRAND_WARNING,
            "Non-Compliant": BRAND_DANGER}.get(status, BRAND_GRAY_MID)


def _score_badge_style(val: int, styles: dict):
    if val >= 70: return styles["badge_ok"]
    if val >= 40: return styles["badge_warn"]
    return styles["badge_err"]


def _score_badge_text(val: int):
    if val >= 70: return f"● Satisfactory ({val}%)"
    if val >= 40: return f"▲ Needs Attention ({val}%)"
    return f"✕ Below Threshold ({val}%)"


def _kv_table(rows: list, styles: dict, col_widths=None):
    """Two-column label→value info grid with alternating rows."""
    if col_widths is None:
        col_widths = [4.8 * cm, USABLE_W - 4.8 * cm]
    data = [
        [Paragraph(lbl, styles["kv_label"]),
         Paragraph(str(val) if val else "—", styles["kv_value"])]
        for lbl, val in rows
    ]
    tbl = Table(data, colWidths=col_widths, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BRAND_WHITE, BRAND_GRAY_LIGHT]),
        ("LINEBELOW",      (0, 0), (-1, -2), 0.3, colors.HexColor("#E5E7EB")),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    return tbl


def _data_table(headers: list, rows: list, col_widths: list, styles: dict,
                repeat_header: bool = True):
    """
    Styled data table with dark header, alternating rows, wrapped cells.
    Cells that are already Paragraph objects are passed through unchanged.
    """
    hdr_row = [Paragraph(h, styles["table_header"]) for h in headers]
    body = []
    for row in rows:
        cells = []
        for cell in row:
            if hasattr(cell, "wrap"):          # already a Paragraph/Flowable
                cells.append(cell)
            else:
                cells.append(Paragraph(str(cell) if cell else "—",
                                       styles["table_cell"]))
        body.append(cells)

    all_rows = [hdr_row] + body
    tbl = Table(all_rows, colWidths=col_widths, hAlign="LEFT",
                repeatRows=1 if repeat_header else 0)

    row_bgs = [
        ("BACKGROUND", (0, i), (-1, i),
         BRAND_ROW_ALT if i % 2 == 0 else BRAND_WHITE)
        for i in range(1, len(all_rows))
    ]
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), BRAND_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("WORDWRAP",      (0, 0), (-1, -1), "CJK"),
        *row_bgs,
    ]))
    return tbl


def _inline_bar(score: int, bar_width: float = USABLE_W * 0.55, height: int = 12):
    """
    Renders a professional inline progress bar as a two-cell table.
    """
    colour = BRAND_SUCCESS if score >= 70 else BRAND_WARNING if score >= 40 else BRAND_DANGER
    filled = max(int(bar_width * score / 100), 2) if score > 0 else 2
    empty  = int(bar_width) - filled

    if score == 0:
        bar_data = [[""]]
        bar_tbl = Table(bar_data, colWidths=[int(bar_width)], rowHeights=[height])
        bar_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#E5E7EB")),
            ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
    elif score >= 100:
        bar_data = [[""]]
        bar_tbl = Table(bar_data, colWidths=[int(bar_width)], rowHeights=[height])
        bar_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colour),
            ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
    else:
        bar_data = [["", ""]]
        bar_tbl = Table(bar_data, colWidths=[filled, empty], rowHeights=[height])
        bar_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, 0), colour),
            ("BACKGROUND",    (1, 0), (1, 0), colors.HexColor("#E5E7EB")),
            ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
    return bar_tbl


def _score_row(label: str, score: int, styles: dict):
    """
    Returns a KeepTogether block: label + bar + percentage, all on one line-group.
    """
    colour = BRAND_SUCCESS if score >= 70 else BRAND_WARNING if score >= 40 else BRAND_DANGER
    bar    = _inline_bar(score)
    pct_style = ParagraphStyle(
        f"pct_{label}", fontName="Helvetica-Bold", fontSize=8,
        textColor=colour, leading=11, alignment=TA_LEFT,
    )
    # Pack label + bar + pct into a 3-column single-row table so they sit on one line
    row_tbl = Table(
        [[Paragraph(f"<b>{label}</b>", styles["body"]), bar,
          Paragraph(f"{score}%", pct_style)]],
        colWidths=[4.5 * cm, USABLE_W * 0.55, 1.5 * cm],
        rowHeights=[12],
        hAlign="LEFT",
    )
    row_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (1, 0), (1, 0), 4),
    ]))
    return row_tbl


# ─────────────────────────────────────────────────────────────
#  COVER PAGE  — rich executive layout, no large blank areas
# ─────────────────────────────────────────────────────────────
def _build_cover(system, score_eu, score_nist, styles, report_id: str):
    story = []
    today  = datetime.now(timezone.utc).strftime("%B %d, %Y")
    tier   = system.risk_tier   or "Pending"
    status = system.compliance_status or "Pending"

    # ── Dark hero panel (simulated with a full-width table)
    hero_content = [
        [
            Table([
                [Paragraph("GOVERNANCE AUDIT REPORT", styles["cover_eyebrow"]),
                 Paragraph("INTERNAL / CONFIDENTIAL", ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=7, textColor=BRAND_WARNING, alignment=TA_RIGHT))]
            ], colWidths=[(USABLE_W-32)/2, (USABLE_W-32)/2], hAlign="LEFT", style=[("PADDING", (0,0), (-1,-1), 0)])
        ],
        [_sp(4)],
        [Paragraph("AI Governance<br/>Audit Report", styles["cover_title"])],
        [_sp(6)],
        [Paragraph("Governance & Compliance Assessment<br/>under the EU AI Act and NIST AI RMF", 
                   ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11, textColor=colors.HexColor("#93C5FD"), leading=14))],
        [_sp(14)],
        [Paragraph(system.name, styles["cover_system"])],
        [_sp(8)],
        [HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT)],
    ]
    hero_tbl = Table(
        hero_content, colWidths=[USABLE_W], hAlign="LEFT",
        style=TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BRAND_DARK),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 16),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ("TOPPADDING",    (0, 0), (0, 0), 20),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
        ])
    )
    story.append(hero_tbl)
    story.append(_sp(12))

    # ── Metric cards row  (4 cards side by side)
    tier_col  = _risk_colour(tier)
    stat_col  = _status_colour(status)
    eu_col    = BRAND_SUCCESS if score_eu  >= 70 else BRAND_WARNING if score_eu  >= 40 else BRAND_DANGER
    nist_col  = BRAND_SUCCESS if score_nist >= 70 else BRAND_WARNING if score_nist >= 40 else BRAND_DANGER

    def _metric_card(top_label: str, value: str, sub_label: str = "",
                     value_colour=BRAND_WHITE):
        card_rows = [
            [Paragraph(top_label.upper(), styles["cover_kv_label"])],
            [Paragraph(value, ParagraphStyle(
                "card_val", fontName="Helvetica-Bold", fontSize=13,
                textColor=value_colour, leading=16, alignment=TA_CENTER,
                spaceBefore=2
            ))],
        ]
        
        # Ensure identical 3-row geometry for all cards to keep them perfectly vertically aligned
        sub_style = ParagraphStyle(
            "cover_score_label", fontName="Helvetica", fontSize=7,
            textColor=colors.HexColor("#94A3B8"), leading=10, alignment=TA_CENTER,
            spaceBefore=1
        )
        if sub_label:
            card_rows.append([Paragraph(sub_label, sub_style)])
        else:
            # Invisible placeholder text to match geometry
            card_rows.append([Paragraph("<font color='#1A3C5E'>.</font>", sub_style)])
        card = Table(card_rows, colWidths=[USABLE_W / 4])
        card.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BRAND_PRIMARY),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return card

    card_w = USABLE_W / 4
    cards_row = Table(
        [[
            _metric_card("Risk Tier",  tier,           value_colour=tier_col),
            _metric_card("Status",     status,          value_colour=stat_col),
            _metric_card("EU AI Act",  f"{score_eu}%",  "Compliance",
                         value_colour=eu_col),
            _metric_card("NIST RMF",   f"{score_nist}%", "Compliance",
                         value_colour=nist_col),
        ]],
        colWidths=[card_w, card_w, card_w, card_w],
        rowHeights=[2 * cm],
        spaceBefore=0,
        hAlign="LEFT",
    )
    cards_row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(cards_row)
    story.append(_sp(12))

    # ── Document metadata grid
    def _fmt_id(val):
        s = str(val)
        return f"{s[:8]}••••{s[-4:]}" if len(s) > 12 else s.upper()

    meta_rows = [
        ("Report Date",       today),
        ("System Owner",      system.owner or "—"),
        ("Model Type",        system.model_type or "—"),
        ("Report ID",         _fmt_id(report_id).upper()),
        ("System ID",         _fmt_id(system.id).upper()),
        ("Framework",         "EU AI Act (2024) + NIST AI RMF 1.0"),
        ("Generated By",      "GovernAI Audit Platform v1.0"),
        ("Document Version",  "1.0"),
    ]
    story.append(_kv_table(meta_rows, styles, col_widths=[4.8 * cm, USABLE_W - 4.8 * cm]))
    story.append(_sp(12))

    # ── Confidentiality notice
    notice = Table(
        [[Paragraph(
            "<b>CONFIDENTIAL — RESTRICTED DISTRIBUTION.</b>  This report is prepared exclusively "
            "for internal governance review and regulatory audit purposes. Unauthorised distribution "
            "or reproduction is strictly prohibited. Recipients must treat this document in accordance "
            "with the organisation's information security policy.",
            styles["body"]
        )]],
        colWidths=[USABLE_W],
        hAlign="LEFT",
    )
    notice.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
        ("LINEABOVE",     (0, 0), (-1, -1), 2.5, BRAND_WARNING),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(notice)
    story.append(PageBreak())
    return story


# (TOC temporarily removed until dynamically generated)


# ─────────────────────────────────────────────────────────────
#  SECTION BUILDER HELPERS
# ─────────────────────────────────────────────────────────────

def _section_header(title: str, styles: dict):
    """
    Section title flowable that registers itself with the TOC.
    Returns a KeepTogether so the heading never orphans at page bottom.
    """
    p = Paragraph(title.upper(), styles["section_heading"])
    p._bookmarkName = title   # used by GovernAIDocTemplate
    return KeepTogether([
        HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT,
                   spaceBefore=0, spaceAfter=3),
        p,
        _sp(SP_AFTER_HEADING),
    ])


# ─────────────────────────────────────────────────────────────
#  SECTION 1 – EXECUTIVE SUMMARY
# ─────────────────────────────────────────────────────────────
def _build_executive_summary(system, score_eu, score_nist, styles):
    story = []
    story.append(_section_header("1. Executive Summary", styles))

    tier   = system.risk_tier   or "Pending"
    status = system.compliance_status or "Pending"

    story.append(Paragraph(
        f"This report presents the AI governance audit findings for <b>{system.name}</b>, "
        f"owned by <b>{system.owner or 'N/A'}</b>. "
        f"The system is classified as <b>{tier}</b>-risk under the EU AI Act "
        f"with a current compliance status of <b>{status}</b>. "
        f"EU AI Act checklist completion stands at <b>{score_eu}%</b>; "
        f"NIST AI RMF completion at <b>{score_nist}%</b>. "
        "This document covers the system overview, risk classification, data governance, "
        "compliance controls, performance monitoring, and the immutable audit trail.",
        styles["body"]
    ))
    story.append(_sp(SP_AFTER_BODY))

    # Scorecard table
    def _badge(val):
        return Paragraph(_score_badge_text(val), _score_badge_style(val, styles))

    tier_badge_text  = ("● Low Risk"    if tier == "Minimal"  else
                        "▲ Elevated"    if tier == "Limited"  else
                        "✕ High Risk"   if tier in ("High","Prohibited") else "– Pending")
    tier_badge_style = ParagraphStyle(
        "tier_badge", fontName="Helvetica-Bold", fontSize=8,
        textColor=_risk_colour(tier), alignment=TA_CENTER)

    stat_badge_text  = ("● Compliant"      if status == "Compliant"     else
                        "▲ At Risk"        if status == "At Risk"       else
                        "✕ Non-Compliant"  if status == "Non-Compliant" else "– Pending")
    stat_badge_style = ParagraphStyle(
        "stat_badge", fontName="Helvetica-Bold", fontSize=8,
        textColor=_status_colour(status), alignment=TA_CENTER)

    hdr = [Paragraph(h, styles["table_header"])
           for h in ["Dimension", "Value", "Assessment"]]
    rows = [
        [Paragraph("EU AI Act Compliance",  styles["table_cell"]),
         Paragraph(f"{score_eu}%",          styles["table_cell"]), _badge(score_eu)],
        [Paragraph("NIST AI RMF",           styles["table_cell"]),
         Paragraph(f"{score_nist}%",        styles["table_cell"]), _badge(score_nist)],
        [Paragraph("Risk Tier",             styles["table_cell"]),
         Paragraph(tier,                    styles["table_cell"]),
         Paragraph(tier_badge_text, tier_badge_style)],
        [Paragraph("Compliance Status",     styles["table_cell"]),
         Paragraph(status,                  styles["table_cell"]),
         Paragraph(stat_badge_text, stat_badge_style)],
    ]
    all_rows = [hdr] + rows
    row_bgs  = [("BACKGROUND", (0, i), (-1, i),
                 BRAND_ROW_ALT if i % 2 == 0 else BRAND_WHITE)
                for i in range(1, len(all_rows))]
    sc = Table(all_rows, colWidths=[6 * cm, 4 * cm, 6 * cm], hAlign="LEFT")
    sc.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BRAND_PRIMARY),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        *row_bgs,
    ]))
    story.append(sc)
    story.append(_sp(SP_AFTER_TABLE))
    return story


# ─────────────────────────────────────────────────────────────
#  SECTION 2 – SYSTEM OVERVIEW
# ─────────────────────────────────────────────────────────────
def _build_system_overview(system, styles):
    story = []
    story.append(_section_header("2. System Overview", styles))
    rows = [
        ("System Name",       system.name),
        ("System Owner",      system.owner),
        ("Business Purpose",  system.business_purpose),
        ("Model Type",        system.model_type),
        ("Model Source",      system.model_source),
        ("Model Vendor",      getattr(system, "model_vendor", None)),
        ("Agentic Tracing",   getattr(system, "agentic_trace_required", None)),
        ("Risk Tier",         system.risk_tier),
        ("Compliance Status", system.compliance_status),
        ("Registered On",     (system.created_at or "")[:10] or "—"),
        ("Last Updated",      (system.updated_at or "")[:10] or "—"),
    ]
    story.append(_kv_table(rows, styles))
    story.append(_sp(SP_AFTER_TABLE))
    return story


# ─────────────────────────────────────────────────────────────
#  SECTION 3 – RISK CLASSIFICATION
# ─────────────────────────────────────────────────────────────
def _build_risk_section(system, styles):
    story = []
    story.append(_section_header("3. Risk Classification & Assessment", styles))

    tier = system.risk_tier or "Pending"
    tier_descriptions = {
        "Prohibited": (
            "This system falls into the <b>Prohibited</b> category under the EU AI Act (Article 5). "
            "These uses pose an unacceptable risk to fundamental rights and are not permitted under any circumstances."
        ),
        "High": (
            "This system is classified as <b>High-Risk</b> under Annex III of the EU AI Act. "
            "Strict requirements apply: conformity assessments, technical documentation, transparency obligations, "
            "human oversight, and registration in the EU database prior to deployment."
        ),
        "Limited": (
            "This system carries <b>Limited Risk</b> under the EU AI Act. "
            "Primary obligations relate to transparency — users must be informed they are interacting with an AI system."
        ),
        "Minimal": (
            "This system is classified as <b>Minimal Risk</b>. No mandatory requirements apply, "
            "though voluntary codes of conduct are encouraged."
        ),
        "Pending": (
            "Risk classification is <b>pending</b>. A formal risk assessment must be completed before "
            "this system can be registered or deployed in a regulated context."
        ),
    }
    story.append(Paragraph(
        tier_descriptions.get(tier, "Risk tier not determined."), styles["body"]
    ))
    story.append(_sp(SP_AFTER_BODY))

    if system.risk_assessments and system.risk_assessments[0].answers:
        assessment = system.risk_assessments[0]
        story.append(KeepTogether([
            Paragraph("Risk Assessment Detail", styles["sub_heading"]),
            _sp(2),
            Paragraph(
                f"Assessment conducted by <b>{assessment.assessed_by or 'Unknown'}</b> "
                f"on <b>{(assessment.assessed_at or '')[:10]}</b>.",
                styles["body"]
            ),
            _sp(SP_AFTER_BODY),
        ]))
        data_rows = [
            [ans.question_key, ans.answer or "—", f"{ans.weight:.1f}"]
            for ans in assessment.answers
        ]
        story.append(_data_table(
            ["Question", "Response", "Weight"],
            data_rows,
            [10 * cm, 4.5 * cm, 1.5 * cm],
            styles
        ))
        story.append(Paragraph("Table 1: Risk Classification Responses", styles["caption"]))
    else:
        story.append(Paragraph(
            "No formal risk assessment has been recorded for this system.", styles["body"]
        ))
    story.append(_sp(SP_AFTER_TABLE))
    return story


# ─────────────────────────────────────────────────────────────
#  SECTION 4 – DATA GOVERNANCE & PRIVACY
# ─────────────────────────────────────────────────────────────
def _build_data_section(system, styles):
    story = []
    story.append(PageBreak())
    story.append(_section_header("4. Data Governance & Privacy", styles))
    story.append(Paragraph(
        "The table below enumerates all registered data sources, including personal data classification "
        "and associated PII categories. Organisations must maintain clear records of data provenance "
        "for high-risk AI systems under GDPR and EU AI Act Article 10.",
        styles["body"]
    ))
    story.append(_sp(SP_AFTER_BODY))

    if system.data_sources:
        pii_style = ParagraphStyle(
            "pii_warn", fontName="Helvetica-Bold", fontSize=8,
            textColor=BRAND_WARNING, leading=11, alignment=TA_LEFT)
        data_rows = [
            [
                ds.source_name,
                Paragraph("⚠ Yes", pii_style) if ds.contains_pii
                    else Paragraph("No", styles["table_cell"]),
                ds.pii_categories or "N/A",
                getattr(ds, "description", None) or "—",
            ]
            for ds in system.data_sources
        ]
        story.append(_data_table(
            ["Source Name", "PII?", "PII Categories", "Description"],
            data_rows,
            [4.5 * cm, 2 * cm, 4 * cm, USABLE_W - 10.5 * cm],
            styles
        ))
        story.append(Paragraph("Table 2: Registered Data Sources", styles["caption"]))
    else:
        story.append(Paragraph(
            "No data sources have been registered for this system. "
            "Data source registration is mandatory for High-Risk AI systems under EU AI Act Article 10.",
            styles["body"]
        ))
    story.append(_sp(SP_AFTER_TABLE))
    return story


# ─────────────────────────────────────────────────────────────
#  SECTION 5 – COMPLIANCE CONTROLS
# ─────────────────────────────────────────────────────────────
def _build_compliance_section(system, score_eu, score_nist, styles):
    story = []
    story.append(_section_header("5. Compliance Control Verification", styles))
    story.append(Paragraph(
        "Controls are mapped to two frameworks: the EU AI Act and the NIST AI Risk Management Framework (RMF). "
        "Each control is verified as Met or Outstanding with supporting evidence links where available.",
        styles["body"]
    ))
    story.append(_sp(SP_AFTER_BODY))

    # Inline score bars
    score_tbl = Table(
        [
            [_score_row("EU AI Act",  score_eu,   styles)],
            [_sp(4)],
            [_score_row("NIST AI RMF", score_nist, styles)],
        ],
        colWidths=[USABLE_W],
    )
    score_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(score_tbl)
    story.append(_sp(8))

    if system.compliance_records:
        by_fw = {}
        for rec in system.compliance_records:
            by_fw.setdefault(rec.framework, []).append(rec)

        for fw_idx, (fw_name, records) in enumerate(by_fw.items()):
            story.append(KeepTogether([
                Paragraph(fw_name, styles["sub_heading"]),
                _sp(2),
            ]))
            data_rows = []
            for rec in records:
                met_text  = "✓ Yes" if rec.is_met else "✗ No"
                met_st    = styles["badge_ok"] if rec.is_met else styles["badge_err"]
                data_rows.append([
                    Paragraph(rec.control_id or "—",           styles["table_cell"]),
                    Paragraph(rec.control_description or "—",  styles["table_cell"]),
                    Paragraph(met_text, met_st),
                    Paragraph(rec.evidence_link or "Pending",  styles["table_cell"]),
                ])
            story.append(_data_table(
                ["Control ID", "Description", "Met?", "Evidence"],
                data_rows,
                [2.8 * cm, 7.2 * cm, 1.6 * cm, USABLE_W - 11.6 * cm],
                styles
            ))
            story.append(Paragraph(
                f"Table {fw_idx + 3}: {fw_name} Control Verification",
                styles["caption"]
            ))
    else:
        story.append(Paragraph(
            "No compliance records have been generated. "
            "Complete the Risk Assessment first to auto-generate the compliance checklist.",
            styles["body"]
        ))
    story.append(_sp(SP_AFTER_TABLE))
    return story


# ─────────────────────────────────────────────────────────────
#  SECTION 6 – PERFORMANCE MONITORING
# ─────────────────────────────────────────────────────────────
def _build_monitoring_section(system, styles):
    story = []
    story.append(_section_header("6. Performance Monitoring", styles))

    metrics = getattr(system, "monitoring_metrics", []) or []
    total   = len(metrics)
    shown   = metrics[:20]     # cap at 20 rows

    breached_count = sum(1 for m in metrics if m.is_breached)
    
    if total > 0:
        rate = int(((total - breached_count) / total) * 100)
        sum_tbl = Table([
            [Paragraph("METRICS RECORDED", styles["cover_kv_label"]),
             Paragraph("THRESHOLD BREACHES", styles["cover_kv_label"]),
             Paragraph("COMPLIANCE RATE", styles["cover_kv_label"])],
            [Paragraph(str(total), ParagraphStyle("s1", fontName="Helvetica-Bold", fontSize=14, textColor=BRAND_GRAY_DARK, alignment=TA_CENTER)),
             Paragraph(str(breached_count), ParagraphStyle("s2", fontName="Helvetica-Bold", fontSize=14, textColor=BRAND_DANGER if breached_count > 0 else BRAND_SUCCESS, alignment=TA_CENTER)),
             Paragraph(f"{rate}%", ParagraphStyle("s3", fontName="Helvetica-Bold", fontSize=14, textColor=BRAND_SUCCESS if rate >= 90 else BRAND_WARNING, alignment=TA_CENTER))]
        ], colWidths=[USABLE_W/3]*3)
        sum_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), BRAND_ROW_ALT),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(sum_tbl)
        story.append(_sp(SP_AFTER_TABLE))
        if total > 20:
            story.append(Paragraph(f"<i>Showing most recent {len(shown)} entries.</i>", styles["caption"]))
            story.append(_sp(SP_AFTER_BODY))
    else:
        story.append(Paragraph(
            "No monitoring data has been ingested. "
            "Upload metric data via the Monitoring page to populate this section.",
            styles["body"]
        ))
        story.append(_sp(SP_AFTER_BODY))

    if shown:
        data_rows = []
        for m in shown:
            breached = bool(m.is_breached)
            st       = styles["badge_err"] if breached else styles["badge_ok"]
            data_rows.append([
                (m.timestamp or "")[:16],
                m.metric_name,
                Paragraph(str(m.metric_value), styles["table_cell_center"]),
                Paragraph(str(m.threshold_value), styles["table_cell_center"]),
                Paragraph("✗ BREACH" if breached else "✓ OK", st),
            ])
        # Tighter, better-proportioned column widths
        story.append(_data_table(
            ["Timestamp", "Metric", "Value", "Threshold", "Status"],
            data_rows,
            [3.8 * cm, 4.2 * cm, 2 * cm, 2.4 * cm, 3.6 * cm],
            styles
        ))
        cap_text = "Table: Performance Monitoring Metrics"
        if total > 20:
            cap_text += f" (showing 20 of {total} records)"
        story.append(Paragraph(cap_text, styles["caption"]))

        if total > 20:
            story.append(Paragraph(
                f"<i>Note: {total - 20} additional metric records are stored but not shown above. "
                "Export the full dataset from the Monitoring page for a complete listing.</i>",
                ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=7.5,
                               textColor=BRAND_GRAY_MID, leading=11, alignment=TA_LEFT)
            ))

    story.append(_sp(SP_AFTER_TABLE))
    return story


# ─────────────────────────────────────────────────────────────
#  SECTION 7 – AUDIT TRAIL
# ─────────────────────────────────────────────────────────────
def _build_audit_section(system, styles):
    story = []
    story.append(_section_header("7. Audit Trail", styles))
    story.append(Paragraph(
        "The audit trail records all material governance actions. "
        "Entries are immutable and time-stamped to provide a complete chain of accountability "
        "for regulatory inspectors and internal reviewers.",
        styles["body"]
    ))
    story.append(_sp(SP_AFTER_BODY))

    logs  = getattr(system, "audit_logs", []) or []
    total = len(logs)
    shown = logs[:20]

    if shown:
        # Details column uses wider wrapping; split key:value onto own lines
        detail_style = ParagraphStyle(
            "detail_wrap", fontName="Helvetica", fontSize=7.5,
            textColor=BRAND_GRAY_DARK, leading=11, alignment=TA_LEFT,
        )
        data_rows = []
        for log in shown:
            ts = (log.timestamp or "")[:16]
            try:
                obj = json.loads(log.details) if log.details else {}
                detail_str = "<br/>".join(
                    f"<b>{k.replace('_', ' ').title()}:</b> {v}" for k, v in obj.items()
                ) if obj else "—"
            except Exception:
                detail_str = str(log.details or "—")
            data_rows.append([
                ts,
                log.user or "—",
                log.action or "—",
                Paragraph(detail_str, detail_style),
            ])

        story.append(_data_table(
            ["Timestamp", "User", "Action", "Details"],
            data_rows,
            [3.2 * cm, 3.2 * cm, 4.2 * cm, USABLE_W - 10.6 * cm],
            styles
        ))
        cap_text = "Table: Audit Log Entries"
        if total > 20:
            cap_text += f" (showing 20 of {total} entries)"
        story.append(Paragraph(cap_text, styles["caption"]))

        if total > 20:
            story.append(Paragraph(
                f"<i>Note: {total - 20} additional audit entries are not shown. "
                "The complete audit log is available via the Monitoring page.</i>",
                ParagraphStyle("note2", fontName="Helvetica-Oblique", fontSize=7.5,
                               textColor=BRAND_GRAY_MID, leading=11)
            ))
    else:
        story.append(Paragraph("No audit log entries have been recorded.", styles["body"]))

    story.append(_sp(SP_AFTER_TABLE))
    return story


# ─────────────────────────────────────────────────────────────
#  SECTION 8 – DISCLAIMER
# ─────────────────────────────────────────────────────────────
def _build_disclaimer(styles):
    story = []
    story.append(_section_header("8. Disclaimer & Notes", styles))
    story.append(Paragraph(
        "This report is generated automatically by the GovernAI platform based on data recorded "
        "at the time of export. It is intended to support — not replace — formal legal or regulatory "
        "assessments. For High-Risk AI systems, a qualified third-party conformity assessment may be "
        "required before deployment under the EU AI Act. GovernAI and its authors accept no liability "
        "for decisions made solely on the basis of this automated report.",
        styles["body"]
    ))
    story.append(_sp(8))
    story.append(Paragraph(
        "© GovernAI Platform — Confidential. All rights reserved.",
        ParagraphStyle("disc_foot", fontName="Helvetica-Oblique", fontSize=8,
                       textColor=BRAND_GRAY_MID, alignment=TA_CENTER)
    ))
    return story


# ─────────────────────────────────────────────────────────────
#  DOC TEMPLATE SUBCLASS (wires TOC bookmarks)
# ─────────────────────────────────────────────────────────────
class GovernAIDocTemplate(SimpleDocTemplate):
    """Subclasses SimpleDocTemplate to notify the TOC on section headings."""

    def __init__(self, *args, **kwargs):
        self._toc = kwargs.pop("toc", None)
        self._canvas_metadata = kwargs.pop("canvas_metadata", {})
        super().__init__(*args, **kwargs)

    def afterFlowable(self, flowable):
        """Called by ReportLab after each flowable is rendered; registers TOC entries."""
        if self._toc is None:
            return
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name if hasattr(flowable, "style") else ""
            if style_name == "section_heading":
                text = flowable.getPlainText()
                self._toc.addEntry(0, text, self.page)


# ─────────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────
def generate_pdf_report(system_id: str, output_path: str):
    """Generates a corporate-grade, enterprise-layout PDF audit report."""
    db     = SessionLocal()
    system = get_system_by_id(db, system_id)

    if not system:
        db.close()
        raise ValueError("System not found")

    score_eu   = get_compliance_score(db, system_id, "EU AI Act")
    score_nist = get_compliance_score(db, system_id, "NIST AI RMF")
    report_id  = str(uuid.uuid4())

    styles = _build_styles()

    # Margins tuned so content fills 80-90 % of each page
    # topMargin must clear the 14 mm header bar + small gap
    doc = GovernAIDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,     # tight — header is only 14 mm
        bottomMargin=1.6 * cm,  # tight — footer is 12 mm
        title=f"AI Governance Audit Report – {system.name}",
        author="GovernAI Platform",
        subject="AI Governance Audit",
        creator="GovernAI",
    )

    # Assemble the full story (no inter-section Spacers — sections manage their own)
    story = []
    story.extend(_build_cover(system, score_eu, score_nist, styles, report_id))
    story.extend(_build_executive_summary(system, score_eu, score_nist, styles))
    story.extend(_build_system_overview(system, styles))
    story.extend(_build_risk_section(system, styles))
    story.extend(_build_data_section(system, styles))
    story.extend(_build_compliance_section(system, score_eu, score_nist, styles))
    story.extend(_build_monitoring_section(system, styles))
    story.extend(_build_audit_section(system, styles))
    story.extend(_build_disclaimer(styles))

    # Canvas factory with injected metadata
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def canvas_maker(filename, **kwargs):
        c = GovernAICanvas(filename, **kwargs)
        c._report_id   = report_id
        c._system_name = system.name
        c._gen_time    = gen_time
        return c

    # multiBuild resolves TOC page numbers correctly
    doc.multiBuild(story, canvasmaker=canvas_maker)
    db.close()
    return output_path


if __name__ == "__main__":
    from database.models import AISystem
    db = SessionLocal()
    sys_obj = db.query(AISystem).first()
    if sys_obj:
        generate_pdf_report(sys_obj.id, "test_report.pdf")
        print("Generated test_report.pdf")
    db.close()

