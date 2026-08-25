#!/usr/bin/env python3
"""Generate a targeted CV in LaTeX from the Spanish source sections using Gemini."""

import argparse
import subprocess
import sys
from datetime import datetime
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


def build_prompt(source: str, target: str, lang: str, max_tokens: int) -> str:
    lang_name = "Spanish" if lang == "es" else "English"
    return (
        f"Source CV (Spanish, moderncv LaTeX):\n\n{source}\n\n"
        f"---\n\n"
        f"Target profile:\n\n{target}\n\n"
        f"Generate the tailored CV body in {lang_name}. "
        "Output only LaTeX body content — no preamble. "
        f"Your response must not exceed {int(max_tokens * 0.75)} words — stay within this limit to avoid truncation."
    )


def generate_body(source: str, target: str, lang: str, max_tokens: int = 8192, model: str = "models/gemini-2.5-flash") -> str:
    client = genai.Client()
    contents = build_prompt(source, target, lang, max_tokens)

    print(f"  Prompt assembled ({len(contents)} chars, max {max_tokens} tokens)")
    print(f"  Sending request to {model}...")

    chunks = []
    char_count = 0

    for chunk in client.models.generate_content_stream(
        model=model,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=max_tokens,
            temperature=0.3,
        ),
        contents=contents,
    ):
        if chunk.text:
            chunks.append(chunk.text)
            char_count += len(chunk.text)
            print(f"\r  Receiving... {char_count} chars", end="", flush=True)

    print(f"\r  Done. {char_count} chars received.          ")
    return "".join(chunks)


def assemble_tex(body: str, lang: str, target: str, run_at: datetime) -> str:
    preamble = PREAMBLE[lang]
    target_summary = target.replace("\n", " ").strip()
    header = (
        f"% Generated: {run_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"% Language:  {lang}\n"
        f"% Target:    {target_summary}\n"
    )
    return f"{header}\n{preamble}\n\\begin{{document}}\n\\makecvtitle\n\n{body}\n\n\\end{{document}}\n"


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
    parser.add_argument(
        "--target",
        required=True,
        help="Target job profile: free text, a file path, or '-' to read from stdin",
    )
    parser.add_argument("--lang", choices=["es", "en"], default="en", help="Output language")
    parser.add_argument(
        "--output", default="cv_output", help="Output base name (no extension)"
    )
    parser.add_argument("--pdf", action="store_true", help="Compile to PDF with pdflatex")
    parser.add_argument("--prompt-only", action="store_true", help="Write the full prompt to a .txt file without calling Gemini")
    parser.add_argument("--max-tokens", type=int, default=8192, help="Max output tokens for Gemini (default: 8192)")
    parser.add_argument(
        "--model",
        default="models/gemini-2.5-flash",
        help="Gemini model to use (default: models/gemini-2.5-flash). "
             "Other options: models/gemini-2.5-pro, models/gemini-2.0-flash, models/gemini-flash-latest",
    )
    args = parser.parse_args()

    target_text = args.target
    if args.target == "-":
        target_text = sys.stdin.read()
    else:
        target_path = Path(args.target)
        if target_path.exists():
            target_text = target_path.read_text(encoding="utf-8")

    print("Loading source sections...")
    source = load_source()

    if args.prompt_only:
        prompt = build_prompt(source, target_text, args.lang, args.max_tokens)
        prompt_path = REPO_DIR / f"{args.output}_prompt.txt"
        prompt_path.write_text(
            f"=== SYSTEM PROMPT ===\n{SYSTEM_PROMPT}\n\n=== USER PROMPT ===\n{prompt}\n",
            encoding="utf-8",
        )
        print(f"Prompt written to: {prompt_path}")
        return

    print("Generating tailored CV body with Gemini...")
    body = generate_body(source, target_text, args.lang, args.max_tokens, args.model)

    tex_path = REPO_DIR / f"{args.output}.tex"
    tex_path.write_text(assemble_tex(body, args.lang, target_text, datetime.now()), encoding="utf-8")
    print(f"LaTeX: {tex_path}")

    if args.pdf:
        print("Compiling PDF...")
        compile_pdf(tex_path)


if __name__ == "__main__":
    main()
