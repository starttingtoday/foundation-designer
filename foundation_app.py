from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import streamlit as st
import json
import datetime
import math
import matplotlib.pyplot as plt
import pandas as pd

st.set_page_config(page_title="Pile Foundation Designer", layout="centered")

st.title("🌍 Pile Foundation Designer")

# Basic inputs
diameter = st.number_input("Pile Diameter (m)", value=0.6, step=0.05)
safety_factor = st.number_input("Safety Factor", value=2.5)
total_load = st.number_input("Total Building Load (kN)", value=1000)

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

def suggest_layout(n_piles):
    rows = math.ceil(math.sqrt(n_piles))
    cols = math.ceil(n_piles / rows)
    return rows, cols

def draw_pile_layout(rows, cols, spacing):
    fig, ax = plt.subplots(figsize=(5, 5))
    
    for i in range(rows):
        for j in range(cols):
            x = j * spacing
            y = i * spacing
            ax.add_patch(plt.Circle((x, y), 0.3, color='gray'))

    ax.set_aspect('equal')
    ax.set_title(f"Pile Layout: {rows} x {cols}")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.grid(True)
    plt.tight_layout()
    return fig

def calculate_concrete_volume(diameter, length):
    radius = diameter / 2
    volume = 3.14 * radius ** 2 * length
    return round(volume, 2)
    
def calculate_capacity(diameter, safety_factor, layers):
    perimeter = 3.14 * diameter
    length = sum(layer["thickness"] for layer in layers)

    skin = sum(layer["cohesion"] * perimeter * layer["thickness"] for layer in layers)
    base_area = 3.14 * (diameter / 2) ** 2
    end = layers[-1]["cohesion"] * 9 * base_area
    ultimate = skin + end

    allowable = round(ultimate / safety_factor, 2)

    return allowable, round(length, 2)  # return pile capacity and length

def calculate_group_efficiency(rows, cols, spacing, diameter):
    spacing_ratio = spacing / diameter
    efficiency = (rows * cols) / (1 + 0.1 * spacing_ratio)
    return round(min(efficiency, rows * cols), 2)

def estimate_settlement(Q, L, diameter, Es):
    A = 3.14 * (diameter / 2) ** 2
    S = (Q * L) / (A * Es * 1000)  # Convert kPa to kN/m²
    return round(S * 1000, 2)  # return in mm

def estimate_pile_cost(volume, cost_per_m3):
    return round(volume * cost_per_m3, 2)

st.subheader("💰 Cost & Material Estimation")

cost_rate = st.number_input("Cost per m³ of Concrete (USD)", value=120.0)

def generate_excel_data(piles_needed, capacity, pile_length, diameter, volume_per_pile, total_volume, total_cost):
    data = {
        "Item": [
            "Pile Diameter (m)",
            "Pile Length (m)",
            "Allowable Load per Pile (kN)",
            "Required Number of Piles",
            "Concrete Volume per Pile (m³)",
            "Total Concrete Volume (m³)",
            "Estimated Total Cost (USD)"
        ],
        "Value": [
            diameter,
            pile_length,
            capacity,
            piles_needed,
            volume_per_pile,
            total_volume,
            total_cost
        ]
    }
    df = pd.DataFrame(data)
    return df


def generate_pdf(project_data, result_text):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from io import BytesIO

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "Pile Foundation Design Report")

    c.setFont("Helvetica", 11)
    y = height - 100
    c.drawString(50, y, f"Project Name: {project_data.get('project_name', 'Unnamed')}")
    y -= 30

    c.drawString(50, y, "Soil Layers:")
    for i, layer in enumerate(project_data["soil_layers"], start=1):
        y -= 20
        c.drawString(70, y, f"Layer {i}: {layer['type']}, {layer['thickness']} m, Cohesion: {layer['cohesion']} kPa")

    y -= 40
    for line in result_text.split("\n"):
        c.drawString(50, y, line)
        y -= 20

    c.save()
    buffer.seek(0)
    return buffer


