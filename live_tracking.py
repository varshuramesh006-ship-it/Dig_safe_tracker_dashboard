import streamlit as st
import pandas as pd
import sqlite3
import time
import folium
from streamlit_folium import st_folium

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="DigSafe Tracker - Live Monitoring",
    page_icon="🚛",
    layout="wide"
)

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DB_FILE = "data/digsafe_tracker.db"

try:
    conn = sqlite3.connect(DB_FILE)

    tracking_df = pd.read_sql_query(
        "SELECT * FROM vehicle_tracking ORDER BY vehicle_id, timestamp",
        conn
    )

    alerts_df = pd.read_sql_query(
        "SELECT * FROM alerts",
        conn
    )

    summary_df = pd.read_sql_query(
        "SELECT * FROM vehicle_summary",
        conn
    )

    conn.close()

except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

# --------------------------------------------------
# TITLE
# --------------------------------------------------

st.title("🚛 DigSafe Tracker - Live Monitoring")

st.write(
    "Integrated monitoring system for GPS tracking, "
    "vehicle movement, truck weight, geofence violations "
    "and suspicious activity detection."
)

st.divider()

# --------------------------------------------------
# BASIC COUNTS
# --------------------------------------------------

total_vehicles = tracking_df["vehicle_id"].nunique()
total_records = len(tracking_df)

if "alert_level" in alerts_df.columns:
    high_priority = len(
        alerts_df[alerts_df["alert_level"] == "HIGH PRIORITY ALERT"]
    )
    suspicious = len(
        alerts_df[alerts_df["alert_level"] == "SUSPICIOUS MOVEMENT"]
    )
else:
    high_priority = len(
        alerts_df[
            alerts_df["final_alert_level"] == "HIGH PRIORITY ALERT"
        ]
    )
    suspicious = len(
        alerts_df[
            alerts_df["final_alert_level"] == "SUSPICIOUS MOVEMENT"
        ]
    )

if "weight_status" in tracking_df.columns:
    overweight = len(
        tracking_df[
            tracking_df["weight_status"].astype(str).str.upper()
            == "OVERWEIGHT"
        ]
    )
else:
    overweight = 0

# --------------------------------------------------
# TOP DASHBOARD METRICS
# --------------------------------------------------

st.subheader("System Overview")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Vehicles", total_vehicles)
c2.metric("GPS Records", total_records)
c3.metric("High Priority", high_priority)
c4.metric("Suspicious", suspicious)
c5.metric("Overweight", overweight)

st.divider()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.header("Live Tracking Controls")

vehicles = sorted(
    tracking_df["vehicle_id"].unique()
)

selected_vehicle = st.sidebar.selectbox(
    "Select Vehicle",
    vehicles
)

update_interval = st.sidebar.selectbox(
    "Update Interval (seconds)",
    [1, 2, 3, 4, 5],
    index=0
)

start_tracking = st.sidebar.button(
    "▶ Start Live Tracking"
)

st.sidebar.divider()

st.sidebar.info(
    "DigSafe Tracker\n\n"
    "GPS Monitoring\n"
    "Weight Monitoring\n"
    "Geofencing\n"
    "ML Anomaly Detection\n"
    "Alert Management"
)

# --------------------------------------------------
# VEHICLE MONITORING
# --------------------------------------------------

st.subheader("🚛 Vehicle Monitoring")

if summary_df is not None and len(summary_df) > 0:
    st.dataframe(
        summary_df,
        width="stretch"
    )

st.divider()

# --------------------------------------------------
# SELECT VEHICLE DATA
# --------------------------------------------------

vehicle_data = tracking_df[
    tracking_df["vehicle_id"] == selected_vehicle
].sort_values("timestamp").reset_index(drop=True)

# --------------------------------------------------
# RESTRICTED ZONE
# --------------------------------------------------

RESTRICTED_LATITUDE = 10.7950
RESTRICTED_LONGITUDE = 10.7100

# Correct longitude for the DigSafe synthetic zone
RESTRICTED_LONGITUDE = 78.7100

RESTRICTED_RADIUS_M = 500

# --------------------------------------------------
# INITIAL VEHICLE STATUS
# --------------------------------------------------

