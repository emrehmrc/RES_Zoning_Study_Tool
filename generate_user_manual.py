"""
Generate a comprehensive User Manual for the Renewable Energy Zoning Dashboard.
Output: User_Manual.docx
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import os

doc = Document()

# ── Global styles ───────────────────────────────────────────────────
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = 1.15

# Heading styles
for level in range(1, 5):
    hs = doc.styles[f'Heading {level}']
    hs.font.name = 'Calibri'
    hs.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)  # dark blue

doc.styles['Heading 1'].font.size = Pt(22)
doc.styles['Heading 2'].font.size = Pt(16)
doc.styles['Heading 3'].font.size = Pt(13)
doc.styles['Heading 4'].font.size = Pt(11)

# Helper: add a styled table
def add_table(doc, headers, rows, col_widths=None):
    """Add a formatted table to the document."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="1B3A5C"/>')
        cell._tc.get_or_add_tcPr().append(shading)
    # Rows
    for ri, row_data in enumerate(rows):
        for ci, val in enumerate(row_data):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    return table


def add_note(doc, text, bold_prefix="Note: "):
    """Add a highlighted note paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(bold_prefix)
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x8B, 0x00, 0x00)
    run2 = p.add_run(text)
    run2.font.size = Pt(10)
    run2.font.italic = True


def add_tip(doc, text):
    """Add a tip paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    run = p.add_run("Tip: ")
    run.bold = True
    run.font.color.rgb = RGBColor(0x00, 0x6B, 0x3F)
    run.font.size = Pt(10)
    run2 = p.add_run(text)
    run2.font.size = Pt(10)
    run2.font.italic = True


