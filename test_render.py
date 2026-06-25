from app import Section, render_learning_mat

sections = [
    Section(
        title="Sample Section",
        questions=["Describe the diagram."],
        space_weight=3,
        lined_space=True,
    )
]

result, warnings = render_learning_mat(
    title="Test Mat (no images)",
    subtitle="",
    sections=sections,
    page_size="A4",
    orientation="Landscape",
    name_class_boxes=False,
    preferred_font_size=27,
    minimum_font_size=14,
)
result.save("out_no_image.png")

print("Rendered out_no_image.png")