if len(vehicle_data) > 0:

    first = vehicle_data.iloc[0]

    st.subheader(
        f"📡 Current Status - {selected_vehicle}"
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Vehicle",
        selected_vehicle
    )

    col2.metric(
        "Speed",
        f"{float(first['speed']):.2f} km/h"
    )

    col3.metric(
        "Truck Weight",
        f"{float(first['truck_weight_kg']):.0f} kg"
    )

    col4.metric(
        "Capacity",
        f"{float(first['truck_capacity_kg']):.0f} kg"
    )

    col5.metric(
        "Weight Status",
        str(first["weight_status"])
    )

    st.write(
        f"**Timestamp:** {first['timestamp']}  |  "
        f"**Latitude:** {float(first['latitude']):.6f}  |  "
        f"**Longitude:** {float(first['longitude']):.6f}"
    )

    if "final_alert_level" in first.index:
        st.write(
            f"**Alert Level:** {first['final_alert_level']}"
        )

    if "alert_reason" in first.index:
        st.write(
            f"**Alert Reason:** {first['alert_reason']}"
        )

st.divider()

# --------------------------------------------------
# LIVE TRACKING
# --------------------------------------------------

if start_tracking:

    st.subheader(
        f"📍 Live GPS Tracking - {selected_vehicle}"
    )

    info_area = st.empty()
    map_area = st.empty()
    table_area = st.empty()
    status_area = st.empty()

    progress_bar = st.progress(0)

    route_points = []

    for index, row in vehicle_data.iterrows():

        latitude = float(row["latitude"])
        longitude = float(row["longitude"])

        route_points.append(
            [latitude, longitude]
        )

        # ------------------------------------------
        # LIVE VEHICLE INFORMATION
        # ------------------------------------------

        with info_area.container():

            st.subheader(
                f"🚛 Live Vehicle Status: {selected_vehicle}"
            )

            col1, col2, col3, col4, col5 = st.columns(5)

            col1.metric(
                "Speed",
                f"{float(row['speed']):.2f} km/h"
            )

            col2.metric(
                "Truck Weight",
                f"{float(row['truck_weight_kg']):.0f} kg"
            )

            col3.metric(
                "Capacity",
                f"{float(row['truck_capacity_kg']):.0f} kg"
            )

            col4.metric(
                "Weight Status",
                str(row["weight_status"])
            )

            col5.metric(
                "Alert Level",
                str(row["final_alert_level"])
            )

            st.write(
                f"**Timestamp:** {row['timestamp']}"
            )

            st.write(
                f"**GPS:** {latitude:.6f}, {longitude:.6f}"
            )

            if "alert_reason" in row.index:
                st.write(
                    f"**Alert Reason:** {row['alert_reason']}"
                )

        # ------------------------------------------
        # MAP
        # ------------------------------------------

        m = folium.Map(
            location=[
                latitude,
                longitude
            ],
            zoom_start=14
        )

        folium.Circle(
            location=[
                RESTRICTED_LATITUDE,
                RESTRICTED_LONGITUDE
            ],
            radius=RESTRICTED_RADIUS_M,
            color="red",
            fill=True,
            fill_opacity=0.15,
            popup="Restricted Zone"
        ).add_to(m)

        if len(route_points) > 1:

            folium.PolyLine(
                route_points,
                weight=4,
                tooltip="Vehicle Route"
            ).add_to(m)

        folium.Marker(
            location=[
                latitude,
                longitude
            ],
            popup=(
                f"Vehicle: {selected_vehicle}<br>"
                f"Speed: {float(row['speed']):.2f} km/h<br>"
                f"Weight: {float(row['truck_weight_kg']):.0f} kg<br>"
                f"Weight Status: {row['weight_status']}<br>"
                f"Alert: {row['final_alert_level']}"
            ),
            tooltip="Current Vehicle"
        ).add_to(m)

        map_area.empty()

        with map_area:

            st_folium(
                m,
                width=None,
                height=500,
                key=f"live_map_{selected_vehicle}_{index}"
            )

        # ------------------------------------------
        # RECENT RECORDS
        # ------------------------------------------

        recent = vehicle_data.iloc[
            max(0, index - 9):index + 1
        ]

        table_area.subheader(
            "📋 Recent Vehicle Records"
        )

        columns_to_show = [
            "timestamp",
            "latitude",
            "longitude",
            "speed",
            "truck_weight_kg",
            "weight_status",
            "final_alert_level"
        ]

        available_columns = [
            c for c in columns_to_show
            if c in recent.columns
        ]

        table_area.dataframe(
            recent[available_columns],
            width="stretch"
        )

        # ------------------------------------------
        # PROGRESS
        # ------------------------------------------

        progress = int(
            ((index + 1) / len(vehicle_data)) * 100
        )

        progress_bar.progress(progress)

        status_area.info(
            f"Live tracking in progress: "
            f"{index + 1} / {len(vehicle_data)} records"
        )

        time.sleep(update_interval)

    progress_bar.progress(100)

    status_area.success(
        f"Live tracking completed for {selected_vehicle}."
    )

    st.success(
        "MODULE 11 COMPLETED - Simulated Live Tracking Finished"
    )

