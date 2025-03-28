# --- Imports ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import streamlit as st
import json
import datetime
import math
import matplotlib.pyplot as plt
import pandas as pd
import pydeck as pdk
from collections import Counter, defaultdict
import uuid

st.cache_data.clear()
st.cache_resource.clear()

# --- Streamlit Config ---
st.set_page_config(page_title="Pile Foundation Designer", layout="centered")
st.title("🌍 Pile Foundation Designer")

# --- Soil Types Dictionary ---
soil_types = {
    "Soft Clay": 25,
    "Medium Clay": 50,
    "Stiff Clay": 75,
    "Loose Sand": 0,
    "Dense Sand": 0
}

# --- Functions ---
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
    return round(3.14 * (diameter / 2) ** 2 * length, 2)

def calculate_capacity(diameter, safety_factor, layers):
    perimeter = 3.14 * diameter
    length = sum(layer["thickness"] for layer in layers)

    skin = sum(layer["cohesion"] * perimeter * layer["thickness"] for layer in layers)
    base_area = 3.14 * (diameter / 2) ** 2
    end = layers[-1]["cohesion"] * 9 * base_area
    ultimate = skin + end

    allowable = round(ultimate / safety_factor, 2)

    # 🔁 Return extra details for learning mode
    return allowable, round(length, 2), perimeter, base_area, skin, end, ultimate

def calculate_group_efficiency(rows, cols, spacing, diameter):
    spacing_ratio = spacing / diameter
    return round(min((rows * cols) / (1 + 0.1 * spacing_ratio), rows * cols), 2)

def estimate_settlement(Q, L, diameter, Es):
    A = 3.14 * (diameter / 2) ** 2
    S = (Q * L) / (A * Es * 1000)
    return round(S * 1000, 2)

def estimate_pile_cost(volume, cost_per_m3):
    return round(volume * cost_per_m3, 2)

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
    return pd.DataFrame(data)

def pile_design_summary(d, l, sf, c, load, cost_rate):
    perimeter = 3.14 * d
    skin = c * perimeter * l
    base = c * 9 * (3.14 * (d / 2) ** 2)
    allowable = (skin + base) / sf
    piles = int((load / allowable) + 1)
    volume = calculate_concrete_volume(d, l)
    total_cost = estimate_pile_cost(volume * piles, cost_rate)
    return round(allowable, 2), piles, round(volume, 2), round(total_cost, 2)

def generate_pdf(project_data, result_text):
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
    for i, layer in enumerate(project_data["soil_layers"], 1):
        y -= 20
        c.drawString(70, y, f"Layer {i}: {layer['type']}, {layer['thickness']} m, Cohesion: {layer['cohesion']} kPa")
    y -= 40
    for line in result_text.split("\n"):
        c.drawString(50, y, line)
        y -= 20
    c.save()
    buffer.seek(0)
    return buffer

def generate_boq(piles, volume_per_pile, total_volume, concrete_rate, rebar_rate, labor_rate):
    boq = [
        {"Item": "Concrete", "Unit": "m³", "Qty": total_volume, "Unit Rate": concrete_rate},
        {"Item": "Rebar (5%)", "Unit": "kg", "Qty": round(total_volume * 0.05 * 7850, 2), "Unit Rate": rebar_rate},
        {"Item": "Pile Excavation", "Unit": "m³", "Qty": total_volume, "Unit Rate": 25.0},
        {"Item": "Pile Installation", "Unit": "each", "Qty": piles, "Unit Rate": labor_rate},
        {"Item": "Mobilization & Setup", "Unit": "lump sum", "Qty": 1, "Unit Rate": 1000.0},
    ]
    for row in boq:
        row["Total"] = round(row["Qty"] * row["Unit Rate"], 2)
    return pd.DataFrame(boq)

st.markdown(
    """
    Welcome to the **🌍 Pile Foundation Designer**!

    This tool helps engineers, students, and designers calculate pile capacities, estimate costs, visualize layouts, and more — all in one clean interface.

    👉 Use the tabs above to explore:
    - 🧮 Structural design
    - 📐 Layout & efficiency
    - 📉 Settlement estimation
    - 🆚 Compare options
    - 💾 Export your project

    Built with love and concrete. 🧱💙
    """
)

