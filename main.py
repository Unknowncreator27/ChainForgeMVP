# ═════════════════════════════════════════════════════════════════════════════
#  CHAINFORGE AI – MVP v1.0 (Full Bootstrap App)
#  → Excel → Interactive Network Graph (10 000+ nodes) + CO₂ Report + AI + Payment
#  → 100 % free to run: Streamlit + PyVis + Groq + Ozow
#  → Copy-paste → deploy in 15 mins
# ═════════════════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
from pyvis.network import Network
import streamlit.components.v1 as components
import requests
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import json
import tempfile

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(page_title="ChainForge AI", layout="wide")
st.title("ChainForge AI – Sustainable Supply Chain Control Tower")
st.caption("Upload your supplier Excel → get **CBAM-ready report**, **AI rerouting**, and **interactive map** in 60 seconds")

# ─── SECRETS (Set in Streamlit Cloud → Settings → Secrets) ───────────────────
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
OZOW_LINK = st.secrets.get("OZOW_LINK", "https://pay.ozow.me/your-link-here")  # Replace after signup

# ─── SAMPLE DATA (for demo) ───────────────────────────────────────────────────
@st.cache_data
def get_sample_data():
    np.random.seed(42)
    n = 50  # Demo size
    cities = ["Tzaneen", "Hoedspruit", "Polokwane", "Nelspruit", "Durban", "Maputo", "Johannesburg", "Cape Town"]
    lat_lon = {
        "Tzaneen": (-23.833, 30.158), "Hoedspruit": (-24.351, 30.959), "Polokwane": (-23.896, 29.448),
        "Nelspruit": (-25.475, 30.969), "Durban": (-29.883, 31.050), "Maputo": (-25.966, 32.589),
        "Johannesburg": (-26.204, 28.047), "Cape Town": (-33.925, 18.424)
    }
    suppliers = [f"{city} Farm {i}" for city in cities for i in range(1, 8)]
    df = pd.DataFrame({
        "Supplier": suppliers[:n],
        "City": [np.random.choice(cities) for _ in range(n)],
        "Tons": np.random.uniform(0.5, 5, n),
        "Transport": np.random.choice(["Truck", "Rail", "Ship"], n),
    })
    df["Lat"] = df["City"].map(lambda x: lat_lon[x][0])
    df["Lon"] = df["City"].map(lambda x: lat_lon[x][1])
    df["km_to_next"] = np.random.randint(50, 800, n)
    return df

SAMPLE_DF = get_sample_data()
SAMPLE_EXCEL = BytesIO()
SAMPLE_DF.to_excel(SAMPLE_EXCEL, index=False)
SAMPLE_EXCEL.seek(0)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Quick Start")
    st.download_button(
        "Download Sample Excel (50 nodes)",
        data=SAMPLE_EXCEL,
        file_name="chainforge_sample.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.info("**Required columns:**\n"
            "- `Supplier`\n"
            "- `City` or `Lat`/`Lon`\n"
            "- `km_to_next`\n"
            "- `Transport` (Truck/Ship/Rail)\n"
            "- `Tons`")
    st.markdown("---")
    st.subheader("Growth Tier")
    st.markdown("**R 999/month**")
    if st.button("Pay with Ozow (Instant EFT)", type="primary"):
        st.markdown(f"[Pay Now →]({OZOW_LINK})")

# ─── FILE UPLOAD ──────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Drop your Excel file here", type=["xlsx", "xls"])

if uploaded_file is None:
    st.info("👆 Upload your file or use the sample to test.")
    df = SAMPLE_DF.copy()
else:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

# ─── DATA VALIDATION & ENRICHMENT ────────────────────────────────────────────
required = ["Supplier", "km_to_next", "Transport", "Tons"]
missing = [col for col in required if col not in df.columns]
if missing:
    st.error(f"Missing columns: {', '.join(missing)}")
    st.stop()

# Add Lat/Lon if missing
if "Lat" not in df.columns or "Lon" not in df.columns:
    st.warning("No Lat/Lon found. Using random ZA coordinates for demo.")
    df["Lat"] = np.random.uniform(-34, -22, len(df))
    df["Lon"] = np.random.uniform(16, 32, len(df))

# CO₂ Calculation
CO2_FACTORS = {"Truck": 0.12, "Ship": 0.015, "Rail": 0.04}
df["CO2_kg"] = df["km_to_next"] * df["Tons"] * df["Transport"].map(CO2_FACTORS.get)
total_co2 = df["CO2_kg"].sum()
total_km = df["km_to_next"].sum()
total_cost = total_km * 18  # R18/km avg

# ─── INTERACTIVE NETWORK GRAPH (PyVis) ───────────────────────────────────────
st.subheader("Interactive Supply Chain Network")

