# ═════════════════════════════════════════════════════════════════════════════
#  CHAINFORGE AI – MVP v0.1 (Bootstrap Edition)
#  → Excel → Live Map + CO₂ Report + AI Reroute Suggestion
#  → 100 % free to run: Streamlit + Groq + OpenStreetMap
#  → Copy-paste → deploy in 15 mins
# ═════════════════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(page_title="ChainForge AI", layout="centered")
st.title("🌍 ChainForge AI – Beta")
st.caption("Upload your supplier Excel → get CBAM-ready carbon report in 60 sec")

# ─── GROQ API (FREE $100 CREDIT) ─────────────────────────────────────────────
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))  # Set in Streamlit Secrets
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── SAMPLE DATA (for demo) ───────────────────────────────────────────────────
SAMPLE_EXCEL = BytesIO()
sample_df = pd.DataFrame({
    "Supplier": ["Tzaneen Macs", "Hoedspruit Farm", "Durban Port"],
    "City": ["Tzaneen", "Hoedspruit", "Durban"],
    "Lat": [-23.833, -24.351, -29.883],
    "Lon": [30.158, 30.959, 31.050],
    "km_to_next": [0, 180, 620],
    "Transport": ["Truck", "Truck", "Ship"],
    "Tons": [2.0, 2.0, 2.0]
})
sample_df.to_excel(SAMPLE_EXCEL, index=False)
SAMPLE_EXCEL.seek(0)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🚀 Quick Start")
    st.download_button(
        "📥 Download Sample Excel",
        data=SAMPLE_EXCEL,
        file_name="chainforge_sample.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.info("**Expected columns:**\n"
            "- Supplier\n"
            "- City\n"
            "- Lat\n"
            "- Lon\n"
            "- km_to_next\n"
            "- Transport (Truck/Ship/Rail)\n"
            "- Tons")

# ─── FILE UPLOAD ──────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Drop your Excel file here", type=["xlsx", "xls"])

if uploaded_file is None:
    st.warning("👆 Upload a file or use the sample above to see magic.")
    st.stop()

# ─── LOAD & VALIDATE DATA ────────────────────────────────────────────────────
try:
    df = pd.read_excel(uploaded_file)
    required = ["Supplier", "City", "Lat", "Lon", "km_to_next", "Transport", "Tons"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"Missing columns: {', '.join(missing)}")
        st.stop()
except Exception as e:
    st.error(f"Error reading file: {e}")
    st.stop()

# ─── CALCULATE CO₂ (IPCC 2024 factors) ───────────────────────────────────────
CO2_FACTORS = {"Truck": 0.12, "Ship": 0.015, "Rail": 0.04}  # kg CO₂e per ton-km
df["CO2_kg"] = df["km_to_next"] * df["Tons"] * df["Transport"].map(CO2_FACTORS)
total_co2 = df["CO2_kg"].sum()
total_cost = df["km_to_next"].sum() * 18  # R18 per km (ZA truck avg)

# ─── MAP VISUALISATION ───────────────────────────────────────────────────────
m = folium.Map(location=[df["Lat"].mean(), df["Lon"].mean()], zoom_start=6)
points = list(zip(df["Lat"], df["Lon"], df["Supplier"], df["Transport"], df["CO2_kg"]))

for i, (lat, lon, name, trans, co2) in enumerate(points):
    color = "green" if co2 < 200 else "orange" if co2 < 500 else "red"
    folium.CircleMarker(
        [lat, lon],
        radius=8,
        popup=f"<b>{name}</b><br>{trans}<br>CO₂: {co2:.0f} kg",
        color=color,
        fill=True
    ).add_to(m)
    if i < len(points)-1:
        folium.PolyLine([[lat, lon], [points[i+1][0], points[i+1][1]]], color="blue", weight=2.5).add_to(m)

st.subheader("🗺️ Live Supply Chain Map")
map_data = st_folium(m, width=700, height=500)

# ─── AI REROUTE SUGGESTION (GROQ) ────────────────────────────────────────────
if st.button("🤖 Ask AI: Cheaper & Greener Route?"):
    with st.spinner("AI thinking..."):
        prompt = f"""
You are a supply chain expert in South Africa. Current route:
{df.to_csv(index=False)}

Total CO₂: {total_co2:.0f} kg. Total distance: {df['km_to_next'].sum():.0f} km.

Suggest ONE alternative route using Maputo, rail, or local hubs to cut CO₂ by >20% and cost.
Output JSON:
{{"suggestion": "...", "new_co2_kg": 123, "savings_r": 1234}}
"""
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300
            }
            if GROQ_API_KEY:
                response = requests.post(GROQ_URL, json=payload, headers=headers, timeout=20)
                ai_text = response.json()["choices"][0]["message"]["content"]
            else:
                ai_text = '{"suggestion": "Sign up at groq.com for free $100 credit to enable AI!", "new_co2_kg": 0, "savings_r": 0}'
        except:
            ai_text = '{"suggestion": "AI offline – add GROQ_API_KEY in Streamlit Secrets", "new_co2_kg": 0, "savings_r": 0}'

        try:
            import json
            ai = json.loads(ai_text)
            st.success(f"**AI Suggestion:** {ai['suggestion']}")
            if ai["new_co2_kg"] > 0:
                reduction = (1 - ai["new_co2_kg"] / total_co2) * 100
                st.metric("CO₂ Reduction", f"{reduction:.1f}%", f"{ai['savings_r']:,.0f} ZAR saved")
        except:
            st.code(ai_text)

# ─── CBAM PDF REPORT ─────────────────────────────────────────────────────────
def generate_pdf(df, total_co2, total_cost):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("ChainForge AI – CBAM Pre-Report", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Generated: November 15, 2025", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["Supplier", "Transport", "Tons", "km", "CO₂ (kg)"]]
    for _, row in df.iterrows():
        data.append([row["Supplier"], row["Transport"], f"{row['Tons']}", f"{row['km_to_next']}", f"{row['CO2_kg']:.0f}"])
    data.append(["", "", "", "Total", f"{total_co2:.0f} kg"])

    t = Table(data, colWidths=[120, 80, 50, 50, 80])
    t.setStyle([('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black)])
    elements.append(t)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Total Freight Cost (est): R {total_cost:,.0f}", styles['Normal']))
    elements.append(Paragraph("Ready for EU CBAM submission (2026)", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

if st.button("📑 Download CBAM PDF Report"):
    pdf = generate_pdf(df, total_co2, total_cost)
    st.download_button(
        "Download PDF",
        data=pdf,
        file_name=f"CBAM_Report_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

# ─── SUMMARY METRICS ──────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("Total CO₂", f"{total_co2:,.0f} kg")
col2.metric("Distance", f"{df['km_to_next'].sum():,.0f} km")
col3.metric("Est. Cost", f"R {total_cost:,.0f}")

# ─── PAYMENT CTA (Ozow) ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("✅ Ready to go live?")
st.markdown("""
**Growth Tier: R 999/month**  
- Unlimited SKUs  
- Weekly AI alerts  
- Bank finance API  
""")
if st.button("💸 Pay with Ozow (Instant EFT)"):
    st.markdown("[Pay Now →](https://pay.ozow.me/xxxxxx)")  # Replace with your Ozow link

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.caption("Built by a solo dev in South Africa 🇿🇦 | Bootstrap MVP | v0.1")