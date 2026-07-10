"""학원 평판 리포트 PDF 생성.

reportlab은 순수 Python이라 Render 같은 컨테이너 배포에서 별도 시스템 라이브러리
설치 없이 동작한다(weasyprint는 cairo/pango 등 시스템 의존성이 필요해 배포 리스크가 큼).
"""
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models_reputation import Academy, ReputationScore

_STYLES = getSampleStyleSheet()
_BODY = ParagraphStyle("body_kr", parent=_STYLES["BodyText"], fontName="Helvetica", fontSize=10, leading=15)
_H1 = ParagraphStyle("h1_kr", parent=_STYLES["Heading1"], fontName="Helvetica-Bold", fontSize=18)
_H2 = ParagraphStyle("h2_kr", parent=_STYLES["Heading2"], fontName="Helvetica-Bold", fontSize=13)


def build_reputation_pdf(academy: Academy, score: ReputationScore) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )

    elements = [
        Paragraph(f"{academy.name} — 학원 평판 리포트", _H1),
        Spacer(1, 4 * mm),
        Paragraph(
            f"생성일: {datetime.now(timezone.utc).strftime('%Y-%m-%d')} · "
            f"평판 계산 기준일: {score.computed_at.strftime('%Y-%m-%d')}",
            _BODY,
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            f"종합 평판 점수: <b>{score.overall_score}점</b> "
            f"(데이터 신뢰도 {score.confidence_score}점, 표본 {score.sample_size}건)",
            _H2,
        ),
        Spacer(1, 4 * mm),
    ]

    if score.category_scores:
        table_data = [["카테고리", "점수"]] + [
            [k, f"{v}점"] for k, v in score.category_scores.items()
        ]
        table = Table(table_data, colWidths=[100 * mm, 40 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D1B16")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8D3C4")),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(table)
    else:
        elements.append(Paragraph("(카테고리별 점수 데이터 없음)", _BODY))

    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph("AI 분석 요약", _H2))
    elements.append(Spacer(1, 2 * mm))

    summary = (score.ai_summary or "(AI 요약이 아직 생성되지 않았습니다)").replace("\n", "<br/>")
    elements.append(Paragraph(summary, _BODY))

    elements.append(Spacer(1, 10 * mm))
    elements.append(
        Paragraph(
            "※ 본 리포트는 학부모·학생 설문과 학원 운영 지표를 바탕으로 한 참고 자료이며, "
            "공식 평가나 법적 효력을 갖지 않습니다.",
            ParagraphStyle("footer", parent=_BODY, fontSize=8, textColor=colors.HexColor("#6B6558")),
        )
    )

    doc.build(elements)
    return buffer.getvalue()
