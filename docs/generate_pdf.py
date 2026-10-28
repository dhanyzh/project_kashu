import os
import subprocess
import markdown

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_MD = os.path.join(DOCS_DIR, "PROJECT_REPORT.md")
TEMP_HTML = os.path.join(DOCS_DIR, "PROJECT_REPORT.html")
OUTPUT_PDF = os.path.join(DOCS_DIR, "PROJECT_REPORT.pdf")

# Detect browser
browsers = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

browser_exe = None
for b in browsers:
    if os.path.exists(b):
        browser_exe = b
        break

if not browser_exe:
    print("Error: No Chromium-based browser found.")
    exit(1)

with open(REPORT_MD, "r", encoding="utf-8") as f:
    text = f.read()

html_body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])

html_template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PROJECT KASHI - DBMS Lab Project Report</title>
<style>
  @page {
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
    @bottom-right {
      content: counter(page);
    }
  }
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    color: #1a202c;
    line-height: 1.55;
    font-size: 10.5pt;
    background: #ffffff;
    margin: 0;
    padding: 0;
  }
  .header-banner {
    background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
    color: white;
    padding: 24px 28px;
    border-radius: 8px;
    margin-bottom: 25px;
  }
  .header-banner h1 {
    color: #ffffff;
    margin: 0 0 8px 0;
    font-size: 22pt;
    border-bottom: none;
    letter-spacing: -0.5px;
  }
  .header-banner p {
    color: #e0e7ff;
    margin: 4px 0;
    font-size: 10pt;
  }
  h1 {
    color: #1e3a8a;
    font-size: 20pt;
    border-bottom: 2.5px solid #3b82f6;
    padding-bottom: 6px;
    margin-top: 24px;
    page-break-before: auto;
  }
  h2 {
    color: #1e40af;
    font-size: 14pt;
    border-bottom: 1.5px solid #e2e8f0;
    padding-bottom: 4px;
    margin-top: 22px;
    page-break-after: avoid;
  }
  h3 {
    color: #334155;
    font-size: 11.5pt;
    margin-top: 16px;
    page-break-after: avoid;
  }
  p, li {
    color: #334155;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 9pt;
    page-break-inside: avoid;
  }
  th, td {
    border: 1px solid #cbd5e1;
    padding: 6px 10px;
    text-align: left;
    vertical-align: top;
  }
  th {
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
  }
  tr:nth-child(even) {
    background-color: #f8fafc;
  }
  pre, code {
    font-family: 'Consolas', 'Courier New', monospace;
  }
  code {
    background-color: #f1f5f9;
    color: #b91c1c;
    padding: 2px 5px;
    border-radius: 4px;
    font-size: 9pt;
  }
  pre {
    background-color: #0f172a;
    color: #f8fafc;
    padding: 12px 14px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 8.5pt;
    line-height: 1.45;
    page-break-inside: avoid;
  }
  pre code {
    background-color: transparent;
    color: inherit;
    padding: 0;
  }
  blockquote {
    border-left: 4px solid #3b82f6;
    padding: 6px 12px;
    color: #475569;
    margin: 12px 0;
    background-color: #f8fafc;
    border-radius: 0 4px 4px 0;
  }
  hr {
    border: 0;
    height: 1px;
    background: #e2e8f0;
    margin: 22px 0;
  }
  .badge {
    display: inline-block;
    padding: 3px 8px;
    background: #dbeafe;
    color: #1e40af;
    border-radius: 12px;
    font-size: 8pt;
    font-weight: 600;
    margin-right: 6px;
  }
  .mermaid {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 10px;
    border-radius: 6px;
    font-size: 8.5pt;
  }
</style>
</head>
<body>

<div class="header-banner">
  <div style="font-size: 9pt; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; margin-bottom: 4px;">
    Department of Computer Science &amp; Engineering &bull; DBMS Lab (3rd Semester)
  </div>
  <h1>PROJECT KASHI: Banking Management System</h1>
  <p><strong>Architecture:</strong> 3-Tier Enterprise Model (HTML5/CSS &bull; Python Flask &bull; MySQL 8.0)</p>
  <p><strong>Evaluation:</strong> Class Internal Assessment &bull; Maximum Marks: 10/10</p>
</div>

""" + html_body + """
</body>
</html>
"""

with open(TEMP_HTML, "w", encoding="utf-8") as f:
    f.write(html_template)

print(f"Generated clean HTML at: {TEMP_HTML}")

# Execute browser headless print to PDF
cmd = [
    browser_exe,
    "--headless",
    "--disable-gpu",
    "--run-all-compositor-stages-before-draw",
    f"--print-to-pdf={OUTPUT_PDF}",
    "--no-pdf-header-footer",
    TEMP_HTML
]

print("Converting to PDF via:", browser_exe)
res = subprocess.run(cmd, capture_output=True, text=True)

if os.path.exists(OUTPUT_PDF) and os.path.getsize(OUTPUT_PDF) > 0:
    print(f"SUCCESS: PDF created successfully at: {OUTPUT_PDF}")
    print(f"File size: {os.path.getsize(OUTPUT_PDF) / 1024:.1f} KB")
else:
    print("Failed to generate PDF. Return code:", res.returncode)
    print("Error:", res.stderr)
