import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import date, timedelta

# === SITE DATA ===
site_data = {
    "McKenzie": {
        2025: {
            "monthly_revenue": [272803.51, 355176.29, 523682.78, 652686.87, 754675.75, 1531734.07,
                                1590784.93, 1453134.10, 1082549.32, 549349.73, 338379.46, 247321.94],
            "monthly_production_mwh": [2037.21722, 3376.4360016, 3914.709997986, 6572.517997944,
                                       9148.466001012, 8810.423007636, 8957.332998318, 8403.698998662,
                                       7197.752998434, 5559.753996096, 3375.548002026, 2137.745999724]
        },
        2026: {
            "monthly_revenue": [280000.00, 360000.00, 530000.00, 660000.00, 760000.00, 1540000.00,
                                1600000.00, 1460000.00, 1090000.00, 550000.00, 340000.00, 250000.00],
            "monthly_production_mwh": [2100.0, 3400.0, 4000.0, 6600.0, 9200.0, 8900.0,
                                       9000.0, 8500.0, 7300.0, 5600.0, 3400.0, 2200.0]
        }
    },
    "AnotherSite": {
        2025: {
            "monthly_revenue": [200000, 300000, 450000, 600000, 700000, 1400000,
                                1500000, 1400000, 1000000, 500000, 300000, 200000],
            "monthly_production_mwh": [1800, 3000, 3500, 6000, 8800, 8500,
                                       8700, 8100, 7000, 5400, 3200, 2000]
        }
    }
}

# === PARAMETERS ===
string_kw = 5.6
plant_kw = 37970
team_members = 2
workday_minutes = 480
travel_time_per_day = 240
safety_procedure_time = 15
fixed_per_day = travel_time_per_day + safety_procedure_time
labor_rate = 130.44
travel_cost_per_day = 75
locate_time_per_string = 30
repair_time_per_string = 45
diag_time_per_cb = 30
string_counts = np.arange(1, 101)
cb_estimate = [max(1, int(np.ceil(s / 5))) for s in string_counts]
month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# === FUNCTIONS ===
def calculate_repair_cost(strings, combiner_boxes):
    diag = combiner_boxes * diag_time_per_cb
    per_string = strings * (locate_time_per_string + repair_time_per_string)
    var_total = diag + per_string
    var_per_day = workday_minutes - fixed_per_day
    days = np.ceil(var_total / (var_per_day * team_members))
    total_time_minutes = var_total / team_members + (fixed_per_day * days)
    total_time_hours = total_time_minutes / 60
    labor_cost = total_time_hours * labor_rate * team_members
    travel_cost = days * travel_cost_per_day * team_members
    return labor_cost + travel_cost

@st.cache_data
def compute_repair_costs():
    return [calculate_repair_cost(s, cb_estimate[i]) for i, s in enumerate(string_counts)]

# === STREAMLIT LAYOUT ===
st.set_page_config(page_title="PV Repair Payback", layout="wide")
st.title("📊 PV Repair Payback Calculator")

# === Sidebar Site & Year ===
site = st.sidebar.selectbox("Site", list(site_data.keys()), key="site")
year = st.sidebar.selectbox("Year", list(site_data[site].keys()), key="year")

# === Dynamic revenue per day ===
monthly_revenue = site_data[site][year]["monthly_revenue"]
monthly_production = site_data[site][year]["monthly_production_mwh"]
revenue_per_day = [rev / days for rev, days in zip(monthly_revenue, month_lengths)]
repair_costs = compute_repair_costs()

# === Graph 1: Repair Cost Curve ===
st.header("Repair Cost Curve")
fig_cost = go.Figure(go.Scatter(
    x=string_counts,
    y=repair_costs,
    mode='lines+markers',
    text=[f"{s} strings → ${c:,.2f}" for s, c in zip(string_counts, repair_costs)]
))
fig_cost.update_layout(title="Repair Cost vs. Strings", xaxis_title="Strings", yaxis_title="Repair Cost (USD)")
st.plotly_chart(fig_cost, use_container_width=True)

# === Graph 2: Payback vs Strings Down ===
st.header("Payback vs Strings Down")
col1, col2, col3 = st.columns(3)
month = col1.slider("Start Month", 1, 12, 5, key="pvs_month")
day = col2.slider("Start Day", 1, 31, 15, key="pvs_day")
dispatch_delay = col3.slider("Dispatch Delay (days)", 0, 30, 0, key="pvs_delay")

start_date = date(year, month, day) + timedelta(days=dispatch_delay)
paybacks_days = []