if st.button("Calculate Pile Capacity"):
    capacity, total_depth = calculate_capacity(diameter, safety_factor, layers)
    piles_needed = int((total_load / capacity) + 1)

    st.success(f"✅ Allowable Load per Pile: {capacity} kN")
    st.info(f"📏 Total Pile Length: {total_depth} m")
    st.warning(f"🔢 Required Number of Piles: {piles_needed}")

    capacity, total_depth = calculate_capacity(diameter, safety_factor, layers)
    piles_needed = int((total_load / capacity) + 1)
    
    volume_per_pile = calculate_concrete_volume(diameter, total_depth)
    total_volume = volume_per_pile * piles_needed
    total_cost = estimate_pile_cost(total_volume, cost_rate)
    
    st.info(f"🧱 Concrete per Pile: {volume_per_pile} m³")
    st.info(f"🧱 Total Concrete Volume: {total_volume} m³")
    st.success(f"💵 Estimated Total Cost: ${total_cost}")

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

if st.button("Show Pile Layout + Group Efficiency"):
    capacity, total_depth = calculate_capacity(diameter, safety_factor, layers)
    piles_needed = int((total_load / capacity) + 1)
    rows, cols = suggest_layout(piles_needed)

    spacing = st.number_input("Pile Spacing (m)", value=2.5, step=0.1)
    st.write(f"🔢 Suggested Layout: {rows} rows × {cols} columns")

    fig = draw_pile_layout(rows, cols, spacing)
    st.pyplot(fig)

    efficiency = calculate_group_efficiency(rows, cols, spacing, diameter)
    group_capacity = round(capacity * efficiency, 2)

    st.info(f"📉 Group Efficiency Factor: {efficiency}/{rows * cols}")
    st.success(f"🧱 Total Group Capacity: {group_capacity} kN")

st.subheader("📉 Settlement Estimation")

Es = st.number_input("Soil Modulus Es (kPa)", value=15000)

if st.button("Estimate Settlement"):
    Q = total_load
    L = sum(layer["thickness"] for layer in layers)

    st.session_state["Q"] = Q
    st.session_state["L"] = L
    st.session_state["Es"] = Es
    st.session_state["diameter"] = diameter

    settlement = estimate_settlement(Q, L, diameter, Es)
    st.success(f"📏 Estimated Settlement: {settlement} mm")

if st.checkbox("📈 Show Load vs. Settlement Curve"):
    if "Q" in st.session_state and "L" in st.session_state:
        Q = st.session_state["Q"]
        L = st.session_state["L"]
        Es = st.session_state["Es"]
        diameter = st.session_state["diameter"]

        loads = [Q * x for x in [0.2, 0.4, 0.6, 0.8, 1.0]]
        settlements = [estimate_settlement(q, L, diameter, Es) for q in loads]

        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot(settlements, loads, marker='o')
        ax.set_xlabel("Settlement (mm)")
        ax.set_ylabel("Load (kN)")
        ax.set_title("Load vs. Settlement")
        ax.grid(True)
        st.pyplot(fig)
    else:
        st.warning("⚠️ Please click 'Estimate Settlement' first.")

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

df = generate_excel_data(piles_needed, capacity, total_depth, diameter, volume_per_pile, total_volume, total_cost)

excel_buffer = BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="Pile Summary")

st.download_button(
    label="📥 Download Excel Report",
    data=excel_buffer.getvalue(),
    file_name="pile_design_summary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.subheader("📁 Load Saved Project")
uploaded_file = st.file_uploader("Upload your `.json` project file")

if uploaded_file is not None:
    loaded_data = json.load(uploaded_file)

    diameter = loaded_data["diameter"]
    safety_factor = loaded_data["safety_factor"]
    total_load = loaded_data["total_load"]
    layers = loaded_data["soil_layers"]

    st.success("✅ Project loaded successfully!")
