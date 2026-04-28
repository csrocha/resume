#!/usr/bin/env python3
"""Generate a targeted CV in LaTeX from the Spanish source sections using Gemini."""

import argparse
import subprocess
import sys
from pathlib import Path

from google import genai
from google.genai import types

REPO_DIR = Path(__file__).parent

SECTION_FILES = [
    "sec_resumen.tex",
    "sec_habilidades.tex",
    "sec_profesionales.tex",
    "sec_cientificos.tex",
    "sec_congresos.tex",
    "sec_publicaciones.tex",
    "sec_tesis.tex",
    "sec_extension.tex",
    "sec_docentes.tex",
    "sec_titulos.tex",
]

PREAMBLE = {
    "es": r"""\documentclass[9pt,a4paper,sans]{moderncv}
\moderncvstyle{casual}
\moderncvcolor{blue}
\usepackage[scale=0.75]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8x]{inputenc}
\usepackage[spanish]{babel}
\usepackage{bibunits}
\usepackage{xcolor}

\newcommand{\Q}{{\textsf{Q}\hspace*{-1.1ex}%
  \rule{0.15ex}{1.5ex}\hspace*{1.1ex}}}
\newcommand{\Cuat}{º\Q~}
\newcommand{\actual}{$\infty$}
\newcommand{\vat}{CUIT}
\newcommand{\birthdate}{Fecha de Nacimiento}

\firstname{Cristian Sebastian}
\familyname{Rocha}
\title{Curriculum Vitae}
\address{Lavalle 2294 2°}{Villa Ballester, Gral. San Martin, Buenos Aires (1653)}
\phone[mobile]{(+54-911)~6800~0269}
\email{csrocha@gmail.com}
\homepage{https://github.com/csrocha}
\extrainfo{\vat 23-25095454-9 - \birthdate: 4 dic 1975}
""",
    "en": r"""\documentclass[9pt,a4paper,sans]{moderncv}
\moderncvstyle{casual}
\moderncvcolor{blue}
\usepackage[scale=0.75]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8x]{inputenc}
\usepackage{xcolor}

\newcommand{\actual}{$\infty$}

\firstname{Cristian Sebastian}
\familyname{Rocha}
\title{Curriculum Vitae}
\address{Lavalle 2294}{Villa Ballester, Buenos Aires, Argentina (1653)}
\phone[mobile]{(+54-911)~6800~0269}
\email{csrocha@gmail.com}
\homepage{https://github.com/csrocha}
""",
}

SYSTEM_PROMPT = """You are an expert CV writer specializing in LaTeX with the moderncv package.
You receive the full source CV in Spanish (using moderncv LaTeX commands) and a target job profile.
Your task: generate tailored CV body content in LaTeX, optimized for the target.

Output rules:
- Output ONLY body content — no \\documentclass, no preamble, no \\begin{document} or \\end{document}
- Use standard moderncv commands: \\section, \\cventry, \\cvitem, \\cvlistitem, \\cvlistdoubleitem
- \\cventry syntax: \\cventry{dates}{title}{organization}{location}{grade/subtitle}{description}
- Descriptions inside \\cventry can use \\begin{description}...\\end{description} with \\item[label] content
- Select and order sections to best match the target profile (most relevant first)
- Trim or omit entries that add no value for this target
- Rewrite descriptions to emphasize achievements relevant to the target
- Keep descriptions concise and impactful — bullet points over long prose
- Generate all output in the requested language (translate from Spanish if needed)
- Do not include \\input{} commands — embed all content directly
- Do not include bibliography/publications sections unless the target is academic"""


def load_source() -> str:
    parts = []
    for filename in SECTION_FILES:
        path = REPO_DIR / filename
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                parts.append(f"% === {filename} ===\n{content}")
    return "\n\n".join(parts)


def generate_body(source: str, target: str, lang: str) -> str:
    client = genai.Client()
    lang_name = "Spanish" if lang == "es" else "English"

    response = client.models.generate_content(
        model="models/gemini-flash-latest",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=4096,
            temperature=0.3,
        ),
        contents=(
            f"Source CV (Spanish, moderncv LaTeX):\n\n{source}\n\n"
            f"---\n\n"
            f"Target profile: {target}\n\n"
            f"Generate the tailored CV body in {lang_name}. "
            "Output only LaTeX body content — no preamble."
        ),
    )

    return response.text


def assemble_tex(body: str, lang: str) -> str:
    preamble = PREAMBLE[lang]
    return f"{preamble}\n\\begin{{document}}\n\\makecvtitle\n\n{body}\n\n\\end{{document}}\n"


def compile_pdf(tex_file: Path) -> None:
    for _ in range(2):  # two passes for correct layout
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_file.name],
            cwd=tex_file.parent,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout[-3000:], file=sys.stderr)
            print("pdflatex failed — check the .log file for details.", file=sys.stderr)
            sys.exit(1)
    print(f"PDF: {tex_file.with_suffix('.pdf')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a targeted CV from the Spanish source sections."
    )
    parser.add_argument("--target", required=True, help="Target job profile (free text)")
    parser.add_argument("--lang", choices=["es", "en"], default="en", help="Output language")
    parser.add_argument(
        "--output", default="cv_output", help="Output base name (no extension)"
    )
    parser.add_argument("--pdf", action="store_true", help="Compile to PDF with pdflatex")
    args = parser.parse_args()

    print("Loading source sections...")
    source = load_source()

    print("Generating tailored CV body with Gemini...")
    body = generate_body(source, args.target, args.lang)

    tex_path = REPO_DIR / f"{args.output}.tex"
    tex_path.write_text(assemble_tex(body, args.lang), encoding="utf-8")
    print(f"LaTeX: {tex_path}")

    if args.pdf:
        print("Compiling PDF...")
        compile_pdf(tex_path)


if __name__ == "__main__":
    main()
