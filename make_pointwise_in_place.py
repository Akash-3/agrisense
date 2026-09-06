import os
import time
import docx
from docx import Document
from docx.oxml import OxmlElement

def add_paragraph_after(paragraph, text, style='List Bullet'):
    new_p = OxmlElement('w:p')
    paragraph._element.addnext(new_p)
    new_para = docx.text.paragraph.Paragraph(new_p, paragraph._parent)
    new_para.style = style
    new_para.add_run(text)
    return new_para

def transform_synopsis_to_pointwise(docx_path):
    print(f"Modifying {docx_path} IN-PLACE to add point-wise formatting...")
    doc = Document(docx_path)
    
    # We will map paragraphs that contain long text to point-wise bullet lists
    # Executive Summary Paragraph 4
    for p in doc.paragraphs:
        t = p.text.strip()
        
        # Executive summary P1
        if t.startswith("Farming is one of the most important jobs in the world"):
            p.text = "Executive Summary Key Points:"
            p.style = 'Normal'
            add_paragraph_after(p, "Fungal, bacterial, and viral pathogens infect leaf cells internally days before any visual spots manifest on the leaf surface.", style='List Bullet')
            add_paragraph_after(p, "Traditional manual field inspection spots diseases only after brown or yellow lesions form, by which time internal cellular damage is already irreversible.", style='List Bullet')
            add_paragraph_after(p, "Applying fungicides or chemical treatments after visual spots emerge fails to recover lost crop yield.", style='List Bullet')
            add_paragraph_after(p, "Farming provides essential global food supplies, but crops face constant threats from diseases, climate volatility, and water scarcity.", style='List Bullet')

        # Executive summary P2
        elif t.startswith("To solve this problem, we created AgriSense."):
            p.text = "AgriSense Early Protection & Spectral Sensing:"
            p.style = 'Normal'
            add_paragraph_after(p, "Internal Cellular Health Tracking: Healthy leaf cell walls reflect NIR light like a mirror; pathogen infection causes cell wall collapse and an immediate drop in NIR reflection 5.4 days before visual spots appear.", style='List Bullet')
            add_paragraph_after(p, "10-Channel Spectral Optical Sensing: Mounted on the drone, the Adafruit AS7341 sensor [2] acts like high-tech glasses, measuring 10 light channels including Near-Infrared (NIR) light.", style='List Bullet')
            add_paragraph_after(p, "AgriSense Early Protection Platform: AgriSense combines a lightweight flying drone payload, a ground soil sensor node, and an artificial intelligence (AI) diagnostic backend to protect crops early.", style='List Bullet')

        # Executive summary P3
        elif t.startswith("At the same time, a rust-free capacitive sensor placed in the ground"):
            p.text = "Edaphic Hydration & User Dashboard:"
            p.style = 'Normal'
            add_paragraph_after(p, "Wireless Wi-Fi Telemetry & Real-Time Dashboard: Telemetry is transmitted via Wi-Fi to a responsive web dashboard [4, 5], rendering live color-coded status badges (Green, Yellow, Red) on any device.", style='List Bullet')
            add_paragraph_after(p, "Continuous Soil Moisture Monitoring: A rust-free capacitive soil probe [12] sits in the ground to measure soil volumetric water content (VWC%), ensuring roots receive optimal hydration.", style='List Bullet')

        # Section 1 Introduction P1
        elif t.startswith("Around the world, plant diseases and insect pests destroy between 20%"):
            p.text = "Agricultural Losses & Manual Inspection Challenges:"
            p.style = 'Normal'
            add_paragraph_after(p, "Limitations of Manual Inspection Walks: Workers walking under the hot sun inspect plants slowly and inefficiently; localized fungal outbreaks in large fields are frequently missed until widespread damage occurs.", style='List Bullet')
            add_paragraph_after(p, "Global Crop Yield Destruction: Plant pathogens and insect pests ruin 20% to 40% of global food production annually, severely impacting smallholder farming livelihoods.", style='List Bullet')

        # Section 1 Introduction P2
        elif t.startswith("Modern information technology has introduced the concept of 'Precision Agriculture,'"):
            p.text = "Precision Agriculture & Existing Technology Limits:"
            p.style = 'Normal'
            add_paragraph_after(p, "Satellite Remote Sensing Latency: Satellite imagery suffers from coarse spatial resolution (10m-30m per pixel) and long pass-over intervals (5-16 days), making it too slow for rapid fungal outbreaks.", style='List Bullet')
            add_paragraph_after(p, "Prohibitive Hardware Costs: Commercial agricultural survey drones and hyperspectral cameras cost over $5,000 to $10,000, creating an impassable financial barrier for smallholders.", style='List Bullet')
            add_paragraph_after(p, "Precision Agriculture Paradigm: Utilizing smart sensors, microcontrollers, and software algorithms enables targeted, plant-specific agronomic care.", style='List Bullet')

        # Section 1 Introduction P3
        elif t.startswith("AgriSense bridges this gap by creating an affordable, simple solution."):
            p.text = "AgriSense Hardware & Weight Optimization:"
            p.style = 'Normal'
            add_paragraph_after(p, "Ultra-Lightweight Aerial Footprint: The entire optical and environmental sensor package weighs only 82 grams—lighter than a small apple—allowing safe flight on makeshift quadcopter frames without motor strain.", style='List Bullet')
            add_paragraph_after(p, "Accessible Micro-Electronics Integration: AgriSense combines a low-cost $4 ESP32 microcontroller [1] with a solid-state AS7341 10-channel spectral sensor [2].", style='List Bullet')

        # Section 1 Introduction P4
        elif t.startswith("AgriSense also cleverly separates flying duties from ground duties."):
            p.text = "Decoupled Sensor Node Strategy:"
            p.style = 'Normal'
            add_paragraph_after(p, "Optimized Flight Endurance: Stationary ground nodes [12] handle heavy soil probing, while the lightweight drone focuses exclusively on high-speed aerial optical scanning.", style='List Bullet')
            add_paragraph_after(p, "Decoupled Sensing Architecture: Ground soil probing is separated from aerial canopy scanning to prevent drone overweight and battery drain.", style='List Bullet')

        # Section 4 Methodology Intro P
        elif t.startswith("The AgriSense platform processes information through a smooth 5-step"):
            p.text = "System Methodology & 5-Step Data Processing Pipeline:"
            p.style = 'Normal'

        # Section 4 Steps
        elif t.startswith("Step 1 - Data Sampling at Canopy & Soil Level:"):
            p.style = 'List Bullet'
        elif t.startswith("Step 2 - Wireless JSON Serialization & Wi-Fi Transmission:"):
            p.style = 'List Bullet'
        elif t.startswith("Step 3 - Backend Ingestion & Pydantic Validation:"):
            p.style = 'List Bullet'
        elif t.startswith("Step 4 - MM-SSNet AI Disease Classification:"):
            p.style = 'List Bullet'
        elif t.startswith("Step 5 - UI Rendering & Real-Time Alert Triggering:"):
            p.style = 'List Bullet'

        # Section 7 Budget P1
        elif t.startswith("Commercial precision agriculture systems and specialized survey drones cost over"):
            p.text = "Budget & Cost Estimation Overview:"
            p.style = 'Normal'
            add_paragraph_after(p, "Commercial Cost Barrier: Industrial farm survey drones cost over $5,000 to $10,000, placing them out of reach for small family farms and educational institutions.", style='List Bullet')
            add_paragraph_after(p, "Affordable Hobby Hardware: AgriSense utilizes off-the-shelf ESP32 microcontrollers [1] and solid-state optical breakout boards [2].", style='List Bullet')
            add_paragraph_after(p, "Zero Software Licensing Fees: Backend microservices, web dashboards, and AI engines use 100% free open-source software (Python, FastAPI, React, PyTorch).", style='List Bullet')

        # Section 9 Conclusion
        elif t.startswith("The AgriSense project successfully proves that high-precision early plant disease"):
            p.text = "Project Summary & Concluding Achievements:"
            p.style = 'Normal'
            add_paragraph_after(p, "Global Agricultural Impact: Helps farmers protect crop yields, prevent water waste, and support global food security.", style='List Bullet')
            add_paragraph_after(p, "Affordable & Accessible Engineering: Built with budget-friendly electronics and 100% free open-source software.", style='List Bullet')
            add_paragraph_after(p, "Pre-Symptomatic Pathogen Detection: Detects fungal leaf infection 5.4 days before visible spots appear with 97.4% accuracy.", style='List Bullet')
            add_paragraph_after(p, "Proven High-Precision AI: Combines 10-channel spectral canopy profiling with ground soil moisture tracking.", style='List Bullet')

    doc.save(docx_path)
    print(f"Successfully updated {docx_path} IN-PLACE with point-wise bullet lists!")

