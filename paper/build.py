"""Build paper/paper.pdf from paper/paper.md (Markdown -> HTML -> PDF with headless Chrome).

Run:  .venv/bin/python paper/build.py
"""
import subprocess
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CSS = """
@page { size: A4; margin: 13mm 16mm 13mm 16mm; }
body { font-family: Charter, "Bitstream Charter", Georgia, serif; font-size: 9.4pt; line-height: 1.33; color: #0b0b0b; }
h1 { font-size: 20pt; margin: 0 0 2pt; letter-spacing: -0.2pt; }
.subtitle { font-size: 11pt; color: #52514e; margin: 0 0 2pt; }
.byline { font-size: 9pt; color: #52514e; margin: 0 0 8pt; }
h2 { font-size: 12pt; margin: 11pt 0 4pt; padding-bottom: 2pt; border-bottom: 0.6pt solid #d9d7d0; break-after: avoid; }
h3 { font-size: 10.2pt; margin: 8pt 0 3pt; break-after: avoid; }
p { margin: 0 0 5pt; }
ul { margin: 0 0 5pt; padding-left: 15pt; }
li { margin-bottom: 1.5pt; }
li > ul { margin: 1.5pt 0 0; }
.summary { background: #f3f2ee; border-left: 3pt solid #2a78d6; padding: 7pt 10pt 4pt; margin: 0 0 8pt; }
figure { margin: 6pt 0 8pt; break-inside: avoid; }
figure img { width: 100%; display: block; }
figure.w80 { width: 80%; margin-left: auto; margin-right: auto; }
figure.w88 { width: 88%; margin-left: auto; margin-right: auto; }
figure.w92 { width: 92%; margin-left: auto; margin-right: auto; }
figcaption { font-size: 8.2pt; color: #52514e; margin-top: 2pt; line-height: 1.3; }
table { border-collapse: collapse; width: 100%; font-size: 8.4pt; margin: 3pt 0 7pt; break-inside: avoid; }
th, td { text-align: left; vertical-align: top; padding: 2.4pt 5pt 2.4pt 0; border-bottom: 0.5pt solid #e4e3df; }
th { border-bottom: 0.9pt solid #52514e; }
.small { font-size: 8.2pt; line-height: 1.3; }
.small h2 { font-size: 10.5pt; }
"""

body = markdown.markdown((HERE / "paper.md").read_text(), extensions=["tables", "md_in_html"])
html = HERE / "paper.html"
html.write_text(f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Can Ships Predict Oil Prices?</title>"
                f"<style>{CSS}</style></head><body>{body}</body></html>")
subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                f"--print-to-pdf={HERE / 'paper.pdf'}", html.as_uri()], check=True, capture_output=True, timeout=120)
print("Wrote", HERE / "paper.pdf")
