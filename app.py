import numpy as np
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

# === Constants ===
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
month_lengths = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
string_counts = np.arange(1, 101)
cb_estimate = [max(1, int(np.ceil(s / 5))) for s in string_counts]

# === Sidebar Inputs ===
st.sidebar.header("🌍 Site & Year")
site = st.sidebar.selectbox("Select Site", list(site_data.keys()))
year = st.sidebar.selectbox("Select Year", [2025, 2026])

# === Revenue Data ===
data = site_data[site][year]
monthly_revenue = data['monthly_revenue']
monthly_production = data['monthly_production_mwh']
revenue_per_day = [rev / days for rev, days in zip(monthly_revenue, [31,28,31,30,31,30,31,31,30,31,30,31])]

# === Repair Cost ===
def calculate_repair_cost(strings, cb):
    diag = cb * diag_time_per_cb
    per_string = strings * (locate_time_per_string + repair_time_per_string)
    var_total = diag + per_string
    var_per_day = workday_minutes - fixed_per_day
    days = np.ceil(var_total / (var_per_day * team_members))
    total_time = var_total / team_members + (fixed_per_day * days)
    total_hours = total_time / 60
    labor = total_hours * labor_rate * team_members
    travel = days * travel_cost_per_day * team_members
    return labor + travel, total_time

repair_results = [calculate_repair_cost(s, cb_estimate[i]) for i, s in enumerate(string_counts)]
repair_costs = [res[0] for res in repair_results]

# === Graph 1 ===
st.header("📈 Payback vs Strings Down")
month1 = st.slider("Start Month", 1, 12, 5, key="month1")
day1 = st.slider("Start Day", 1, 31, 15, key="day1")
dispatch1 = st.slider("Dispatch Delay (days)", 0, 30, 0, key="dispatch1")

start_date = date(year, month1, day1) + timedelta(days=dispatch1)
month_idx = (start_date.year - 2025) * 12 + start_date.month - 1

paybacks_days = []
for strings_down in string_counts:
    rev_stream = []
    for m in range(month_idx, 24):
        actual_month = m % 12
        days_in_month = month_lengths[actual_month + 1]
        start_day = start_date.day if m == month_idx else 1
        for d in range(start_day, days_in_month + 1):
            daily_rev = revenue_per_day[actual_month] * (string_kw / plant_kw) * strings_down
            rev_stream.append(daily_rev)
    cumulative_rev = np.cumsum(rev_stream)
    cost = repair_costs[strings_down - 1]
    idx = next((i for i, val in enumerate(cumulative_rev) if val >= cost), None)
    paybacks_days.append((idx+1) if idx is not None else float('inf'))

paybacks_months = [d / 30.44 for d in paybacks_days]
fig1 = go.Figure(data=go.Scatter(x=string_counts, y=paybacks_months, mode='lines+markers'))
fig1.update_layout(title="Payback vs Strings Down", xaxis_title="Strings", yaxis_title="Payback (months)")
st.plotly_chart(fig1, use_container_width=True)

# === Graph 2 ===
st.header("📊 Payback Crossover")
month2 = st.slider("Month", 1, 12, 5, key="month2")
day2 = st.slider("Day", 1, 31, 15, key="day2")
strings2 = st.slider("Strings Down", 1, 100, 20, key="strings2")
dispatch2 = st.slider("Dispatch Delay (days)", 0, 30, 0, key="dispatch2")

start_date2 = date(year, month2, day2) + timedelta(days=dispatch2)
month_idx2 = (start_date2.year - 2025) * 12 + start_date2.month - 1

rev_stream2 = []
for m in range(month_idx2, 24):
    actual_month = m % 12
    days_in_month = month_lengths[actual_month + 1]
    start_day = start_date2.day if m == month_idx2 else 1
    for d in range(start_day, days_in_month + 1):
        daily_rev = revenue_per_day[actual_month] * (string_kw / plant_kw) * strings2
        rev_stream2.append(daily_rev)

cumulative_revenue2 = np.cumsum(rev_stream2)
repair_cost2 = repair_costs[strings2 - 1]
payback_idx2 = next((i for i, val in enumerate(cumulative_revenue2) if val >= repair_cost2), None)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=np.arange(1, len(cumulative_revenue2)+1)/30.44, y=cumulative_revenue2, mode='lines'))
fig2.add_hline(y=repair_cost2, line_dash='dash', line_color='red', annotation_text=f'Repair Cost ${repair_cost2:,.0f}')
if payback_idx2 is not None:
    fig2.add_vline(x=(payback_idx2+1)/30.44, line_dash='dot', line_color='blue', annotation_text=f'Payback {(payback_idx2+1)/30.44:.2f} mo')
fig2.update_layout(title="Crossover Payback Curve", xaxis_title="Months", yaxis_title="Cumulative Revenue")
st.plotly_chart(fig2, use_container_width=True)

# === Graph 3 ===
st.header("📅 Target Payback → Optimal Repair Date")
month3 = st.slider("Month", 1, 12, 5, key="month3")
day3 = st.slider("Day", 1, 31, 15, key="day3")
strings3 = st.slider("Strings", 1, 100, 20, key="strings3")
target_payback = st.slider("Target Payback (months)", 0.5, 12.0, 2.0, 0.1, key="target3")
dispatch3 = st.slider("Dispatch Delay (days)", 0, 30, 0, key="dispatch3")

start_date3 = date(year, month3, day3)
repair_cost3 = repair_costs[strings3 - 1]
optimal_date = None
rev_stream3 = []

for delay in range(dispatch3, 365):
    shifted_date = start_date3 + timedelta(days=delay)
    month_idx3 = (shifted_date.year - 2025) * 12 + shifted_date.month - 1
    rev_tmp = []
    for m in range(month_idx3, 24):
        actual_month = m % 12
        days_in_month = month_lengths[actual_month + 1]
        start_day = shifted_date.day if m == month_idx3 else 1
        for d in range(start_day, days_in_month + 1):
            daily_rev = revenue_per_day[actual_month] * (string_kw / plant_kw) * strings3
            rev_tmp.append(daily_rev)
    cumulative_rev = np.cumsum(rev_tmp)
    payback_idx = next((i for i, val in enumerate(cumulative_rev) if val >= repair_cost3), None)
    if payback_idx is not None:
        total_days = delay + payback_idx + 1
        payback_months = total_days / 30.44
        if payback_months <= target_payback:
            optimal_date = shifted_date
            rev_stream3 = rev_tmp
            break

if optimal_date:
    st.success(f"✅ Repair on: {optimal_date.strftime('%Y-%m-%d')} | Payback: {total_days} days ({payback_months:.2f} mo)")
    cumulative_revenue3 = np.cumsum(rev_stream3)
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=np.arange(1, len(cumulative_revenue3)+1)/30.44, y=cumulative_revenue3, mode='lines'))
    fig3.add_hline(y=repair_cost3, line_dash='dash', line_color='red', annotation_text=f'Repair Cost ${repair_cost3:,.0f}')
    fig3.add_vline(x=(payback_idx+1)/30.44, line_dash='dot', line_color='blue', annotation_text=f'Payback {(payback_idx+1)/30.44:.2f} mo')
    fig3.update_layout(title="Target Payback Crossover", xaxis_title="Months", yaxis_title="Cumulative Revenue")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.error(f"❌ No repair meets target payback ≤ {target_payback:.2f} months")
