"""Generator script for ELO Face V3 Emotion Reference & Animation Specification DOCX.

Produces a polished, professional Word document containing all 20 emotions,
intro sequence, design specifications, pairwise comparisons, full timeline,
and real screenshots captured directly from the V3 animation engine.
"""

import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# Asset Directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
ASSET_DIR = os.path.join(BASE_DIR, "docs", "assets")
OUTPUT_DOCX = os.path.join(BASE_DIR, "ELO_Face_V3_Emotion_Reference.docx")

# Color Palette Constants (RGB)
COLOR_NAVY = RGBColor(15, 23, 42)       # #0F172A - Deep Slate/Navy
COLOR_SLATE = RGBColor(51, 65, 85)      # #334155 - Slate Body Text
COLOR_ROSE = RGBColor(225, 29, 72)      # #E11D48 - Accent Rose/Pink
COLOR_MUTED = RGBColor(100, 116, 139)   # #64748B - Muted Gray
COLOR_DARK = RGBColor(30, 41, 59)       # #1E293B - Dark Text

HEX_NAVY = "0F172A"
HEX_SLATE_LIGHT = "F1F5F9"
HEX_SLATE_ROW = "F8FAFC"
HEX_BORDER = "CBD5E1"
HEX_ROSE = "E11D48"
HEX_ACCENT_BG = "FFF1F2"


