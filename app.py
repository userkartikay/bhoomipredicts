import os

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("BHOOMIPREDICT_API", os.getenv("RISKXPLAIN_API", "http://localhost:8000"))
st.set_page_config(page_title="BhooMiPredict", page_icon="BP", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#17352e; --muted:#6d7c75; --line:#dce7df; --paper:#fbfcf8; --orange:#d86b32; }
    .stApp { background:var(--paper); color:var(--ink); font-family:'DM Sans', sans-serif; }
    h1,h2,h3,h4 { font-family:'Space Grotesk', sans-serif !important; color:var(--ink) !important; letter-spacing:-.02em; }
    h1 { font-size:2.6rem !important; line-height:1.05 !important; }
    h2 { font-size:1.55rem !important; }
    [data-testid="stSidebar"] { background:#17352e; border-right:0; }
    [data-testid="stSidebar"] * { color:#eef7f0 !important; }
    [data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:12px; padding:16px 18px; box-shadow:0 4px 16px rgba(23,53,46,.04); }
    [data-testid="stMetricLabel"] { color:var(--muted); font-size:.78rem; }
    [data-testid="stMetricValue"] { color:var(--ink); font-family:'Space Grotesk', sans-serif; }
    .brand-mark { display:flex; align-items:center; gap:10px; margin:8px 0 35px; }
    .brand-icon { background:#e9ad4e; color:#17352e; width:34px; height:34px; display:grid; place-items:center; border-radius:9px; font-weight:700; }
    .brand-name { font-family:'Space Grotesk', sans-serif; font-size:1.25rem; font-weight:700; color:#fff; }
    .brand-sub { color:#a9c3b5; font-size:.72rem; margin-top:-2px; }
    .eyebrow { color:var(--orange); text-transform:uppercase; font-size:.7rem; letter-spacing:.12em; font-weight:700; margin-bottom:8px; }
    .hero { background:linear-gradient(120deg,#e4f1e6 0%,#f7f0dc 100%); border:1px solid #d6e5d8; border-radius:16px; padding:26px 30px 24px; margin-bottom:22px; }
    .hero p { color:#51665c; max-width:680px; margin:8px 0 0; font-size:1rem; }
    .section-head { display:flex; justify-content:space-between; align-items:end; margin:28px 0 10px; }
    .section-note { color:var(--muted); font-size:.82rem; }
    .insight { background:white; border-left:4px solid var(--orange); border-top:1px solid var(--line); border-right:1px solid var(--line); border-bottom:1px solid var(--line); border-radius:0 10px 10px 0; padding:14px 16px; color:#40554b; font-size:.9rem; }
    .case-banner { background:#17352e; color:#fff; border-radius:14px; padding:20px 22px; margin:16px 0 20px; }
    .case-banner small { color:#afd0bc; text-transform:uppercase; letter-spacing:.1em; font-size:.65rem; }
    .case-banner strong { display:block; color:#fff; font:600 1.3rem 'Space Grotesk', sans-serif; margin-top:5px; }
    .detail-card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px 18px; min-height:132px; }
    .detail-card h4 { margin:0 0 12px; font-size:.9rem !important; }
    .detail-line { display:flex; justify-content:space-between; gap:12px; padding:5px 0; border-bottom:1px solid #eef3ee; font-size:.82rem; }
    .detail-line:last-child { border-bottom:0; }
    .detail-line span:first-child { color:var(--muted); }
    .detail-line span:last-child { color:var(--ink); font-weight:600; text-align:right; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=20)
def get(path: str, params: dict | None = None):
    response = requests.get(f"{API_URL}{path}", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def detail_card(title: str, values: dict) -> None:
    lines = "".join(f'<div class="detail-line"><span>{key}</span><span>{value}</span></div>' for key, value in values.items())
    st.markdown(f'<div class="detail-card"><h4>{title}</h4>{lines}</div>', unsafe_allow_html=True)


try:
    overview = get("/overview")
except requests.RequestException:
    st.error("The case service is not available. Please start the application service and try again.")
    st.stop()

with st.sidebar:
    st.markdown('<div class="brand-mark"><div class="brand-icon">BP</div><div><div class="brand-name">BhooMiPredict</div><div class="brand-sub">Land case intelligence</div></div></div>', unsafe_allow_html=True)
    st.caption("Prototype workspace")
    page = st.radio("Workspace", ["At a glance", "Cases needing attention", "Case details", "Data explorer", "Issues & alerts"], label_visibility="collapsed")
    st.caption("Data refreshed from the local case service")

if page == "At a glance":
    st.markdown('<div class="hero"><div class="eyebrow">Decision view · September 2026</div><h1>Know which land cases need help first.</h1><p>BhooMiPredict brings land, court, payment and rehabilitation updates into one clear view, so officers can act before a delay becomes a crisis.</p></div>', unsafe_allow_html=True)
    cards = st.columns(5, gap="medium")
    cards[0].metric("Cases being watched", overview["total_cases"])
    cards[1].metric("Needs quick action", overview["high_risk"])
    cards[2].metric("Needs follow-up", overview["medium_risk"])
    cards[3].metric("Moving normally", overview["low_risk"])
    cards[4].metric("Records to check", overview["fuzzy_matches"])
    st.markdown('<div class="section-head"><div><div class="eyebrow">Where attention is building</div><h2>District view</h2></div><div class="section-note">Average chance of delay</div></div>', unsafe_allow_html=True)
    districts = pd.DataFrame(overview["districts"])
    chart_col, list_col = st.columns([1.45, 1], gap="large")
    with chart_col:
        st.bar_chart(districts.set_index("district")["avg_probability"].rename("Chance of delay"), color="#d86b32", height=300)
    with list_col:
        st.dataframe(districts.rename(columns={"district": "District", "cases": "Cases", "avg_probability": "Average chance"}), use_container_width=True, hide_index=True, column_config={"Average chance": st.column_config.ProgressColumn("Average chance", min_value=0, max_value=1, format="%.0%")})
    st.markdown('<div class="insight"><strong>Today\'s reading:</strong> high-priority cases are surfaced first, with the likely reason and a suggested next step available for every case.</div>', unsafe_allow_html=True)

elif page == "Cases needing attention":
    st.markdown('<div class="eyebrow">Worklist</div><h1>Cases needing attention</h1><p class="section-note">Start with the cases most likely to lose time. Filter by priority or district.</p>', unsafe_allow_html=True)
    filter_a, filter_b, _ = st.columns([1, 1, 2])
    with filter_a:
        tier = st.selectbox("Priority", ["All", "High", "Medium", "Low"])
    with filter_b:
        district = st.selectbox("District", ["All"] + [item["district"] for item in overview["districts"]])
    params = {"tier": "" if tier == "All" else tier, "district": "" if district == "All" else district}
    queue = pd.DataFrame(get("/risk-queue", params)).rename(columns={"ulcid": "Case ID", "case_no": "Case number", "district": "District", "stage": "Current step", "risk_tier": "Priority", "risk_score": "Priority score", "delay_probability": "Chance of delay", "stay_status": "Court status"})
    st.markdown(f'<div class="insight"><strong>{len(queue)} cases</strong> match this view. Select a case in the Case details tab to see why it is flagged.</div>', unsafe_allow_html=True)
    st.dataframe(queue, use_container_width=True, hide_index=True, height=500, column_config={"Priority score": st.column_config.ProgressColumn("Priority score", min_value=0, max_value=1, format="%.2f"), "Chance of delay": st.column_config.ProgressColumn("Chance of delay", min_value=0, max_value=1, format="%.0%")})

elif page == "Case details":
    st.markdown('<div class="eyebrow">One case, one clear story</div><h1>Case details</h1>', unsafe_allow_html=True)
    queue = get("/risk-queue")
    labels = {item["ulcid"]: f"{item['case_no']} · {item['district']} · {item['risk_tier']} priority" for item in queue}
    selected = st.selectbox("Choose a case", list(labels), format_func=lambda key: labels[key])
    case = get(f"/cases/{selected}")
    prediction = case["prediction"]
    st.markdown(f'<div class="case-banner"><small>Selected case · {case["identity"]["ulcid"]}</small><strong>{case["identity"]["case_no"]} · {case["acquisition"]["district"]}</strong></div>', unsafe_allow_html=True)
    cards = st.columns(4, gap="medium")
    cards[0].metric("Priority", prediction["risk_tier"])
    cards[1].metric("Chance of delay", f'{prediction["delay_probability"]:.0%}')
    cards[2].metric("Priority score", f'{prediction["risk_score"]:.2f}')
    cards[3].metric("Record match", f'{case["identity"]["confidence"]:.0%}')
    row_a, row_b = st.columns(2, gap="medium")
    with row_a:
        detail_card("Acquisition", {"District": case["acquisition"]["district"], "Block": case["acquisition"]["block"], "Project type": case["acquisition"]["project_type"], "Current step": case["acquisition"]["stage"], "Days in step": case["acquisition"]["days_in_stage"]})
    with row_b:
        detail_card("Land and court", {"Land size": f'{case["land"]["area_hectares"]} hectares', "Land type": case["land"]["classification"], "Owner type": case["land"]["owner_type"], "Court status": case["legal"]["stay_status"]})
    st.markdown('<div class="section-head"><div><div class="eyebrow">Decision support</div><h2>Why this case is flagged</h2></div></div>', unsafe_allow_html=True)
    why_col, next_col = st.columns([1.15, 1], gap="large")
    with why_col:
        drivers = pd.DataFrame(prediction["drivers"]).rename(columns={"feature": "Reason", "impact": "Effect", "direction": "Trend"})
        st.dataframe(drivers, use_container_width=True, hide_index=True, column_config={"Effect": st.column_config.ProgressColumn("Effect", min_value=0, max_value=0.25, format="+%.0%%")})
    with next_col:
        st.markdown(f'<div class="insight"><strong>Suggested next step</strong><br>{prediction["recommendation"]}</div>', unsafe_allow_html=True)
        detail_card("Payments and rehabilitation", {"Compensation paid": f'{case["compensation"]["ratio"]:.0%}', "Families affected": case["acquisition"]["affected_families"], "Families resettled": case["rehabilitation"]["families_resettled"], "Open grievances": case["rehabilitation"]["grievances"]})

elif page == "Data explorer":
    st.markdown('<div class="eyebrow">See the data behind the decision</div><h1>Data explorer</h1><p class="section-note">Compare each department\'s records with the joined case view used by BhooMiPredict.</p>', unsafe_allow_html=True)
    catalog = get("/datasets")
    summary = pd.DataFrame(catalog).rename(columns={"key": "Dataset", "table": "Source table", "records": "Records"})
    st.dataframe(summary, use_container_width=True, hide_index=True)
    selected_dataset = st.selectbox("Choose a dataset", [item["key"] for item in catalog], index=len(catalog) - 1)
    selected = get(f"/datasets/{selected_dataset}")
    st.markdown(f'<div class="insight"><strong>{selected["name"].title()}</strong> · {selected["records"]} records · {len(selected["columns"])} fields</div>', unsafe_allow_html=True)
    dataset_frame = pd.DataFrame(selected["rows"])
    st.dataframe(dataset_frame, use_container_width=True, hide_index=True, height=480)
    st.download_button("Download this dataset as CSV", dataset_frame.to_csv(index=False), file_name=f"bhoomipredict_{selected_dataset.replace(' ', '_')}.csv", mime="text/csv")

else:
    st.markdown('<div class="eyebrow">Keep the records clean</div><h1>Issues & alerts</h1><p class="section-note">Review records that need a human check and new cases that crossed the attention line.</p>', unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("### Records to review")
        st.dataframe(pd.DataFrame(get("/data-quality")), use_container_width=True, hide_index=True, height=360)
    with right:
        st.markdown("### New alerts")
        st.dataframe(pd.DataFrame(get("/alerts")), use_container_width=True, hide_index=True, height=360)