else:

    st.info(
        "Click 'Start Live Tracking' in the sidebar "
        "to start the GPS simulation."
    )

st.divider()

# ==================================================
# ALERT RECORDS
# ==================================================

st.subheader("⚠️ Alert Records")

if len(alerts_df) > 0:

    if "alert_level" in alerts_df.columns:
        alert_level_column = "alert_level"
    else:
        alert_level_column = "final_alert_level"

    alert_filter = st.selectbox(
        "Filter Alert Level",
        [
            "ALL",
            "HIGH PRIORITY ALERT",
            "SUSPICIOUS MOVEMENT"
        ]
    )

    if alert_filter == "ALL":

        filtered_alerts = alerts_df.copy()

    else:

        filtered_alerts = alerts_df[
            alerts_df[alert_level_column]
            == alert_filter
        ].copy()

    st.write(
        f"Showing {len(filtered_alerts)} alert records"
    )

    st.dataframe(
        filtered_alerts,
        width="stretch"
    )

else:

    st.success("No alert records found.")

st.divider()

# ==================================================
# ALERT SUMMARY
# ==================================================

st.subheader("📊 Alert Summary")

if len(alerts_df) > 0:

    if "alert_level" in alerts_df.columns:

        alert_summary = (
            alerts_df["alert_level"]
            .value_counts()
            .reset_index()
        )

    else:

        alert_summary = (
            alerts_df["final_alert_level"]
            .value_counts()
            .reset_index()
        )

    alert_summary.columns = [
        "Alert Level",
        "Count"
    ]

    st.dataframe(
        alert_summary,
        width="stretch"
    )

else:

    st.info("No alerts available.")

st.divider()

# ==================================================
# WEIGHT MONITORING
# ==================================================

st.subheader("⚖️ Weight Monitoring")

if "weight_status" in tracking_df.columns:

    weight_summary = (
        tracking_df["weight_status"]
        .value_counts()
        .reset_index()
    )

    weight_summary.columns = [
        "Weight Status",
        "Count"
    ]

    st.dataframe(
        weight_summary,
        width="stretch"
    )

    overweight_records = tracking_df[
        tracking_df["weight_status"]
        .astype(str)
        .str.upper()
        == "OVERWEIGHT"
    ]

    if len(overweight_records) > 0:

        st.warning(
            f"⚠️ {len(overweight_records)} overweight "
            "records detected."
        )

        st.dataframe(
            overweight_records,
            width="stretch"
        )

    else:

        st.success(
            "No overweight records detected."
        )

else:

    st.info(
        "Weight information is not available."
    )

st.divider()

# ==================================================
# SYSTEM INFORMATION
# ==================================================

st.subheader("ℹ️ System Information")

st.write(
    """
**DigSafe Tracker Architecture**

ESP32 / GPS / Weight Sensor  
↓  
Python Data Processing  
↓  
GPS + Weight + Geofence Analysis  
↓  
Machine Learning Anomaly Detection  
↓  
SQLite Database  
↓  
Streamlit Monitoring Dashboard
"""
)

st.success(
    "DigSafe Tracker - Integrated Monitoring Dashboard"
)
