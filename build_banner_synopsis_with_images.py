import os
import shutil
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

def add_bottom_border_to_paragraph(paragraph, color="1E3A8A", size="12"):
    pPr = paragraph._element.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), size)
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), color)
    pBdr.append(bottom)
    pPr.append(pBdr)

def add_page_number_to_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    
    run1 = p.add_run("Page ")
    run1.font.name = 'Arial'
    run1.font.size = Pt(9.5)
    run1.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    
    fldSimple1 = OxmlElement('w:fldSimple')
    fldSimple1.set(qn('w:instr'), 'PAGE')
    p._element.append(fldSimple1)
    
    run2 = p.add_run(" of ")
    run2.font.name = 'Arial'
    run2.font.size = Pt(9.5)
    run2.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    
    fldSimple2 = OxmlElement('w:fldSimple')
    fldSimple2.set(qn('w:instr'), 'NUMPAGES')
    p._element.append(fldSimple2)

def generate_synopsis_with_images(docx_path, md_path):
    print(f"Building AgriSense Project Synopsis with embedded drone & ground node images at {docx_path}...")
    doc = Document()
    
    sec = doc.sections[0]
    sec.top_margin = Inches(1.0)
    sec.bottom_margin = Inches(1.0)
    sec.left_margin = Inches(1.0)
    sec.right_margin = Inches(1.0)
    add_page_number_to_footer(sec)

    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    style.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    # ==================== TOP BANNER BOX (PAGE 1 HEADER) ====================
    table_banner = doc.add_table(rows=1, cols=1)
    table_banner.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_b = table_banner.rows[0].cells[0]
    cell_b.width = Inches(6.5)
    set_cell_background(cell_b, "B8D0FF") # Soft Light Blue Background matching user image

    # Title
    p_b1 = cell_b.paragraphs[0]
    p_b1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_b1.paragraph_format.space_before = Pt(16)
    p_b1.paragraph_format.space_after = Pt(4)
    r1 = p_b1.add_run("AgriSense")
    r1.font.name = 'Arial'
    r1.font.size = Pt(24)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    # Subtitle
    p_b2 = cell_b.add_paragraph()
    p_b2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_b2.paragraph_format.space_after = Pt(4)
    r2 = p_b2.add_run("A Low-Cost, Dual-Node IoT Drone Platform with Multi-Modal AI for Early Asymptomatic Crop Disease Diagnosis & Soil Health Monitoring")
    r2.font.name = 'Arial'
    r2.font.size = Pt(12)
    r2.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    # Tagline
    p_b3 = cell_b.add_paragraph()
    p_b3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_b3.paragraph_format.space_after = Pt(12)
    r3 = p_b3.add_run("Project Synopsis | Final Year Project Proposal")
    r3.font.name = 'Arial'
    r3.font.size = Pt(11)
    r3.font.italic = True
    r3.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)

    # Right-aligned Authors
    authors = [
        "Kavya Bhandary 261796",
        "Rehaan Shaikh 261831",
        "Aditya Surve 261844"
    ]
    for auth in authors:
        p_a = cell_b.add_paragraph()
        p_a.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_a.paragraph_format.space_after = Pt(2)
        r_a = p_a.add_run(f"{auth}   ")
        r_a.font.name = 'Arial'
        r_a.font.size = Pt(10.5)
        r_a.font.italic = True
        r_a.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    p_spacer_b = cell_b.add_paragraph()
    p_spacer_b.paragraph_format.space_after = Pt(6)

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_after = Pt(12)

    def add_sec_heading(title_text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title_text)
        run.font.name = 'Arial'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        add_bottom_border_to_paragraph(p, color="1E3A8A", size="8")
        return p

    def add_sub_heading(title_text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title_text)
        run.font.name = 'Arial'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)
        return p

    def add_p(text, space_after=6):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.space_after = Pt(space_after)
        p.add_run(text)
        return p

    def add_bullet(bold_prefix, text_content):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.space_after = Pt(5)
        r_b = p.add_run(bold_prefix + " ")
        r_b.font.name = 'Arial'
        r_b.font.bold = True
        r_t = p.add_run(text_content)
        r_t.font.name = 'Arial'
        return p

    def add_image_figure(img_path, caption_text, width_inches=5.2):
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(10)
            p_img.paragraph_format.space_after = Pt(4)
            r_i = p_img.add_run()
            r_i.add_picture(img_path, width=Inches(width_inches))
            
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(12)
            r_c = p_cap.add_run(caption_text)
            r_c.font.name = 'Arial'
            r_c.font.size = Pt(9.5)
            r_c.font.italic = True
            r_c.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
        else:
            print(f"Warning: Image not found at {img_path}")

    # ==================== 1. INTRODUCTION ====================
    add_sec_heading("1. Introduction")
    add_p("Precision agriculture is a critical technological domain that combines remote sensing, internet-connected microcontrollers, autonomous robotics, and machine learning to optimize global crop yield and protect food security. It helps answer fundamental agronomic questions like: 'How can farmers detect crop disease before physical leaf damage occurs?' or 'How can irrigation schedules be dynamically tuned to prevent both drought stress and root waterlogging?'")
    add_p("However, agricultural monitoring solutions available today are either too expensive, require specialized pilot licenses, or depend on closed proprietary cloud subscriptions. Commercial survey drones equipped with industrial hyperspectral cameras cost over $5,000 to $10,000 (₹50,000 to ₹1,00,000), making them completely inaccessible for smallholder farmers, local agronomists, and university research laboratories. Furthermore, standard RGB camera vision systems are strictly reactive, spotting plant pathogens only after macroscopic brown or yellow lesions physically cover the leaf surfaces—a stage where irreversible cellular destruction has already occurred.")
    add_p("AgriSense is our proposed solution to this problem: a free, open-source, dual-node IoT monitoring platform and Multi-Modal Spectral-Spatial Network (MM-SSNet) AI diagnostic engine that allows farmers and researchers to achieve 5.4-day pre-symptomatic plant disease detection and continuous soil moisture tracking at a fraction of commercial hardware costs.")

    # ==================== 2. PROBLEM STATEMENT ====================
    add_sec_heading("2. Problem Statement")
    add_p("Phytopathological disease outbreaks and sub-optimal edaphic hydration account for an estimated 20% to 40% of global crop yield losses annually. Despite advances in agricultural computer vision, effective crop health monitoring remains out of reach for most farming communities due to five key technical and financial bottlenecks:")
    
    add_bullet("Late Pathogen Detection in Conventional RGB Systems:", "Standard smartphone cameras and 2D RGB computer vision models (e.g., YOLO, ResNet-50) only detect plant diseases after physical brown lesions or chlorotic yellowing form on leaf surfaces. At this advanced pathological stage, fungal hyphae have already colonized internal vascular tissue, causing permanent yield loss regardless of chemical application.")
    add_bullet("Prohibitive Cost of Commercial Hyperspectral Hardware:", "Commercial hyperspectral camera systems and specialized agricultural survey drones cost industrial-level budgets (₹50,000 to ₹1,00,000+), creating an impassable cost barrier for smallholders.")
    add_bullet("Drone Flight Payload & Battery Limits:", "Attaching heavy soil moisture probes, long cables, and large battery packs directly onto low-cost makeshift drone frames exceeds maximum takeoff weight limits (MTOW), leading to motor overheating, short flight times, and flight instability.")
    add_bullet("Closed Proprietary Systems & Monthly Cloud Subscriptions:", "Commercial agricultural IoT platforms rely on proprietary cloud backends that enforce monthly subscription fees, lack open REST APIs, and block custom AI model integration.")
    add_bullet("Undetected Environmental Field Hazards:", "Agricultural fields face undetected environmental hazards such as stubble fires, dry brush combustion, toxic gas accumulations, and extreme heatwaves that ruin crop yields before manual field workers notice.")

    add_p("As a result, precision agriculture remains largely limited to large industrial conglomerates and high-budget research institutions. Smallholder farmers cultivating small land plots have no practical, affordable tool to inspect crop health before physical damage manifests.")
    add_p("There is a clear need for an end-to-end platform that is low-cost, open-source, decouples aerial canopy scanning from ground soil probing, provides pre-symptomatic AI warnings, and is accessible from any web browser on any device.")

    # ==================== 3. PROPOSED SOLUTION ====================
    add_sec_heading("3. Proposed Solution")
    add_p("We propose to build AgriSense—an integrated, low-cost Internet of Things (IoT) aerial and terrestrial monitoring platform paired with a novel Multi-Modal Spectral-Spatial Network (MM-SSNet) deep learning model that runs microservice ingestion in real time. The platform decouples flying canopy inspection from stationary soil sensing to keep aerial flight weight strictly under 82 grams.")
    add_p("The platform will allow users to:")
    
    add_bullet("Profile Leaf Canopy Multi-Spectral Optics:", "Sample 10 discrete optical wavelengths (415nm to 885nm) using an Adafruit AS7341 spectral sensor [2] mounted on an ESP32 drone payload [1] to track Near-Infrared (NIR) mesophyll scattering breakdown 5.4 days before visible leaf chlorosis.")
    add_bullet("Monitor Ground Soil Hydration Without Rust:", "Continuously measure volumetric soil water content (VWC%) using stationary capacitive soil moisture nodes [12] that operate via high-frequency dielectric permittivity with zero metal probe corrosion.")
    add_bullet("Execute Pre-Symptomatic Multi-Modal AI Inference:", "Process telemetry through MM-SSNet [13, 15]—a dual-stream neural network fusing 1D-spectral reflectance vectors with 2D spatial MobileNetV3 foliage images via cross-attention to output pre-symptomatic disease probability ratings.")
    add_bullet("Ingest JSON Telemetry under 200ms Latency:", "Process incoming JSON telemetry payloads via an asynchronous Python FastAPI application server [3] with strict Pydantic schema validation and PostgreSQL database persistence.")
    add_bullet("Visualize Real-Time Field Telemetry:", "Inspect live 10-channel spectral reflectance bar charts, climate metrics, and edaphic status on a glassmorphism Single-Page Application (SPA) web dashboard built with React.js [4], Chart.js [5], and Lucide icons [6].")
    add_bullet("Receive Automated Early Hazard Warnings:", "Generate immediate high-priority alert banners on the web dashboard whenever smoke levels exceed 400 PPM or soil moisture drops below 30%.")
    add_bullet("Test System Live via Built-In Simulation Mode:", "Execute a dedicated demonstration endpoint (`POST /api/v1/simulate`) that generates realistic mock telemetry for examiner live testing without needing active physical hardware connected.")

    add_p("The platform is designed to be simple enough for a first-year agronomy student to operate while technically rigorous enough for academic viva examination and research deployment.")

    # ==================== 4. PROJECT OBJECTIVES ====================
    add_sec_heading("4. Project Objectives")
    add_p("The primary objectives of this project are:")

    add_bullet("To design and assemble", "a feather-light 82g aerial optical sensor payload featuring an ESP32 DevKit V1 [1], Raspberry Pi Zero W, Adafruit AS7341 10-channel multi-spectral sensor [2], DHT22 microclimate sensor, and MQ-2 smoke detector.")
    add_bullet("To construct autonomous ground sensor nodes", "equipped with capacitive soil moisture probes [12] for continuous, corrosion-free edaphic hydration tracking.")
    add_bullet("To implement an asynchronous Python FastAPI microservice backend", "running on Starlette ASGI with strict Pydantic JSON schema validation and sub-200ms latency [3].")
    add_bullet("To formulate and train the novel MM-SSNet deep learning model", "fusing 1D-spectral reflectance vectors with 2D spatial MobileNetV3 foliage images via cross-attention, achieving 97.4% accuracy and 5.4-day pre-symptomatic detection lead time [13, 15].")
    add_bullet("To develop a responsive glassmorphic web dashboard", "utilizing React.js [4], HTML5, CSS3, Chart.js [5], and Lucide iconography [6] to display real-time 10-channel spectral bar graphs and edaphic status.")
    add_bullet("To build an automated environmental hazard alert engine", "that flags smoke levels over 400 PPM or soil moisture deficits below 30% instantly.")
    add_bullet("To incorporate a built-in simulation mode endpoint", "allowing live system demonstrations and examiner testing without requiring physical hardware connections.")
    add_bullet("To ensure complete economic accessibility", "by keeping total hardware costs strictly at ₹9,000 and utilizing 100% free open-source software.")

    # ==================== 5. PROPOSED MODULES & SYSTEM DIAGRAMS ====================
    add_sec_heading("5. Proposed Modules & Hardware Architecture")
    add_p("The system is divided into 9 well-defined modules, each responsible for a distinct part of the platform:")

    table_mod = doc.add_table(rows=10, cols=3)
    table_mod.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_mod = ["#", "Module Name", "What it does"]
    
    for i, title in enumerate(headers_mod):
        c = table_mod.rows[0].cells[i]
        c.text = title
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(10)
            p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_background(c, "1E3A8A")

    modules_data = [
        ("1", "Aerial Drone Sensing Payload Module", "Samples 10 AS7341 spectral channels, DHT22 climate, MQ-2 gas every 5s; 82g payload weight."),
        ("2", "Terrestrial Ground Soil Module", "Measures soil volumetric water content (VWC%) using rust-free capacitive probe every 10s."),
        ("3", "FastAPI Microservice Telemetry Engine", "Asynchronous ASGI backend server handling JSON ingestion, API routing, and database persistence."),
        ("4", "Pydantic Validation & CHI Engine", "Validates telemetry bounds and computes synthetic Crop Health Index (R_CRI & S_NIR)."),
        ("5", "MM-SSNet Pre-Symptomatic AI Engine", "Dual-stream 1D-Spectral CNN + 2D-Spatial MobileNetV3 model fused via cross-attention."),
        ("6", "React Glassmorphism Web Dashboard", "Single-Page Application UI displaying real-time sensor cards, alert banners, and dark theme."),
        ("7", "Chart.js 10-Channel Spectral Module", "Dynamic bar chart visualization rendering normalized light counts from 415nm to 885nm."),
        ("8", "Field Hazard Early Warning System", "Generates high-priority alert banners for smoke (>400 PPM) or severe soil drought (<30%)."),
        ("9", "System Simulation & Testing Engine", "Mock endpoint (POST /api/v1/simulate) generating realistic telemetry for live examiner testing.")
    ]

    for r_idx, (num, name, desc) in enumerate(modules_data, start=1):
        row_cells = table_mod.rows[r_idx].cells
        row_cells[0].text = num
        row_cells[1].text = name
        row_cells[2].text = desc
        
        row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for c_idx in range(3):
            cell_p = row_cells[c_idx].paragraphs[0]
            if cell_p.runs:
                cell_p.runs[0].font.name = 'Arial'
                cell_p.runs[0].font.size = Pt(9.5)
                if c_idx == 1:
                    cell_p.runs[0].font.bold = True
            set_cell_background(row_cells[c_idx], "F8FAFC" if r_idx % 2 == 0 else "FFFFFF")

    # EMBEDDING IMAGE 1: DRONE PAYLOAD
    add_sub_heading("Module 1 Detail: Aerial Drone Multi-Spectral Sensor Payload")
    add_p("The aerial drone sensing payload mounts directly onto the quadcopter frame, integrating an ESP32 DevKit V1 board, Adafruit AS7341 10-channel optical breakout board, DHT22 climate sensor, MQ-2 gas sensor, and LiPo power supply into a feather-light 82-gram package:")
    
    img1_path = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\agrisense_drone_payload.jpg"
    add_image_figure(img1_path, "Figure 5.1: Custom Quadcopter Drone Payload with ESP32, AS7341 Multi-Spectral Sensor, DHT22 Climate Probe, and MQ-2 Hazard Module Attached", width_inches=5.2)

    # EMBEDDING IMAGE 2: GROUND SOIL NODE
    add_sub_heading("Module 2 Detail: Terrestrial Ground Soil Hydration Node")
    add_p("The stationary ground soil module isolates heavy edaphic probes from the flying drone. It couples an ESP32/Raspberry Pi microcontroller with a non-corrosive capacitive soil moisture probe v1.2 operating via high-frequency dielectric permittivity:")

    img2_path = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs\agrisense_ground_node.jpg"
    add_image_figure(img2_path, "Figure 5.2: Terrestrial Ground Soil Hydration Node featuring ESP32 and Non-Corrosive Capacitive Soil Moisture Probe v1.2", width_inches=5.2)

    # ==================== 6. TECHNOLOGY STACK & COST ESTIMATION ====================
    add_sec_heading("6. Technology Stack & Cost Estimation")
    add_p("The following technologies will be used to build AgriSense:")

    table_tech = doc.add_table(rows=12, cols=3)
    table_tech.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_tech = ["Category", "Technology", "Why we chose it"]
    
    for i, title in enumerate(headers_tech):
        c = table_tech.rows[0].cells[i]
        c.text = title
        p = c.paragraphs[0]
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(10)
            p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_background(c, "1E3A8A")

    tech_data = [
        ("Microcontroller Board", "Raspi Zero W & ESP32 DevKit V1", "Dual processing units for onboard flight telemetry and ground node communication"),
        ("Multi-Spectral Sensor", "Adafruit AS7341 10-Channel", "10-channel solid-state optical sensor measuring visible to NIR (885nm) wavelengths"),
        ("Soil Moisture Sensor", "Capacitive Probe v1.2", "Non-corrosive dielectric permittivity sensor with zero metal probe rust"),
        ("Microclimate Sensor", "DHT22 Sensor", "High-accuracy digital temperature (-40 to 80°C) and relative humidity probe"),
        ("Hazard Gas Sensor", "MQ-2 Gas / Smoke Module", "Detects combustible gas, LPG, methane, hydrogen, and stubble fire smoke"),
        ("Backend Framework", "Python FastAPI + ASGI", "Asynchronous microservice delivering sub-200ms latency and Pydantic validation"),
        ("AI / ML Framework", "PyTorch + MobileNetV3", "Lightweight dual-stream spectral-spatial CNN architecture quantized for 15ms inference"),
        ("Web Frontend Framework", "React.js (Single Page App)", "Modern declarative UI framework with modular component state management"),
        ("Styling & Icons", "CSS3 Glassmorphism + Lucide", "Blur backdrop panels, vibrant neon status indicators, and clear vector icons"),
        ("Data Visualization", "Chart.js Engine", "High-performance HTML5 canvas charting rendering real-time 10-channel bar graphs"),
        ("Database & ORM", "PostgreSQL + SQLAlchemy", "Robust relational database with Python ORM for historical telemetry persistence")
    ]

    for r_idx, (cat, tech, why) in enumerate(tech_data, start=1):
        row_cells = table_tech.rows[r_idx].cells
        row_cells[0].text = cat
        row_cells[1].text = tech
        row_cells[2].text = why
        
        for c_idx in range(3):
            cell_p = row_cells[c_idx].paragraphs[0]
            if cell_p.runs:
                cell_p.runs[0].font.name = 'Arial'
                cell_p.runs[0].font.size = Pt(9.5)
                if c_idx == 0:
                    cell_p.runs[0].font.bold = True
            set_cell_background(row_cells[c_idx], "F8FAFC" if r_idx % 2 == 0 else "FFFFFF")

    # EXACT USER COST ESTIMATION TABLE
    add_sub_heading("Project Cost Estimation & Hardware Budget Profile (INR ₹)")
    add_p("Commercial precision agriculture survey drones cost over ₹50,000 to ₹1,00,000, placing them completely out of reach for small family farms and educational institutions. AgriSense achieves significant cost reduction by pairing accessible hardware components with 100% free open-source software:")

    table_cost = doc.add_table(rows=6, cols=3)
    table_cost.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_cost = ["Component Category", "Items Included", "Budget Profile"]
    
    for i, title in enumerate(headers_cost):
        c = table_cost.rows[0].cells[i]
        c.text = title
        p = c.paragraphs[0]
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(10)
            p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_background(c, "1E3A8A")

    cost_data_user = [
        ("Microcontrollers", "Raspi Zero W & ESP32 DevKit V1 Boards (Drone & Ground)", "₹2500"),
        ("Optical Sensors", "Adafruit AS7341 10-Channel Breakout Board", "₹2500"),
        ("Environmental Sensors", "Capacitive Soil Probe v1.2 + DHT22 + MQ-2", "₹1500"),
        ("Drone Body & Power", "Drone", "₹2500"),
        ("Total Cost", "Complete System Hardware Deployment", "₹9000")
    ]

    for r_idx, (cat, items, budg) in enumerate(cost_data_user, start=1):
        row_cells = table_cost.rows[r_idx].cells
        row_cells[0].text = cat
        row_cells[1].text = items
        row_cells[2].text = budg
        
        for c_idx in range(3):
            cell_p = row_cells[c_idx].paragraphs[0]
            if cell_p.runs:
                cell_p.runs[0].font.name = 'Arial'
                cell_p.runs[0].font.size = Pt(9.5)
                if r_idx == 5 or c_idx == 0:
                    cell_p.runs[0].font.bold = True
            
            fill_bg = "1E3A8A" if r_idx == 5 else ("F8FAFC" if r_idx % 2 == 0 else "FFFFFF")
            if r_idx == 5:
                cell_p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                set_cell_background(row_cells[c_idx], "1E3A8A")
            else:
                set_cell_background(row_cells[c_idx], fill_bg)

    add_p("\nFinancial Summary: Total hardware cost is ₹9,000, while software licensing costs are zero. This makes precision farming accessible to smallholder farmers worldwide!")

    # ==================== 7. WHAT MAKES AGRISENSE UNIQUE ====================
    add_sec_heading("7. What Makes AgriSense Unique")
    add_p("AgriSense stands apart from existing agricultural monitoring tools in the following ways:")

    add_bullet("Pre-Symptomatic Pathogen Detection —", "spots plant disease and cell wall breakdown 5.4 days before physical brown or yellow spots appear on leaf surfaces.")
    add_bullet("Dual-Stream Multi-Modal AI Fusion —", "combines 1D multi-spectral reflectance vectors with 2D spatial foliage images via cross-attention layers, outperforming standard RGB cameras.")
    add_bullet("Decoupled Aerial-Terrestrial Sensing Architecture —", "separates heavy soil probes onto stationary ground nodes, keeping aerial drone flight weight strictly at 82g for maximum flight endurance.")
    add_bullet("Significantly Cheaper Than Commercial Survey Drones —", "replaces $5,000–$10,000 industrial hyperspectral drones with an accessible ₹9,000 hardware setup.")
    add_bullet("Rust-Free Capacitive Soil Moisture Sensing —", "measures soil dielectric permittivity with high-frequency electrical capacitance, completely avoiding metal probe corrosion.")
    add_bullet("100% Free & Open-Source Software Stack —", "built with FastAPI, React, and PostgreSQL, eliminating monthly cloud subscription fees or proprietary vendor lock-in.")

    add_p("No existing agricultural platform combines all of these features. This makes AgriSense a genuinely new contribution to the field of accessible precision farming tooling.")

    # ==================== 8. TARGET USERS ====================
    add_sec_heading("8. Target Users")
    add_bullet("Smallholder Farmers & Agricultural Cooperatives", "who need an affordable, easy-to-use tool to inspect crop health and prevent disease outbreaks before yield loss occurs.")
    add_bullet("Agricultural Extension Officers & Agronomists", "who require fast field diagnostic tools to evaluate crop canopy health and advise farmers.")
    add_bullet("Precision Farming Researchers & University Labs", "who need an accessible 10-channel multi-spectral research platform for field optical experimentation.")
    add_bullet("Academic Examiners & Project Committees", "who evaluate full-stack IoT, asynchronous microservice APIs, and novel deep learning implementations.")

    # ==================== 9. EXPECTED OUTCOME ====================
    add_sec_heading("9. Expected Outcome")
    add_p("By the end of this project, we aim to deliver a fully working hardware-software platform with:")

    add_bullet("A feather-light 82g optical drone payload", "and stationary ground soil node capable of real-time multi-spectral and soil moisture telemetry collection.")
    add_bullet("An asynchronous Python FastAPI microservice backend", "processing JSON ingestion, Pydantic validation, and database persistence under 200ms latency.")
    add_bullet("A trained MM-SSNet multi-modal deep learning model", "achieving 97.4% accuracy in early asymptomatic plant disease classification with 5.4-day lead time.")
    add_bullet("A responsive React glassmorphism web dashboard", "featuring live Chart.js 10-channel spectral reflectance bar charts, telemetry cards, and color-coded hazard alerts.")
    add_bullet("A built-in simulation testing engine", "allowing live demonstration and examiner testing without physical hardware.")

    add_p("The project will demonstrate a full-stack IoT and AI application with microservice architecture, real-time wireless telemetry, and a technically challenging multi-modal deep learning model covering embedded C++, backend ASGI services, WebAssembly/API integration, and database design.")

    p_footer = doc.add_paragraph()
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_footer.paragraph_format.space_before = Pt(24)
    p_footer.paragraph_format.space_after = Pt(12)
    r_foot = p_footer.add_run("Submitted for approval as Final Year Project | AgriSense Project")
    r_foot.font.name = 'Arial'
    r_foot.font.size = Pt(10)
    r_foot.font.italic = True
    r_foot.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    doc.save(docx_path)
    print(f"Successfully generated AgriSense Synopsis with embedded images at: {docx_path}")

    # EXPORT MARKDOWN
    doc_read = Document(docx_path)
    md_lines = []
    
    md_lines.append("# AGRISENSE")
    md_lines.append("### A Low-Cost, Dual-Node IoT Drone Platform with Multi-Modal AI for Early Asymptomatic Crop Disease Diagnosis & Soil Health Monitoring")
    md_lines.append("*Project Synopsis | Final Year Project Proposal*\n")
    md_lines.append("* Kavya Bhandary 261796")
    md_lines.append("* Rehaan Shaikh 261831")
    md_lines.append("* Aditya Surve 261844\n")
    md_lines.append("---\n")

    for p in doc_read.paragraphs:
        t = p.text.strip()
        if not t or "AgriSense" == t or "A Low-Cost, Dual-Node" in t or "Project Synopsis |" in t or "Kavya Bhandary" in t:
            continue
            
        if t.startswith("1. ") or t.startswith("2. ") or t.startswith("3. ") or t.startswith("4. ") or t.startswith("5. ") or t.startswith("6. ") or t.startswith("7. ") or t.startswith("8. ") or t.startswith("9. "):
            md_lines.append(f"\n## {t}\n")
        elif p.style.name == 'List Bullet':
            md_lines.append(f"* {t}")
        elif t.startswith("Submitted for approval"):
            md_lines.append(f"\n\n---\n*{t}*\n")
        else:
            md_lines.append(f"{t}\n")

    md_lines.append("\n### Figure 5.1: Aerial Drone Multi-Spectral Payload System")
    md_lines.append(f"![Aerial Drone Sensor Payload](file:///{img1_path.replace(os.sep, '/')})")
    
    md_lines.append("\n### Figure 5.2: Terrestrial Ground Soil Hydration Node")
    md_lines.append(f"![Terrestrial Ground Soil Hydration Node](file:///{img2_path.replace(os.sep, '/')})")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Successfully exported AgriSense Project Synopsis MD with image links at: {md_path}")

if __name__ == "__main__":
    docs_dir = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs"
    syn_docx_path = os.path.join(docs_dir, "AgriSense_Project_Synopsis.docx")
    syn_md_path = os.path.join(docs_dir, "AgriSense_Project_Synopsis.md")
    
    generate_synopsis_with_images(syn_docx_path, syn_md_path)
    
    # Copy to OneDrive
    onedrive_syn = r"C:\Users\tempm\OneDrive\Documents\AgriSense_Project_Synopsis.docx"
    shutil.copy(syn_docx_path, onedrive_syn)
    print(f"Copied updated synopsis with images to OneDrive: {onedrive_syn}")

    # Copy to Downloads
    downloads_syn = r"C:\Users\tempm\Downloads\AgriSense_Project_Synopsis.docx"
    shutil.copy(syn_docx_path, downloads_syn)
    print(f"Copied updated synopsis with images to Downloads: {downloads_syn}")
