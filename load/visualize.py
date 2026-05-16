import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime
 
# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Canada Weather Dashboard",
    page_icon="🍁",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');
 
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    h1, h2, h3 { font-family: 'Space Mono', monospace; }
 
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: white;
    }
    .metric-card .value {
        font-size: 2.5rem;
        font-weight: 700;
        font-family: 'Space Mono', monospace;
        color: #e94560;
    }
    .metric-card .label {
        font-size: 0.85rem;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 4px;
    }
    .weather-row {
        background: #1a1a2e;
        border-left: 4px solid #e94560;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 6px 0;
        color: white;
    }
    .stSelectbox label, .stMultiSelect label { color: #a0aec0 !important; }
    .sidebar .stSelectbox { background: #1a1a2e; }
    div[data-testid="metric-container"] {
        background: #1a1a2e;
        border: 1px solid #0f3460;
        border-radius: 10px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)
 
# ── DB Connection ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host     = os.getenv("POSTGRES_HOST", "postgres"),
        port     = int(os.getenv("POSTGRES_PORT", 5432)),
        dbname   = os.getenv("POSTGRES_DB", "weather_db"),
        user     = os.getenv("POSTGRES_USER"),
        password = os.getenv("POSTGRES_PASSWORD"),
    )

@st.cache_data(ttl=300)
def load_table(query: str) -> pd.DataFrame:
    try:
        conn = get_connection()
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Query failed: {e}")
        return pd.DataFrame()
 
# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all():
    weather     = load_table("SELECT * FROM gold.weather")
    weather_day = load_table("SELECT * FROM gold.weather_day")
    weather_ngt = load_table("SELECT * FROM gold.weather_night")
    weather_dif = load_table("SELECT * FROM gold.weather_difference")
    return weather, weather_day, weather_ngt, weather_dif
 
try:
    weather, weather_day, weather_night, weather_diff = load_all()
    data_loaded = True
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    data_loaded = False
 
# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🍁 Weather")
    st.markdown("### Filters")
 
    if data_loaded:
        provinces = sorted(weather["province"].dropna().str.upper().unique())
        selected_province = st.selectbox("Province", ["All"] + list(provinces))
 
        if selected_province != "All":
            cities = sorted(weather[weather["province"].str.upper() == selected_province]["city"].unique())
        else:
            cities = sorted(weather["city"].unique())
 
        selected_city = st.selectbox("City", ["All"] + list(cities))
 
        st.markdown("---")
        st.markdown("### Info")
        if not weather.empty and "time_create" in weather.columns:
            last_update = pd.to_datetime(weather["time_create"]).max()
            st.markdown(f"**Last updated:**  \n`{last_update}`")
        st.markdown(f"**Total cities:** `{len(weather)}`")
 
# ── Filter data ───────────────────────────────────────────────────────────────
def apply_filters(df):
    if not data_loaded:
        return df
    if selected_province != "All":
        df = df[df["province"].str.upper() == selected_province]
    if selected_city != "All":
        df = df[df["city"] == selected_city]
    return df
 
# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("# 🍁 Canada Daily Weather Dashboard")
st.markdown(f"*Report for {datetime.now().strftime('%A, %B %d %Y')}*")
st.markdown("---")
 
if data_loaded:
    day_f   = apply_filters(weather_day)
    night_f = apply_filters(weather_night)
    diff_f  = apply_filters(weather_diff)
    meta_f  = apply_filters(weather)
 
    # ── KPI Row ───────────────────────────────────────────────────────────────
    st.markdown("### 📊 Summary")
    k1, k2, k3, k4, k5 = st.columns(5)
 
    with k1:
        avg_temp = day_f["temp_c"].mean()
        st.metric("Avg Daytime Temp", f"{avg_temp:.1f} °C" if not pd.isna(avg_temp) else "N/A")
    with k2:
        avg_temp_n = night_f["temp_c"].mean()
        st.metric("Avg Night Temp", f"{avg_temp_n:.1f} °C" if not pd.isna(avg_temp_n) else "N/A")
    with k3:
        rain_cities = day_f[day_f["precip_mm"] > 0]["city"].nunique()
        st.metric("Cities with Rain", rain_cities)
    with k4:
        avg_wind = day_f["wind_speed_kmh"].mean()
        st.metric("Avg Wind Speed", f"{avg_wind:.0f} km/h" if not pd.isna(avg_wind) else "N/A")
    with k5:
        avg_humidity = day_f["humidity_pct"].mean()
        st.metric("Avg Humidity", f"{avg_humidity:.0f}%" if not pd.isna(avg_humidity) else "N/A")
 
    st.markdown("---")
 
    # ── Day / Night tabs ──────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["☀️ Daytime", "🌙 Tonight", "📈 Day vs Night", "🗺️ City Info"])
 
    with tab1:
        st.markdown("### ☀️ Daytime Forecast")
        if day_f.empty:
            st.info("No daytime data available for selected filters.")
        else:
            # Hottest / coldest
            c1, c2 = st.columns(2)
            with c1:
                hottest = day_f.nlargest(5, "temp_c")[["city", "province", "temp_c", "humidity_pct", "wind_speed_kmh"]]
                st.markdown("**🌡️ Hottest Cities**")
                st.dataframe(hottest, use_container_width=True, hide_index=True)
            with c2:
                coldest = day_f.nsmallest(5, "temp_c")[["city", "province", "temp_c", "humidity_pct", "wind_speed_kmh"]]
                st.markdown("**🥶 Coldest Cities**")
                st.dataframe(coldest, use_container_width=True, hide_index=True)
 
            st.markdown("**Full Daytime Data**")
            display_cols = ["city", "region", "province", "temp_c", "temp_class",
                            "humidity_pct", "uv_index", "uv_category",
                            "precip_mm", "precip_type", "wind_speed_kmh", "wind_gust_kmh"]
            st.dataframe(
                day_f[[c for c in display_cols if c in day_f.columns]],
                use_container_width=True,
                hide_index=True
            )
 
    with tab2:
        st.markdown("### 🌙 Tonight Forecast")
        if night_f.empty:
            st.info("No tonight data available for selected filters.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                warmest = night_f.nlargest(5, "temp_c")[["city", "province", "temp_c", "humidity_pct"]]
                st.markdown("**🌡️ Warmest Nights**")
                st.dataframe(warmest, use_container_width=True, hide_index=True)
            with c2:
                coldest_n = night_f.nsmallest(5, "temp_c")[["city", "province", "temp_c", "humidity_pct"]]
                st.markdown("**🥶 Coldest Nights**")
                st.dataframe(coldest_n, use_container_width=True, hide_index=True)
 
            st.markdown("**Full Tonight Data**")
            display_cols_n = ["city", "region", "province", "temp_c", "temp_class",
                              "humidity_pct", "precip_mm", "precip_type",
                              "wind_speed_kmh", "wind_gust_kmh"]
            st.dataframe(
                night_f[[c for c in display_cols_n if c in night_f.columns]],
                use_container_width=True,
                hide_index=True
            )
 
    with tab3:
        st.markdown("### 📈 Day vs Night Difference")
        if diff_f.empty:
            st.info("No difference data available for selected filters.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                biggest_swing = diff_f.nlargest(5, "temp_c")[["city", "province", "temp_c"]]
                biggest_swing.columns = ["City", "Province", "Temp Swing (°C)"]
                st.markdown("**🌡️ Biggest Temp Swings**")
                st.dataframe(biggest_swing, use_container_width=True, hide_index=True)
            with c2:
                humid_swing = diff_f.nlargest(5, "humidity_pct")[["city", "province", "humidity_pct"]]
                humid_swing.columns = ["City", "Province", "Humidity Swing (%)"]
                st.markdown("**💧 Biggest Humidity Swings**")
                st.dataframe(humid_swing, use_container_width=True, hide_index=True)
            with c3:
                wind_swing = diff_f.nlargest(5, "wind_speed_kmh")[["city", "province", "wind_speed_kmh"]]
                wind_swing.columns = ["City", "Province", "Wind Swing (km/h)"]
                st.markdown("**💨 Biggest Wind Swings**")
                st.dataframe(wind_swing, use_container_width=True, hide_index=True)
 
            st.markdown("**Full Difference Table**")
            st.dataframe(diff_f, use_container_width=True, hide_index=True)
 
    with tab4:
        st.markdown("### 🗺️ City Info")
        if meta_f.empty:
            st.info("No city data available for selected filters.")
        else:
            st.markdown("**Sunrise & Sunset**")
            sun_cols = ["city", "province", "region", "sunrise_str", "sunset_str",
                        "normal_high_c", "normal_low_c"]
            st.dataframe(
                meta_f[[c for c in sun_cols if c in meta_f.columns]],
                use_container_width=True,
                hide_index=True
            )