if __name__ == "__main__":
    synopsis_path = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\AgriSense_Project_Synopsis.docx"
    synopsis_md = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\AgriSense_Project_Synopsis.md"
    
    transform_synopsis_to_pointwise(synopsis_path)
    
    # Export Markdown from updated docx
    doc = Document(synopsis_path)
    md_lines = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if t.startswith("PROJECT SYNOPSIS"):
            md_lines.append(f"# {t}\n")
        elif t.startswith("1.") or t.startswith("2.") or t.startswith("3.") or t.startswith("4.") or t.startswith("5.") or t.startswith("6.") or t.startswith("7.") or t.startswith("8.") or t.startswith("9."):
            md_lines.append(f"\n## {t}\n")
        elif p.style.name == 'List Bullet':
            md_lines.append(f"* {t}\n")
        elif "Figure " in t:
            if "Figure 5.1" in t:
                md_lines.append(f"\n![Aerial Drone Payload](agrisense_drone_payload.jpg)\n*{t}*\n")
            elif "Figure 5.2" in t:
                md_lines.append(f"\n![Ground Node Unit](agrisense_ground_node.jpg)\n*{t}*\n")
            else:
                md_lines.append(f"*{t}*\n")
        else:
            md_lines.append(f"\n**{t}**\n" if len(t) < 50 and not t.endswith(".") else f"{t}\n")
            
    with open(synopsis_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Successfully updated {synopsis_md}!")
