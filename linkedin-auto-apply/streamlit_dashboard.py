"""
streamlit_dashboard.py — Real-time dashboard for application tracking.
Run with: streamlit run streamlit_dashboard.py
"""

import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time

from logger import load_applications, init_csv
from config import CSV_FILE, MIN_COMPATIBILITY_SCORE

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LinkedIn Auto-Apply Dashboard",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #0a0f1e; }
    .stMetric { background: #111827; border-radius: 12px; padding: 1rem; }
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .metric-value { font-size: 3rem; font-weight: 700; margin: 0; }
    .metric-label { color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em; }
    h1 { color: #f1f5f9 !important; }
    h2, h3 { color: #cbd5e1 !important; }
</style>
""", unsafe_allow_html=True)


# ─── Load Data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_data() -> pd.DataFrame:
    init_csv()
    rows = load_applications()
    if not rows:
        return pd.DataFrame(columns=[
            "date_applied","company","role","location","salary",
            "url","status","compatibility_score","skip_reason","cover_letter_used"
        ])
    df = pd.DataFrame(rows)
    df["compatibility_score"] = pd.to_numeric(df["compatibility_score"], errors="coerce").fillna(0).astype(int)
    df["date_applied"] = pd.to_datetime(df["date_applied"], errors="coerce")
    return df


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background: linear-gradient(135deg, #1e40af, #0f172a); padding: 2rem; border-radius: 16px; margin-bottom: 2rem;'>
    <h1 style='color: white; margin: 0; font-size: 2rem;'>💼 LinkedIn Auto-Apply Dashboard</h1>
    <p style='color: #93c5fd; margin: 0.5rem 0 0;'>Real-time job application tracker for Golla Nanda Kumar — DevOps Engineer</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh toggle
col_refresh, col_spacer = st.columns([1, 5])
with col_refresh:
    auto_refresh = st.toggle("Auto-refresh (10s)", value=False)

df = load_data()

# ─── KPI Cards ────────────────────────────────────────────────────────────────
total_found   = len(df)
total_applied = len(df[df["status"] == "Applied"])
total_skipped = len(df[df["status"] == "Skipped"])
total_errors  = len(df[df["status"] == "Error"])
success_rate  = round((total_applied / total_found * 100) if total_found > 0 else 0, 1)
avg_score     = round(df[df["status"] == "Applied"]["compatibility_score"].mean(), 1) if total_applied > 0 else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)

def kpi(col, icon: str, value, label: str, color: str) -> None:
    col.markdown(f"""
    <div class='metric-card'>
        <div style='font-size:2rem'>{icon}</div>
        <div class='metric-value' style='color:{color}'>{value}</div>
        <div class='metric-label'>{label}</div>
    </div>
    """, unsafe_allow_html=True)

kpi(col1, "🔍", total_found,   "Jobs Found",    "#60a5fa")
kpi(col2, "✅", total_applied, "Applied",        "#34d399")
kpi(col3, "⏭",  total_skipped, "Skipped",        "#fbbf24")
kpi(col4, "❌", total_errors,  "Errors",         "#f87171")
kpi(col5, "📈", f"{success_rate}%", "Apply Rate","#a78bfa")
kpi(col6, "🎯", f"{avg_score}", "Avg Score",     "#38bdf8")

st.markdown("<br>", unsafe_allow_html=True)

if df.empty:
    st.info("No applications recorded yet. Run `python main.py` to start the bot.")
    st.stop()

# ─── Charts ──────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("### Application Status Distribution")
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    colors = {"Applied": "#34d399", "Skipped": "#fbbf24", "Error": "#f87171"}
    fig_pie = px.pie(
        status_counts, names="Status", values="Count",
        color="Status", color_discrete_map=colors,
        hole=0.5,
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"), legend=dict(font=dict(color="#cbd5e1")),
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with chart_col2:
    st.markdown("### Compatibility Score Distribution")
    applied_df = df[df["status"] == "Applied"]
    if not applied_df.empty:
        fig_hist = px.histogram(
            applied_df, x="compatibility_score", nbins=10,
            color_discrete_sequence=["#6366f1"],
            labels={"compatibility_score": "Score", "count": "Applications"},
        )
        fig_hist.add_vline(
            x=MIN_COMPATIBILITY_SCORE, line_dash="dash", line_color="#f87171",
            annotation_text=f"Min threshold ({MIN_COMPATIBILITY_SCORE})",
            annotation_font_color="#f87171",
        )
        fig_hist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"), margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No applied jobs to show.")

# ─── Timeline ────────────────────────────────────────────────────────────────
st.markdown("### Applications Over Time")
timeline_df = df.dropna(subset=["date_applied"]).copy()
if not timeline_df.empty:
    timeline_df["date"] = timeline_df["date_applied"].dt.date
    daily = timeline_df.groupby(["date", "status"]).size().reset_index(name="count")
    fig_line = px.bar(
        daily, x="date", y="count", color="status",
        color_discrete_map={"Applied": "#34d399", "Skipped": "#fbbf24", "Error": "#f87171"},
        barmode="stack",
    )
    fig_line.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"), margin=dict(t=10, b=10),
        xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ─── Skip Reasons ─────────────────────────────────────────────────────────────
skip_col, loc_col = st.columns(2)

with skip_col:
    st.markdown("### Top Skip Reasons")
    skipped_df = df[df["status"] == "Skipped"]
    if not skipped_df.empty:
        reasons = skipped_df["skip_reason"].value_counts().head(8).reset_index()
        reasons.columns = ["Reason", "Count"]
        fig_bar = px.bar(
            reasons, x="Count", y="Reason", orientation="h",
            color_discrete_sequence=["#fbbf24"],
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"), margin=dict(t=10, b=10),
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with loc_col:
    st.markdown("### Applied Jobs by Location")
    applied_df = df[df["status"] == "Applied"]
    if not applied_df.empty:
        loc_counts = applied_df["location"].str.split(",").str[0].value_counts().reset_index()
        loc_counts.columns = ["Location", "Count"]
        fig_loc = px.bar(
            loc_counts, x="Location", y="Count",
            color_discrete_sequence=["#6366f1"],
        )
        fig_loc.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"), margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_loc, use_container_width=True)

# ─── Applications Table ───────────────────────────────────────────────────────
st.markdown("### All Applications")

filter_status = st.multiselect(
    "Filter by status",
    options=["Applied", "Skipped", "Error"],
    default=["Applied", "Skipped"],
)

filtered = df[df["status"].isin(filter_status)] if filter_status else df

display_cols = ["date_applied", "company", "role", "location", "status",
                "compatibility_score", "salary", "skip_reason"]
display_df = filtered[display_cols].sort_values("date_applied", ascending=False)
display_df["date_applied"] = display_df["date_applied"].dt.strftime("%Y-%m-%d %H:%M")

def highlight_status(row):
    color_map = {"Applied": "#052e16", "Skipped": "#422006", "Error": "#450a0a"}
    color = color_map.get(row["status"], "")
    return [f"background-color: {color}" if color else ""] * len(row)

st.dataframe(
    display_df.style.apply(highlight_status, axis=1),
    use_container_width=True,
    height=400,
)

# Download CSV
with open(CSV_FILE, "rb") as f:
    st.download_button(
        label="⬇ Download applications.csv",
        data=f,
        file_name="applications.csv",
        mime="text/csv",
    )

# Auto-refresh
if auto_refresh:
    time.sleep(10)
    st.rerun()
