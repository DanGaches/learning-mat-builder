# Learning Mat Builder

A local Python/Streamlit program for creating printable revision learning mats.

## Main features

- Choose A4 or A3.
- Choose portrait or landscape.
- Create between 1 and 12 sections.
- Set a different number of questions in every section.
- Select how much writing space each section needs.
- Add writing lines.
- Upload PNG, JPG, WEBP or PDF exam questions and diagrams.
- Automatically choose a balanced grid.
- Automatically wrap and reduce text where needed.
- Receive warnings when a section is too crowded.
- Export as a high-resolution PNG or printable PDF.

## Install

1. Install Python 3.10 or newer.
2. Open Terminal, Command Prompt or PowerShell in this folder.
3. Run:

```bash
python -m pip install -r requirements.txt
```

## Start the program

```bash
python -m streamlit run app.py
```

A browser window should open automatically. If it does not, copy the local address shown in the terminal, normally:

```text
http://localhost:8501
```

## Using exam questions

Upload a screenshot/image or a PDF inside the relevant section. For a PDF, the first page is inserted. Crop the source first when you only need one question from a full exam paper.

## Getting the best-sized student writing spaces

- Use the **Writing space** control in each section.
- Choose A3 for mats with many sections or long exam questions.
- Split a crowded topic across two sections rather than allowing very small text.
- Keep the **Smallest allowed size** at about 18–20 for most classroom printing.
- The on-screen warning identifies sections that need adjusting.

## Files

- `app.py` — the complete program.
- `requirements.txt` — packages needed to run it.