language = st.sidebar.selectbox("🌐 Language", ["English", "မြန်မာ", "ភាសាខ្មែរ"])
learning_mode = st.sidebar.checkbox("🎓 Enable Learning Mode")

translations = {
    "English": {
        "title": "Pile Foundation Designer",
        "calculate": "Calculate Pile Capacity",
        "load": "Total Building Load (kN)",
        "diameter": "Pile Diameter (m)",
        "safety_factor": "Safety Factor",
        "layers": "Soil Layers",
        "cost": "Concrete Cost (USD/m³)",
        "save": "Save This Design",
    },
    "မြန်မာ": {
        "title": "အုတ်ထောင်ခြင်း ဒီဇိုင်းကိရိယာ",
        "calculate": "အုတ်စွမ်းရည်တွက်ချက်ပါ",
        "load": "အဆောက်အဦး တင်မြှောက်မှု (kN)",
        "diameter": "အုတ်အချင်း (မီတာ)",
        "safety_factor": "လုံခြုံမှုအချက်",
        "layers": "မြေဆီလွှာများ",
        "cost": "ကွန်ကရစ်ဈေးနှုန်း (USD/m³)",
        "save": "ဒီဇိုင်း သိမ်းဆည်းပါ",
    },
    "ភាសាខ្មែរ": {
        "title": "កម្មវិធីរចនាគោលស្ថាបនា",
        "calculate": "គណនសមត្ថភាពគោលស្ថាបនា",
        "load": "បន្ទុកសំណង់សរុប (kN)",
        "diameter": "អង្កត់ផ្ចិតគោល (m)",
        "safety_factor": "កត្តាសុវត្ថិភាព",
        "layers": "ស្រទាប់ដី",
        "cost": "តម្លៃកុងគ្រីត (USD/m³)",
        "save": "រក្សាទុកការរចនានេះ",
    }
}

_ = translations[language]

st.title(_["title"])

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Design Calculator",
    "Layout & Efficiency",
    "Settlement",
    "Compare Designs",
    "BOQ",
    "Save / Export",
    "Project Manager",
    "Dashboard",
    "Community"
])

