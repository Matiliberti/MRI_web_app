#!/usr/bin/env python3
"""Generate client instruction PDF in Spanish."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus.flowables import HRFlowable
from PIL import Image as PILImage
import os

PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm

GRAY_LIGHT = HexColor("#f5f5f5")
GRAY_MID   = HexColor("#e0e0e0")
GRAY_TEXT  = HexColor("#555555")
BLACK      = HexColor("#111111")
BLUE       = HexColor("#0057F1")
GREEN      = HexColor("#22c55e")
RED        = HexColor("#ef4444")

doc = SimpleDocTemplate(
    "/Users/matiliberti/Documents/MRI_display/MRI_web_app/instrucciones_cliente.pdf",
    pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=2 * cm, bottomMargin=2 * cm,
)

title_style = ParagraphStyle("title",
    fontName="Helvetica-Bold", fontSize=20, textColor=BLACK,
    spaceAfter=4, leading=24,
)
subtitle_style = ParagraphStyle("subtitle",
    fontName="Helvetica", fontSize=11, textColor=GRAY_TEXT,
    spaceAfter=0, leading=15,
)
step_num_style = ParagraphStyle("stepnum",
    fontName="Helvetica-Bold", fontSize=13, textColor=BLUE,
    leading=16,
)
step_title_style = ParagraphStyle("steptitle",
    fontName="Helvetica-Bold", fontSize=13, textColor=BLACK,
    leading=16,
)
body_style = ParagraphStyle("body",
    fontName="Helvetica", fontSize=11, textColor=GRAY_TEXT,
    leading=16, spaceAfter=4,
)
mono_style = ParagraphStyle("mono",
    fontName="Courier-Bold", fontSize=11, textColor=BLACK,
    leading=16,
)
note_style = ParagraphStyle("note",
    fontName="Helvetica-Oblique", fontSize=9, textColor=GRAY_TEXT,
    leading=13,
)
caption_style = ParagraphStyle("caption",
    fontName="Helvetica", fontSize=9, textColor=GRAY_TEXT,
    leading=12, alignment=TA_CENTER,
)

CONTENT_W = PAGE_W - 2 * MARGIN

def step_block(num, title, content_rows):
    """Returns a Table that renders as a numbered step box."""
    num_para   = Paragraph(f"0{num}", step_num_style)
    title_para = Paragraph(title, step_title_style)

    header = Table(
        [[num_para, title_para]],
        colWidths=[1.2*cm, CONTENT_W - 1.2*cm - 0.6*cm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
    ]))

    rows = [header] + content_rows

    box = Table(
        [[r] for r in rows],
        colWidths=[CONTENT_W - 0.6*cm],
    )
    box.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), GRAY_LIGHT),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("TOPPADDING",   (0,0), (0,0),   12),
        ("BOTTOMPADDING",(0,-1),(0,-1),  12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    return box


# ── Screenshot helper ──────────────────────────────────────────────────────────
def scaled_image(path, max_w_cm, max_h_cm=None):
    img = PILImage.open(path)
    iw, ih = img.size
    max_w = max_w_cm * cm
    scale = max_w / iw
    if max_h_cm:
        max_h = max_h_cm * cm
        scale = min(scale, max_h / ih)
    return Image(path, width=iw*scale, height=ih*scale)


# ── Assemble content ───────────────────────────────────────────────────────────
SCREENSHOT_DIR = "/Users/matiliberti/Documents/Imagenes/Screenshots"
STATUS_IMG     = os.path.join(SCREENSHOT_DIR, "online_status.png")

story = []

# Title
story.append(Paragraph("Instrucciones de uso", title_style))
story.append(Paragraph("Pantalla MRI · Display Manager", subtitle_style))
story.append(Spacer(1, 0.5*cm))
story.append(HRFlowable(width=CONTENT_W, thickness=1, color=GRAY_MID, spaceAfter=0.5*cm))

# ── Step 1: WiFi ──────────────────────────────────────────────────────────────
story.append(step_block(1, "Conectar al WiFi", [
    Paragraph("Conectá el dispositivo a la red del equipo:", body_style),
    Spacer(1, 0.2*cm),
    Table([
        [Paragraph("Red:", body_style),        Paragraph("MRI_hotspot", mono_style)],
        [Paragraph("Contraseña:", body_style),  Paragraph("password1234", mono_style)],
    ], colWidths=[3*cm, CONTENT_W - 3*cm - 2.8*cm],
       style=[
           ("LEFTPADDING",  (0,0),(-1,-1), 0),
           ("RIGHTPADDING", (0,0),(-1,-1), 0),
           ("TOPPADDING",   (0,0),(-1,-1), 2),
           ("BOTTOMPADDING",(0,0),(-1,-1), 2),
           ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
       ]),
    Spacer(1, 0.1*cm),
    Paragraph("Si no hay hotspot disponible, conectate al WiFi habitual del lugar.", note_style),
]))
story.append(Spacer(1, 0.4*cm))

# ── Step 2: Open app ──────────────────────────────────────────────────────────
story.append(step_block(2, "Abrir la aplicación", [
    Paragraph("Desde cualquier dispositivo (móvil, tablet o PC) abrí el navegador y entrá a:", body_style),
    Spacer(1, 0.15*cm),
    Paragraph("https://projectwebapp-xi.vercel.app", mono_style),
]))
story.append(Spacer(1, 0.4*cm))

# ── Step 3: Check status ──────────────────────────────────────────────────────
status_img = scaled_image(STATUS_IMG, max_w_cm=6, max_h_cm=3)
status_img.hAlign = "LEFT"

story.append(step_block(3, "Verificar que la pantalla está conectada", [
    Paragraph(
        "En la parte superior de la app hay dos indicadores. "
        "El de la izquierda muestra el estado de la app (RDY = listo). "
        "El de la derecha muestra si la pantalla está conectada:",
        body_style,
    ),
    Spacer(1, 0.3*cm),
    Table([
        [
            Table([
                [Paragraph("● LIVE", ParagraphStyle("g", fontName="Helvetica-Bold", fontSize=11, textColor=GREEN))],
                [Paragraph("Pantalla conectada — podés continuar.", body_style)],
            ], style=[("LEFTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]),
            Table([
                [Paragraph("● OFF", ParagraphStyle("r", fontName="Helvetica-Bold", fontSize=11, textColor=RED))],
                [Paragraph("Pantalla sin conexión — verificá que el equipo esté encendido.", body_style)],
            ], style=[("LEFTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]),
        ]
    ], colWidths=[(CONTENT_W-2.8*cm)/2]*2,
       style=[
           ("LEFTPADDING",  (0,0),(-1,-1), 0),
           ("RIGHTPADDING", (0,0),(-1,-1), 8),
           ("TOPPADDING",   (0,0),(-1,-1), 0),
           ("BOTTOMPADDING",(0,0),(-1,-1), 0),
           ("VALIGN",       (0,0),(-1,-1), "TOP"),
       ]),
    Spacer(1, 0.3*cm),
    status_img,
    Paragraph("Indicadores de estado en la app (izquierda: RDY — derecha: estado de la pantalla)", caption_style),
]))
story.append(Spacer(1, 0.4*cm))

# ── Step 4: Upload ────────────────────────────────────────────────────────────
story.append(step_block(4, "Subir una imagen o vídeo", [
    Paragraph("Tocá el recuadro central de la app y seleccioná el archivo. "
              "También podés arrastrarlo directamente al recuadro desde una PC.", body_style),
    Spacer(1, 0.1*cm),
    Paragraph('Cuando termine la carga, el recuadro mostrará "Transmitted" con un tilde verde.', body_style),
]))
story.append(Spacer(1, 0.4*cm))

# ── Step 5: Display ───────────────────────────────────────────────────────────
story.append(step_block(5, "Mostrar en pantalla", [
    Paragraph("El archivo más reciente se muestra automáticamente en la pantalla. "
              "No hace falta hacer nada más.", body_style),
    Spacer(1, 0.1*cm),
    Paragraph("Si querés mostrar una imagen anterior, tocá su miniatura en la lista "
              "y la pantalla se actualizará en unos segundos.", body_style),
]))

story.append(Spacer(1, 0.8*cm))
story.append(HRFlowable(width=CONTENT_W, thickness=1, color=GRAY_MID, spaceAfter=0.3*cm))
story.append(Paragraph("Display Manager v1.0", note_style))

doc.build(story)
print("PDF generado: instrucciones_cliente.pdf")