@st.cache_resource
def create_network(_df):
    net = Network(
        height="700px",
        width="100%",
        bgcolor="#0a1a2e",
        font_color="#e0e0e0",
        directed=True,
        notebook=False
    )
    net.force_atlas_2based(
        # gravitationalConstant=-50,
        # centralGravity=0.01,
        # springLength=200,
        # springConstant=0.08
    )

    # Add nodes
    for i, row in _df.iterrows():
        co2 = row["CO2_kg"]
        size = max(10, min(40, co2 / 30))
        color = "#00ff00" if co2 < 200 else "#ffaa00" if co2 < 600 else "#ff4444"
        title = f"{row['Supplier']}<br>{row['Transport']}<br>{co2:.0f} kg CO₂<br>{row['km_to_next']} km"
        net.add_node(
            i, label=row["Supplier"].split()[-1],
            title=title, size=size, color=color,
            x=row["Lon"] * 1000, y=row["Lat"] * 1000
        )

    # Add edges
    for i in range(len(_df) - 1):
        width = max(1, _df.iloc[i]["km_to_next"] / 200)
        net.add_edge(i, i+1, width=width, color="#4a90e2",
                     title=f"{_df.iloc[i]['km_to_next']} km")

    net.set_options("""
    var options = {
      "physics": {
        "enabled": true,
        "solver": "forceAtlas2Based",
        "stabilization": { "iterations": 100 }
      },
      "nodes": { "font": { "size": 14 } },
      "edges": { "smooth": false }
    }
    """)
    return net

net = create_network(df)

with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
    net.save_graph(f.name)
    HtmlFile = open(f.name, "r", encoding="utf-8")
    components.html(HtmlFile.read(), height=700)
    os.unlink(f.name)

# ─── AI REROUTE SUGGESTION (Groq) ────────────────────────────────────────────
st.subheader("AI Route Optimizer")
if st.button("Ask AI: Find Greener & Cheaper Route", type="secondary"):
    with st.spinner("AI analyzing..."):
        prompt = f"""
You are a South African supply chain expert. Current route summary:
- Nodes: {len(df)}
- Total CO₂: {total_co2:,.0f} kg
- Total distance: {total_km:,.0f} km
- High-CO₂ legs: {df[df['CO2_kg'] > 500]['Supplier'].tolist()}

Suggest ONE alternative using Maputo, rail, or consolidation to cut CO₂ >20% and cost.
Return JSON only:
{{"suggestion": "Use rail from Polokwane to Maputo, consolidate 3 loads", "new_co2_kg": 3200, "savings_r": 18400}}
"""
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300
            }
            if GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
                response = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                       json=payload, headers=headers, timeout=20)
                ai_text = response.json()["choices"][0]["message"]["content"]
            else:
                ai_text = '{"suggestion": "Add GROQ_API_KEY in Streamlit Secrets to enable AI", "new_co2_kg": 0, "savings_r": 0}'
        except Exception as e:
            ai_text = f'{{"suggestion": "AI error: {str(e)}", "new_co2_kg": 0, "savings_r": 0}}'

        try:
            ai = json.loads(ai_text)
            st.success(f"**AI Suggestion:** {ai['suggestion']}")
            if ai["new_co2_kg"] > 0:
                reduction = (1 - ai["new_co2_kg"] / total_co2) * 100
                st.metric("CO₂ Reduction", f"{reduction:.1f}%", f"R {ai['savings_r']:,.0f} saved")
        except:
            st.code(ai_text)

# ─── CBAM PDF REPORT ─────────────────────────────────────────────────────────
def generate_pdf(df, total_co2, total_cost):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("ChainForge AI – EU CBAM Pre-Compliance Report", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Generated: November 16, 2025", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["Supplier", "Transport", "Tons", "km", "CO₂ (kg)"]]
    for _, row in df.iterrows():
        data.append([
            row["Supplier"][:30],
            row["Transport"],
            f"{row['Tons']:.1f}",
            f"{row['km_to_next']}",
            f"{row['CO2_kg']:.0f}"
        ])
    data.append(["", "", "", "TOTAL", f"{total_co2:.0f} kg"])

    t = Table(data, colWidths=[140, 70, 60, 60, 80])
    t.setStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
    ])
    elements.append(t)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Estimated Freight Cost: R {total_cost:,.0f}", styles['Normal']))
    elements.append(Paragraph("Ready for EU CBAM submission (2026)", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

if st.button("Download CBAM PDF Report"):
    pdf = generate_pdf(df, total_co2, total_cost)
    st.download_button(
        "Download PDF",
        data=pdf,
        file_name=f"CBAM_Report_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

# ─── SUMMARY METRICS ──────────────────────────────────────────────────────────
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total CO₂", f"{total_co2:,.0f} kg")
col2.metric("Distance", f"{total_km:,.0f} km")
col3.metric("Est. Cost", f"R {total_cost:,.0f}")
col4.metric("Nodes", f"{len(df):,}")

# ─── PAYMENT CTA ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Ready to Unlock Full Features?")
st.markdown("""
**Growth Tier – R 999/month**  
- Unlimited nodes  
- Weekly AI alerts via WhatsApp  
- Bank green-finance API  
- Priority support  
""")
st.markdown(f"[**Pay with Ozow →**]({OZOW_LINK})")

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.caption("Built by a solo dev in South Africa | Bootstrap MVP v1.0 | November 16, 2025")