def add_placeholder(doc, caption="[Screenshot placeholder]"):
    """Add a placeholder box for manual screenshot insertion."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(f"  {caption}  ")
    run.font.size = Pt(10)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)


# ════════════════════════════════════════════════════════════════════
#  COVER PAGE
# ════════════════════════════════════════════════════════════════════
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for _ in range(6):
    p.add_run("\n")

title_run = p.add_run("Renewable Energy Zoning Dashboard")
title_run.bold = True
title_run.font.size = Pt(28)
title_run.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub_run = p2.add_run("User Manual")
sub_run.font.size = Pt(20)
sub_run.font.color.rgb = RGBColor(0x3D, 0x7E, 0xAA)

p3 = doc.add_paragraph()
p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
p3.add_run("\n\n")
ver = p3.add_run("Version 2.0")
ver.font.size = Pt(14)
ver.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

p4 = doc.add_paragraph()
p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
date_run = p4.add_run("March 2026")
date_run.font.size = Pt(12)
date_run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

add_placeholder(doc, "[Company logo placeholder]")

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  TABLE OF CONTENTS PLACEHOLDER
# ════════════════════════════════════════════════════════════════════
doc.add_heading("Table of Contents", level=1)
p = doc.add_paragraph()
p.add_run("(Right-click → Update Field to generate the Table of Contents after inserting screenshots.)")
p.runs[0].font.italic = True
p.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

# Insert a TOC field
p_toc = doc.add_paragraph()
run_toc = p_toc.add_run()
fldChar1 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
run_toc._r.append(fldChar1)
run_toc2 = p_toc.add_run()
instrText = parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText>')
run_toc2._r.append(instrText)
run_toc3 = p_toc.add_run()
fldChar2 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="separate"/>')
run_toc3._r.append(fldChar2)
run_toc4 = p_toc.add_run("(Table of Contents — press Ctrl+A then F9 to update)")
run_toc4.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
run_toc5 = p_toc.add_run()
fldChar3 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>')
run_toc5._r.append(fldChar3)

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  SECTION 1 — INTRODUCTION
# ════════════════════════════════════════════════════════════════════
doc.add_heading("1. Introduction", level=1)

doc.add_heading("1.1 Purpose and Scope", level=2)
doc.add_paragraph(
    "The Renewable Energy Zoning Dashboard is a GIS-based web application designed "
    "for identifying, evaluating, and ranking optimal sites for renewable energy projects. "
    "The platform supports three distinct project modes:"
)
bullets = [
    ("Solar PV Zoning", "Identifies and scores land parcels suitable for photovoltaic solar installations based on solar irradiation, terrain, land use, and infrastructure proximity."),
    ("On-Shore Wind Zoning", "Evaluates inland areas for wind turbine deployment using wind resource data, terrain constraints, environmental exclusions, and grid connectivity."),
    ("Off-Shore Wind Zoning", "Analyzes maritime Exclusive Economic Zones (EEZ) for offshore wind farms, incorporating bathymetry, marine constraints, port proximity, and subsea infrastructure."),
]
for title, desc in bullets:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + " — ")
    run.bold = True
    p.add_run(desc)

doc.add_paragraph(
    "The application guides the user through a structured five-step analytical pipeline — "
    "from defining the study area and generating a spatial grid, through multi-layer raster analysis, "
    "weighted scoring, spatial clustering, and finally financial viability assessment. "
    "Each step builds upon the results of the previous one, creating a comprehensive site suitability analysis."
)

doc.add_heading("1.2 Technology Stack", level=2)
doc.add_paragraph(
    "The dashboard is built on a modern full-stack architecture orchestrated with Docker Compose:"
)
add_table(doc,
    ["Component", "Technology", "Description"],
    [
        ["Frontend", "Next.js 14, React 18, Tailwind CSS, Leaflet", "Interactive UI with map visualization at port 3000"],
        ["Backend", "Django 4.2, Django REST Framework", "REST API serving analysis endpoints at port 8000"],
        ["GIS Engines", "GeoPandas, Rasterio, GDAL 3.11, NetworkX", "Spatial analysis, raster processing, graph-based clustering"],
        ["Deployment", "Docker Compose", "Two-container setup with shared data volumes"],
    ],
    col_widths=[3, 5.5, 7.5]
)

doc.add_heading("1.3 Five-Step Analytical Pipeline", level=2)
doc.add_paragraph(
    "The entire workflow is organized into four sequential tabs in the dashboard interface, "
    "each corresponding to one or more steps of the pipeline:"
)

add_table(doc,
    ["Step", "Dashboard Tab", "Purpose", "Key Output"],
    [
        ["1", "Gridization", "Define the study area boundary and divide it into uniform rectangular grid cells", "Grid of cells covering the selected region"],
        ["2", "Layer Calculation", "Analyze each grid cell against multiple GIS raster layers (distances, coverage, statistics)", "Per-cell metrics for each configured layer"],
        ["3", "Scoring", "Assign weighted scores to each cell based on configurable thresholds; apply hard exclusion constraints", "FINAL_GRID_SCORE per cell (0–100)"],
        ["4", "Cluster & Aggregation", "Group adjacent high-scoring cells into project clusters; evaluate transmission connections; calculate CAPEX, LCOE, and payback period", "Ranked clusters with financial feasibility metrics"],
    ],
    col_widths=[1, 3, 5.5, 5.5]
)

doc.add_paragraph(
    "Results are visualized on an interactive Leaflet map at each stage, and can be downloaded "
    "as CSV files for further analysis in external tools such as QGIS or Excel."
)

doc.add_heading("1.4 Session Management", level=2)
doc.add_paragraph(
    "When a project mode is selected, the backend assigns a unique Session ID (UUID). "
    "This identifier is attached to every subsequent API request via the X-Session-ID HTTP header. "
    "All intermediate results — grid data, analysis outputs, scoring tables — are persisted "
    "server-side as serialized files (pickle format) under a session-specific directory. "
    "This allows the user to progress through the pipeline at their own pace without losing data."
)
add_note(doc, "Sessions are temporary. If the backend container is restarted or the session is reset, all intermediate results will be lost. Always download important results before closing the application.")

doc.add_heading("1.5 Getting Started", level=2)
doc.add_paragraph(
    "To launch the dashboard, ensure Docker is installed and run the following command "
    "from the project root directory:"
)
p = doc.add_paragraph()
run = p.add_run("    docker compose up")
run.font.name = 'Consolas'
run.font.size = Pt(10)

doc.add_paragraph("Once the containers are running:")
steps = [
    "Open a web browser and navigate to http://localhost:3000",
    "The Landing Page will appear with three project mode cards",
    "Click on a project mode to begin (e.g., \"Select Solar PV Zoning\")",
    "You will be redirected to the main Dashboard view with four analysis tabs",
]
for s in steps:
    doc.add_paragraph(s, style='List Number')

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  SECTION 2 — SOLAR PV ZONING STUDY
# ════════════════════════════════════════════════════════════════════
doc.add_heading("2. Solar PV Zoning Study — Detailed Software Functionalities", level=1)

doc.add_paragraph(
    "This section provides a comprehensive walkthrough of the Solar PV Zoning mode, "
    "covering every screen, button, input field, and interactive element from the moment "
    "the application is opened. While this guide focuses on the Solar PV workflow, "
    "the On-Shore and Off-Shore Wind modes follow the same four-tab structure with "
    "project-specific layers and parameters noted where applicable."
)

# ── 2.0 Landing Page ───────────────────────────────────────────────
doc.add_heading("2.0 Landing Page — Project Mode Selection", level=2)

add_placeholder(doc, "[Screenshot: Landing page with three project cards]")

doc.add_paragraph(
    "Upon navigating to the application URL, the user is presented with the Landing Page. "
    "This page serves as the entry point and project mode selector."
)

doc.add_heading("2.0.1 Page Layout", level=3)
p = doc.add_paragraph(
    "The Landing Page features a dark gradient background (slate tones) with the following elements:"
)
elements = [
    ("Main Title", "\"Renewable Energy Zoning Dashboard\" — displayed prominently at the top center."),
    ("Subtitle", "\"Select a project mode to begin analysis\" — guides the user to choose a mode."),
    ("About Button", "Located in the top-left corner. Labeled \"About\" — opens an informational modal describing the platform's purpose, pipeline steps, and technical architecture."),
    ("OST Logo", "Displayed in the top-right corner of the page."),
    ("Project Mode Cards", "Three large selection cards arranged horizontally (responsive layout)."),
]
for title, desc in elements:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_heading("2.0.2 Project Mode Cards", level=3)
doc.add_paragraph("Each card contains:")
items = [
    "A project-specific icon image (Solar panel, wind turbine on land, or offshore turbine)",
    "The project mode title (e.g., \"Solar PV Zoning\")",
    "A brief list of key analysis capabilities",
    "A selection button (e.g., \"Select Solar PV Zoning\")",
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

add_table(doc,
    ["Card", "Title", "Key Capabilities", "Button Color"],
    [
        ["Solar PV", "Solar PV Zoning", "Solar PV Potential Analysis; Slope & Terrain & Constraints; Proximity to Transmission Lines", "Orange"],
        ["On-Shore Wind", "On-Shore Wind Zoning", "Wind Resource & Potential; Turbine Specific Suitability; Environmental & Social Constraints", "Dark Blue"],
        ["Off-Shore Wind", "Off-Shore Wind Zoning", "Wind Resource & Potential; Turbine Specific Suitability; Marine Constraints", "Cyan/Blue"],
    ],
    col_widths=[2.5, 3.5, 6, 2.5]
)

doc.add_paragraph(
    "Clicking a card initiates a backend call to create a new session with the selected project type. "
    "A loading spinner appears on the card during this process. Upon success, the user is automatically "
    "redirected to the main Dashboard."
)

doc.add_heading("2.0.3 About Modal", level=3)
doc.add_paragraph(
    "The About modal provides detailed information organized into sections: "
    "Overview, How It Works (5-Step Pipeline), Solar PV Mode, On-Shore Wind Mode, "
    "Off-Shore Wind Mode, Financial Analysis, Technical Architecture, and Data & Outputs. "
    "The modal can be closed by clicking the X button or clicking outside the modal area."
)

doc.add_page_break()

# ── 2.0.5 Main Dashboard Layout ────────────────────────────────────
doc.add_heading("2.0.4 Main Dashboard Layout", level=2)

add_placeholder(doc, "[Screenshot: Dashboard overview with sidebar and tab bar visible]")

doc.add_paragraph(
    "After selecting Solar PV mode, the Dashboard page loads. The interface consists of:"
)

doc.add_heading("Header Bar", level=3)
items = [
    ("Color Accent Bar", "A thin colored line at the very top of the page (orange for Solar PV, dark blue for On-Shore Wind, cyan for Off-Shore Wind) provides instant visual identification of the active project mode."),
    ("Project Icon", "The project-specific icon is displayed on the left side of the header."),
    ("Application Title", "Shown next to the icon, pulled from the project configuration."),
    ("Mode Badge", "Displays the active project type (e.g., \"Solar\") in the header's right area."),
    ("Switch Mode Button", "Labeled \"Switch Mode\" — resets the current session entirely and returns to the Landing Page for a new project selection."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_heading("Sidebar (Left Panel)", level=3)
doc.add_paragraph(
    "A fixed-width sidebar (256 pixels) on the left side displays the project status at a glance:"
)
items = [
    ("Status Title", "Shows the project type followed by \"Status\" (e.g., \"Solar Status\")."),
    ("Step Indicators", "Four status rows — Grid, Layers, Scoring, Clusters — each showing a checkmark (completed) or hourglass (pending) icon. When a step is completed, it also displays the count of items (e.g., \"1,250 cells\" for Grid, \"5 layer(s)\" for Layers)."),
    ("Reset Project Button", "A red button labeled \"Reset Project\" at the bottom of the sidebar. Prompts for confirmation before clearing all project data while keeping the same project mode active."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_heading("Tab Bar (Main Content Area)", level=3)
doc.add_paragraph(
    "The main content area occupies the remaining space to the right of the sidebar. "
    "At the top, a horizontal tab bar provides navigation between the four pipeline steps:"
)
add_table(doc,
    ["Tab #", "Label", "Pipeline Step"],
    [
        ["1", "Gridization", "Define study area & create grid"],
        ["2", "Layer Calculation", "Raster analysis across all layers"],
        ["3", "Scoring", "Weighted scoring & exclusion"],
        ["4", "Cluster & Aggregation", "Clustering, connection scoring, financials"],
    ],
    col_widths=[1.5, 4, 8]
)
doc.add_paragraph(
    "The active tab is highlighted with a distinct background color and bottom border accent. "
    "Inactive tabs are shown in muted gray tones and become highlighted on hover."
)

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  2.1 TAB 1 — GRIDIZATION
# ════════════════════════════════════════════════════════════════════
doc.add_heading("2.1 Tab 1 — Gridization", level=2)

add_placeholder(doc, "[Screenshot: Gridization tab — Generate New Grid mode]")

doc.add_paragraph(
    "The Gridization tab is the first step in the analytical pipeline. Its purpose is to define "
    "the geographic study area and subdivide it into a uniform grid of rectangular cells. "
    "Each cell will later be individually analyzed, scored, and potentially clustered."
)

doc.add_heading("2.1.1 Mode Selection", level=3)
doc.add_paragraph(
    "At the top of the tab, two toggle buttons allow the user to choose between:"
)
items = [
    ("Generate New Grid", "Create a fresh grid by selecting a geographic boundary and specifying cell dimensions. This is the primary workflow."),
    ("Upload Existing Grid", "Import a previously created grid as a CSV file. Useful for re-running analysis on a previously defined study area."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

# Generate New Grid
doc.add_heading("2.1.2 Generate New Grid", level=3)
doc.add_paragraph(
    "When \"Generate New Grid\" is selected, the interface splits into two columns:"
)

doc.add_heading("Left Column: Boundary Definition", level=4)
doc.add_paragraph(
    "This section determines the geographic area that will be divided into grid cells."
)

doc.add_paragraph("For Solar PV and On-Shore Wind modes, two boundary methods are available:")
items = [
    ("Select Country", "Choose from a dropdown list of European countries. The country boundaries are derived from the NUTS (Nomenclature of Territorial Units for Statistics) dataset at the national level (LEVL_CODE = 0). The dropdown is populated automatically on load."),
    ("Upload File", "Upload a custom boundary file (shapefile or GeoJSON). This option allows users to analyze any arbitrary region."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_paragraph(
    "For Off-Shore Wind mode, the boundary source is fixed to EEZ (Exclusive Economic Zone) selection. "
    "A dropdown is populated with available European maritime zones from the EEZ shapefile dataset."
)

add_note(doc, "Once a boundary is selected, an interactive map preview appears below the form, showing the boundary polygon and a grid overlay in real time.")

doc.add_heading("Right Column: Grid Parameters", level=4)
doc.add_paragraph("The grid dimensions depend on the project type:")

doc.add_heading("Solar PV:", level=4)
add_table(doc,
    ["Parameter", "Input Type", "Range", "Default", "Description"],
    [
        ["Grid Width (m)", "Number", "100 – 10,000", "1,000 m", "Horizontal dimension of each grid cell in meters"],
        ["Grid Height (m)", "Number", "100 – 10,000", "1,000 m", "Vertical dimension of each grid cell in meters"],
    ],
    col_widths=[3, 2, 2.5, 2, 5]
)

doc.add_heading("On-Shore / Off-Shore Wind:", level=4)
add_table(doc,
    ["Parameter", "Input Type", "Range", "Default", "Description"],
    [
        ["Turbine Diameter (m)", "Number", "10 – 500", "200 m", "Rotor diameter; grid dimensions are auto-calculated as 3D × 5D"],
    ],
    col_widths=[3, 2, 2.5, 2, 5]
)
doc.add_paragraph(
    "For wind projects, the grid cell size is calculated automatically based on standard turbine spacing rules: "
    "the width is set to 3 times the turbine diameter, and the height to 5 times the diameter. "
    "For example, a 200m diameter turbine yields a 600m × 1000m grid cell. "
    "An information box below the input field displays the computed dimensions in real time."
)
add_note(doc, "Input validation is applied in real time. If a value falls outside the allowed range, the input border turns red and an error message is displayed. The value is automatically clamped to the valid range when the field loses focus.")

doc.add_heading("2.1.3 Map Preview", level=3)

add_placeholder(doc, "[Screenshot: Map preview showing boundary polygon and grid overlay]")

doc.add_paragraph(
    "When a boundary (country, EEZ zone, or uploaded file) is selected, an interactive map "
    "appears below the form. The map provides:"
)
items = [
    ("Boundary Polygon", "The selected region boundary displayed as a blue polygon with semi-transparent blue fill."),
    ("Grid Overlay", "A visualization of the grid cells as colored lines, computed in real time based on the specified cell dimensions. If the number of grid lines exceeds 600, the preview adaptively reduces detail to maintain performance."),
    ("Base Map Toggle", "Two radio buttons in the top-right corner allow switching between \"Street\" (OpenStreetMap) and \"Satellite\" (ArcGIS World Imagery) base maps."),
    ("Layer Toggles", "Checkboxes to show/hide the boundary and grid overlay independently."),
    ("Grid Information", "A small info panel in the bottom-left corner displays the grid cell size and the estimated total number of cells."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_heading("2.1.4 Create Grid Button", level=3)
doc.add_paragraph(
    "The \"Create Grid\" button (blue, full-width) at the bottom of the parameters section "
    "initiates the grid generation process. When clicked:"
)
steps = [
    "A processing overlay appears with an animated indicator and the message \"Creating grid cells...\"",
    "The backend engine (FastGridEngine) reprojects the boundary to Web Mercator (EPSG:3857), calculates the bounding box, and generates rectangular cells",
    "Only cells whose centroids fall within the boundary polygon are retained",
    "Each cell is assigned a unique cell_id and its geometry is stored as WKT (Well-Known Text)",
    "The overlay disappears and results are displayed",
]
for s in steps:
    doc.add_paragraph(s, style='List Number')

doc.add_heading("2.1.5 Upload Existing Grid", level=3)
doc.add_paragraph(
    "When the \"Upload Existing Grid\" mode is selected, a file input appears. "
    "The user can upload a CSV file that must contain at least the following columns:"
)
items = ["cell_id — a unique identifier for each grid cell", "wkt — the Well-Known Text geometry representation of each cell"]
for item in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(item.split(" — ")[0])
    run.bold = True
    run.font.name = 'Consolas'
    run.font.size = Pt(10)
    p.add_run(" — " + item.split(" — ")[1])

doc.add_heading("2.1.6 Grid Results", level=3)

add_placeholder(doc, "[Screenshot: Grid results with success message and preview table]")

doc.add_paragraph("After successful grid creation, the following elements appear:")
items = [
    ("Success Message", "A green banner displays the confirmation message (e.g., \"Grid created successfully\") along with the total number of cells generated."),
    ("Download CSV Button", "Labeled \"Download CSV\" — allows the user to export the full grid dataset as a comma-separated file for external use."),
    ("Preview Table", "A scrollable table showing the first 20 rows of the generated grid, displaying all columns including cell_id, bounding coordinates (left, top, right, bottom), WKT geometry, and center point coordinates in both EPSG:3857 and EPSG:4326."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  2.2 TAB 2 — LAYER CALCULATION
# ════════════════════════════════════════════════════════════════════
doc.add_heading("2.2 Tab 2 — Layer Calculation", level=2)

add_placeholder(doc, "[Screenshot: Layer Calculation tab with layers configured]")

doc.add_paragraph(
    "The Layer Calculation tab (labeled \"Layer Calculation\" in the interface) is the second pipeline step. "
    "Here, the user configures which GIS raster layers to analyze and how each layer should be processed "
    "for every grid cell. This step transforms raw raster data into per-cell numerical metrics."
)

doc.add_heading("2.2.1 Prerequisites", level=3)
doc.add_paragraph(
    "This tab requires a grid to have been created in Step 1. If no grid data is available, "
    "a warning message is displayed: \"No grid data available. Complete Step 1 first.\""
)

doc.add_heading("2.2.2 Add New Layer", level=3)
doc.add_paragraph(
    "The \"Add New Layer\" section provides a form to add raster layers for analysis. "
    "Two modes are available via toggle buttons:"
)

doc.add_heading("Predefined List Mode", level=4)
doc.add_paragraph(
    "This mode presents a dropdown of predefined layer names that are specific to the active project type. "
    "When a predefined layer is selected, the system automatically assigns the appropriate analysis modes "
    "based on the project configuration."
)
doc.add_paragraph("For Solar PV, the predefined layers are organized into categories:")

add_table(doc,
    ["Category", "Layer Names", "Default Modes"],
    [
        ["Infrastructure – Transmission Lines", "Distance to 110kV Line, Distance to 220kV Line, Distance to 400kV Line", "distance"],
        ["Infrastructure – Substations", "Distance to 110kV Substation, Distance to 220kV Substation, Distance to 400kV Substation", "distance"],
        ["Land Use & Environment", "Agricultural Areas, Forest, Urban/Residential/Industrial, Military, Protected Habitats", "distance + coverage"],
        ["Natural Resources", "Energy Sources, Hydrography, Mineral Resources", "distance + coverage"],
        ["Risk & Climate", "Natural Risk Zones, Slope (%), Solar Irradiation, Temperature", "Varies: distance, or min/max/mean"],
        ["Transportation", "Transport Networks", "distance"],
    ],
    col_widths=[3, 5.5, 3.5]
)

add_note(doc, "On-Shore Wind and Off-Shore Wind modes have their own predefined layer lists with different categories. For example, On-Shore Wind includes Altitude and Wind layers, while Off-Shore Wind includes Bathymetry, Ports, and Subsea Cables.")

doc.add_heading("Custom Layer Mode", level=4)
doc.add_paragraph(
    "In Custom mode, the user can define a new layer from scratch:"
)
items = [
    ("Custom Layer Name", "A free-text input for the layer name (e.g., \"My Custom Layer\")."),
    ("Analysis Modes", "A set of toggle pill buttons for selecting one or more modes. Available modes are: distance, coverage, mean, max, min, median, std. Multiple modes can be selected simultaneously. Selected modes appear in blue."),
    ("Target Pixel Value", "Shown only when \"distance\" or \"coverage\" is among the selected modes. This numeric input (0–255) specifies which raster pixel value to target for distance calculation or coverage percentage computation. Default: 1."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_heading("Raster File Selection", level=4)
doc.add_paragraph("Regardless of mode, a raster file (.tif) must be specified for each layer. Two methods are available:")
items = [
    ("File Browser", "Click the \"Choose File\" button to open a file selection dialog. This launches either a native OS file picker or a built-in file browser modal. The browser shows the directory structure, listing only .tif/.tiff files. Recent folders are remembered for quick access."),
    ("Manual Path Entry", "A text field allows pasting the full file path manually (e.g., \"C:\\data\\solar_irradiation.tif\")."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

add_note(doc, "All raster files must be in EPSG:3857 (Web Mercator) projection. The system validates the CRS on submission and rejects files with incompatible projections with a clear error message.")

doc.add_heading("Add Layer Button", level=4)
doc.add_paragraph(
    "Clicking the \"Add Layer\" button validates the input and adds the layer to the configured layers list. "
    "A layer that has already been added cannot be duplicated — it is automatically removed from the predefined dropdown."
)

doc.add_heading("2.2.3 Configured Layers List", level=3)

add_placeholder(doc, "[Screenshot: Configured layers list with multiple layers]")

doc.add_paragraph(
    "Below the \"Add New Layer\" form, a \"Configured Layers\" section displays all currently added layers. "
    "The count is shown in the section title (e.g., \"Configured Layers (5)\")."
)
doc.add_paragraph("Each layer card shows:")
items = [
    "An icon indicating predefined (tag icon) vs. custom (gear icon) origin",
    "The layer name",
    "The assigned analysis modes (comma-separated)",
    "The filename of the associated raster file",
    "A red \"×\" button to remove the layer from the list",
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_heading("2.2.4 Layer Map Preview", level=3)
doc.add_paragraph(
    "An interactive Leaflet map below the layer list provides spatial context. It displays:"
)
items = [
    ("Boundary Layer", "The study area boundary polygon (toggleable)."),
    ("Grid Layer", "The grid cells overlay (toggleable)."),
    ("Raster Layer Previews", "Each configured layer can be toggled on/off individually. When toggled on for the first time, the system requests a raster preview image (base64-encoded PNG with a blue-cyan-green-yellow-red colormap). The preview is overlaid on the map at 70% opacity."),
    ("Base Map Toggle", "Street (OpenStreetMap) or Satellite (ArcGIS) base maps."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_heading("2.2.5 Run Analysis", level=3)
doc.add_paragraph(
    "The \"Run Analysis\" button (green, full-width) starts the raster analysis pipeline. "
    "This is a long-running operation that processes each layer against every grid cell:"
)
steps = [
    "A processing overlay appears with animated dots and a progress message",
    "The backend loads the grid data and reprojects it to match the raster CRS",
    "For each configured layer, the UniversalRasterScorer engine computes the requested metrics. The engine uses memory-aware chunking for large rasters, automatically splitting the grid spatially when memory limits are approached.",
    "Analysis modes are computed per cell: distance (km to nearest target pixel via GDAL proximity), coverage (percentage of target pixels within cell), and statistical aggregates (mean, max, min, median, std) of pixel values within each cell",
    "Results are merged into a single DataFrame and stored in the session",
    "The overlay disappears and results are displayed",
]
for s in steps:
    doc.add_paragraph(s, style='List Number')

add_tip(doc, "Analysis time depends on the number of layers, grid cell count, and raster resolution. Large study areas with high-resolution rasters may take several minutes. The system processes layers in parallel when memory allows.")

doc.add_heading("2.2.6 Analysis Results", level=3)

add_placeholder(doc, "[Screenshot: Analysis results with statistics cards and data table]")

doc.add_paragraph("After successful analysis, the results section displays:")

doc.add_heading("Success Banner", level=4)
doc.add_paragraph(
    "A green-bordered container with the success message and a \"Download\" button for exporting "
    "the full results as a CSV file."
)

doc.add_heading("Statistics Cards", level=4)
doc.add_paragraph(
    "A grid of summary statistic cards (up to 4 per row) — one for each computed column. "
    "Each card shows the column name, the average value (avg), and the min–max range. "
    "This provides a quick overview of data distributions across the study area."
)

doc.add_heading("Data Table", level=4)
doc.add_paragraph(
    "A full-featured interactive data table (powered by TanStack React Table) displays the analysis results:"
)
items = [
    ("Row Count Selector", "A dropdown to control how many rows are displayed per page (10, 25, 50, or 100)."),
    ("Sortable Columns", "Click any column header to sort ascending (▲) or descending (▼)."),
    ("Column Filters", "A text input below each column header enables real-time filtering."),
    ("Pagination", "Navigation buttons (first, previous, next, last) and a page indicator."),
    ("Number Formatting", "Numeric values are rounded to 3 decimal places for readability."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  2.3 TAB 3 — SCORING
# ════════════════════════════════════════════════════════════════════
doc.add_heading("2.3 Tab 3 — Scoring", level=2)

add_placeholder(doc, "[Screenshot: Scoring tab with layer configuration cards]")

doc.add_paragraph(
    "The Scoring tab (labeled \"Scoring\" in the interface) is the third pipeline step. "
    "In this step, the raw metric values from Step 2 are converted into normalized scores (0–100) "
    "using configurable scoring levels and weights. Hard exclusion constraints can also be applied "
    "to eliminate cells that violate critical thresholds."
)

doc.add_heading("2.3.1 Prerequisites", level=3)
doc.add_paragraph(
    "This tab requires analysis results from Step 2. If no analysis data is available, "
    "a warning message is displayed: \"No analysis data available. Complete Step 2 first.\""
)

doc.add_heading("2.3.2 Import CSV", level=3)
doc.add_paragraph(
    "A header button labeled \"Import CSV\" allows importing a previously configured scoring table. "
    "This loads the column names and any pre-assigned weights/levels from the CSV file, "
    "saving time when reusing a known configuration."
)

doc.add_heading("2.3.3 Layer Configuration Cards", level=3)
doc.add_paragraph(
    "For each layer analyzed in Step 2, a configuration card is displayed. "
    "Each card has a header showing the layer name and its available modes (e.g., \"Modes: distance, coverage\"). "
    "Three mode buttons on the right side of the header control how the layer participates in scoring:"
)

add_table(doc,
    ["Mode", "Icon", "Description"],
    [
        ["Scoring", "📊", "The layer's metrics are scored using configurable thresholds and contribute to the final weighted score"],
        ["Exclusion", "🚫", "The layer is used as a hard constraint — cells exceeding a threshold receive a score of zero"],
        ["Skip", "⏭️", "The layer is excluded from the scoring calculation entirely"],
    ],
    col_widths=[2.5, 1.5, 10]
)

doc.add_heading("Scoring Mode Configuration", level=4)
doc.add_paragraph("When a layer is set to \"Scoring\" mode, the following options appear:")

doc.add_heading("Weight", level=4)
p = doc.add_paragraph()
run = p.add_run("Layer Weight (%): ")
run.bold = True
p.add_run(
    "A numeric input (0–100) that determines how much this layer contributes to the final combined score. "
    "The weights across all scoring layers should ideally sum to 100%, but this is not strictly enforced."
)

doc.add_heading("Max Coverage for Distance Scoring", level=4)
p = doc.add_paragraph()
p.add_run(
    "For layers with both distance and coverage modes (\"distance_coverage\" type), an additional input "
    "labeled \"Max Coverage for Distance Scoring (%)\" appears. This threshold (0–100, default 5%) "
    "determines when to bypass distance scoring: if a cell's coverage for the layer exceeds this value, "
    "the distance score is automatically set to the minimum level (worst score) because the obstacle "
    "already significantly overlaps the cell."
)

doc.add_heading("Scoring Levels", level=4)

add_placeholder(doc, "[Screenshot: Scoring levels grid with 4 level columns]")

doc.add_paragraph(
    "Four scoring level columns (Level 1 through Level 4) define the value-to-score mapping. "
    "Each level contains three input fields:"
)
add_table(doc,
    ["Field", "Description"],
    [
        ["Max", "The upper bound of the value range for this level"],
        ["Min", "The lower bound of the value range for this level"],
        ["Score", "The score (0–100) assigned to cells whose metric falls within this range"],
    ],
    col_widths=[2, 12]
)
doc.add_paragraph(
    "Typically, Level 1 represents the most favorable range (highest score) and Level 4 the least favorable. "
    "For example, for a distance-to-transmission-line layer:"
)
add_table(doc,
    ["Level", "Min (km)", "Max (km)", "Score", "Interpretation"],
    [
        ["Level 1", "10", "999", "100", "Far from obstacles — best"],
        ["Level 2", "5", "10", "70", "Moderate distance — good"],
        ["Level 3", "2", "5", "40", "Close proximity — fair"],
        ["Level 4", "0", "2", "10", "Very close — poor"],
    ],
    col_widths=[2, 2, 2, 1.5, 5.5]
)
add_note(doc, "If the minimum value is greater than or equal to the maximum for any level, the level card will be highlighted in red with the warning \"min ≥ max\" to indicate an invalid configuration.")

doc.add_heading("Exclusion Mode Configuration", level=4)
doc.add_paragraph(
    "When a layer is set to \"Exclusion\" mode, a simpler configuration appears:"
)
items = [
    ("Metric Selector", "If the layer has multiple analysis modes (e.g., distance and coverage), a dropdown allows the user to select which metric column to use for the exclusion constraint."),
    ("Maximum Allowed Value", "A numeric input specifying the upper limit. Any cell where the selected metric exceeds this value will have its FINAL_GRID_SCORE set to zero."),
    ("Constraint Preview", "The interface shows the constraint formula (e.g., \"Agricultural_Areas_coverage_pct ≤ 30\") for clarity."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

p = doc.add_paragraph()
run = p.add_run("Warning: ")
run.bold = True
run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
p.add_run("\"Cells exceeding the maximum threshold will have final score = 0\" — this hard exclusion permanently removes cells from consideration in subsequent steps.")

doc.add_heading("2.3.4 Run Level Scoring", level=3)
doc.add_paragraph(
    "The \"Run Level Scoring\" button (purple, full-width) starts the scoring calculation. The process:"
)
steps = [
    "Collects the scoring configuration (levels, weights) and constraint configuration from all layer cards",
    "For each scoring layer, assigns scores to cells based on which level range their metric falls into",
    "Applies the layer weight to compute the weighted contribution",
    "Combines all weighted layer scores into FINAL_GRID_SCORE (sum of all weighted contributions)",
    "Applies hard exclusion constraints — cells violating any constraint have their score set to 0",
    "Records exclusion reasons for transparency (EXCLUSION_REASONS column)",
]
for s in steps:
    doc.add_paragraph(s, style='List Number')

doc.add_heading("2.3.5 Scoring Results", level=3)

add_placeholder(doc, "[Screenshot: Scoring results with distribution cards and preview table]")

doc.add_paragraph("After scoring completes, a comprehensive results section appears:")

doc.add_heading("Score Distribution Cards", level=4)
doc.add_paragraph("Six color-coded cards display the distribution of cells across quality categories:")

add_table(doc,
    ["Category", "Score Range", "Color", "Description"],
    [
        ["Excellent", "≥ 80", "Green", "Highly suitable cells — top candidates for project development"],
        ["Good", "60 – 80", "Light Green", "Well-suited cells with minor limitations"],
        ["Fair", "40 – 60", "Yellow", "Moderate suitability — may require additional evaluation"],
        ["Poor", "20 – 40", "Orange", "Low suitability — significant constraints present"],
        ["Very Poor", "< 20", "Red", "Unsuitable cells — multiple unfavorable factors"],
        ["Excluded", "= 0", "Gray", "Hard-excluded cells that violated one or more constraint thresholds"],
    ],
    col_widths=[2.5, 2, 2, 7.5]
)

doc.add_heading("Summary Statistics", level=4)
doc.add_paragraph("Below the distribution cards, three key metrics are displayed:")
items = [
    "Total: Total number of cells processed",
    "Excluded: Number of cells with score = 0 due to constraints",
    "Avg Score: The average FINAL_GRID_SCORE across all non-excluded cells",
]
for item in items:
    p = doc.add_paragraph(style='List Bullet')
    parts = item.split(": ")
    run = p.add_run(parts[0] + ": ")
    run.bold = True
    p.add_run(parts[1])

doc.add_heading("Exclusion Summary Table", level=4)
doc.add_paragraph(
    "If any exclusion constraints were applied, a summary table shows the breakdown per layer: "
    "for each constraint layer, it lists the column used, the threshold applied, and the number "
    "of cells excluded by that specific constraint."
)

doc.add_heading("Download & Data Preview", level=4)
doc.add_paragraph(
    "A \"Download\" button exports the full scored dataset as a CSV file (semicolon-separated with comma decimals). "
    "A scrollable data preview table (same interactive features as in Step 2) shows the results "
    "including the FINAL_GRID_SCORE and EXCLUSION_REASONS columns."
)

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  2.4 TAB 4 — CLUSTER & AGGREGATION
# ════════════════════════════════════════════════════════════════════
doc.add_heading("2.4 Tab 4 — Cluster & Aggregation", level=2)

add_placeholder(doc, "[Screenshot: Cluster tab overview]")

doc.add_paragraph(
    "The Cluster & Aggregation tab is the final pipeline step, combining spatial clustering, "
    "transmission connection scoring, and financial analysis. This step groups adjacent high-scoring "
    "grid cells into project-sized clusters, evaluates the optimal grid connection for each cluster, "
    "and computes financial feasibility metrics."
)

doc.add_heading("2.4.1 Prerequisites", level=3)
doc.add_paragraph(
    "This tab requires scored results from Step 3. If no scoring data is available, "
    "a warning message is displayed: \"No scoring data available. Complete Step 3 first.\""
)

doc.add_heading("2.4.2 Data Source & Capacity Setup", level=3)
doc.add_paragraph(
    "The top section of the tab is divided into two columns:"
)

doc.add_heading("Data Source (Left Column)", level=4)
doc.add_paragraph("Two toggle buttons control the data input:")
items = [
    ("Step 3 Results", "Uses the scored DataFrame from the previous step directly. This is the standard workflow."),
    ("Upload CSV", "Allows uploading an external CSV file with pre-scored data. The file must contain wkt and FINAL_GRID_SCORE columns. The separator is automatically detected (semicolon with comma decimals)."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

doc.add_heading("Capacity Constraints (Right Column)", level=4)
add_table(doc,
    ["Parameter", "Input Type", "Range/Step", "Default", "Description"],
    [
        ["Nominal Capacity (MW)", "Number", "Min 0.1, Step 0.5", "13 MW", "The assumed power capacity of each grid cell. For wind projects, this represents the turbine rating per cell."],
        ["Max Cluster Capacity (MW)", "Number", "Min 10, Step 10", "250 MW", "The maximum allowed total capacity per cluster. Clusters exceeding this limit are automatically split."],
        ["Adjust capacity for coverage", "Checkbox", "On/Off", "Checked", "When enabled, each cell's nominal capacity is reduced proportionally based on land-use coverage. For example, if a cell has 20% forest coverage and 10% urban coverage, the effective capacity is reduced to 70% of nominal."],
    ],
    col_widths=[3.5, 2, 2, 1.5, 6]
)

doc.add_heading("2.4.3 Reference Data Configuration", level=3)
doc.add_paragraph(
    "Below the capacity setup, a tabbed interface with three sub-tabs allows the user to review "
    "and customize the reference parameters used for connection scoring and financial analysis."
)

doc.add_heading("Sub-Tab A: Connection Rules", level=4)

add_placeholder(doc, "[Screenshot: Connection Rules table with editable scoring rules]")

doc.add_paragraph(
    "This table defines how transmission connection quality is scored for each cluster. "
    "Each row represents a scoring rule for a specific transmission asset type (e.g., 110kV Line, 220kV Substation). "
    "The editable columns are:"
)
add_table(doc,
    ["Column", "Description"],
    [
        ["Criteria", "The name of the transmission asset being evaluated (read-only)"],
        ["Weight", "Fractional weight (0–1) for this asset type in the overall connection score"],
        ["kV", "Voltage level: 110, 220, or 400 kV (read-only)"],
        ["Kind", "Asset type: Line or Substation (read-only)"],
        ["L1 Min / Max / Score", "Level 1 (best): distance range (km) and assigned score"],
        ["L2 Min / Max / Score", "Level 2: distance range and score"],
        ["L3 Min / Max / Score", "Level 3: distance range and score"],
        ["L4 Min / Max / Score", "Level 4 (worst): distance range and score"],
    ],
    col_widths=[3, 11]
)
doc.add_paragraph(
    "The system evaluates each cluster's distance to all six transmission asset types "
    "(110/220/400 kV × Line/Substation), applies the scoring rules, and selects the "
    "best connection — defined as the one with the highest score, or in case of a tie, "
    "the shortest distance."
)
add_note(doc, "For Off-Shore Wind mode, only 220kV and 400kV assets are available (no 110kV offshore infrastructure). The rules table adjusts accordingly.")

doc.add_paragraph(
    "Clicking the \"Save Rules\" button persists the modified rules to the session."
)

doc.add_heading("Sub-Tab B: Financial Constants", level=4)

add_placeholder(doc, "[Screenshot: Financial Constants editing grid]")

doc.add_paragraph(
    "This sub-tab displays all editable financial parameters used in CAPEX and LCOE calculations. "
    "The parameters are arranged in a grid layout. Key parameters include:"
)
add_table(doc,
    ["Parameter", "Default Value", "Description"],
    [
        ["PV CAPEX per MW", "$500,000", "Capital cost per MW for Solar PV installations"],
        ["Wind CAPEX per MW", "$1,000,000", "Capital cost per MW for Wind installations"],
        ["Substation PV Ratio", "0.08 (8%)", "Substation cost as a fraction of PV CAPEX"],
        ["Substation Wind Ratio", "0.06 (6%)", "Substation cost as a fraction of Wind CAPEX"],
        ["Line Expropriation Ratio", "0.1 (10%)", "Land expropriation cost as fraction of line CAPEX"],
        ["Land Cost Ratio", "0.1 (10%)", "Land acquisition cost as fraction of total CAPEX"],
        ["Transport Network Base", "$400,000", "Fixed transportation infrastructure cost"],
        ["Transport Network per MW", "$500", "Variable transportation cost per MW of capacity"],
    ],
    col_widths=[4, 2.5, 7.5]
)

doc.add_paragraph(
    "Additionally, transmission line costs are defined per voltage level and asset type, "
    "including cost per km and fixed costs (such as substation construction costs)."
)

doc.add_heading("Sub-Tab C: Technical Constants", level=4)
doc.add_paragraph(
    "This sub-tab provides technical parameter overrides:"
)

items = [
    ("Capacity Factor Override", "A numeric input (0–1) that allows the user to set a fixed capacity factor for all clusters. If left empty, the system calculates the capacity factor individually for each cluster based on energy yield."),
    ("Cp Values Table (Wind projects only)", "A scrollable table of wind speed vs. power coefficient (Cp) pairs. This lookup table defines the turbine's power curve — the relationship between wind speed and energy extraction efficiency. The user can edit these values to match the specific turbine model being considered."),
]
for title, desc in items:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(title + ": ")
    run.bold = True
    p.add_run(desc)

add_tip(doc, "The Cp values table should be populated with the specific turbine power curve data for accurate energy yield calculations in wind projects.")

doc.add_heading("2.4.4 Run Cluster Analysis", level=3)
doc.add_paragraph(
    "The \"Run Cluster Analysis & Scoring\" button (indigo, full-width) initiates the complete clustering pipeline:"
)

doc.add_heading("Phase 1: Spatial Clustering (ClusterEngine)", level=4)
steps = [
    "Loads the scored data (from Step 3 or uploaded CSV) and filters out cells with FINAL_GRID_SCORE ≤ 0 (excluded cells)",
    "Calculates effective capacity per cell (adjusted for land-use coverage if the checkbox is enabled)",
    "Performs spatial adjacency analysis — identifies which cells share a boundary using spatial intersection",
    "Builds a graph (NetworkX) where cells are nodes and adjacencies are edges",
    "Identifies connected components — groups of mutually adjacent cells",
    "Enforces the maximum cluster capacity constraint: components exceeding the limit are split using a greedy breadth-first search algorithm that keeps sub-clusters spatially contiguous",
    "Dissolves cell geometries within each cluster into a unified cluster polygon",
    "Aggregates per-cell metrics to cluster level (sum for capacity, mean for scores, min for distances)",
]
for s in steps:
    doc.add_paragraph(s, style='List Number')

doc.add_heading("Phase 2: Connection Scoring (ClusterScorer)", level=4)
steps = [
    "For each cluster, identifies the nearest transmission asset of each type (110/220/400 kV × Line/Substation) by taking the minimum distance across all cells in the cluster",
    "Evaluates each asset against the connection scoring rules (4 levels per rule)",
    "Selects the optimal connection: highest score wins; ties broken by shortest distance",
    "Records the winning connection type, voltage level, distance, and score",
    "Computes the Overall Score = Mean Cell Score + Connection Weight contribution",
]
for s in steps:
    doc.add_paragraph(s, style='List Number')

doc.add_heading("Phase 3: Financial Analysis (FinancialScorer)", level=4)
doc.add_paragraph("The financial scorer computes project economics for each cluster:")

doc.add_heading("Solar PV Financial Model:", level=4)
items = [
    "PV CAPEX = Installed Capacity × PV CAPEX per MW",
    "Substation Cost = PV CAPEX × Substation Ratio",
    "Land Cost = PV CAPEX × Land Cost Ratio",
    "Slope Cost = (PV CAPEX × Mean Slope % × 9/15) / 100",
    "Line CAPEX = Connection Distance × Cost per km + Fixed Costs (from transmission rules)",
    "Total CAPEX = PV + Substation + Land + Slope + Line + Expropriation",
    "Yearly Energy (MWh) = 1688 × Solar Irradiation × Capacity × Temperature Correction Factor",
    "LCOE ($/MWh) = Annualized CAPEX + Annual OPEX) / Yearly Energy",
    "Payback Period = Total CAPEX / (Yearly Energy × $50/MWh default electricity price)",
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

add_note(doc, "For Wind projects (On-Shore and Off-Shore), the financial model uses wind-specific parameters: wind CAPEX per MW, wind substation ratio, air density correction by altitude, and the Cp lookup table for energy yield calculation.")

doc.add_heading("2.4.5 Cluster Results", level=3)

add_placeholder(doc, "[Screenshot: Cluster results with summary statistics and data table]")

doc.add_paragraph("After the clustering pipeline completes, a comprehensive results section appears:")

doc.add_heading("Success Banner", level=4)
doc.add_paragraph(
    "A green banner displays the success message and a \"Download\" button for exporting the full "
    "cluster results as a CSV file."
)

doc.add_heading("Summary Statistics Cards", level=4)
doc.add_paragraph("A grid of cards (up to 4 per row) displays key aggregate metrics:")
add_table(doc,
    ["Metric", "Description"],
    [
        ["Total Clusters", "The total number of clusters formed from the eligible cells"],
        ["Avg Capacity (MW)", "The average installed capacity per cluster"],
        ["Total Capacity (MW)", "The sum of all cluster capacities"],
        ["Avg Overall Score", "The mean Overall Score across all clusters"],
        ["Avg LCOE ($/MWh)", "The average Levelized Cost of Energy across all clusters"],
    ],
    col_widths=[3.5, 10.5]
)

doc.add_heading("Cluster Data Table", level=4)
doc.add_paragraph(
    "A scrollable data table displays detailed per-cluster information including: cluster ID, "
    "installed capacity, number of cells, connection type/kV/distance/score, "
    "overall score, total CAPEX, yearly energy yield, LCOE, capacity factor, "
    "payback period, and all component cost breakdowns. Numeric values are rounded to 2 decimal places."
)

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  SECTION 3 — PROJECT MODE DIFFERENCES
# ════════════════════════════════════════════════════════════════════
doc.add_heading("3. Project Mode Differences", level=1)

doc.add_paragraph(
    "While the four-tab pipeline structure is identical across all project modes, "
    "each mode has distinct parameters, layers, and scoring configurations. "
    "This section summarizes the key differences."
)

doc.add_heading("3.1 Grid Parameters", level=2)
add_table(doc,
    ["Parameter", "Solar PV", "On-Shore Wind", "Off-Shore Wind"],
    [
        ["Grid Input", "Width × Height (m)", "Turbine Diameter → 3D × 5D", "Turbine Diameter → 3D × 5D"],
        ["Default Cell Size", "1000m × 1000m", "600m × 1000m (200m turbine)", "600m × 1000m (200m turbine)"],
        ["Boundary Source", "Country (NUTS) or File", "Country (NUTS) or File", "EEZ (Maritime Zones)"],
    ],
    col_widths=[3.5, 4, 4, 4]
)

doc.add_heading("3.2 Predefined Layers", level=2)
add_table(doc,
    ["Layer Category", "Solar PV", "On-Shore Wind", "Off-Shore Wind"],
    [
        ["Wind Resources", "—", "Wind (max, mean, min)", "Wind Speed (max, mean, min)"],
        ["Solar Resources", "Solar Irradiation, Temperature", "—", "—"],
        ["Terrain", "Slope (%)", "Slope (%), Altitude", "Slope (%), Bathymetry, Sea Bed"],
        ["Grid Infrastructure", "110/220/400kV Lines & Substations", "110/220/400kV Lines & Substations", "220/400kV Lines & Substations only"],
        ["Land/Marine Use", "Agriculture, Forest, Urban, Military, Protected", "Agriculture, Airports, Forest, Land Use, Military, Protected", "Fishing, Military, Shipping, Tourism, Protected"],
        ["Transportation", "Transport Networks", "Transport Networks", "Ports, Subsea Cables"],
        ["Natural Resources", "Energy Sources, Hydrography, Minerals", "Energy, Hydrography, Minerals, Natural Risk", "Natural Risk"],
    ],
    col_widths=[3, 3.5, 3.5, 4]
)

doc.add_heading("3.3 Color Theme", level=2)
add_table(doc,
    ["Element", "Solar PV", "On-Shore Wind", "Off-Shore Wind"],
    [
        ["Header Accent", "Orange", "Dark Blue (Navy)", "Cyan / Blue"],
        ["Card Border", "Orange-300", "Blue-400", "Cyan-300"],
        ["Selection Button", "Orange", "Dark Blue", "Blue"],
    ],
    col_widths=[3.5, 4, 4, 4]
)

doc.add_heading("3.4 Financial Model Differences", level=2)
add_table(doc,
    ["Parameter", "Solar PV", "Wind (On-Shore & Off-Shore)"],
    [
        ["Base CAPEX", "$500,000 / MW", "$1,000,000 / MW"],
        ["Substation Ratio", "8% of CAPEX", "6% of CAPEX"],
        ["Slope Cost", "Included (terrain impact)", "Not applicable"],
        ["Transport Cost", "Not applicable", "Included (access road cost)"],
        ["Energy Calculation", "Solar irradiation × Temperature correction", "Wind speed × Cp lookup × Air density correction"],
        ["Capacity Factor Source", "Solar irradiation based", "Wind speed & Cp table based"],
    ],
    col_widths=[3, 5.5, 5.5]
)

doc.add_page_break()

# ════════════════════════════════════════════════════════════════════
#  SECTION 4 — APPENDICES
# ════════════════════════════════════════════════════════════════════
doc.add_heading("4. Appendices", level=1)

doc.add_heading("4.1 Glossary of Terms", level=2)
add_table(doc,
    ["Term", "Definition"],
    [
        ["CAPEX", "Capital Expenditure — total upfront investment cost for the project"],
        ["CRS / EPSG", "Coordinate Reference System / European Petroleum Survey Group code. EPSG:3857 (Web Mercator) is required for all input rasters."],
        ["Cp (Power Coefficient)", "The fraction of wind energy extracted by the turbine, ranging from 0 to the Betz limit (~0.59)"],
        ["EEZ", "Exclusive Economic Zone — maritime area where a coastal state has resource rights"],
        ["GeoJSON", "An open standard format for encoding geographic data structures"],
        ["Grid Cell", "A single rectangular polygon unit within the study area grid"],
        ["LCOE", "Levelized Cost of Energy — lifetime cost per MWh of electricity produced"],
        ["NUTS", "Nomenclature of Territorial Units for Statistics — EU standard for administrative divisions"],
        ["Raster", "A pixel-based spatial data format (GeoTIFF) representing continuous variables"],
        ["WKT", "Well-Known Text — a text representation of geometric shapes"],
        ["Shapefile", "A geospatial vector data format commonly used in GIS applications"],
    ],
    col_widths=[3, 11]
)

doc.add_heading("4.2 Data Requirements", level=2)
doc.add_heading("Input Raster Files", level=3)
items = [
    "Format: GeoTIFF (.tif / .tiff)",
    "Coordinate Reference System: EPSG:3857 (Web Mercator) — mandatory",
    "Recommended Resolution: Match the intended grid cell size or finer",
    "Storage: Place files in the data/ directory or specify full path during layer configuration",
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_heading("Upload Grid CSV Format", level=3)
add_table(doc,
    ["Column", "Type", "Required", "Description"],
    [
        ["cell_id", "Integer", "Yes", "Unique identifier for each cell"],
        ["wkt", "String (WKT)", "Yes", "Geometry in Well-Known Text format"],
    ],
    col_widths=[2.5, 3, 2, 6.5]
)

doc.add_heading("4.3 Keyboard Shortcuts and Tips", level=2)
items = [
    "Use the file browser's \"Recent\" button to quickly navigate to previously used directories",
    "The file browser remembers your last browsed path across sessions (stored in browser localStorage)",
    "Column headers in all data tables are clickable for sorting — click once for ascending, again for descending",
    "Use the filter inputs below column headers to search for specific cells or clusters",
    "The map supports standard Leaflet controls: scroll to zoom, click-drag to pan, double-click to zoom in",
    "Switch between Street and Satellite base maps using the radio buttons in the top-right corner of any map",
    "Download results at each step as a checkpoint — this protects your work in case of session loss",
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_heading("4.4 Troubleshooting", level=2)
add_table(doc,
    ["Issue", "Possible Cause", "Solution"],
    [
        ["\"No grid data available\" warning", "Step 1 was not completed", "Go to the Gridization tab and create or upload a grid first"],
        ["Raster file rejected with CRS error", "File is not in EPSG:3857", "Reproject the raster to EPSG:3857 using QGIS or gdal_warp"],
        ["Analysis runs very slowly", "Large study area or high-resolution rasters", "Reduce grid cell count by using larger cell sizes, or use lower-resolution rasters"],
        ["Session data lost after restart", "Docker container was restarted", "Download CSV results at each step to preserve your work; re-upload as needed"],
        ["Map preview not loading", "Browser cache or WebGL issue", "Try refreshing the page or clearing browser cache"],
        ["File browser shows empty directory", "Permission issue or wrong path", "Ensure the data directory is mounted in Docker and contains .tif files"],
    ],
    col_widths=[3.5, 3.5, 7]
)

# ── Save ─────────────────────────────────────────────────────────
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "User_Manual.docx")
doc.save(output_path)
print(f"User manual generated successfully: {output_path}")
