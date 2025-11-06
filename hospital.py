import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import openrouteservice
from io import BytesIO

# -----------------------------
# 1️⃣ Load hospital data
# -----------------------------
file_path = "Malaysia Hospital.xlsx"
df = pd.read_excel(file_path)
df = df.rename(columns=lambda x: x.strip())

# Ensure correct column names
df.rename(columns={
    "Hospital Name": "Hospital",
    "State": "State"
}, inplace=True)

df.dropna(subset=["Latitude", "Longitude"], inplace=True)

# -----------------------------
# 2️⃣ Sidebar UI
# -----------------------------
st.sidebar.title("⚙️ Control Panel")

api_key = st.sidebar.text_input("🔑 OpenRouteService API Key", type="password")
speed_input = st.sidebar.number_input("🚘 Average Driving Speed (km/h):", min_value=10, max_value=200, value=80)

# Select State and Hospital A
state_a = st.sidebar.selectbox("🌍 Select State for Hospital A:", sorted(df["State"].unique()))
hospitals_a = df[df["State"] == state_a]["Hospital"].unique()
hospital_a = st.sidebar.selectbox("🏥 Select Hospital A:", hospitals_a)

# Select State and Hospital B
state_b = st.sidebar.selectbox("🌍 Select State for Hospital B:", sorted(df["State"].unique()))
hospitals_b = df[df["State"] == state_b]["Hospital"].unique()
hospital_b = st.sidebar.selectbox("🏥 Select Hospital B:", hospitals_b)

# Reset map button
reset_map = st.sidebar.button("🔄 Reset Map")

# -----------------------------
# 3️⃣ Main UI
# -----------------------------
st.title("🏥 Malaysia Hospital Route & Driving Distance Map")
st.write("Select hospitals across Malaysia to calculate the road distance and estimated travel time.")

# Base map
m = folium.Map(location=[4.2105, 101.9758], zoom_start=6)

# Add hospital markers
for _, row in df.iterrows():
    folium.Marker(
        [row["Latitude"], row["Longitude"]],
        popup=f"{row['Hospital']} ({row['State']})",
        icon=folium.Icon(color="blue", icon="plus-sign"),
    ).add_to(m)

# Handle reset map
if reset_map:
    st.experimental_rerun()

# -----------------------------
# 4️⃣ Calculate Distance
# -----------------------------
route_data = None

if api_key and hospital_a and hospital_b:
    try:
        a_row = df[df["Hospital"] == hospital_a].iloc[0]
        b_row = df[df["Hospital"] == hospital_b].iloc[0]
        coord_a = (a_row["Longitude"], a_row["Latitude"])
        coord_b = (b_row["Longitude"], b_row["Latitude"])

        client = openrouteservice.Client(key=api_key)
        route = client.directions(
            coordinates=[coord_a, coord_b],
            profile="driving-car",
            format="geojson"
        )

        distance_m = route["features"][0]["properties"]["segments"][0]["distance"]
        duration_s = route["features"][0]["properties"]["segments"][0]["duration"]

        distance_km = distance_m / 1000
        duration_hr = duration_s / 3600
        est_time_hr = distance_km / speed_input
        est_hours = int(est_time_hr)
        est_minutes = int((est_time_hr - est_hours) * 60)

        folium.GeoJson(route, name="Route").add_to(m)
        folium.Marker(
            [a_row["Latitude"], a_row["Longitude"]],
            popup=f"Hospital A: {hospital_a}",
            icon=folium.Icon(color="green"),
        ).add_to(m)
        folium.Marker(
            [b_row["Latitude"], b_row["Longitude"]],
            popup=f"Hospital B: {hospital_b}",
            icon=folium.Icon(color="red"),
        ).add_to(m)

        st.success(f"🚗 Distance from **{hospital_a}** → **{hospital_b}**: **{distance_km:.2f} km**")
        st.info(f"🕒 Estimated time @ {speed_input} km/h: **{est_hours} hr {est_minutes} min**")
        st.caption(f"⏱ Actual time from OpenRouteService: {duration_hr:.2f} hr")

        # Save route info
        route_data = {
            "Hospital A": [hospital_a],
            "State A": [state_a],
            "Hospital B": [hospital_b],
            "State B": [state_b],
            "Distance (km)": [distance_km],
            "Est. Time (user speed)": [f"{est_hours} hr {est_minutes} min"],
            "API Time (hr)": [f"{duration_hr:.2f} hr"]
        }

    except Exception as e:
        st.error(f"⚠️ Error calculating route: {e}")

elif not api_key:
    st.warning("Please enter your OpenRouteService API key in the sidebar.")

# -----------------------------
# 5️⃣ Export Excel
# -----------------------------
if route_data:
    df_export = pd.DataFrame(route_data)
    output = BytesIO()
    df_export.to_excel(output, index=False)
    st.download_button(
        label="📤 Export Route Info to Excel",
        data=output.getvalue(),
        file_name="hospital_route.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -----------------------------
# 6️⃣ Display Map
# -----------------------------
st_folium(m, width=900, height=600)
