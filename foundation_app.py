from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import streamlit as st
import json
import datetime

st.set_page_config(page_title="Pile Foundation Designer", layout="centered")

st.title("🌍 Pile Foundation Designer")

# Basic inputs
diameter = st.number_input("Pile Diameter (m)", value=0.6, step=0.05)
safety_factor = st.number_input("Safety Factor", value=2.5)
total_load = st.number_input("Total Building Load (kN)", value=10000)

# Soil layers input
st.subheader("Soil Layers")
layer_count = st.number_input("Number of Layers", min_value=1, max_value=5, value=2)

soil_types = {
    "Soft Clay": 25,
    "Medium Clay": 50,
    "Stiff Clay": 75,
    "Loose Sand": 0,
    "Dense Sand": 0
}

layers = []
for i in range(int(layer_count)):
    col1, col2 = st.columns(2)
    with col1:
        soil = st.selectbox(f"Soil Type - Layer {i+1}", list(soil_types.keys()), key=f"type_{i}")
    with col2:
        thickness = st.number_input(f"Thickness (m) - Layer {i+1}", min_value=0.1, value=5.0, step=0.5, key=f"thick_{i}")
    cohesion = soil_types[soil]
    layers.append({"type": soil, "cohesion": cohesion, "thickness": thickness})
    
def calculate_capacity(d, sf, layers):
    perimeter = 3.14 * d
    length = sum(layer["thickness"] for layer in layers)
    skin = sum(layer["cohesion"] * perimeter * layer["thickness"] for layer in layers)
    base_area = 3.14 * (d / 2) ** 2
    end = layers[-1]["cohesion"] * 9 * base_area
    ultimate = skin + end
    return round(ultimate / sf, 2), round(length, 2)

if st.button("Calculate Pile Capacity"):
    capacity, total_depth = calculate_capacity(diameter, safety_factor, layers)
    piles_needed = int((total_load / capacity) + 1)

    st.success(f"✅ Allowable Load per Pile: {capacity} kN")
    st.info(f"📏 Total Pile Length: {total_depth} m")
    st.warning(f"🔢 Required Number of Piles: {piles_needed}")

    # Prepare report content
    project_data = {
        "project_name": "My Project",
        "soil_layers": layers
    }

    result_text = f"""Allowable Load per Pile: {capacity} kN
    Total Pile Length: {total_depth} m
    Required Number of Piles: {piles_needed}
    """

    # Generate PDF
    pdf_file = generate_pdf(project_data, result_text)

    st.download_button(
        label="📄 Download PDF Report",
        data=pdf_file,
        file_name="foundation_report.pdf",
        mime="application/pdf"
    )

if st.button("📦 Download Project File"):
    project_data = {
        "diameter": diameter,
        "safety_factor": safety_factor,
        "total_load": total_load,
        "soil_layers": layers
    }
    json_string = json.dumps(project_data, indent=2)

    filename = f"foundation_project_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    st.download_button("⬇️ Download Project", data=json_string, file_name=filename, mime="application/json")

st.subheader("📁 Load Saved Project")
uploaded_file = st.file_uploader("Upload your `.json` project file")

if uploaded_file is not None:
    loaded_data = json.load(uploaded_file)

    diameter = loaded_data["diameter"]
    safety_factor = loaded_data["safety_factor"]
    total_load = loaded_data["total_load"]
    layers = loaded_data["soil_layers"]

    st.success("✅ Project loaded successfully!")
