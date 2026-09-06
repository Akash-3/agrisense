import docx

doc = docx.Document(r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\AgriSense_8000Word_Master_Report.docx")

md_content = []
for p in doc.paragraphs:
    text = p.text.strip()
    if not text:
        continue
    if text.startswith("CHAPTER") or text.startswith("AGRISENSE:") or text.startswith("CERTIFICATE") or text.startswith("DECLARATION") or text.startswith("ACKNOWLEDGEMENTS") or text.startswith("ABSTRACT") or text.startswith("TABLE OF CONTENTS") or text.startswith("BIBLIOGRAPHY"):
        md_content.append(f"\n# {text}\n")
    elif text.startswith("1.") or text.startswith("2.") or text.startswith("3.") or text.startswith("4.") or text.startswith("5.") or text.startswith("6.") or text.startswith("7.") or text.startswith("8.") or text.startswith("9."):
        md_content.append(f"\n## {text}\n")
    else:
        md_content.append(f"{text}\n")

with open(r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\AgriSense_8000Word_Master_Report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md_content))

print("Successfully exported 8,000-word master report Markdown file!")
