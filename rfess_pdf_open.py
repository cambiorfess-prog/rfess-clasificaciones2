from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)
from reportlab.lib.units import cm
import pandas as pd

RFESS_BLUE = "#2E5B92"
RFESS_RED = "#C8102E"
RFESS_YELLOW = "#F2D335"


def _club_sort_key(name: str) -> str:
    return str(name or "").lower().strip()


def build_pdf(
    classifications: pd.DataFrame,
    out_path: str,
    title: str = "Clasificaciones RFESS",
    subtitle: str = "",
    logo_path: str | None = None,
) -> None:
    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        rightMargin=1.15 * cm,
        leftMargin=1.15 * cm,
        topMargin=1.15 * cm,
        bottomMargin=1.15 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "rfess_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor(RFESS_BLUE),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "rfess_subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#445066"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    block_style = ParagraphStyle(
        "rfess_block",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor(RFESS_BLUE),
        alignment=TA_LEFT,
        spaceAfter=10,
    )

    story = []

    if logo_path:
        try:
            logo = Image(logo_path, width=5.0 * cm, height=3.15 * cm)
            logo.hAlign = "CENTER"
            story.append(logo)
            story.append(Spacer(1, 0.15 * cm))
        except Exception:
            pass

    story.append(Paragraph(title, title_style))
    if subtitle:
        story.append(Paragraph(subtitle, subtitle_style))
    story.append(Spacer(1, 0.25 * cm))

    if classifications.empty:
        story.append(Paragraph("No hay clasificaciones para mostrar.", styles["Normal"]))
    else:
        grouped = list(classifications.groupby("block", sort=False))
        for i, (block, g) in enumerate(grouped):
            if i:
                story.append(PageBreak())
                if logo_path:
                    try:
                        logo = Image(logo_path, width=3.8 * cm, height=2.4 * cm)
                        logo.hAlign = "LEFT"
                        story.append(logo)
                        story.append(Spacer(1, 0.12 * cm))
                    except Exception:
                        pass
            story.append(Paragraph(str(block), block_style))
            data = [["Puesto", "Club", "Puntos"]]
            g_sorted = g.sort_values(["rank", "club"], key=lambda s: s.map(_club_sort_key) if s.name == "club" else s)
            for _, r in g_sorted.iterrows():
                score_val = r["score"]
                try:
                    score = int(score_val) if float(score_val).is_integer() else score_val
                except Exception:
                    score = score_val
                data.append([int(r["rank"]), str(r["club"]), score])

            table = Table(data, colWidths=[2.0 * cm, 12.7 * cm, 2.2 * cm], repeatRows=1)
            table_style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(RFESS_BLUE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6dce8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9.2),
            ]
            for row_idx in range(1, len(data)):
                bg = colors.HexColor("#f7f9fc") if row_idx % 2 == 1 else colors.white
                table_style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))
            table.setStyle(TableStyle(table_style_cmds))
            story.append(table)

    doc.build(story)