def set_cell_background(cell, fill_hex: str):
    """Set background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    """Set inner padding of a table cell (in twips: 20 twips = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    """Set borders for a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')

    border_specs = {'top': top, 'bottom': bottom, 'left': left, 'right': right}
    for side, spec in border_specs.items():
        if spec:
            val = spec.get('val', 'single')
            sz = spec.get('sz', '4')
            space = spec.get('space', '0')
            color = spec.get('color', HEX_BORDER)
            el = parse_xml(f'<w:{side} {nsdecls("w")} w:val="{val}" w:sz="{sz}" w:space="{space}" w:color="{color}"/>')
            borders.append(el)
        else:
            el = parse_xml(f'<w:{side} {nsdecls("w")} w:val="none"/>')
            borders.append(el)
    tcPr.append(borders)


def add_styled_heading(doc, text: str, level: int = 1, space_before: int = 16, space_after: int = 6):
    """Add a styled heading with consistent spacing and typography."""
    heading = doc.add_heading(level=level)
    heading.paragraph_format.space_before = Pt(space_before)
    heading.paragraph_format.space_after = Pt(space_after)
    heading.paragraph_format.keep_with_next = True

    run = heading.add_run(text)
    run.font.name = "Segoe UI"
    if level == 1:
        run.font.size = Pt(18)
        run.font.bold = True
        run.font.color.rgb = COLOR_NAVY
    elif level == 2:
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = COLOR_NAVY
    elif level == 3:
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = COLOR_SLATE
    return heading


def add_callout_box(doc, text: str, title: str = "", border_color: str = HEX_ROSE, fill_color: str = HEX_SLATE_LIGHT):
    """Add a styled callout box with a thick left accent border."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.8)

    set_cell_background(cell, fill_color)
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
    set_cell_borders(cell, left={'val': 'single', 'sz': '24', 'color': border_color})

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15

    if title:
        run_title = p.add_run(f"{title}\n")
        run_title.font.name = "Segoe UI"
        run_title.font.bold = True
        run_title.font.size = Pt(10.5)
        run_title.font.color.rgb = COLOR_NAVY

    run_text = p.add_run(text)
    run_text.font.name = "Segoe UI"
    run_text.font.size = Pt(9.5)
    run_text.font.color.rgb = COLOR_SLATE

    # Add small spacing after table
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(6)


def format_table_header(row, col_widths, headers, bg_hex=HEX_NAVY):
    """Format the header row of a table."""
    for idx, header_text in enumerate(headers):
        cell = row.cells[idx]
        cell.width = col_widths[idx]
        set_cell_background(cell, bg_hex)
        set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
        set_cell_borders(cell,
            top={'val': 'single', 'sz': '6', 'color': HEX_BORDER},
            bottom={'val': 'single', 'sz': '12', 'color': HEX_NAVY},
            left={'val': 'none'}, right={'val': 'none'}
        )
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(header_text)
        run.font.name = "Segoe UI"
        run.font.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(255, 255, 255)


def add_table_data_row(tbl, col_widths, values, is_even=False, is_monospace=False):
    """Add and format a data row in a table."""
    row = tbl.add_row()
    bg_hex = HEX_SLATE_ROW if is_even else "FFFFFF"
    for idx, val in enumerate(values):
        cell = row.cells[idx]
        cell.width = col_widths[idx]
        set_cell_background(cell, bg_hex)
        set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
        set_cell_borders(cell,
            bottom={'val': 'single', 'sz': '4', 'color': HEX_BORDER},
            left={'val': 'none'}, right={'val': 'none'}, top={'val': 'none'}
        )
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.1
        run = p.add_run(str(val))
        run.font.name = "Consolas" if (is_monospace and idx > 0) else "Segoe UI"
        run.font.size = Pt(9.0)
        run.font.color.rgb = COLOR_DARK if idx == 0 else COLOR_SLATE
        if idx == 0:
            run.font.bold = True
    return row


def build_document():
    print("Initializing ELO Face V3 Document Builder...")
    doc = Document()

    # ---------------------------------------------------------------------------
    # Page Setup
    # ---------------------------------------------------------------------------
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11.0)
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    # Header & Footer setup
    header = section.header
    hp = header.paragraphs[0]
    hp.text = "ELO Face V3 — Emotion Reference & Animation Specification (FINAL / LOCKED)"
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.runs[0].font.name = "Segoe UI"
    hp.runs[0].font.size = Pt(8.0)
    hp.runs[0].font.color.rgb = COLOR_MUTED

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.text = "Confidential & Proprietary — ELO Face Robotics Project — 800x480 @ 60 FPS"
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.runs[0].font.name = "Segoe UI"
    fp.runs[0].font.size = Pt(8.0)
    fp.runs[0].font.color.rgb = COLOR_MUTED

    # Default style adjustments
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Segoe UI'
    normal_style.font.size = Pt(10.0)
    normal_style.font.color.rgb = COLOR_SLATE
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    # ---------------------------------------------------------------------------
    # COVER / HERO SECTION
    # ---------------------------------------------------------------------------
    p_title_pre = doc.add_paragraph()
    p_title_pre.paragraph_format.space_before = Pt(20)
    p_title_pre.paragraph_format.space_after = Pt(2)
    run_pre = p_title_pre.add_run("OFFICIAL SPECIFICATION & REFERENCE MANUAL")
    run_pre.font.name = "Segoe UI"
    run_pre.font.bold = True
    run_pre.font.size = Pt(11)
    run_pre.font.color.rgb = COLOR_ROSE

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run("ELO Face V3")
    run_title.font.name = "Segoe UI"
    run_title.font.bold = True
    run_title.font.size = Pt(28)
    run_title.font.color.rgb = COLOR_NAVY

    p_subtitle = doc.add_paragraph()
    p_subtitle.paragraph_format.space_before = Pt(0)
    p_subtitle.paragraph_format.space_after = Pt(14)
    run_sub = p_subtitle.add_run("Emotion Reference & Animation Specification")
    run_sub.font.name = "Segoe UI"
    run_sub.font.size = Pt(15)
    run_sub.font.color.rgb = COLOR_SLATE

    # Hero Metadata Grid Table
    meta_table = doc.add_table(rows=4, cols=4)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_w = [Inches(1.75), Inches(1.75), Inches(1.75), Inches(1.75)]

    meta_items = [
        ("Version", "V3 (Final)"),
        ("Resolution", "800 x 480 px"),
        ("Target Frame Rate", "60 FPS"),
        ("Design Language", "Minimalist Big Eyes"),
        ("Total Loop Duration", "103.0 Seconds"),
        ("Timeline Segments", "21 Segments"),
        ("Emotion Count", "20 Emotions"),
        ("Intro Sequence", "2 Text States + Fade"),
        ("Display Canvas", "Pure Black (0, 0, 0)"),
        ("Eye Geometry", "Pure White (255, 255, 255)"),
        ("Blush Accent", "Soft Pink (255, 160, 185)"),
        ("Baseline Radius", "R = 85.0 px (D = 170 px)"),
        ("Status", "FINAL / LOCKED"),
        ("Verification Suite", "64 / 64 PASS (100%)"),
        ("Simulation Check", "6,180 Frames Simulated"),
        ("Git Commit Hash", "5bdabea"),
    ]

    for i, (label, val) in enumerate(meta_items):
        r = i // 4
        c = i % 4
        cell = meta_table.cell(r, c)
        cell.width = col_w[c]
        set_cell_background(cell, HEX_SLATE_ROW)
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        set_cell_borders(cell,
            top={'val': 'single', 'sz': '4', 'color': HEX_BORDER},
            bottom={'val': 'single', 'sz': '4', 'color': HEX_BORDER},
            left={'val': 'single', 'sz': '4', 'color': HEX_BORDER},
            right={'val': 'single', 'sz': '4', 'color': HEX_BORDER}
        )
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)

        run_lbl = p.add_run(f"{label}\n")
        run_lbl.font.name = "Segoe UI"
        run_lbl.font.size = Pt(8.0)
        run_lbl.font.color.rgb = COLOR_MUTED

        run_v = p.add_run(val)
        run_v.font.name = "Segoe UI"
        run_v.font.bold = True
        run_v.font.size = Pt(9.5)
        run_v.font.color.rgb = COLOR_NAVY if "Status" not in label else COLOR_ROSE

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(8)
    p_sp.paragraph_format.space_after = Pt(6)

    add_callout_box(
        doc,
        title="EXECUTIVE SUMMARY & SYSTEM SCOPE",
        text="This specification documents the complete, finalized, and locked ELO Face V3 visual emotion and animation system. "
             "ELO Face V3 implements a minimalist, expressive robotic identity designed for 800x480 displays at 60 FPS. "
             "All 20 emotional behaviors, the 10.0-second typewriter intro, geometric squash-based eye morphing, and continuous "
             "interpolation parameters are fully documented herein. Every screenshot in this document is captured directly from "
             "the live, deterministic V3 rendering engine.",
        border_color=HEX_ROSE,
        fill_color=HEX_ACCENT_BG
    )

    doc.add_page_break()

    # ---------------------------------------------------------------------------
    # SECTION 1: OVERVIEW & DESIGN PHILOSOPHY
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "1. Overview & Visual Identity", level=1)

    p = doc.add_paragraph(
        "ELO Face V3 is a modern, expressive robotic facial animation system designed for the ELO social robot. "
        "It operates on a dedicated 800x480 display canvas at 60 frames per second, communicating rich emotional states "
        "through a clean, iconic 'Big Eyes' minimalist visual identity."
    )

    p = doc.add_paragraph(
        "Unlike conventional anthropomorphic cartoon faces that rely on complex facial anatomy, ELO communicates nuance, "
        "warmth, intelligence, and empathy exclusively through the parametric manipulation of two solid geometric eyes."
    )

    add_styled_heading(doc, "Core Communication Mechanisms", level=2)
    p = doc.add_paragraph("Emotion in ELO Face V3 is synthesized through nine fundamental physical and geometric modulators:")

    modulators = [
        ("Eye Openness (0.0 to 1.0):", "Continuous vertical stadium-to-circle morphing controlling attention, focus, and consciousness."),
        ("Squash & Stretch Deformation:", "Horizontal width expansion (+12%) during vertical compression for organic mechanical elasticity."),
        ("Gaze Offset Displacement (dx, dy):", "Synchronous and independent 2D displacement vectors indicating focus, contemplation, or hesitation."),
        ("Scale Modulation (0.5x to 1.5x):", "Dynamic enlargement or deflation communicating emotional arousal, energy, or melancholia."),
        ("Controlled Asymmetry:", "Independent left/right eye openness and squinting for complex states like Curiosity, Confusion, and Winking."),
        ("Micro-Motion & Organic Breathing:", "Subtle sinusoidal scale breathing (T=4.0s) and fine gaze tremors that prevent static lifelessness."),
        ("Framerate-Agnostic Easing:", "Physically-based exponential decay smoothing (rates 10.0 to 24.0) paired with cubic and quad eases."),
        ("Cute Pink Blush Accent:", "Soft rounded horizontal cheek strokes (alpha up to 180) for affectionate, shy, and warm expressions."),
        ("Floating Sleep Z Particles:", "Smoothly drifting, sinusoidal swaying alpha particles during deep sleep cycles.")
    ]
    for name, desc in modulators:
        p_mod = doc.add_paragraph(style='List Bullet')
        p_mod.paragraph_format.space_before = Pt(1)
        p_mod.paragraph_format.space_after = Pt(2)
        r_name = p_mod.add_run(f"{name} ")
        r_name.font.bold = True
        r_name.font.color.rgb = COLOR_NAVY
        r_desc = p_mod.add_run(desc)
        r_desc.font.color.rgb = COLOR_SLATE

    add_styled_heading(doc, "Strict Design Constraints (Zero Clutter)", level=2)
    p = doc.add_paragraph(
        "To preserve the iconic robotic identity and prevent visual distraction, ELO Face V3 enforces strict negative constraints:"
    )

    constraints_tbl = doc.add_table(rows=1, cols=2)
    constraints_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_widths = [Inches(2.2), Inches(4.6)]
    format_table_header(constraints_tbl.rows[0], c_widths, ["Forbidden Element", "V3 Architectural Alternative"])

    constraint_rows = [
        ("No Pupils / Sclera", "Gaze direction is communicated by whole-eye 2D translation offset (dx, dy)."),
        ("No Eyebrows", "Expressions of anger, suspicion, and surprise are formed through squash morphing and scale."),
        ("No Mouth / Lips", "Happiness and excitement are expressed via vertical bouncing, hopping, and scale bursts."),
        ("No Outlines / Chassis", "Zero stroked borders or chassis graphics; pure solid shapes floating on absolute black."),
        ("No External Emoticons", "No tear drops, sweat beads, or lightning bolts; only soft blush and subtle sleep Z's.")
    ]
    for idx, (el, alt) in enumerate(constraint_rows):
        add_table_data_row(constraints_tbl, c_widths, [el, alt], is_even=(idx % 2 == 1))

    doc.add_page_break()

    # ---------------------------------------------------------------------------
    # SECTION 2: ANIMATION SPECIFICATIONS
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "2. Animation & System Specifications", level=1)

    p = doc.add_paragraph(
        "All parameters, dimensions, and timings in ELO Face V3 are governed by centralized configuration constants. "
        "No magic numbers are scattered within the rendering or physics logic."
    )

    add_styled_heading(doc, "Display, Canvas & Color Palette", level=2)

    spec_tbl = doc.add_table(rows=1, cols=4)
    spec_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    s_widths = [Inches(1.5), Inches(1.3), Inches(1.5), Inches(2.5)]
    format_table_header(spec_tbl.rows[0], s_widths, ["Element", "Color / Spec", "RGB / Value", "Design Usage & Behavior"])

    spec_rows = [
        ("Canvas Width", "800 pixels", "WINDOW_WIDTH = 800", "Target display horizontal resolution."),
        ("Canvas Height", "480 pixels", "WINDOW_HEIGHT = 480", "Target display vertical resolution (5:3 aspect)."),
        ("Frame Rate", "60 FPS", "TARGET_FPS = 60", "All physics compute with delta time (dt)."),
        ("Background", "Pure Black", "RGB(0, 0, 0)", "High-contrast OLED/IPS zero emission canvas."),
        ("Eyes (Solid)", "Pure White", "RGB(255, 255, 255)", "Solid opaque rounded stadium/circle geometry."),
        ("Cheek Blush", "Soft Warm Pink", "RGB(255, 160, 185)", "Cute accents with smooth alpha envelope (max alpha 180)."),
        ("Intro Text", "Pure White", "RGB(255, 255, 255)", "Crisp typewriter font for opening greeting."),
        ("Intro Full-Stop", "Signature Pink", "RGB(255, 160, 185)", "Accent dot on 'This is ELO.' for brand personality.")
    ]
    for idx, (el, col, rgb_val, usage) in enumerate(spec_rows):
        add_table_data_row(spec_tbl, s_widths, [el, col, rgb_val, usage], is_even=(idx % 2 == 1), is_monospace=True)

    add_styled_heading(doc, "Eye Baseline Layout & Morphing Geometry", level=2)

    geom_tbl = doc.add_table(rows=1, cols=3)
    geom_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    g_widths = [Inches(2.0), Inches(1.8), Inches(3.0)]
    format_table_header(geom_tbl.rows[0], g_widths, ["Geometric Parameter", "Finalized Value", "Technical & Visual Function"])

    geom_rows = [
        ("Base Radius (R)", "85.0 pixels", "Base eye radius; full open diameter = 170 px."),
        ("Left Eye Center X", "270.0 px", "Horizontal anchor for left optical axis."),
        ("Right Eye Center X", "530.0 px", "Horizontal anchor for right optical axis (260 px spacing)."),
        ("Eye Center Y (Baseline)", "240.0 px", "Vertical center line for both eyes on 480px canvas."),
        ("Min Open Ratio", "0.06 (6.0%)", "Minimum vertical height ratio when fully squashed/closed."),
        ("Squash Width Expansion", "+0.12 (+12.0%)", "Horizontal expansion factor when eyes compress vertically."),
        ("Max Look Offset X", "+/- 65.0 px", "Maximum horizontal gaze displacement travel."),
        ("Max Look Offset Y", "+/- 45.0 px", "Maximum vertical gaze displacement travel."),
        ("Scale Bounds", "0.5x to 1.5x", "Allowed dynamic scale range (Default = 1.0x)."),
        ("Look Smooth Rate", "lambda = 12.0", "Exponential decay smoothing rate for gaze tracking."),
        ("Scale Smooth Rate", "lambda = 10.0", "Exponential decay rate for scale transitions."),
        ("Open Smooth Rate", "lambda = 24.0", "Exponential decay rate for eyelid morphing/blinking.")
    ]
    for idx, (param, val, func) in enumerate(geom_rows):
        add_table_data_row(geom_tbl, g_widths, [param, val, func], is_even=(idx % 2 == 1), is_monospace=True)

    add_styled_heading(doc, "Mathematical Squash-to-Circle Formula", level=2)
    p = doc.add_paragraph(
        "Each eye is rendered as a single continuous geometric shape (stadium / rounded pill). "
        "Given eye openness parameter o in [0.0, 1.0] and scale multiplier s:"
    )

    add_callout_box(
        doc,
        title="EYE GEOMETRY EQUATIONS",
        text="Width  = 2 * R * s * (1.0 + (1.0 - o) * 0.12)\n"
             "Height = 2 * R * s * (0.06 + (1.0 - 0.06) * o)\n"
             "Corner Radius = min(Width / 2, Height / 2) = Height / 2\n"
             "Center = (Base_X + look_x, Base_Y + look_y)",
        border_color=HEX_NAVY,
        fill_color=HEX_SLATE_ROW
    )

    doc.add_page_break()

    # ---------------------------------------------------------------------------
    # SECTION 3: INTRO SEQUENCE
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "3. Intro Sequence (10.0 Seconds)", level=1)

    p = doc.add_paragraph(
        "The automated sequence begins with a polished 10.0-second typewriter intro. "
        "The intro establishes ELO's identity, greets the user, and smoothly dissolves into the living robotic face. "
        "The intro sequence is strictly sequenced and does not count as one of the 20 emotional expressions."
    )

    # Intro Item 1: "Hii"
    add_styled_heading(doc, "Phase 1: 'Hii' Greeting (0.0s – 4.2s)", level=2)

    intro_hii_path = os.path.join(ASSET_DIR, "intro_hii.png")
    if os.path.exists(intro_hii_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(intro_hii_path, width=Inches(5.0))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(0)
        p_cap.paragraph_format.space_after = Pt(8)
        run_cap = p_cap.add_run("Figure 1.1: Live render of Intro Phase 1 ('Hii') at elapsed = 2.0s with active blinking cursor.")
        run_cap.font.size = Pt(8.5)
        run_cap.font.italic = True
        run_cap.font.color.rgb = COLOR_MUTED

    p = doc.add_paragraph(
        "• Typewriter Reveal (0.0s – 0.6s): Characters 'H', 'i', 'i' type onto the center screen sequentially.\n"
        "• Cursor Blinking (0.0s – 3.2s): A vertical cursor bar '|' toggles every 0.35 seconds.\n"
        "• Message Hold (0.6s – 3.2s): The full text 'Hii' holds at 100% opacity.\n"
        "• Smooth Fade-Out (3.2s – 4.2s): The text smoothly dissolves to 0% alpha using a smootherstep easing curve."
    )

    # Intro Item 2: "This is ELO."
    add_styled_heading(doc, "Phase 2: 'This is ELO.' & Face Transition (4.2s – 10.0s)", level=2)

    intro_elo_path = os.path.join(ASSET_DIR, "intro_this_is_elo.png")
    if os.path.exists(intro_elo_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(intro_elo_path, width=Inches(5.0))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(0)
        p_cap.paragraph_format.space_after = Pt(8)
        run_cap = p_cap.add_run("Figure 1.2: Live render of Intro Phase 2 ('This is ELO.') at elapsed = 6.2s featuring the signature pink full-stop accent.")
        run_cap.font.size = Pt(8.5)
        run_cap.font.italic = True
        run_cap.font.color.rgb = COLOR_MUTED

    p = doc.add_paragraph(
        "• Typewriter Reveal (4.2s – 5.4s): 'This is ELO.' types out smoothly.\n"
        "• Signature Pink Full-Stop: The final period '.' renders in soft warm pink RGB(255, 160, 185), giving ELO its signature friendly brand mark.\n"
        "• Message Hold (5.4s – 7.8s): Full text holds with cursor blinking.\n"
        "• Text Dissolve (7.8s – 8.8s): 'This is ELO.' fades out to 0% opacity.\n"
        "• Face Fade-In (8.8s – 10.0s): Robotic eyes smoothly fade in from alpha 0.0 to 1.0, cleanly establishing baseline eye presence for the emotion loop."
    )

    doc.add_page_break()

    # ---------------------------------------------------------------------------
    # SECTION 4: EMOTION REFERENCE (ALL 20 EMOTIONS)
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "4. Comprehensive Emotion Reference (20 Expressions)", level=1)

    p = doc.add_paragraph(
        "This section documents each of the 20 finalized emotional expressions in ELO Face V3. "
        "Every subsection includes an actual 800x480 screenshot captured from the deterministic V3 renderer, "
        "its exact timeline duration, visual behavioral mechanics, psychological intent, and physical parameters."
    )

    # List of 20 emotions with metadata
    emotions_data = [
        {
            "num": 1,
            "id": "settle",
            "name": "Settle (Neutral Baseline)",
            "file": "01_settle.png",
            "dur": "3.5s",
            "intent": "Calm, conscious resting state; confirms the robot is awake, attentive, and receptive.",
            "behavior": "Both eyes are fully open (o = 1.0) geometric circles positioned at optical center (0, 0). Subtle sinusoidal micro-breathing modulates overall scale by +/-2% over a 4.0-second period, giving the face organic lifelikeness.",
            "params": [
                ("Open Left / Right", "1.00 / 1.00 (Full Circle)"),
                ("Gaze Offset (dx, dy)", "(0.0 px, 0.0 px)"),
                ("Scale Multiplier", "1.00x (+/-0.02x breathing)"),
                ("Breathing Period", "4.0 seconds (Amp = 0.020)"),
                ("Blush Opacity", "0.0 (Inactive)")
            ]
        },
        {
            "num": 2,
            "id": "blink",
            "name": "Blink (Dual Natural Blinks)",
            "file": "02_blink.png",
            "dur": "3.5s",
            "intent": "Essential physiological micro-behavior; relieves visual stare and communicates natural biological cadence.",
            "behavior": "Executes two sequential natural blinks. In each blink, eyes smoothly compress vertically from circles into thin horizontal stadium pills (o = 0.0) via cubic_in_out easing, hold for 20ms, and quickly reopen via quad_out.",
            "params": [
                ("Blink Count", "2 distinct blinks in sequence"),
                ("Peak Openness", "0.00 (Squashed stadium pill)"),
                ("Close / Reopen Curve", "cubic_in_out (close) -> quad_out (reopen)"),
                ("Squash Width Expansion", "+12% horizontal widening during closure"),
                ("Blink 1 / Blink 2 Timing", "u in [0.15, 0.42] / u in [0.58, 0.85]")
            ]
        },
        {
            "num": 3,
            "id": "look_horizontal",
            "name": "Look Horizontal (Environment Scan)",
            "file": "03_look_horizontal.png",
            "dur": "5.0s",
            "intent": "Scanning the room or tracking a user moving horizontally across the robot's field of view.",
            "behavior": "Eyes glide smoothly from Center -> Full Left Glance (dx = -53.3 px) -> Hold -> Smooth sweep across to Full Right Glance (dx = +53.3 px) -> Hold -> Return to Center. Openness remains 1.0 with zero eyelid distortion.",
            "params": [
                ("Gaze Travel (Left / Right)", "dx = -53.3 px / dx = +53.3 px"),
                ("Vertical Offset", "dy = 0.0 px (Pure horizontal track)"),
                ("Openness", "1.00 / 1.00 (Constant)"),
                ("Scale", "1.00x"),
                ("Interpolation Rate", "lambda = 12.0 (exp_decay smoothing)")
            ]
        },
        {
            "num": 4,
            "id": "look_vertical",
            "name": "Look Vertical (Elevation Scan)",
            "file": "04_look_vertical.png",
            "dur": "4.5s",
            "intent": "Inspecting tall objects, looking up at a standing human, or looking down at tabletop interactions.",
            "behavior": "Eyes track smoothly from Center -> Upward Glance (dy = -33.8 px) -> Hold -> Downward Glance (dy = +33.8 px) -> Hold -> Return to Center. Motion follows organic cubic easing with crisp dampening.",
            "params": [
                ("Gaze Travel (Up / Down)", "dy = -33.8 px / dy = +33.8 px"),
                ("Horizontal Offset", "dx = 0.0 px (Pure vertical track)"),
                ("Openness", "1.00 / 1.00 (Full open circles)"),
                ("Scale", "1.00x"),
                ("Interpolation Rate", "lambda = 12.0")
            ]
        },
        {
            "num": 5,
            "id": "curious",
            "name": "Curious (Inquisitive Inspection)",
            "file": "05_curious.png",
            "dur": "4.5s",
            "intent": "Piqued interest in an object or sound; actively investigating something intriguing.",
            "behavior": "Gaze shifts decisively to the right and slightly upward (dx = +40.7 px, dy = -8.7 px). The right eye exhibits an asymmetric squint (o_R = 0.82) while the left eye stays wide open (o_L = 1.0). Layered with subtle 1.5 Hz micro-inspection drift and slight scale growth (1.04x).",
            "params": [
                ("Asymmetric Openness", "Left = 1.00 | Right = 0.82 (Squint)"),
                ("Gaze Vector (dx, dy)", "(+40.7 px, -8.7 px) + micro-drift"),
                ("Scale Multiplier", "1.04x (Slight attentive expansion)"),
                ("Micro-Inspection Motion", "3.5px sine drift at 1.5 Hz"),
                ("Resolution Easing", "Smooth cubic return to neutral")
            ]
        },
        {
            "num": 6,
            "id": "confused",
            "name": "Confused (Puzzled Alternating Scan)",
            "file": "06_confused.png",
            "dur": "4.5s",
            "intent": "Uncertainty or failure to comprehend a command; searching for clarification.",
            "behavior": "A hesitant, alternating two-phase scanning pattern. In Phase 1, eyes shift left (dx = -34 px) with left-eye squint (o_L = 0.82, o_R = 1.0). The gaze pauses, hesitates back toward center, then shifts puzzled to the right (dx = +38 px, dy = +8 px) with right-eye squint (o_L = 1.0, o_R = 0.82).",
            "params": [
                ("Alternating Asymmetry", "Phase 1: o_L=0.82, o_R=1.0 | Phase 2: o_L=1.0, o_R=0.82"),
                ("Gaze Pattern", "Left (-34 px) -> Hesitate Center -> Right (+38 px, +8 px)"),
                ("Scale Multiplier", "1.00x"),
                ("Phase 1 / Phase 2 Split", "u in [0.0, 0.40] / u in [0.40, 0.80]"),
                ("Psychological Cue", "Dynamic searching hesitation vs Curious steady focus")
            ]
        },
        {
            "num": 7,
            "id": "surprise",
            "name": "Surprise (Wide-Eyed Startle)",
            "file": "07_surprise.png",
            "dur": "3.5s",
            "intent": "Sudden unexpected discovery, loud noise, or dramatic revelation.",
            "behavior": "Rapid, clean scale burst from 1.00x up to 1.35x (+35% size) using fast quad_out easing. Eyes remain perfect circles centered at optical zero (0, 0) with completely steady, wide gaze during the peak hold, then smoothly settle back down.",
            "params": [
                ("Peak Scale Multiplier", "1.35x (Dramatic eye enlargement)"),
                ("Eye Openness", "1.00 / 1.00 (Perfect circles)"),
                ("Gaze Displacement", "(0.0 px, 0.0 px) - Motionless shocked stare"),
                ("Burst Time / Hold Time", "0.6s rise -> 1.7s hold -> 1.2s cubic settle"),
                ("Distinction from Scared", "Zero jitter tremor; pristine still circular expansion")
            ]
        },
        {
            "num": 8,
            "id": "excited",
            "name": "Excited (Energetic Bouncing & Pulsing)",
            "file": "08_excited.png",
            "dur": "4.5s",
            "intent": "High joy, successful task completion, enthusiastic celebration, and greeting.",
            "behavior": "Instant scale burst to 1.25x coupled with rapid, energetic vertical hopping at 3.2 Hz (amplitude up to -24 px). Bouncing is dynamically synchronized with harmonic scale pulsation (1.22x +/- 0.06x), producing a bouncy, jubilant celebration.",
            "params": [
                ("Base Scale Burst", "1.25x (1.22x average during bounce)"),
                ("Vertical Bounce Freq", "3.2 Hz high-frequency hop"),
                ("Bounce Amplitude", "Peak -24.0 px upward displacement"),
                ("Synchronous Scale Pulse", "+/-0.06x harmonic scale oscillation"),
                ("Distinction from Happy", "Enlarged scale (1.25x vs 1.0x) + faster hop rate (3.2 vs 2.2 Hz)")
            ]
        },
        {
            "num": 9,
            "id": "happy_bounce",
            "name": "Happy Bounce (Playful Decaying Hops)",
            "file": "09_happy_bounce.png",
            "dur": "4.5s",
            "intent": "Cheery satisfaction, playful contentment, pleasant acknowledgment.",
            "behavior": "Rhythmic, playful vertical hopping at 2.2 Hz with exponentially decaying amplitude (decay rate = 0.65). Eyes remain at standard scale (1.00x) and full circular openness (1.00), giving a lighter, gentler bounce than Excited.",
            "params": [
                ("Scale Multiplier", "1.00x (Standard baseline scale)"),
                ("Bounce Frequency", "2.2 Hz (Relaxed, joyful rhythm)"),
                ("Peak Hop Height", "-28.0 px vertical displacement"),
                ("Decay Function", "A * exp(-0.65 * t) * |sin(2*pi*2.2*t)|"),
                ("Openness", "1.00 / 1.00 (Full circles)")
            ]
        },
        {
            "num": 10,
            "id": "wink",
            "name": "Wink (Single Conspiratorial Wink)",
            "file": "10_wink.png",
            "dur": "3.5s",
            "intent": "Conspiratorial nod, cheeky humor, friendly acknowledgment, or shared joke.",
            "behavior": "Left eye remains wide open and alert (o_L = 1.0) while the right eye smoothly squashes down into a horizontal pill (o_R = 0.0) via cubic_in_out easing. The closed state holds for 1.4s before cleanly reopening via quad_out.",
            "params": [
                ("Left Eye Openness", "1.00 (Remains fully open)"),
                ("Right Eye Openness", "0.00 (Fully squashed horizontal pill)"),
                ("Gaze / Scale", "(0.0 px, 0.0 px) / 1.00x"),
                ("Close / Hold / Open Times", "0.75s close -> 1.40s hold -> 1.05s reopen"),
                ("Squash Width Multiplier", "1.12x on closed right eye")
            ]
        },
        {
            "num": 11,
            "id": "playful_double_wink",
            "name": "Playful Double Wink (Alternating Dual Winks)",
            "file": "11_playful_double_wink.png",
            "dur": "4.5s",
            "intent": "Extra cheeky charm, gameful interaction, rhythmic playful flair.",
            "behavior": "Choreographs two asymmetric winks in alternating succession: Sub-phase 1 winks the right eye (o_R = 0.0, o_L = 1.0) -> short neutral breath with both eyes open -> Sub-phase 2 winks the left eye (o_L = 0.0, o_R = 1.0) -> smooth return to neutral.",
            "params": [
                ("Sequence Structure", "Right Wink (0.05-0.42) -> Neutral (0.42-0.52) -> Left Wink (0.52-0.90)"),
                ("Wink 1 State", "o_L = 1.00, o_R = 0.00"),
                ("Wink 2 State", "o_L = 0.00, o_R = 1.00"),
                ("Scale / Gaze", "1.00x / (0.0 px, 0.0 px)"),
                ("Easing", "cubic_in_out closing / quad_out reopening")
            ]
        },
        {
            "num": 12,
            "id": "shy",
            "name": "Shy (Bashful Downward Glance & Blush)",
            "file": "12_shy.png",
            "dur": "4.5s",
            "intent": "Bashful modesty, receiving a compliment, flattered timidity.",
            "behavior": "Eyes glance bashfully down and away (dx = -22.6 px, dy = +26.7 px) with gentle eyelid droop (o = 0.65) and slightly contracted scale (0.97x). Soft pink cheek blush strokes fade in beneath both eyes at modest opacity (alpha = 70). At u = 0.65, ELO sneaks a timid upward peek before recovering.",
            "params": [
                ("Eyelid Droop", "o = 0.65 (Soft relaxed droop)"),
                ("Gaze Vector", "dx = -22.6 px, dy = +26.7 px (Down-left)"),
                ("Cheek Blush Opacity", "alpha = 70 / 255 (Subtle soft pink)"),
                ("Scale Multiplier", "0.97x (Modest contraction)"),
                ("Micro-Behavior", "Timid peek upward at u = 0.65")
            ]
        },
        {
            "num": 13,
            "id": "cute_blush",
            "name": "Cute / Blush (Full Warm Affection)",
            "file": "13_cute_blush.png",
            "dur": "5.0s",
            "intent": "Warm affection, extreme delight, flattered adoration, loving connection.",
            "behavior": "Soft pink rounded cheek strokes (48x12 px) illuminate beneath both eyes with full alpha opacity (alpha = 180). Eyes take on a relaxed, friendly posture (o = 0.92), gentle scale expansion (1.04x), and slight affectionate upward gaze tilt (dy = -5.0 px).",
            "params": [
                ("Blush Accent Opacity", "alpha = 180 / 255 (Full vibrant pink)"),
                ("Blush Capsule Dimensions", "48.0 px width x 12.0 px height"),
                ("Blush Position", "Y-offset +115.0 px beneath eye centers"),
                ("Eye Openness / Scale", "o = 0.92 (Soft) / Scale = 1.04x"),
                ("Alpha Envelope", "Smooth bell curve: 35% in -> 30% hold -> 35% out")
            ]
        },
        {
            "num": 14,
            "id": "thinking",
            "name": "Thinking (Contemplative Gaze Drift)",
            "file": "14_thinking.png",
            "dur": "5.0s",
            "intent": "Processing data, computing a response, recalling memory, pondering.",
            "behavior": "Eyes cast into a thoughtful upward-and-sideways gaze drift (dx = +23.3 px, dy = -33.6 px). Eyelids narrow into a deliberate contemplative half-squint (o = 0.40) while subtle harmonic drift (4.0 px sine at 0.4 Hz) suggests active cognitive calculation.",
            "params": [
                ("Eyelid Squint", "o = 0.40 (Deliberate half-squint)"),
                ("Gaze Vector", "dx = +23.3 px, dy = -33.6 px (Up-Right)"),
                ("Cognitive Micro-Drift", "4.0 px lateral sway at 0.4 Hz"),
                ("Scale Multiplier", "1.00x (Neutral)"),
                ("Distinction from Curious", "Upward drift (dy=-34 vs -10) + bilateral narrow (0.40 vs 1.0/0.82)")
            ]
        },
        {
            "num": 15,
            "id": "suspicious",
            "name": "Suspicious (Skeptical Side-Eye)",
            "file": "15_suspicious.png",
            "dur": "4.5s",
            "intent": "Doubt, skepticism, scrutinizing suspicious user behavior, side-eye scrutiny.",
            "behavior": "A deliberate, skeptical sideways displacement (dx = +50.0 px, dy = +5.0 px) casting a severe 'side-eye'. Eyelids narrow moderately to o = 0.48, holding the subject in unyielding, skeptical focus before resolving back to center.",
            "params": [
                ("Lateral Displacement", "dx = +50.0 px (Severe side-eye displacement)"),
                ("Vertical Bias", "dy = +5.0 px (Slight downward scrutiny)"),
                ("Eye Openness", "o = 0.48 (Moderate narrowing)"),
                ("Scale Multiplier", "1.00x (No scale collapse)"),
                ("Distinction from Angry", "Heavy lateral offset (dx=+50 vs 0) + moderate open (0.48 vs 0.30)")
            ]
        },
        {
            "num": 16,
            "id": "angry",
            "name": "Angry (Narrow Slits & Tension Pulse)",
            "file": "16_angry.png",
            "dur": "4.5s",
            "intent": "Displeasure, frustration, stern protest, refusal of unauthorized action.",
            "behavior": "Severe horizontal compression squashing both eyes into narrow, intense horizontal slits (o = 0.30). Scale deflates compactly to 0.94x with slight downward gaze lock (dy = +5.0 px). A high-frequency 5.0 Hz micro-pulsation runs through the eyelid tension during peak hold.",
            "params": [
                ("Slit Openness", "o = 0.30 (+/-0.02 tension oscillation)"),
                ("Scale Contraction", "0.94x (Compact, tense mass)"),
                ("Gaze Focus", "dx = 0.0 px, dy = +5.0 px (Locked forward glare)"),
                ("Tension Pulse Frequency", "5.0 Hz rapid eyelid tremor"),
                ("No Eyebrows Needed", "Expression achieved purely through squash, scale & tension")
            ]
        },
        {
            "num": 17,
            "id": "scared_nervous",
            "name": "Scared / Nervous (Elastic Startle & Tremor)",
            "file": "17_scared_nervous.png",
            "dur": "4.5s",
            "intent": "Fright, alarm, apprehension, sensory overload, nervous shock.",
            "behavior": "Eyes burst open into an enlarged scale of 1.28x using an elastic_out overshoot curve. Unlike the motionless shock of Surprise, Scared/Nervous superimposes high-frequency jitter tremors (14.0 Hz horizontal, 16.0 Hz vertical) simulating visceral shaking.",
            "params": [
                ("Enlarged Scale", "1.28x via elastic_out overshoot"),
                ("Openness", "1.00 / 1.00 (Wide open circles)"),
                ("Nervous Tremor Jitter", "dx: 2.5px @ 14 Hz | dy: 2.0px @ 16 Hz"),
                ("Tremor Fade", "Smooth fade-out across final 15% of segment"),
                ("Distinction from Surprise", "Active 14 Hz nervous jitter vs motionless clean stare")
            ]
        },
        {
            "num": 18,
            "id": "sad",
            "name": "Sad (Melancholic Droop & Downward Gaze)",
            "file": "18_sad.png",
            "dur": "5.0s",
            "intent": "Melancholy, disappointment, sorrow, low battery fatigue, sympathy.",
            "behavior": "Both eyes droop into heavy, flattened shapes (o = 0.52) while gaze drops deeply downward (dy = +34.0 px). Overall scale deflates to 0.94x and breathing rhythm slows sluggishly, conveying profound dejection and energy loss.",
            "params": [
                ("Melancholic Droop", "o = 0.52 (Heavy drooped capsules)"),
                ("Downward Gaze Vector", "dy = +34.0 px (Deep downward focus)"),
                ("Scale Deflation", "0.94x (Deflated, sorrowful presence)"),
                ("Horizontal Offset", "dx = 0.0 px (Straight downward gaze)"),
                ("Distinction from Shy", "Zero blush accent + deeper droop (0.52 vs 0.65) + deflated scale")
            ]
        },
        {
            "num": 19,
            "id": "drowsy",
            "name": "Drowsy (Sleepy Droop & Wobble)",
            "file": "19_drowsy.png",
            "dur": "5.0s",
            "intent": "Exhaustion, winding down, fading alertness, impending sleep.",
            "behavior": "Eyelids progressively droop down to a heavy half-closed state (o = 0.38). A gentle sleepy wobble (0.55 Hz) and subtle rhythmic head nod (dy +/- 5 px at 0.45 Hz) simulate fighting off sleep before smoothly settling at o = 0.38 to bridge seamlessly into Sleep.",
            "params": [
                ("Eyelid Droop Baseline", "o = 0.38 (Heavy half-closed capsules)"),
                ("Sleepy Wobble", "+/-0.025 openness oscillation at 0.55 Hz"),
                ("Head Nod Motion", "dy = +5.0 px at 0.45 Hz"),
                ("Scale Multiplier", "1.00x"),
                ("Transition Continuity", "Settles cleanly at o = 0.380 for zero-pop bridge into Sleep")
            ]
        },
        {
            "num": 20,
            "id": "sleep",
            "name": "Sleep (Deep Sleep & Floating Z Particles)",
            "file": "20_sleep.png",
            "dur": "9.0s",
            "intent": "Standby mode, power conservation, deep resting state, calm night mode.",
            "behavior": "Eyes glide smoothly from the 0.38 drowsy state down to completely closed horizontal stadium pills (o = 0.00). Floating 'Z' particles spawn near the right eye (x = 580-630 px) and drift upwards (42 px/s) with sinusoidal sway (15 px sway at 0.8 Hz). Breathing slows to a deep 5.5-second period.",
            "params": [
                ("Eye Openness", "0.00 / 0.00 (Completely closed stadium pills)"),
                ("Z Particle Spawn Rate", "Every 1.3 seconds (Lifespan = 2.8s)"),
                ("Z Rise Velocity / Sway", "42 px/s upward | 15 px sway at 0.8 Hz"),
                ("Deep Sleep Breathing", "Period = 5.5s (Amp = 0.012)"),
                ("Loop Rollover", "Particle spawning halts at 6.5s so screen clears cleanly before loop")
            ]
        }
    ]

    for em in emotions_data:
        add_styled_heading(doc, f"{em['num']}. {em['name']} ({em['dur']})", level=2, space_before=14, space_after=4)

        img_path = os.path.join(ASSET_DIR, em['file'])
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(2)
            p_img.paragraph_format.space_after = Pt(2)
            p_img.add_run().add_picture(img_path, width=Inches(4.8))

            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(0)
            p_cap.paragraph_format.space_after = Pt(6)
            run_cap = p_cap.add_run(f"Figure {em['num'] + 1}: Live V3 Render — {em['name']} (800x480 native resolution).")
            run_cap.font.size = Pt(8.5)
            run_cap.font.italic = True
            run_cap.font.color.rgb = COLOR_MUTED

        p_desc = doc.add_paragraph()
        p_desc.paragraph_format.space_before = Pt(0)
        p_desc.paragraph_format.space_after = Pt(4)

        r_int_lbl = p_desc.add_run("Emotion Intent: ")
        r_int_lbl.font.bold = True
        r_int_lbl.font.color.rgb = COLOR_NAVY
        r_int_txt = p_desc.add_run(f"{em['intent']}\n")
        r_int_txt.font.color.rgb = COLOR_SLATE

        r_beh_lbl = p_desc.add_run("Visual Mechanics: ")
        r_beh_lbl.font.bold = True
        r_beh_lbl.font.color.rgb = COLOR_NAVY
        r_beh_txt = p_desc.add_run(em['behavior'])
        r_beh_txt.font.color.rgb = COLOR_SLATE

        # Parameter Table for Emotion
        em_tbl = doc.add_table(rows=1, cols=2)
        em_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_col_w = [Inches(2.5), Inches(4.3)]
        format_table_header(em_tbl.rows[0], t_col_w, ["Implementation Parameter", "Finalized Value / Dynamic Behavior"])
        for idx, (p_name, p_val) in enumerate(em['params']):
            add_table_data_row(em_tbl, t_col_w, [p_name, p_val], is_even=(idx % 2 == 1), is_monospace=True)

        p_space = doc.add_paragraph()
        p_space.paragraph_format.space_before = Pt(4)
        p_space.paragraph_format.space_after = Pt(4)

    doc.add_page_break()

    # ---------------------------------------------------------------------------
    # SECTION 5: EMOTION COMPARISON & DIFFERENTIATION
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "5. Emotion Comparison & Pairwise Differentiation", level=1)

    p = doc.add_paragraph(
        "A critical engineering requirement of ELO Face V3 is preventing emotional ambiguity. "
        "Because the face operates without eyebrows, mouth, or pupils, nuanced emotional states that share "
        "similar geometric properties are rigorously differentiated through physical dynamics, scale, asymmetry, and accents."
    )

    pairs_data = [
        (
            "Surprise vs. Scared / Nervous",
            "Scale & Micro-Tremor Dynamics",
            "• Surprise scales up dramatically to 1.35x (+35%) and maintains a completely motionless, pristine circular gaze.\n"
            "• Scared/Nervous scales to 1.28x with an elastic overshoot and superimposes high-frequency jitter tremors (14.0 Hz X, 16.0 Hz Y).\n"
            "Key Distinction: Surprise is frozen shock; Scared is visceral, trembling terror."
        ),
        (
            "Happy Bounce vs. Excited",
            "Scale Multiplier & Hop Frequency",
            "• Happy Bounce hops at a relaxed 2.2 Hz cadence with exponentially decaying amplitude at standard scale (1.00x).\n"
            "• Excited maintains an enlarged scale (1.25x average) with rapid 3.2 Hz bouncing and synchronous harmonic scale pulsing.\n"
            "Key Distinction: Happy Bounce is gentle contentment; Excited is high-energy jubilation."
        ),
        (
            "Angry vs. Suspicious",
            "Squash Severity & Gaze Displacement",
            "• Angry squashes eyes into tight horizontal slits (o = 0.30), contracts scale to 0.94x, and glares forward with 5 Hz tension micro-pulsing.\n"
            "• Suspicious narrows moderately (o = 0.48) and casts a severe lateral displacement (+50 px) for skeptical side-eye.\n"
            "Key Distinction: Angry is direct forward confrontation; Suspicious is sideways lateral scrutiny."
        ),
        (
            "Shy vs. Sad",
            "Gaze Vector & Blush Accent",
            "• Shy glances down-and-away (dx = -22 px, dy = +28 px), droops eyelids to 0.65, and displays soft pink cheek blush (alpha = 70).\n"
            "• Sad looks straight down (dx = 0 px, dy = +34 px), droops deeper to 0.52, deflates scale to 0.94x, and has zero blush.\n"
            "Key Distinction: Shy is bashful warmth with pink blush; Sad is deflated sorrow with no blush."
        ),
        (
            "Curious vs. Confused vs. Thinking",
            "Asymmetry Patterns & Gaze Trajectories",
            "• Curious focuses steadily to the right (+41 px) with right-eye squint (o_R = 0.82) and inquisitive micro-inspection.\n"
            "• Confused hesitates left with left squint (o_L = 0.82), pauses, then scans right with right squint (o_R = 0.82).\n"
            "• Thinking drifts upward-right (dx = +23 px, dy = -34 px) with bilateral half-squint (o = 0.40) and cognitive sway.\n"
            "Key Distinction: Curious is single-target investigation; Confused is puzzled searching; Thinking is internal cognitive recall."
        ),
        (
            "Drowsy vs. Sad vs. Sleep",
            "Openness Level, Nodding & Particles",
            "• Drowsy holds eyes at half-closed (o = 0.38) with rhythmic sleepy wobble and head nods at normal scale (1.00x).\n"
            "• Sad droops to 0.52 with heavy downward gaze (+34 px), contracted scale (0.94x), and sluggish breathing.\n"
            "• Sleep closes eyes completely (o = 0.00) and spawns floating 'Z' particles drifting upward with sinusoidal sway.\n"
            "Key Distinction: Drowsy is fighting sleep; Sad is melancholic dejection; Sleep is full unconscious rest."
        )
    ]

    for title, subtitle, details in pairs_data:
        add_styled_heading(doc, title, level=2, space_before=10, space_after=2)
        add_callout_box(doc, text=details, title=f"DIFFERENTIATION FACTOR: {subtitle.upper()}", border_color=HEX_NAVY, fill_color=HEX_SLATE_ROW)

    add_styled_heading(doc, "Master Emotion Comparison Matrix", level=2)

    matrix_tbl = doc.add_table(rows=1, cols=6)
    matrix_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    m_widths = [Inches(1.5), Inches(1.0), Inches(1.1), Inches(0.9), Inches(1.1), Inches(1.2)]
    format_table_header(matrix_tbl.rows[0], m_widths, ["Emotion", "Openness (o)", "Gaze (dx, dy)", "Scale", "Blush / Acc", "Dynamic Motion"])

    matrix_rows = [
        ("Settle", "1.00 / 1.00", "(0, 0)", "1.00x", "None", "Breathing 4.0s"),
        ("Blink", "0.00 / 0.00", "(0, 0)", "1.00x", "None", "Dual 180ms blinks"),
        ("Look Horiz.", "1.00 / 1.00", "(-53..+53, 0)", "1.00x", "None", "Smooth sweep"),
        ("Look Vert.", "1.00 / 1.00", "(0, -34..+34)", "1.00x", "None", "Smooth sweep"),
        ("Curious", "1.00 / 0.82", "(+41, -9)", "1.04x", "None", "Micro-inspection"),
        ("Confused", "0.82 / 1.00*", "(-34..+38, +8)", "1.00x", "None", "Alternating scan"),
        ("Surprise", "1.00 / 1.00", "(0, 0)", "1.35x", "None", "Scale burst / still"),
        ("Excited", "1.00 / 1.00", "(0, -24)", "1.25x", "None", "3.2 Hz bounce + pulse"),
        ("Happy Bounce", "1.00 / 1.00", "(0, -28)", "1.00x", "None", "2.2 Hz decaying hops"),
        ("Wink", "1.00 / 0.00", "(0, 0)", "1.00x", "None", "Right eye squash"),
        ("Double Wink", "1.00/0 -> 0/1.0", "(0, 0)", "1.00x", "None", "Alternating winks"),
        ("Shy", "0.65 / 0.65", "(-23, +27)", "0.97x", "Alpha 70", "Bashful peek"),
        ("Cute Blush", "0.92 / 0.92", "(0, -5)", "1.04x", "Alpha 180", "Soft cheek glow"),
        ("Thinking", "0.40 / 0.40", "(+23, -34)", "1.00x", "None", "0.4 Hz cognitive drift"),
        ("Suspicious", "0.48 / 0.48", "(+50, +5)", "1.00x", "None", "Side-eye hold"),
        ("Angry", "0.30 / 0.30", "(0, +5)", "0.94x", "None", "5 Hz tension tremor"),
        ("Scared/Nervous", "1.00 / 1.00", "(jitter, jitter)", "1.28x", "None", "14 Hz nervous jitter"),
        ("Sad", "0.52 / 0.52", "(0, +34)", "0.94x", "None", "Heavy droop"),
        ("Drowsy", "0.38 / 0.38", "(0, nod)", "1.00x", "None", "Sleepy wobble & nod"),
        ("Sleep", "0.00 / 0.00", "(0, 0)", "1.00x", "Z Part.", "Floating Z drift (42px/s)")
    ]
    for idx, row_vals in enumerate(matrix_rows):
        add_table_data_row(matrix_tbl, m_widths, row_vals, is_even=(idx % 2 == 1), is_monospace=True)

    doc.add_page_break()

    # ---------------------------------------------------------------------------
    # SECTION 6: FULL 21-SEGMENT TIMELINE SCHEDULE
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "6. Full 103-Second Timeline Schedule", level=1)

    p = doc.add_paragraph(
        "The automated demonstration runs as a seamless 103.0-second continuous sequence composed of exactly 21 segments. "
        "Upon completing Segment 21 (Sleep), the timeline seamlessly rolls over back to Segment 1 with zero parameter pop."
    )

    tl_tbl = doc.add_table(rows=1, cols=6)
    tl_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tl_widths = [Inches(0.4), Inches(1.5), Inches(0.8), Inches(1.0), Inches(1.3), Inches(1.8)]
    format_table_header(tl_tbl.rows[0], tl_widths, ["#", "Segment Name", "Dur (s)", "Cumulative", "Key State Parameters", "Visual & Easing Mechanics"])

    timeline_schedule = [
        (1, "intro", 10.0, "0.0s - 10.0s", "Text Alpha 1.0 -> 0.0", "Typewriter 'Hii' -> 'This is ELO.' -> Face Fade"),
        (2, "settle", 3.5, "10.0s - 13.5s", "o=1.0, look=(0,0), s=1.0", "Neutral baseline settle with 4.0s breathing"),
        (3, "blink", 3.5, "13.5s - 17.0s", "o: 1.0 -> 0.0 -> 1.0", "Two natural squash blinks (180ms duration)"),
        (4, "look_horizontal", 5.0, "17.0s - 22.0s", "dx: 0 -> -53 -> +53 -> 0", "Center -> Left -> Right -> Center scan"),
        (5, "look_vertical", 4.5, "22.0s - 26.5s", "dy: 0 -> -34 -> +34 -> 0", "Center -> Up -> Down -> Center scan"),
        (6, "curious", 4.5, "26.5s - 31.0s", "oL=1.0, oR=0.82, dx=+41", "Inquisitive glance with asymmetric squint"),
        (7, "confused", 4.5, "31.0s - 35.5s", "oL=0.82 -> oR=0.82", "Hesitant left-right alternating puzzled scan"),
        (8, "surprise", 3.5, "35.5s - 39.0s", "s=1.35x, o=1.0, dx=0", "Rapid scale burst to 1.35x with still gaze"),
        (9, "excited", 4.5, "39.0s - 43.5s", "s=1.25x, 3.2Hz bounce", "High-energy scale burst + vertical hopping"),
        (10, "happy_bounce", 4.5, "43.5s - 48.0s", "s=1.00x, 2.2Hz hop", "Rhythmic hopping with decaying amplitude"),
        (11, "wink", 3.5, "48.0s - 51.5s", "oL=1.0, oR=0.0", "Right eye squashes closed -> hold -> reopen"),
        (12, "playful_double_wink", 4.5, "51.5s - 56.0s", "Right Wink -> Left Wink", "Alternating dual winks with neutral bridge"),
        (13, "shy", 4.5, "56.0s - 60.5s", "o=0.65, Blush alpha 70", "Downward glance with subtle pink blush"),
        (14, "cute_blush", 5.0, "60.5s - 65.5s", "o=0.92, Blush alpha 180", "Soft pink rounded cheek strokes illuminate"),
        (15, "thinking", 5.0, "65.5s - 70.5s", "o=0.40, dx=+23, dy=-34", "Upward-right contemplative drift and squint"),
        (16, "suspicious", 4.5, "70.5s - 75.0s", "o=0.48, dx=+50, dy=+5", "Skeptical side-eye with lateral displacement"),
        (17, "angry", 4.5, "75.0s - 79.5s", "o=0.30, s=0.94x, 5Hz pulse", "Tight horizontal slits with tension tremor"),
        (18, "scared_nervous", 4.5, "79.5s - 84.0s", "s=1.28x, 14Hz jitter", "Elastic scale burst with high-frequency tremor"),
        (19, "sad", 5.0, "84.0s - 89.0s", "o=0.52, dy=+34, s=0.94x", "Melancholic droop and deep downward gaze"),
        (20, "drowsy", 5.0, "89.0s - 94.0s", "o=0.38, sleepy nod", "Eyelids droop half-closed with sleepy wobble"),
        (21, "sleep", 9.0, "94.0s - 103.0s", "o=0.00, Floating Zs", "Closed eyes with floating drifting Z particles")
    ]

    for row in timeline_schedule:
        idx, name, dur, cum, params, desc = row
        add_table_data_row(tl_tbl, tl_widths, [str(idx), name, f"{dur:.1f}s", cum, params, desc], is_even=(idx % 2 == 1), is_monospace=True)

    p_tot = doc.add_paragraph()
    p_tot.paragraph_format.space_before = Pt(8)
    run_tot = p_tot.add_run("TOTAL TIMELINE DURATION: EXACTLY 103.0 SECONDS (6,180 FRAMES @ 60 FPS)")
    run_tot.font.bold = True
    run_tot.font.size = Pt(11)
    run_tot.font.color.rgb = COLOR_ROSE

    doc.add_page_break()

    # ---------------------------------------------------------------------------
    # SECTION 7: VISUAL DESIGN RULES & MATHEMATICAL PRINCIPLES
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "7. Visual Design Rules & Mathematical Principles", level=1)

    p = doc.add_paragraph(
        "ELO Face V3 adheres to seven immutable design principles that guarantee visual consistency, "
        "render efficiency, and mathematical elegance across all platforms:"
    )

    rules = [
        ("1. Single Continuous Stadium Shape:", "Each eye is mathematically defined as a single stadium capsule (a rectangle capped with two semicircles). At openness o = 1.0, width equals height and corner radius equals half-width, creating a geometrically perfect circle. As o approaches 0.0, height compresses down to 6% baseline while corner radius automatically tracks height / 2, maintaining perfectly rounded ends with zero corner artifacting."),
        ("2. Horizontal Width Expansion (+12%):", "To simulate organic volume conservation during blink squashing, the horizontal width expands dynamically by up to +12% as the eye closes: Width = 2 * R * s * (1.0 + (1.0 - o) * 0.12). This prevents the closed eye from looking tiny and gives the blink a satisfying mechanical weight."),
        ("3. Gaze via Rigid Center Translation:", "Gaze displacement (dx, dy) translates the entire eye geometry rigidly on the 800x480 canvas. No internal pupils or irises exist. Max travel is capped at +/-65 px horizontally and +/-45 px vertically to prevent eyes from colliding or exceeding bezel margins."),
        ("4. Strict 3-Tone Palette:", "The visual system uses strictly three tones: Pure Black background RGB(0,0,0), Solid White eyes RGB(255,255,255), and Soft Warm Pink RGB(255,160,185) for blush and signature intro accents. No grey shades or colored gradients are permitted."),
        ("5. Framerate-Agnostic Exponential Decay:", "All target parameter smoothing uses exact analytical exponential decay: val = target + (val - target) * exp(-lambda * dt). This ensures that animation velocities and damping curves are 100% identical whether rendering at 30 FPS, 60 FPS, or 120 FPS."),
        ("6. Zero-Pop State Boundary Guarantees:", "Every emotion handler is mathematically designed so that its ending boundary matches baseline neutral or seamlessly matches the initial state of the next segment (e.g. Drowsy ends at o=0.380 and Sleep begins at o=0.380). Transient states like blush alpha and sleep particles auto-reset upon segment exit."),
        ("7. Complete Module Independence:", "The V3 codebase has zero imports, dependencies, or couplings to legacy V2/V1 systems. It is entirely self-contained within experiment-3/.")
    ]
    for r_title, r_desc in rules:
        p_r = doc.add_paragraph()
        p_r.paragraph_format.space_before = Pt(2)
        p_r.paragraph_format.space_after = Pt(4)
        r_t = p_r.add_run(f"{r_title}\n")
        r_t.font.bold = True
        r_t.font.color.rgb = COLOR_NAVY
        r_d = p_r.add_run(r_desc)
        r_d.font.color.rgb = COLOR_SLATE

    # ---------------------------------------------------------------------------
    # SECTION 8: HARDWARE HANDOFF NOTE
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "8. Software Handoff & Architecture Scope", level=1, space_before=16)

    add_callout_box(
        doc,
        title="SOFTWARE ARCHITECTURE SCOPE NOTICE",
        text="This document covers the SOFTWARE ANIMATION ENGINE ONLY.\n\n"
             "• The animation engine is fully implemented, verified, and locked in Python/Pygame.\n"
             "• It outputs native 800x480 frames at 60 FPS to any standard Pygame/SDL2 display surface.\n"
             "• Hardware deployment (Raspberry Pi 5 DSI ribbon integration, HDMI displays, Waveshare LCDs, "
             "ESP32 coprocessors, or serial command bridges) is decoupled from animation logic and should be handled downstream.\n"
             "• The engine supports headless off-screen execution via SDL_VIDEODRIVER=dummy for background simulation and testing.",
        border_color=HEX_NAVY,
        fill_color=HEX_SLATE_LIGHT
    )

    # ---------------------------------------------------------------------------
    # SECTION 9: FINAL STATUS & VERIFICATION
    # ---------------------------------------------------------------------------
    add_styled_heading(doc, "9. Final Verification & Locked Status", level=1, space_before=16)

    p = doc.add_paragraph(
        "ELO Face V3 has completed rigorous automated testing and full-duration simulation. "
        "The software implementation is officially declared FINAL, VERIFIED, and LOCKED."
    )

    verif_tbl = doc.add_table(rows=1, cols=3)
    verif_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    v_widths = [Inches(2.2), Inches(1.8), Inches(2.8)]
    format_table_header(verif_tbl.rows[0], v_widths, ["Verification Check", "Result", "Technical Details"])

    verif_rows = [
        ("Automated Test Suite", "64 / 64 PASS (100%)", "Configuration, isolation, math curves, pairwise distinctions."),
        ("Full Loop Simulation", "6,180 Frames PASS", "103.0s continuous 60 FPS headless simulation run."),
        ("Headless Throughput", "3,019 FPS", "Ultra-fast headless simulation execution (2.05s total)."),
        ("Module Isolation", "100% Verified", "Zero imports or runtime couplings to experiment-2 or V2."),
        ("Baseline Git Commit", "5bdabea", "Finalized V3 foundation commit."),
        ("Git Branch", "worktree-experiment-3-foundation", "Dedicated foundation worktree branch."),
        ("Production Status", "FINAL & LOCKED", "Ready for deployment and downstream integration.")
    ]
    for idx, (check, res, det) in enumerate(verif_rows):
        add_table_data_row(verif_tbl, v_widths, [check, res, det], is_even=(idx % 2 == 1), is_monospace=True)

    p_end = doc.add_paragraph()
    p_end.paragraph_format.space_before = Pt(14)
    p_end.paragraph_format.space_after = Pt(4)
    p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_end = p_end.add_run("— END OF SPECIFICATION —\nELO FACE V3 IS LOCKED AND READY FOR USE")
    run_end.font.bold = True
    run_end.font.size = Pt(11)
    run_end.font.color.rgb = COLOR_ROSE

    # Save document
    doc.save(OUTPUT_DOCX)
    print(f"Document successfully created and saved to: {OUTPUT_DOCX}")
    return OUTPUT_DOCX


if __name__ == "__main__":
    build_document()