with tab1:
    
    # --- User Inputs ---
    st.subheader("📌 Input Parameters")
    diameter = st.number_input("Pile Diameter (m)", value=0.6, step=0.05)
    safety_factor = st.number_input("Safety Factor", value=2.5)
    total_load = st.number_input("Total Building Load (kN)", value=1000)

    st.markdown("---")
    st.subheader("🧱 Soil Layers")
    st.caption("📘 Cohesion values auto-fill based on soil type.")

    if learning_mode:
        st.markdown("📚 **Soil Cohesion** is the soil’s natural resistance to shear — typically in kPa.")

    
    layer_count = st.number_input("Number of Layers", min_value=1, max_value=5, value=2)
    layers = []
    for i in range(int(layer_count)):
        col1, col2 = st.columns(2)
        with col1:
            soil = st.selectbox(f"Soil Type - Layer {i+1}", list(soil_types.keys()), key=f"type_{i}")
        with col2:
            thickness = st.number_input(f"Thickness (m) - Layer {i+1}", min_value=0.1, value=5.0, step=0.5, key=f"thick_{i}")
        cohesion = soil_types[soil]
        layers.append({"type": soil, "cohesion": cohesion, "thickness": thickness})
    
    # --- Cost Input ---
    st.markdown("---")
    st.subheader("💰 Concrete Cost")
    cost_rate = st.number_input("Cost per m³ of Concrete (USD)", value=120.0)
    
    # --- Buttons ---
    if st.button("Calculate Pile Capacity"):
        capacity, total_depth, perimeter, base_area, skin, end, ultimate = calculate_capacity(diameter, safety_factor, layers)
        piles_needed = int((total_load / capacity) + 1)
        volume_per_pile = calculate_concrete_volume(diameter, total_depth)
        total_volume = volume_per_pile * piles_needed
        total_cost = estimate_pile_cost(total_volume, cost_rate)
    
        st.success(f"✅ Allowable Load per Pile: {capacity} kN")
        st.info(f"📏 Total Pile Length: {total_depth} m")
        st.warning(f"🔢 Required Number of Piles: {piles_needed}")
        st.info(f"🧱 Concrete per Pile: {volume_per_pile} m³")
        st.info(f"🧱 Total Concrete Volume: {total_volume} m³")
        st.success(f"💵 Estimated Total Cost: ${total_cost}")
    
        df = generate_excel_data(piles_needed, capacity, total_depth, diameter, volume_per_pile, total_volume, total_cost)
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Pile Summary")
        st.download_button("📥 Download Excel Report", data=excel_buffer.getvalue(), file_name="pile_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
        project_data = {"project_name": "My Project", "soil_layers": layers}
        result_text = f"""Allowable Load per Pile: {capacity} kN\nTotal Pile Length: {total_depth} m\nRequired Number of Piles: {piles_needed}"""
        pdf_file = generate_pdf(project_data, result_text)
        st.download_button("📄 Download PDF Report", data=pdf_file, file_name="foundation_report.pdf", mime="application/pdf")

        st.session_state["piles"] = piles_needed
        st.session_state["vol_per_pile"] = volume_per_pile
        st.session_state["total_vol"] = total_volume
        st.session_state["boq_ready"] = True

        st.session_state["calculated"] = {
            "capacity": capacity,
            "pile_length": total_depth,
            "piles_needed": piles_needed,
            "volume_per_pile": volume_per_pile,
            "total_volume": total_volume,
            "total_cost": total_cost,
            "layers": layers,
            "diameter": diameter,
            "safety_factor": safety_factor,
            "total_load": total_load,
        }

        if learning_mode:
            st.caption("🧠 Formula: Allowable = (Skin Friction + End Bearing) / Safety Factor")
            st.caption("📘 Skin Friction = Σ (cohesion × perimeter × thickness)")
            st.caption("📘 End Bearing = cohesion × 9 × base area")

        if learning_mode:
            st.markdown("### 🧾 Calculation Breakdown")
            st.write(f"Perimeter = 3.14 × {diameter} = {3.14 * diameter:.2f} m")
            st.write(f"Base Area = π × (d/2)² = {3.14 * (diameter / 2) ** 2:.2f} m²")
            st.write(f"Ultimate Load = Skin Friction + End Bearing = {ultimate:.2f} kN")
            st.write(f"Allowable Load = Ultimate / SF = {ultimate:.2f} / {safety_factor} = {capacity:.2f} kN")


    if "calculated" in st.session_state:
        st.markdown("---")
        st.subheader("💾 Save This Design")
    
        project_name = st.text_input("Project Name", value="Unnamed Design")
        if st.button("Save Now"):
            st.session_state.setdefault("saved_projects", {})
            st.session_state["saved_projects"][project_name] = st.session_state["calculated"]
            st.success(f"✅ '{project_name}' saved!")
            st.caption("💡 Your knowledge grows as your design evolves.")

with tab2:

    st.caption("Tip: Use standard pile spacing of 2.5–3.0m for typical foundations.")
    if st.button("Show Pile Layout + Group Efficiency"):
        capacity, total_depth, perimeter, base_area, skin, end, ultimate = calculate_capacity(diameter, safety_factor, layers)
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

with tab3:
    
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

with tab4:
    
    st.subheader("🆚 Design Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Design A")
        d1 = st.number_input("Diameter A (m)", value=0.6, key="d1")
        l1 = st.number_input("Length A (m)", value=20.0, key="l1")
        sf1 = st.number_input("Safety Factor A", value=2.5, key="sf1")
    
    with col2:
        st.markdown("### Design B")
        d2 = st.number_input("Diameter B (m)", value=0.45, key="d2")
        l2 = st.number_input("Length B (m)", value=25.0, key="l2")
        sf2 = st.number_input("Safety Factor B", value=2.5, key="sf2")
    
    if st.button("Compare Designs"):
        load = total_load
        cohesion = 50  # For simplicity
    
        cost_rate = 120.0  # USD/m³
        a = pile_design_summary(d1, l1, sf1, cohesion, load, cost_rate)
        b = pile_design_summary(d2, l2, sf2, cohesion, load, cost_rate)
    
        st.write("### 📊 Comparison Table")
        comp_df = pd.DataFrame({
            "Metric": ["Allowable Capacity (kN)", "Pile Count", "Concrete per Pile (m³)", "Total Cost (USD)"],
            "Design A": a,
            "Design B": b
        })
    
        st.dataframe(comp_df)
    
        st.success("✅ Design comparison complete. Choose wisely!")

with tab5:
    st.subheader("📋 Bill of Quantities")

    if st.session_state.get("boq_ready"):
        df_boq = generate_boq(
            st.session_state["piles"],
            st.session_state["vol_per_pile"],
            st.session_state["total_vol"],
            concrete_rate=120.0,
            rebar_rate=1.5,
            labor_rate=50.0
        )
        st.dataframe(df_boq)
        st.success("✅ BOQ generated. Prices are editable in code.")
    else:
        st.info("💡 Calculate pile design first in the Design tab.")

with tab6:
    
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

    st.markdown("---")
    st.subheader("📁 Load Saved Project")
    uploaded_file = st.file_uploader("Upload your `.json` project file")
    
    if uploaded_file is not None:
        loaded_data = json.load(uploaded_file)
    
        diameter = loaded_data["diameter"]
        safety_factor = loaded_data["safety_factor"]
        total_load = loaded_data["total_load"]
        layers = loaded_data["soil_layers"]
    
        st.success("✅ Project loaded successfully!")

with tab7:
    st.subheader("📁 Saved Projects")

    projects = st.session_state.get("saved_projects", {})
    if not projects:
        st.info("No designs saved yet. Go to the Design tab and click Save.")
    else:
        project_names = list(projects.keys())
        selected = st.selectbox("Choose a saved design", project_names)
        if selected:
            details = projects[selected]
            st.write(f"### 🔍 Details for: {selected}")
            st.json(details)

with tab8:
    st.subheader("📊 Project Summary Dashboard")
    st.caption("Built by KIM — now used by hundreds of engineers worldwide.")


    # 🔹 Show metrics for the last calculated design
    if "calculated" in st.session_state:
        calc = st.session_state["calculated"]
        st.metric("Allowable Load per Pile (kN)", calc["capacity"])
        st.metric("Required Piles", calc["piles_needed"])
        st.metric("Total Concrete Volume (m³)", calc["total_volume"])
        st.metric("Estimated Cost (USD)", f"${calc['total_cost']}")
    else:
        st.info("💡 Calculate a pile design in the Design tab to see dashboard results.")

    st.markdown("---")

    # 🔸 Visualize saved projects if they exist
    if "saved_projects" in st.session_state and st.session_state["saved_projects"]:
        st.markdown("### 📋 All Saved Designs")
        df_projects = pd.DataFrame.from_dict(st.session_state["saved_projects"], orient="index")
        st.dataframe(df_projects[["capacity", "piles_needed", "total_volume", "total_cost"]])

        st.markdown("### 📉 Total Cost Comparison")
        fig, ax = plt.subplots()
        ax.bar(df_projects.index, df_projects["total_cost"], color="skyblue")
        ax.set_ylabel("USD")
        ax.set_title("Total Cost per Saved Project")
        ax.tick_params(axis='x', rotation=30)
        st.pyplot(fig)
    else:
        st.info("💾 Save multiple designs to compare their total cost here.")

with tab9:
    # Initialize session storage
    if "community_projects" not in st.session_state:
        st.session_state["community_projects"] = []
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = "Anonymous Engineer"
    if "notifications" not in st.session_state:
        st.session_state["notifications"] = []
    if "comments" not in st.session_state:
        st.session_state["comments"] = defaultdict(list)
    if "reactions" not in st.session_state:
        st.session_state["reactions"] = defaultdict(lambda: {"👍": 0, "💡": 0, "🧪": 0})
    if "reaction_authors" not in st.session_state:
        st.session_state["reaction_authors"] = defaultdict(lambda: {"👍": [], "💡": [], "🧪": []})
    if "tags" not in st.session_state:
        st.session_state["tags"] = defaultdict(list)
    
    st.title("🌍 Luna GroundWorks – Community")
    st.markdown("### 🛠️ v1.1 — The Trust Layer")
    
    # --- User Profile ---
    st.sidebar.markdown("### 👤 Your Profile")
    st.session_state["user_name"] = st.sidebar.text_input("Name or Alias", st.session_state["user_name"])
    
    # --- Notifications ---
    st.sidebar.markdown("### 🔔 Notifications")
    user_notifications = [n for n in st.session_state["notifications"] if n["to"] == st.session_state["user_name"]]
    if user_notifications:
        for note in user_notifications[::-1]:
            st.sidebar.info(f"🔁 {note['from']} forked your design '{note['project']}'")
    else:
        st.sidebar.caption("No new activity yet.")
    
    # --- Submit a Design ---
    st.subheader("📤 Submit a Design")
    with st.form("submit_form"):
        name = st.text_input("Project Name")
        country = st.text_input("Country / Region")
        lat = st.number_input("Latitude (optional)", value=0.0, format="%.6f")
        lon = st.number_input("Longitude (optional)", value=0.0, format="%.6f")
        diameter = st.number_input("Pile Diameter (m)", min_value=0.2, step=0.05)
        length = st.number_input("Pile Length (m)", min_value=1.0, step=0.5)
        load = st.number_input("Total Load (kN)", min_value=100.0, step=10.0)
        notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("🌱 Share This Design")
        if submitted:
            design = {
                "id": str(uuid.uuid4()),
                "name": name,
                "country": country,
                "lat": lat,
                "lon": lon,
                "diameter": diameter,
                "length": length,
                "load": load,
                "notes": notes,
                "user": st.session_state["user_name"],
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "parent_id": None
            }
            st.session_state["community_projects"].append(design)
            st.success("✅ Design shared!")
    
    # --- Fork Function ---
    def fork_design(original):
        fork = original.copy()
        fork["id"] = str(uuid.uuid4())
        fork["user"] = st.session_state["user_name"]
        fork["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        fork["parent_id"] = original["id"]
        fork["name"] += " (Forked)"
        st.session_state["community_projects"].append(fork)
        st.session_state["notifications"].append({
            "to": original["user"], "from": fork["user"], "project": original["name"], "time": fork["timestamp"]
        })
        st.success("✅ Forked & user notified")
    
    # --- Design Threads + Trust Layer ---
    st.markdown("---")
    st.subheader("🧵 Design Threads + 🔍 Filters + 🏷️ Tags + ❤️ Reactions")
    projects = st.session_state["community_projects"]

    # --- Filter Section ---
    st.markdown("### 🔍 Filter Designs")
    
    filter_country = st.text_input("Filter by Country/Region")
    min_load = st.number_input("Minimum Load (kN)", min_value=0.0, value=0.0, step=10.0)
    max_load = st.number_input("Maximum Load (kN)", min_value=0.0, value=10000.0, step=10.0)
    
    filtered_projects = [
        p for p in projects
        if filter_country.lower() in p["country"].lower()
        and min_load <= p["load"] <= max_load
    ]
    
    projects = filtered_projects  # Override with filtered list

    st.caption(f"🔎 Showing {len(projects)} design(s) matching filters.")


    
    # Sort by most reactions
    def total_reactions(pid):
        r = st.session_state["reactions"][pid]
        return r["👍"] + r["💡"] + r["🧪"]
    
    sorted_projects = sorted(projects, key=lambda p: total_reactions(p["id"]), reverse=True)
    
    st.markdown("### 🔥 Trending Forks")
    for p in sorted_projects[:3]:
        st.markdown(f"**{p['name']}** by `{p['user']}` with {total_reactions(p['id'])} reactions")
    
    # ✅ Define this BEFORE using root_projects below
    root_projects = [p for p in projects if not p.get("parent_id")]
    
    st.markdown("### 📋 All Shared Designs (No Forks Yet)")
    for root in root_projects:
        forks = [f for f in projects if f.get("parent_id") == root["id"]]
        if not forks:
            with st.expander(f"{root['name']} by {root['user']}"):
                st.markdown(f"**Diameter:** {root['diameter']} m  \n"
                            f"**Length:** {root['length']} m  \n"
                            f"**Load:** {root['load']} kN  \n"
                            f"**Notes:** {root['notes'] or '—'}  \n"
                            f"**Tags:** {', '.join(st.session_state['tags'][root['id']]) if st.session_state['tags'].get(root['id']) else '—'}")
                if st.button(f"🔁 Fork this Design", key=f"fork_root_{root['id']}"):
                    fork_design(root)
                    st.rerun()


    
    # Threads
    root_projects = [p for p in projects if not p.get("parent_id")]
    for root in root_projects:
        forks = [f for f in projects if f.get("parent_id") == root["id"]]
        if forks:
            st.markdown(f"### 🧩 {root['name']} by `{root['user']}`")
            for f in forks:
                r = st.session_state["reactions"][f['id']]
                badge = "✅ Community Verified" if r["👍"] >= 10 else ""
                st.markdown(f"➡️ *{f['name']}* by `{f['user']}` on {f['timestamp']} {badge}")
                with st.expander("🔍 Inspect Fork"):
                    st.markdown(f"**Diameter:** {f['diameter']} m, **Length:** {f['length']} m, **Load:** {f['load']} kN")
                    st.markdown(f"**Notes:** {f['notes']}")
    
                    # Reactions
                    col1, col2, col3 = st.columns(3)
                    if col1.button(f"👍 Helpful ({r['👍']})", key=f"like_{f['id']}"):
                        r['👍'] += 1
                        st.session_state["reaction_authors"][f['id']]['👍'].append(st.session_state['user_name'])
                        st.rerun()
                    if col2.button(f"💡 Innovative ({r['💡']})", key=f"idea_{f['id']}"):
                        r['💡'] += 1
                        st.session_state["reaction_authors"][f['id']]['💡'].append(st.session_state['user_name'])
                        st.rerun()
                    if col3.button(f"🧪 Site-Tested ({r['🧪']})", key=f"test_{f['id']}"):
                        r['🧪'] += 1
                        st.session_state["reaction_authors"][f['id']]['🧪'].append(st.session_state['user_name'])
                        st.rerun()
    
                    # Tagging
                    tag_options = ["Student Design", "Peer Reviewed", "Green Foundation"]
                    selected_tags = st.multiselect("🏷️ Add Tags", tag_options, default=st.session_state["tags"][f['id']], key=f"tag_{f['id']}")
                    st.session_state["tags"][f['id']] = selected_tags  # ✅ Always sync full state
                    
                    if selected_tags:
                        st.info("Tags: " + ", ".join(selected_tags))

    
                    # Reaction Details
                    st.markdown("### 👥 Who Reacted")
                    authors = st.session_state["reaction_authors"][f['id']]
                    for icon in ["👍", "💡", "🧪"]:
                        if authors[icon]:
                            st.markdown(f"{icon} {', '.join(authors[icon])}")
    
                    # Comments
                    st.markdown("### 💬 Comments")
                    comment_key = f['id']
                    new_comment = st.text_input("Add comment", key=f"cmt_{comment_key}")
                    if st.button("Post", key=f"btn_{comment_key}") and new_comment:
                        st.session_state["comments"][comment_key].append({
                            "author": st.session_state["user_name"],
                            "text": new_comment,
                            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.success("Posted!")
                    for c in st.session_state["comments"][comment_key]:
                        st.markdown(f"- _{c['author']}_: {c['text']} ({c['time']})")


    st.title("🗺️ Global Community Map")
    st.markdown("### 📍 Where engineers build, share, and inspire")
    
    projects = st.session_state["community_projects"]
    
    # --- Filter Map Region ---
    st.sidebar.markdown("### 🌐 Map Filters")
    country_filter = st.sidebar.text_input("Filter by Country/Region", key="geo_country_filter")
    tags_filter = st.sidebar.multiselect("Filter by Tags", [...], key="geo_tags_filter")
    
    # --- Filter logic ---
    filtered = []
    for p in projects:
        tag_match = not tags_filter or any(tag in st.session_state["tags"][p["id"]] for tag in tags_filter)
        country_match = country_filter.lower() in p["country"].lower()
        if tag_match and country_match:
            filtered.append(p)
    
    st.caption(f"Showing {len(filtered)} project(s) on the map.")
    
    # --- Create Map Data ---
    if filtered:
        df_map = pd.DataFrame(filtered)
        df_map = df_map[df_map["lat"] != 0]  # Remove placeholder coordinates
    
        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(
                latitude=df_map["lat"].mean(),
                longitude=df_map["lon"].mean(),
                zoom=2,
                pitch=30
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df_map,
                    get_position="[lon, lat]",
                    get_radius=20000,
                    get_color="[200, 30, 0, 160]",
                    pickable=True
                )
            ],
            tooltip={"text": "{name} by {user}\nLoad: {load} kN"}
        ))
    
        if st.checkbox("📋 Show project details"):
            st.dataframe(df_map[["name", "country", "load", "user", "timestamp"]])
    else:
        st.info("No geo-tagged designs to map. Try submitting one with coordinates!")


    
# To the engineers who design beneath the surface — this tool is for you.
# Build boldly. Build sustainably. Build with clarity.
# – KIM

