# ======================= app.py =========================
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
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

# === CONSTANTS ===
string_kw = 5.6
plant_kw = 37970

team_members = 2
travel_time_per_day = 240
safety_procedure_time = 15
fixed_per_day = travel_time_per_day + safety_procedure_time

labor_rate = 130.44
travel_cost_per_day = 75

workday_minutes = 480
locate_time_per_string = 30
repair_time_per_string = 45
diag_time_per_cb = 30

month_lengths = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

# === FUNCTIONS ===
@st.cache_data
def calculate_repair_cost(strings):
    cb_estimate = max(1, int(np.ceil(strings / 5)))
    diag = cb_estimate * diag_time_per_cb
    per_string = strings * (locate_time_per_string + repair_time_per_string)
    var_total = diag + per_string
    var_per_day = workday_minutes - fixed_per_day
    days = np.ceil(var_total / (var_per_day * team_members))
    total_time_minutes = var_total / team_members + (fixed_per_day * days)
    total_time_hours = total_time_minutes / 60
    labor_cost = total_time_hours * labor_rate * team_members
    travel_cost = days * travel_cost_per_day * team_members
    total_cost = labor_cost + travel_cost
    return total_cost

def get_revenue_data(site, year):
    data = site_data[site][year]
    monthly_revenue = data['monthly_revenue']
    monthly_production = data['monthly_production_mwh']
    revenue_per_day = [rev / days for rev, days in zip(monthly_revenue, [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])]
    return revenue_per_day

# === STREAMLIT UI ===
st.title("DC Health Payback Tool")

col1, col2 = st.columns(2)
site = col1.selectbox("Site", list(site_data.keys()), key='site')
year = col2.selectbox("Year", [2025, 2026], key='year')

revenue_per_day = get_revenue_data(site, year)

# === REPAIR COST CURVE ===
string_counts = np.arange(1, 101)
repair_costs = [calculate_repair_cost(s) for s in string_counts]

fig_cost = go.Figure(data=go.Scatter(
    x=string_counts,
    y=repair_costs,
    mode='lines+markers',
    hoverinfo='x+y',
    name='Repair Cost'
))
fig_cost.update_layout(title="Repair Cost vs Strings", xaxis_title="Strings", yaxis_title="USD")
st.plotly_chart(fig_cost, use_container_width=True)

# === PAYBACK vs STRINGS ===
st.header("Payback vs Strings Down")
col3, col4, col5 = st.columns(3)
month = col3.slider("Month", 1, 12, 5, key='month1')
day = col4.slider("Day", 1, month_lengths[month], 15, key='day1')
dispatch_delay = col5.slider("Dispatch Delay (days)", 0, 30, 0, key='delay1')

start_date = date(year, month, day) + timedelta(days=dispatch_delay)

paybacks_months = []
hover_texts = []

for strings_down in string_counts:
    rev_stream = []
    current_date = start_date
    while len(rev_stream) < 730:
        actual_month = current_date.month
        rev = revenue_per_day[actual_month - 1] * (string_kw / plant_kw) * strings_down
        rev_stream.append(rev)
        current_date += timedelta(days=1)
    cumulative_revenue = np.cumsum(rev_stream)
    repair_cost = repair_costs[strings_down - 1]
    payback_idx = next((i for i, v in enumerate(cumulative_revenue) if v >= repair_cost), None)
    payback_days = payback_idx + 1 if payback_idx is not None else float('inf')
    paybacks_months.append(payback_days / 30.44)
    hover_texts.append(f"{strings_down} strings → {payback_days} days → ${repair_cost:,.0f}")

fig_payback = go.Figure(data=go.Scatter(
    x=string_counts,
    y=paybacks_months,
    mode='lines+markers',
    text=hover_texts,
    hoverinfo='text'
))
fig_payback.update_layout(title=f"Payback vs Strings from {start_date}", xaxis_title="Strings", yaxis_title="Payback (months)")
st.plotly_chart(fig_payback, use_container_width=True)

# === PAYBACK CROSSOVER ===
st.header("Payback Crossover")
col6, col7, col8 = st.columns(3)
month2 = col6.slider("Month", 1, 12, 5, key='month2')
day2 = col7.slider("Day", 1, month_lengths[month2], 15, key='day2')
strings_down = col8.slider("Strings Down", 1, 100, 20, key='strings2')
dispatch_delay2 = st.slider("Dispatch Delay (days)", 0, 30, 0, key='delay2')

start_date2 = date(year, month2, day2) + timedelta(days=dispatch_delay2)

rev_stream = []
current_date = start_date2
while len(rev_stream) < 730:
    actual_month = current_date.month
    rev = revenue_per_day[actual_month - 1] * (string_kw / plant_kw) * strings_down
    rev_stream.append(rev)
    current_date += timedelta(days=1)

cumulative_revenue = np.cumsum(rev_stream)
repair_cost = repair_costs[strings_down - 1]
payback_idx = next((i for i, v in enumerate(cumulative_revenue) if v >= repair_cost), None)

fig_crossover = go.Figure()
fig_crossover.add_trace(go.Scatter(x=np.arange(len(cumulative_revenue)) / 30.44, y=cumulative_revenue, mode='lines', name='Cumulative Revenue'))
fig_crossover.add_hline(y=repair_cost, line_dash='dash', annotation_text=f"Repair Cost ${repair_cost:,.0f}")
if payback_idx is not None:
    payback_months = payback_idx / 30.44
    fig_crossover.add_vline(x=payback_months, line_dash='dot', annotation_text=f"Payback: {payback_months:.2f} mo")

fig_crossover.update_layout(title=f"Crossover Payback from {start_date2}", xaxis_title="Months", yaxis_title="Cumulative Revenue (USD)")
st.plotly_chart(fig_crossover, use_container_width=True)

# === TARGET PAYBACK → OPTIMAL REPAIR DATE ===
st.header("Target Payback → Optimal Repair Date")
col9, col10, col11, col12 = st.columns(4)
month3 = col9.slider("Month", 1, 12, 5, key='month3')
day3 = col10.slider("Day", 1, month_lengths[month3], 15, key='day3')
strings_down3 = col11.slider("Strings Down", 1, 100, 20, key='strings3')
target_payback_months = col12.slider("Target Payback (months)", 0.5, 12.0, 2.0, 0.1, key='target3')
dispatch_delay3 = st.slider("Dispatch Delay (days)", 0, 30, 0, key='delay3')

start_date3 = date(year, month3, day3)

found = False
for delay in range(dispatch_delay3, 365):
    current_date = start_date3 + timedelta(days=delay)
    rev_stream = []
    temp_date = current_date
    while len(rev_stream) < 730:
        actual_month = temp_date.month
        rev = revenue_per_day[actual_month - 1] * (string_kw / plant_kw) * strings_down3
        rev_stream.append(rev)
        temp_date += timedelta(days=1)
    cumulative_revenue = np.cumsum(rev_stream)
    repair_cost = repair_costs[strings_down3 - 1]
    payback_idx = next((i for i, v in enumerate(cumulative_revenue) if v >= repair_cost), None)
    if payback_idx is not None:
        total_days = delay + payback_idx + 1
        if total_days / 30.44 <= target_payback_months:
            st.success(f"✅ Repair on {current_date.strftime('%Y-%m-%d')} with payback in {total_days} days ({total_days/30.44:.2f} months)")
            found = True
            break

if not found:
    st.error("❌ No repair meets target payback within 1 year horizon.")