for strings_down in string_counts:
    rev_stream = []
    shifted_date = start_date
    month_idx = (shifted_date.year - 2025) * 12 + shifted_date.month - 1

    for m in range(month_idx, 24):
        actual_month = m % 12
        days_in_month = month_lengths[actual_month]
        start_day = shifted_date.day if m == month_idx else 1
        for d in range(start_day, days_in_month + 1):
            daily_rev = revenue_per_day[actual_month] * (string_kw / plant_kw) * strings_down
            rev_stream.append(daily_rev)

    cumulative_revenue = np.cumsum(rev_stream)
    repair_cost = repair_costs[strings_down - 1]
    payback_idx = next((i for i, val in enumerate(cumulative_revenue) if val >= repair_cost), None)
    paybacks_days.append(payback_idx+1 if payback_idx is not None else float('inf'))

paybacks_months = [d / 30.44 for d in paybacks_days]
fig_payback = go.Figure(go.Scatter(x=string_counts, y=paybacks_months, mode='lines+markers'))
fig_payback.update_layout(title=f"Payback vs Strings Down (Start {start_date.strftime('%d-%b-%Y')})", xaxis_title="Strings", yaxis_title="Payback (months)")
st.plotly_chart(fig_payback, use_container_width=True)

# === Graph 3: Target Payback → Optimal Repair Date with Visual ===
st.header("📅 Target Payback → Optimal Repair Date (Graph + Result)")
col4, col5, col6, col7, col8 = st.columns(5)
month_tp = col4.slider("Start Month", 1, 12, 5, key="tp_month")
day_tp = col5.slider("Start Day", 1, 31, 15, key="tp_day")
strings_tp = col6.slider("Strings Down", 1, 100, 20, key="tp_strings")
target_payback = col7.slider("Target Payback (months)", 0.5, 12.0, 2.0, 0.1, key="tp_target")
dispatch_delay_tp = col8.slider("Dispatch Delay (days)", 0, 30, 0, key="tp_delay")

start_date_tp = date(year, month_tp, day_tp)
repair_cost = repair_costs[strings_tp - 1]
optimal_date = None

rev_stream = []
for delay_days in range(dispatch_delay_tp, 365):
    rev_stream_tmp = []
    shifted_date = start_date_tp + timedelta(days=delay_days)
    month_idx = (shifted_date.year - 2025) * 12 + shifted_date.month - 1

    for m in range(month_idx, 24):
        actual_month = m % 12
        days_in_month = month_lengths[actual_month]
        start_day = shifted_date.day if m == month_idx else 1
        for d in range(start_day, days_in_month + 1):
            daily_rev = revenue_per_day[actual_month] * (string_kw / plant_kw) * strings_tp
            rev_stream_tmp.append(daily_rev)

    cumulative_revenue = np.cumsum(rev_stream_tmp)
    payback_idx = next((i for i, val in enumerate(cumulative_revenue) if val >= repair_cost), None)
    if payback_idx is not None:
        total_days = delay_days + payback_idx + 1
        payback_months = total_days / 30.44
        if payback_months <= target_payback:
            optimal_date = shifted_date
            rev_stream = rev_stream_tmp
            payback_months_result = payback_months
            payback_day_result = payback_idx + 1
            break

if optimal_date:
    st.success(f"✅ Optimal Repair Date: {optimal_date.strftime('%Y-%m-%d')}")
    st.info(f"⏳ Payback in {total_days} days ({payback_months_result:.2f} months)")
    st.info(f"🔢 Strings Down: {strings_tp}")
    st.info(f"💰 Repair Cost: ${repair_cost:,.0f}")
else:
    st.error(f"❌ No repair meets target payback ≤ {target_payback:.2f} months within 1 year horizon.")

# === Visual Plot for Graph 3 ===
if rev_stream:
    cumulative_revenue = np.cumsum(rev_stream)
    days_after_repair = np.arange(1, len(cumulative_revenue) + 1)
    months_after_repair = days_after_repair / 30.44

    fig_tp = go.Figure()
    fig_tp.add_trace(go.Scatter(
        x=months_after_repair,
        y=cumulative_revenue,
        mode='lines',
        name='Cumulative Revenue',
        line=dict(color='green')
    ))

    # Horizontal line → Repair Cost
    fig_tp.add_hline(y=repair_cost, line_dash='dash', line_color='red',
                     annotation_text=f'Repair Cost (${repair_cost:,.0f})', annotation_position='top left')

    # Vertical line → Payback Crossover
    if optimal_date:
        payback_months_line = payback_day_result / 30.44
        fig_tp.add_vline(x=payback_months_line, line_dash='dot', line_color='blue',
                         annotation_text=f'Payback: {payback_months_line:.2f} mo', annotation_position='bottom right')

    fig_tp.update_layout(
        title="Cumulative Revenue vs Target Payback",
        xaxis_title="Months After Repair",
        yaxis_title="Cumulative Revenue (USD)",
        template='plotly_white',
        width=1200,
        height=500
    )

    st.plotly_chart(fig_tp, use_container_width=True)




