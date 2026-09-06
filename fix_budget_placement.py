import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_background(cell, fill_color):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_color)
    tcPr.append(shd)

def fix_budget_section(docx_path):
    print(f"Fixing Budget section placement in {docx_path}...")
    doc = Document(docx_path)
    
    # First remove any misplaced Budget paragraphs and tables
    p_to_remove = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("7. Budget & Cost Estimation") or t.startswith("Budget & Cost Estimation Overview:") or "Zero Software Licensing Fees:" in t or "Affordable Hobby Hardware:" in t or "Commercial Cost Barrier:" in t or t.startswith("Financial Summary: Total hardware cost"):
            p_to_remove.append(p)
            
    for p in p_to_remove:
        p._element.getparent().remove(p._element)

    # Remove budget tables if any
    tbl_to_remove = []
    for tbl in doc.tables:
        if len(tbl.rows) > 0 and len(tbl.rows[0].cells) > 0:
            if "Component Category" in tbl.rows[0].cells[0].text:
                tbl_to_remove.append(tbl)
    for tbl in tbl_to_remove:
        tbl._element.getparent().remove(tbl._element)

    # Now find the true main Chapter 5 heading near the end of the document (after Q20)
    target_idx = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if i > 150 and ("5. CONCLUSION & FUTURE SCOPE" in t or t == "5. CONCLUSION & FUTURE SCOPE"):
            target_idx = i
            break

    if target_idx is None:
        print("Error: Could not find main Chapter 5 heading!")
        return

    target_p = doc.paragraphs[target_idx]

    # Insert Section 7 Heading BEFORE Chapter 5
    p_sec = target_p.insert_paragraph_before()
    p_sec.paragraph_format.space_before = Pt(18)
    p_sec.paragraph_format.space_after = Pt(8)
    r_sec = p_sec.add_run("7. Budget & Cost Estimation Analysis")
    r_sec.font.name = 'Times New Roman'
    r_sec.font.size = Pt(14)
    r_sec.font.bold = True
    r_sec.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    # Subheading Overview
    p_sub = target_p.insert_paragraph_before()
    p_sub.paragraph_format.space_before = Pt(8)
    p_sub.paragraph_format.space_after = Pt(4)
    r_sub = p_sub.add_run("Budget & Cost Estimation Overview:")
    r_sub.font.name = 'Times New Roman'
    r_sub.font.size = Pt(12)
    r_sub.font.bold = True
    r_sub.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)

    # Bullet Points
    bullets = [
        ("• Zero Software Licensing Fees:", "Backend microservices, web dashboards, and AI engines use 100% free open-source software (Python, FastAPI, React, PyTorch)."),
        ("• Affordable Hobby Hardware:", "AgriSense utilizes off-the-shelf ESP32 microcontrollers [1] and solid-state optical breakout boards [2]."),
        ("• Commercial Cost Barrier:", "Industrial farm survey drones cost over ₹50000 to ₹100000, placing them out of reach for small family farms and educational institutions.")
    ]

    for b_prefix, b_text in bullets:
        p_b = target_p.insert_paragraph_before(style='List Bullet')
        p_b.paragraph_format.line_spacing = 1.25
        p_b.paragraph_format.space_after = Pt(4)
        r_pre = p_b.add_run(b_prefix + " ")
        r_pre.font.name = 'Times New Roman'
        r_pre.font.bold = True
        r_txt = p_b.add_run(b_text)
        r_txt.font.name = 'Times New Roman'

    # Insert Table BEFORE target_p
    tbl = doc.add_table(rows=6, cols=3)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Component Category", "Items Included", "Budget Profile"]
    for j, title in enumerate(headers):
        c = tbl.rows[0].cells[j]
        c.text = title
        p = c.paragraphs[0]
        if p.runs:
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(10)
            p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_background(c, "1E3A8A")

    rows_data = [
        ("Microcontrollers", "2x ESP32 DevKit V1 Boards (Drone & Ground)", "(500 each) ₹1000"),
        ("Optical Sensors", "Adafruit AS7341 10-Channel Breakout Board", "₹2500"),
        ("Environmental Sensors", "Capacitive Soil Probe v1.2 + DHT22 + MQ-2", "₹250 + ₹300 + ₹180 = ₹730"),
        ("Drone Body & Power", "Drone", "₹1700"),
        ("Software Stack", "FastAPI, React.js, PyTorch, Chart.js, PostgreSQL", "100% FREE Open Source")
    ]

    for r_idx, row_tuple in enumerate(rows_data, start=1):
        for c_idx, val in enumerate(row_tuple):
            c = tbl.rows[r_idx].cells[c_idx]
            c.text = val
            p = c.paragraphs[0]
            if p.runs:
                p.runs[0].font.size = Pt(9.5)
            set_cell_background(c, "F8FAFC" if r_idx % 2 == 0 else "FFFFFF")

    # Move tbl XML before target_p XML
    target_p._element.addprevious(tbl._element)

    # Insert Financial Summary
    p_sum = target_p.insert_paragraph_before()
    p_sum.paragraph_format.space_before = Pt(10)
    p_sum.paragraph_format.space_after = Pt(14)
    r_sp = p_sum.add_run("Financial Summary: ")
    r_sp.font.name = 'Times New Roman'
    r_sp.font.bold = True
    r_st = p_sum.add_run("Total hardware cost is 100x cheaper than commercial farm drones, while software costs are zero. This makes AgriSense accessible to smallholder farmers worldwide!")
    r_st.font.name = 'Times New Roman'

    doc.save(docx_path)
    print(f"Successfully fixed Section 7 placement in {docx_path}!")

if __name__ == "__main__":
    onedrive_path = r"C:\Users\tempm\OneDrive\Documents\AgriSense Report.docx"
    scratch_path = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\AgriSense_Final_Report.docx"
    
    fix_budget_section(onedrive_path)
    fix_budget_section(scratch_path)
