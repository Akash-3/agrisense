import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_outline_level(paragraph, level):
    pPr = paragraph._element.get_or_add_pPr()
    outlineLvl = OxmlElement('w:outlineLvl')
    outlineLvl.set(qn('w:val'), str(level))
    pPr.append(outlineLvl)

def fix_toc_heading_styles(docx_path):
    print(f"Applying built-in Word Heading styles (Heading 1 & Heading 2) to {docx_path}...")
    doc = Document(docx_path)
    
    # Configure Heading 1 style
    style_h1 = doc.styles['Heading 1']
    style_h1.font.name = 'Times New Roman'
    style_h1.font.size = Pt(16)
    style_h1.font.bold = True
    style_h1.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A) # Deep Blue
    
    # Configure Heading 2 style
    style_h2 = doc.styles['Heading 2']
    style_h2.font.name = 'Times New Roman'
    style_h2.font.size = Pt(13.5)
    style_h2.font.bold = True
    style_h2.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF) # Royal Blue

    h1_titles = [
        "CERTIFICATE FROM COLLEGE",
        "DECLARATION",
        "ACKNOWLEDGEMENTS",
        "ABSTRACT",
        "TABLE OF CONTENTS",
        "1. INTRODUCTION",
        "2. SYSTEM PLANNING",
        "3. SOFTWARE / HARDWARE MODULES",
        "4. EXPERIMENTAL RESULTS & VIVA DEFENSE PREPARATION",
        "5. CONCLUSION & FUTURE SCOPE",
        "BIBLIOGRAPHY, OPEN-SOURCE CREDITS & IEEE REFERENCES"
    ]

    h2_prefixes = [
        "1.a", "1.b", "1.c", "1.d", "1.e", "1.f",
        "2.a", "2.b", "2.c",
        "3.a", "3.b", "3.c", "3.d", "3.e",
        "4.a", "4.b",
        "5.a", "5.b"
    ]

    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
            
        # Check if it's TOC table text inside TOC section (skip line items with dots)
        if "...." in t:
            continue
            
        # Check for Heading 1 (Chapter titles)
        if t in h1_titles or t.startswith("CHAPTER"):
            p.style = doc.styles['Heading 1']
            set_outline_level(p, 0)
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(10)
            p.paragraph_format.keep_with_next = True
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(16)
                r.font.bold = True
                r.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
                
        # Check for Heading 2 (Section titles)
        elif any(t.startswith(pref) for pref in h2_prefixes):
            p.style = doc.styles['Heading 2']
            set_outline_level(p, 1)
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(13.5)
                r.font.bold = True
                r.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)

    doc.save(docx_path)
    print(f"Successfully applied Word Heading styles to {docx_path}!")

if __name__ == "__main__":
    onedrive_path = r"C:\Users\tempm\OneDrive\Documents\AgriSense Report.docx"
    scratch_path = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\AgriSense_Final_Report.docx"
    
    fix_toc_heading_styles(onedrive_path)
    fix_toc_heading_styles(scratch_path)
