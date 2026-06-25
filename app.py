
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Optional

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Learning Mat Builder", layout="wide")


# -----------------------------
# Data models and page settings
# -----------------------------
@dataclass
class Section:
    title: str
    questions: list[str]
    space_weight: int
    lined_space: bool


PAGE_MM = {
    "A4": (210, 297),
    "A3": (297, 420),
}

# 150 DPI gives clear printing without making previews excessively large.
DPI = 150
MM_TO_PX = DPI / 25.4


def page_pixels(page_size: str, orientation: str) -> tuple[int, int]:
    width_mm, height_mm = PAGE_MM[page_size]
    if orientation == "Landscape":
        width_mm, height_mm = height_mm, width_mm
    return round(width_mm * MM_TO_PX), round(height_mm * MM_TO_PX)


# -----------------------------
# Font and text helpers
# -----------------------------
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/Library/Fonts/Arial Bold.ttf",
         "C:/Windows/Fonts/arialbd.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/Library/Fonts/Arial.ttf",
         "C:/Windows/Fonts/arial.ttf"]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Wrap text by measured pixel width, preserving deliberate paragraph breaks."""
    output: list[str] = []
    paragraphs = text.splitlines() or [""]
    for paragraph in paragraphs:
        if not paragraph.strip():
            output.append("")
            continue
        words = paragraph.split()
        line = words[0]
        for word in words[1:]:
            test = f"{line} {word}"
            if text_width(draw, test, font) <= max_width:
                line = test
            else:
                output.append(line)
                line = word
        output.append(line)
    return output


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    lines: list[str],
    font: ImageFont.ImageFont,
    fill: str,
    line_height: int,
) -> int:
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y





# -----------------------------
# Layout engine
# -----------------------------
def choose_columns(section_count: int, page_width: int, page_height: int) -> int:
    """Choose a balanced grid that avoids extremely narrow or shallow boxes."""
    best_cols = 1
    best_score = float("inf")

    for cols in range(1, min(4, section_count) + 1):
        rows = math.ceil(section_count / cols)
        cell_w = page_width / cols
        cell_h = page_height / rows

        # Aim for useful worksheet boxes rather than perfect squares.
        target_ratio = 1.25 if page_width > page_height else 0.9
        ratio = cell_w / cell_h
        empty_cells = cols * rows - section_count
        score = abs(math.log(max(ratio, 0.01) / target_ratio)) + empty_cells * 0.12

        # Strongly penalise boxes that would be too narrow.
        if cell_w < 500:
            score += 3
        if cell_h < 350:
            score += 2

        if score < best_score:
            best_score = score
            best_cols = cols

    return best_cols


def calculate_boxes(
    sections: list[Section],
    page_w: int,
    page_h: int,
    margin: int,
    header_h: int,
    gap: int,
) -> list[tuple[int, int, int, int]]:
    count = len(sections)
    cols = choose_columns(count, page_w - 2 * margin, page_h - header_h - 2 * margin)
    rows = math.ceil(count / cols)

    usable_w = page_w - 2 * margin - gap * (cols - 1)
    col_w = usable_w / cols

    row_weights = []
    for row in range(rows):
        row_sections = sections[row * cols:(row + 1) * cols]
        # The largest requested answer-space setting controls that row's height.
        row_weights.append(max((s.space_weight for s in row_sections), default=1))

    usable_h = page_h - header_h - 2 * margin - gap * (rows - 1)
    total_weight = sum(row_weights)
    raw_heights = [usable_h * weight / total_weight for weight in row_weights]

    # Prevent one row becoming unusably small.
    min_h = min(360, usable_h / rows * 0.65)
    heights = [max(min_h, h) for h in raw_heights]
    scale = usable_h / sum(heights)
    heights = [h * scale for h in heights]

    boxes = []
    y = margin + header_h
    index = 0
    for row in range(rows):
        x = margin
        for col in range(cols):
            if index >= count:
                break
            w = round(col_w)
            h = round(heights[row])
            boxes.append((round(x), round(y), w, h))
            x += col_w + gap
            index += 1
        y += heights[row] + gap
    return boxes


def fit_section_font(
    draw: ImageDraw.ImageDraw,
    section: Section,
    content_width: int,
    text_height_available: int,
    preferred_size: int,
    minimum_size: int,
) -> tuple[int, list[list[str]], int]:
    """Reduce question font only as far as needed to fit the allocated text area."""
    for size in range(preferred_size, minimum_size - 1, -1):
        font = get_font(size)
        line_height = round(size * 1.3)
        wrapped_questions = []
        total_h = 0
        for number, question in enumerate(section.questions, start=1):
            wrapped = wrap_text(draw, f"{number}. {question}", font, content_width)
            wrapped_questions.append(wrapped)
            total_h += len(wrapped) * line_height + round(size * 0.55)
        if total_h <= text_height_available:
            return size, wrapped_questions, total_h

    font = get_font(minimum_size)
    line_height = round(minimum_size * 1.3)
    wrapped_questions = [
        wrap_text(draw, f"{number}. {question}", font, content_width)
        for number, question in enumerate(section.questions, start=1)
    ]
    total_h = sum(len(lines) * line_height + round(minimum_size * 0.55) for lines in wrapped_questions)
    return minimum_size, wrapped_questions, total_h


def render_learning_mat(
    title: str,
    subtitle: str,
    sections: list[Section],
    page_size: str,
    orientation: str,
    name_class_boxes: bool,
    preferred_font_size: int,
    minimum_font_size: int,
) -> tuple[Image.Image, list[str]]:
    page_w, page_h = page_pixels(page_size, orientation)
    image = Image.new("RGB", (page_w, page_h), "white")
    draw = ImageDraw.Draw(image)

    scale = page_w / 1754  # roughly A4 landscape at 150 DPI
    margin = max(35, round(45 * scale))
    gap = max(18, round(24 * scale))
    header_h = max(150, round(180 * scale))

    title_font = get_font(max(28, round(42 * scale)), bold=True)
    subtitle_font = get_font(max(16, round(23 * scale)))
    label_font = get_font(max(14, round(20 * scale)))
    title_h = draw.textbbox((0, 0), title, font=title_font)[3]

    draw.text((margin, margin), title, font=title_font, fill="#172033")
    subtitle_y = margin + title_h + round(8 * scale)
    if subtitle.strip():
        draw.text((margin, subtitle_y), subtitle, font=subtitle_font, fill="#4b5563")

    if name_class_boxes:
        box_w = round(230 * scale)
        box_h = round(48 * scale)
        right = page_w - margin
        top = margin
        for label in ("Name:", "Class:"):
            left = right - box_w
            draw.rounded_rectangle((left, top, right, top + box_h), radius=8, outline="#64748b", width=2)
            draw.text((left + 10, top + 10), label, font=label_font, fill="#334155")
            top += box_h + round(10 * scale)

    boxes = calculate_boxes(sections, page_w, page_h, margin, header_h, gap)
    warnings: list[str] = []

    palette = ["#eaf2ff", "#eefbf3", "#fff6e6", "#f5efff", "#e9fbfb", "#fff0f3"]

    for idx, (section, box) in enumerate(zip(sections, boxes)):
        x, y, w, h = box
        border = max(2, round(2 * scale))
        radius = max(10, round(14 * scale))
        inner = max(18, round(24 * scale))
        heading_h = max(54, round(68 * scale))

        draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius=radius,
            fill="white",
            outline="#334155",
            width=border,
        )
        draw.rounded_rectangle(
            (x, y, x + w, y + heading_h),
            radius=radius,
            fill=palette[idx % len(palette)],
            outline="#334155",
            width=border,
        )
        # Square off the bottom of the coloured header.
        draw.rectangle((x + border, y + heading_h - radius, x + w - border, y + heading_h), fill=palette[idx % len(palette)])

        heading_font = get_font(max(18, round(27 * scale)), bold=True)
        heading_lines = wrap_text(draw, section.title, heading_font, w - 2 * inner)
        heading_line_h = round(heading_font.size * 1.15) if hasattr(heading_font, "size") else 24
        max_heading_lines = 2
        heading_lines = heading_lines[:max_heading_lines]
        draw_wrapped(draw, (x + inner, y + round(13 * scale)), heading_lines, heading_font, "#172033", heading_line_h)

        content_x = x + inner
        content_y = y + heading_h + inner
        content_w = w - 2 * inner
        content_h = h - heading_h - 2 * inner

        # Images removed: no image rendering or space reservation occurs.

        # Reserve a meaningful proportion for student answers.
        requested_answer_ratio = {1: 0.28, 2: 0.40, 3: 0.52, 4: 0.62, 5: 0.70}[section.space_weight]
        answer_h = round(content_h * requested_answer_ratio)
        question_h_available = content_h - answer_h

        font_size, wrapped_questions, actual_question_h = fit_section_font(
            draw,
            section,
            content_w,
            question_h_available,
            preferred_font_size,
            minimum_font_size,
        )
        q_font = get_font(font_size)
        line_h = round(font_size * 1.3)

        if actual_question_h > question_h_available:
            # Questions cannot safely fit while preserving requested answer room.
            needed_extra = actual_question_h - question_h_available
            answer_h = max(round(70 * scale), answer_h - needed_extra)
            question_h_available = content_h - answer_h
            warnings.append(
                f'"{section.title}" is crowded. Reduce its questions, increase its space setting, '
                "use a larger page, or split it into another section."
            )

        q_y = content_y
        for lines in wrapped_questions:
            q_y = draw_wrapped(draw, (content_x, q_y), lines, q_font, "#111827", line_h)
            q_y += round(font_size * 0.55)

        answer_top = max(q_y + round(8 * scale), content_y + question_h_available)
        answer_bottom = y + h - inner

        if answer_bottom - answer_top < round(60 * scale):
            warnings.append(
                f'"{section.title}" has very little writing space. A3, fewer questions, '
                "or an extra section would improve it."
            )

        if section.lined_space and answer_bottom > answer_top:
            line_gap = max(round(38 * scale), round(font_size * 1.7))
            line_y = answer_top + line_gap
            while line_y < answer_bottom:
                draw.line((content_x, line_y, content_x + content_w, line_y), fill="#cbd5e1", width=1)
                line_y += line_gap

    return image, warnings


def image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", dpi=(DPI, DPI), optimize=True)
    return buffer.getvalue()


def image_to_pdf_bytes(image: Image.Image, page_size: str, orientation: str) -> bytes:
    # Pillow writes physical dimensions from DPI. The image was created at the
    # correct A4/A3 aspect ratio and pixel dimensions.
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PDF", resolution=DPI)
    return buffer.getvalue()


# -----------------------------
# Streamlit interface
# -----------------------------
if __name__ == "__main__":
    st.title("Learning Mat Builder")
    st.caption("Build printable revision mats with questions, writing space, diagrams and exam-question images.")

    with st.sidebar:
        st.header("Page setup")
        mat_title = st.text_input("Learning mat title", "Revision Learning Mat")
        subtitle = st.text_input("Subtitle", "Use your notes and answer every question.")
        page_size = st.selectbox("Paper size", ["A4", "A3"])
        orientation = st.radio("Orientation", ["Landscape", "Portrait"], horizontal=True)
        section_count = st.number_input("Number of sections", min_value=1, max_value=12, value=4, step=1)
        name_class_boxes = st.checkbox("Include Name and Class boxes", value=True)

        st.divider()
        st.subheader("Text sizing")
        preferred_font_size = st.slider("Preferred question size", 18, 100, 27)
        minimum_font_size = st.slider("Smallest allowed size", 14, preferred_font_size, min(20, preferred_font_size))
        st.caption("The app reduces text only when needed and warns when a section is too crowded.")

    sections: list[Section] = []

    st.subheader("Sections")
    for i in range(int(section_count)):
        with st.expander(f"Section {i + 1}", expanded=(i == 0)):
            title = st.text_input("Section heading", f"Topic {i + 1}", key=f"title_{i}")
            question_count = st.number_input(
                "Number of questions",
                min_value=1,
                max_value=15,
                value=3,
                step=1,
                key=f"count_{i}",
            )

            questions = []
            for q in range(int(question_count)):
                questions.append(
                    st.text_area(
                        f"Question {q + 1}",
                        value="",
                        height=70,
                        placeholder="Type the question here...",
                        key=f"question_{i}_{q}",
                    ).strip()
                )
            questions = [q for q in questions if q] or ["Add your question here."]

            c1, c2 = st.columns(2)
            with c1:
                space_weight = st.select_slider(
                    "Writing space",
                    options=[1, 2, 3, 4, 5],
                    value=3,
                    format_func=lambda n: {
                        1: "Small",
                        2: "Medium-small",
                        3: "Medium",
                        4: "Large",
                        5: "Very large",
                    }[n],
                    key=f"space_{i}",
                )
                lined_space = st.checkbox("Add writing lines", value=True, key=f"lines_{i}")

            with c2:
                st.write("No image support: images have been removed from this version.")
            sections.append(
                Section(
                    title=title.strip() or f"Topic {i + 1}",
                    questions=questions,
                    space_weight=int(space_weight),
                    lined_space=lined_space,
                )
            )

    st.divider()

    try:
        result, warnings = render_learning_mat(
            title=mat_title.strip() or "Revision Learning Mat",
            subtitle=subtitle,
            sections=sections,
            page_size=page_size,
            orientation=orientation,
            name_class_boxes=name_class_boxes,
            preferred_font_size=preferred_font_size,
            minimum_font_size=minimum_font_size,
        )

        st.subheader("Preview")
        preview = result.copy()
        preview.thumbnail((1400, 1400))
        st.image(preview, use_container_width=True)

        if warnings:
            st.warning("\n\n".join(dict.fromkeys(warnings)))
        else:
            st.success("The content fits while keeping the requested writing space.")

        png_data = image_to_png_bytes(result)
        pdf_data = image_to_pdf_bytes(result, page_size, orientation)

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Download PNG",
                data=png_data,
                file_name="learning_mat.png",
                mime="image/png",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Download printable PDF",
                data=pdf_data,
                file_name="learning_mat.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    except Exception as exc:
        st.error(f"The learning mat could not be generated: {exc}")
        st.exception(exc)
