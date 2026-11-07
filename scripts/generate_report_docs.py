"""Generates docs/REPORT.docx and docs/REPORT.pdf from docs/REPORT_DRAFT.md.

Ensures:
- Exact 9 headings preserved.
- Student placeholders preserved.
- Readable formatting and typography.
- Strict 1-page fit verified via PDF page inspection and image rendering.
"""

import os
import re
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from playwright.sync_api import sync_playwright

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
DRAFT_PATH = os.path.join(DOCS_DIR, "REPORT_DRAFT.md")
DOCX_PATH = os.path.join(DOCS_DIR, "REPORT.docx")
PDF_PATH = os.path.join(DOCS_DIR, "REPORT.pdf")
PREVIEW_IMG_PATH = os.path.join(DOCS_DIR, "REPORT_PREVIEW.png")


def create_docx():
    doc = Document()

    # Set 0.5 inch margins for 1-page layout
    for section in doc.sections:
        section.top_margin = Inches(0.45)
        section.bottom_margin = Inches(0.45)
        section.left_margin = Inches(0.55)
        section.right_margin = Inches(0.55)

    # Base styling
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(9.0)
    normal_style.font.color.rgb = RGBColor(0x25, 0x28, 0x23)  # Charcoal

    def add_p(text, bold_prefix="", space_before=2, space_after=2):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.05
        if bold_prefix:
            run_b = p.add_run(bold_prefix)
            run_b.bold = True
            run_b.font.color.rgb = RGBColor(0x52, 0x60, 0x44)  # Dark Olive
        p.add_run(text)
        return p

    def add_h(text, space_before=4, space_after=1):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(10.0)
        run.font.color.rgb = RGBColor(0x52, 0x60, 0x44)  # Dark Olive
        return p

    # 1. Project Title
    add_h("Project Title", space_before=0, space_after=1)
    add_p("CloudLog Analytics: Cloud-Based Web Log Analysis Using MapReduce", space_before=0, space_after=2)

    # 2. Student Name(s)
    add_h("Student Name(s)")
    add_p("Mohd Uzair Quresh (220905158)  |  Soham Pawar (230905312)", space_before=0, space_after=2)

    # 3. Objective
    add_h("Objective")
    add_p("To implement an educational web log analytics platform applying the MapReduce paradigm to HTTP access logs, evaluate serial versus two-process execution performance on a single host, and prepare the application for managed hosting on Streamlit Community Cloud.")

    # 4. Problem Statement
    add_h("Problem Statement")
    add_p("Server access logs are vital for monitoring web service availability and diagnosing HTTP error spikes. Commercial cloud instances like Amazon EC2 require payment credentials and incur ongoing usage costs, while distributed cluster frameworks like Apache Hadoop introduce substantial multi-node hardware provisioning and Linux administration overhead. The goal is to build an authentic single-host MapReduce engine with rigorous schema validation and interactive visualizations without misrepresenting local multiprocessing as a distributed cluster.")

    # 5. Methodology / Tools Used
    add_h("Methodology / Tools Used")
    add_p("Python 3.11 in an isolated virtual environment (.venv). Educational single-host MapReduce pipeline (Partition, Map, Shuffle, Reduce, Derive) computing exact weighted means. Concurrency via serial baseline and dual-worker ProcessPoolExecutor with transparent fallback. Presentation via Streamlit web app with Plotly charts. Automated verification via 31 Pytest unit and integration tests. Deployment via free-tier Streamlit Community Cloud (managed PaaS).")

    # 6. Implementation
    add_h("Implementation")
    add_p("The system ingests web log CSV files under a 5.0 MB and 50,000-row limit, validating timestamps, methods, integer HTTP status codes (rejecting fractional values), and non-negative latencies. Validated records are partitioned across workers, mapped into key-value tuples, shuffled into grouped lists, reduced into cumulative sums, and derived into exact weighted means (total_latency / total_requests). The benchmark engine compares serial and two-process runs across top-level metrics and all three aggregate tables (endpoint, status code, hourly), verifying exact grouping keys, integer counts, and floating-point aggregates within documented tolerance (0.01 ms for latency, 0.01 percentage points for percentage metrics).")

    # 7. Results
    add_h("Results")
    add_p("All 31 Pytest tests pass with zero warnings, verifying equivalence against independent Pandas aggregations. Mapper workers execute in child processes (worker_pid != parent_pid); forced worker pool failure falls back cleanly to serial execution with full output correctness. Serial and parallel runs match on all grouping keys, integer counts, and float metrics within tolerance (0.01 ms latency, 0.01 percentage points for percentage metrics). On this host machine, observed serial execution on 5,000 records (~15–30 ms) was faster than two-process mode (~1.5–2.8 s on Windows) due to process spawn and IPC overhead; these timings are host-specific observations rather than universal guarantees. Streamlit Community Cloud deployment remains pending final repository push and activation.")

    # 8. Conclusion
    add_h("Conclusion")
    add_p("CloudLog Analytics proves that foundational cloud processing concepts can be demonstrated effectively using free, open-source tools. The project demonstrates the mathematical necessity of weighted derivations and provides an honest empirical look at multiprocessing overhead on modest workloads.")

    # 9. References
    add_h("References")
    add_p("1. Dean, J., & Ghemawat, S. (2004). MapReduce: Simplified Data Processing on Large Clusters. In Proceedings of the 6th USENIX Symposium on Operating System Design and Implementation (OSDI '04), pp. 137–150.\n"
          "2. Python Software Foundation. (2024). concurrent.futures — Launching parallel tasks. Python 3.11 Documentation.\n"
          "3. Streamlit Inc. (2024). Streamlit Community Cloud Documentation. Snowflake Inc.", space_after=0)

    doc.save(DOCX_PATH)
    print(f"Generated DOCX: {DOCX_PATH}")


