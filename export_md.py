import docx

doc = docx.Document(r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\AgriSense_Final_Capstone_Report_NoPrice.docx")

md_content = []
for p in doc.paragraphs:
    text = p.text.strip()
    if not text:
        continue
    if text.startswith("CHAPTER") or text.startswith("AGRISENSE:") or text.startswith("CERTIFICATE") or text.startswith("DECLARATION") or text.startswith("ACKNOWLEDGEMENTS") or text.startswith("ABSTRACT") or text.startswith("TABLE OF CONTENTS") or text.startswith("CREDITS") or text.startswith("BIBLIOGRAPHY"):
        md_content.append(f"\n# {text}\n")
    elif text.startswith("1.") or text.startswith("2.") or text.startswith("3.") or text.startswith("4.") or text.startswith("5.") or text.startswith("6.") or text.startswith("7.") or text.startswith("8.") or text.startswith("9."):
        md_content.append(f"\n## {text}\n")
    else:
        md_content.append(f"{text}\n")

with open(r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\AgriSense_Final_Capstone_Report_NoPrice.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md_content))

print("Saved Markdown version of Report without prices!")