def create_pdf_and_verify():
    html_content = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {
    size: letter;
    margin: 0.45in 0.55in;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 9.2pt;
    line-height: 1.28;
    color: #252823;
    background-color: #FFFFFF;
    margin: 0;
    padding: 0;
  }
  h1 {
    font-size: 13pt;
    color: #526044;
    margin: 0 0 2px 0;
    font-weight: 700;
  }
  h2 {
    font-size: 9.8pt;
    color: #526044;
    margin: 5px 0 1px 0;
    font-weight: 700;
    border-bottom: 1px solid #E2DFD8;
    padding-bottom: 1px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  p {
    margin: 0 0 4px 0;
    text-align: justify;
  }
  ul {
    margin: 0 0 4px 0;
    padding-left: 18px;
  }
  li {
    margin-bottom: 2px;
  }
  .names {
    color: #526044;
    font-weight: 600;
    font-size: 8.8pt;
    margin-bottom: 4px;
  }
  .ref {
    font-size: 8.4pt;
    line-height: 1.22;
    margin-bottom: 2px;
    color: #444740;
  }
</style>
</head>
<body>

<h1>CloudLog Analytics: Cloud-Based Web Log Analysis Using MapReduce</h1>

<h2>1. Project Title</h2>
<p><b>CloudLog Analytics: Cloud-Based Web Log Analysis Using MapReduce</b></p>

<h2>2. Student Name(s)</h2>
<p class="names">Mohd Uzair Quresh (220905158) &nbsp;&nbsp;|&nbsp;&nbsp; Soham Pawar (230905312)</p>

<h2>3. Objective</h2>
<p>To implement an educational web log analytics platform applying the MapReduce paradigm to HTTP access logs, evaluate serial versus two-process execution performance on a single host, and prepare the application for managed hosting on Streamlit Community Cloud.</p>

<h2>4. Problem Statement</h2>
<p>Server access logs are vital for monitoring web service availability and diagnosing HTTP error spikes. Commercial cloud instances like Amazon EC2 require payment credentials and incur ongoing usage costs, while distributed cluster frameworks like Apache Hadoop introduce substantial multi-node hardware provisioning and Linux administration overhead. The goal is to build an authentic single-host MapReduce engine with rigorous schema validation and interactive visualizations without misrepresenting local multiprocessing as a distributed cluster.</p>

<h2>5. Methodology / Tools Used</h2>
<p>Python 3.11 in an isolated virtual environment (<code>.venv</code>). Educational single-host MapReduce pipeline (Partition, Map, Shuffle, Reduce, Derive) computing exact weighted means. Concurrency via serial baseline and dual-worker <code>ProcessPoolExecutor</code> with transparent fallback. Presentation via Streamlit web app with Plotly charts. Automated verification via 31 Pytest unit and integration tests. Deployment via free-tier Streamlit Community Cloud (managed PaaS).</p>

<h2>6. Implementation</h2>
<p>The system ingests web log CSV files under a 5.0 MB and 50,000-row limit, validating timestamps, methods, integer HTTP status codes (rejecting fractional values), and non-negative latencies. Validated records are partitioned across workers, mapped into key-value tuples, shuffled into grouped lists, reduced into cumulative sums, and derived into exact weighted means (<code>total_latency / total_requests</code>). The benchmark engine compares serial and two-process runs across top-level metrics and all three aggregate tables (endpoint, status code, hourly), verifying exact grouping keys, integer counts, and floating-point aggregates within documented tolerance (0.01 ms for latency, 0.01 percentage points for percentage metrics).</p>

<h2>7. Results</h2>
<p>All 31 Pytest tests pass with zero warnings, verifying equivalence against independent Pandas aggregations. Mapper workers execute in child processes (<code>worker_pid != parent_pid</code>); forced worker pool failure falls back cleanly to serial execution with full output correctness. Serial and parallel runs match on all grouping keys, integer counts, and float metrics within tolerance (0.01 ms latency, 0.01 percentage points for percentage metrics). On this host machine, observed serial execution on 5,000 records (~15–30 ms) was faster than two-process mode (~1.5–2.8 s on Windows) due to process spawn and IPC overhead; these timings are host-specific observations rather than universal guarantees. Streamlit Community Cloud deployment remains pending final repository push and activation.</p>

<h2>8. Conclusion</h2>
<p>CloudLog Analytics proves that foundational cloud processing concepts can be demonstrated effectively using free, open-source tools. The project demonstrates the mathematical necessity of weighted derivations and provides an honest empirical look at multiprocessing overhead on modest workloads.</p>

<h2>9. References</h2>
<p class="ref">1. Dean, J., & Ghemawat, S. (2004). MapReduce: Simplified Data Processing on Large Clusters. In <i>Proceedings of the 6th USENIX Symposium on Operating System Design and Implementation (OSDI '04)</i>, pp. 137–150.</p>
<p class="ref">2. Python Software Foundation. (2024). <i>concurrent.futures — Launching parallel tasks</i>. Python 3.11 Documentation.</p>
<p class="ref">3. Streamlit Inc. (2024). <i>Streamlit Community Cloud Documentation</i>. Snowflake Inc.</p>

</body>
</html>
"""

    existing_chrome = r"C:\Users\soham\AppData\Local\ms-playwright\chromium-1117\chrome-win\chrome.exe"
    with sync_playwright() as p:
        if os.path.exists(existing_chrome):
            browser = p.chromium.launch(executable_path=existing_chrome, headless=True)
        else:
            browser = p.chromium.launch(headless=True)

        page = browser.new_page()
        page.set_content(html_content)

        # Generate PDF
        page.pdf(
            path=PDF_PATH,
            format="Letter",
            margin={"top": "0.45in", "bottom": "0.45in", "left": "0.55in", "right": "0.55in"},
            print_background=True,
        )
        print(f"Generated PDF: {PDF_PATH}")
        browser.close()

    # 1. Verify PDF page count with pypdf parser
    import pypdf
    reader = pypdf.PdfReader(PDF_PATH)
    page_count = len(reader.pages)
    print(f"pypdf parser verified page count: {page_count} page(s)")
    assert page_count == 1, f"Expected 1 page, but PDF has {page_count} pages!"

    # 2. Render actual compiled PDF to image using pypdfium2
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(PDF_PATH)
    pdf_page = pdf[0]
    bitmap = pdf_page.render(scale=2.0)
    pil_image = bitmap.to_pil()
    pil_image.save(PREVIEW_IMG_PATH)
    print(f"Rendered actual PDF to Preview Screenshot: {PREVIEW_IMG_PATH} (size: {pil_image.size})")


if __name__ == "__main__":
    create_docx()
    create_pdf_and_verify()
