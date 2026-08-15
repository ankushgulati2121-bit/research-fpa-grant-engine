import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Research Portfolio FP&A Engine",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Research Portfolio FP&A & Grant Performance Engine")
st.caption("Multi-Year Research Grant Accounting, FTE Labor Recovery & Dynamic Variance Scenario Engine")

# ---------------------------------------------------------
# Data Generation & Financial Engine Logic
# ---------------------------------------------------------
@st.cache_data
def load_base_data():
    np.random.seed(101)
    divisions = [
        "Applied Agricultural Science",
        "Ecosystem & Environmental Risk", 
        "Biotechnology & Health Solutions",
        "Sustainable Materials & Forestry"
    ]
    funding_mechanisms = [
        "Government Crown Core", 
        "Competitive Research Grant", 
        "Commercial Enterprise Contract", 
        "International Research Consortium"
    ]
    
    projects = []
    p_counter = 101
    for div in divisions:
        for i in range(1, 6):
            projects.append({
                "Project_ID": f"RND-{p_counter}",
                "Division": div,
                "Project_Name": f"{div} Programme {i}",
                "Funding_Mechanism": np.random.choice(funding_mechanisms, p=[0.40, 0.35, 0.15, 0.10]),
                "Total_Funding_NZD": np.random.uniform(1_500_000, 5_000_000),
                "Duration_Months": int(np.random.choice([24, 36, 48])),
                "Planned_FTE": round(np.random.uniform(2.0, 7.5), 1),
                "Hourly_Chargeout_Rate": round(np.random.uniform(140.0, 190.0), 2)
            })
            p_counter += 1
            
    df_projects = pd.DataFrame(projects)
    
    months = pd.date_range(start="2025-07-01", periods=12, freq="MS")
    gl_records = []
    
    for _, prj in df_projects.iterrows():
        base_monthly_rev = prj["Total_Funding_NZD"] / prj["Duration_Months"]
        base_fte_hours = prj["Planned_FTE"] * 140
        base_direct_cost = base_fte_hours * 72.50
        base_lab_opex = base_monthly_rev * np.random.uniform(0.14, 0.22)
        base_overhead = base_monthly_rev * 0.18
        base_deprec = np.random.uniform(5_000, 15_000)
        
        for m in months:
            gl_records.append({
                "Period": m,
                "Project_ID": prj["Project_ID"],
                "Division": prj["Division"],
                "Funding_Mechanism": prj["Funding_Mechanism"],
                "Base_Budget_Rev": base_monthly_rev,
                "Base_Budget_Hours": base_fte_hours,
                "Base_Budget_Direct_Cost": base_direct_cost,
                "Base_Budget_Lab_OpEx": base_lab_opex,
                "Base_Budget_Overhead": base_overhead,
                "Base_Budget_Deprec": base_deprec,
                "Rev_Factor": np.random.normal(0.98, 0.07),
                "FTE_Factor": np.random.normal(0.96, 0.05),
                "Lab_Factor": np.random.normal(1.04, 0.10),
                "Wage_Inflation": np.random.uniform(0.99, 1.04),
                "Deprec_Multiplier": np.random.choice([1.0, 1.05]),
                "Hourly_Chargeout_Rate": prj["Hourly_Chargeout_Rate"]
            })
            
    return df_projects, pd.DataFrame(gl_records)

df_projects, df_raw_gl = load_base_data()

# ---------------------------------------------------------
# Sidebar: Dynamic Business Partnering Scenario Controls
# ---------------------------------------------------------
st.sidebar.header("Scenario & Sensitivity Parameters")
st.sidebar.markdown("Adjust operational parameters to test financial resilience:")

rev_slider = st.sidebar.slider("Grant Milestone Realization Shift (%)", -15, 15, 0, 1)
chargeout_slider = st.sidebar.slider("FTE Chargeout Rate Adjustment ($/hr)", -25, 25, 0, 5)
lab_opex_slider = st.sidebar.slider("Lab Consumables Inflation Shift (%)", -10, 20, 0, 1)
overhead_pct = st.sidebar.slider("Institutional Overhead Rate (%)", 12, 25, 18, 1)

division_filter = st.sidebar.multiselect(
    "Filter by Science Division",
    options=df_projects["Division"].unique().tolist(),
    default=df_projects["Division"].unique().tolist()
)

# ---------------------------------------------------------
# Scenario Calculation Engine
# ---------------------------------------------------------
df_calc = df_raw_gl[df_raw_gl["Division"].isin(division_filter)].copy()

# Apply baseline budget values
df_calc["Budget_Revenue"] = df_calc["Base_Budget_Rev"]
df_calc["Budget_Direct_Labor_Cost"] = df_calc["Base_Budget_Direct_Cost"]
df_calc["Budget_Lab_OpEx"] = df_calc["Base_Budget_Lab_OpEx"]
df_calc["Budget_Overhead"] = df_calc["Base_Budget_Rev"] * (overhead_pct / 100.0)
df_calc["Budget_Depreciation"] = df_calc["Base_Budget_Deprec"]
df_calc["Budget_FTE_Hours"] = df_calc["Base_Budget_Hours"]

# Apply scenario-adjusted actuals
applied_chargeout = df_calc["Hourly_Chargeout_Rate"] + chargeout_slider
rev_adjustment = 1.0 + (rev_slider / 100.0)
lab_adjustment = 1.0 + (lab_opex_slider / 100.0)

df_calc["Actual_Revenue"] = df_calc["Base_Budget_Rev"] * df_calc["Rev_Factor"] * rev_adjustment
df_calc["Actual_FTE_Hours"] = df_calc["Base_Budget_Hours"] * df_calc["FTE_Factor"]
df_calc["Actual_Labor_Recovery"] = df_calc["Actual_FTE_Hours"] * applied_chargeout
df_calc["Actual_Direct_Labor_Cost"] = df_calc["Actual_FTE_Hours"] * 72.50 * df_calc["Wage_Inflation"]
df_calc["Actual_Lab_OpEx"] = df_calc["Base_Budget_Lab_OpEx"] * df_calc["Lab_Factor"] * lab_adjustment
df_calc["Actual_Overhead"] = df_calc["Budget_Overhead"]
df_calc["Actual_Depreciation"] = df_calc["Base_Budget_Deprec"] * df_calc["Deprec_Multiplier"]

# Cost totals & Margins
df_calc["Budget_Total_Cost"] = df_calc["Budget_Direct_Labor_Cost"] + df_calc["Budget_Lab_OpEx"] + df_calc["Budget_Overhead"] + df_calc["Budget_Depreciation"]
df_calc["Actual_Total_Cost"] = df_calc["Actual_Direct_Labor_Cost"] + df_calc["Actual_Lab_OpEx"] + df_calc["Actual_Overhead"] + df_calc["Actual_Depreciation"]
df_calc["Budget_Net_Margin"] = df_calc["Budget_Revenue"] - df_calc["Budget_Total_Cost"]
df_calc["Actual_Net_Margin"] = df_calc["Actual_Revenue"] - df_calc["Actual_Total_Cost"]

# Variances
tot_b_rev = df_calc["Budget_Revenue"].sum()
tot_a_rev = df_calc["Actual_Revenue"].sum()
tot_b_margin = df_calc["Budget_Net_Margin"].sum()
tot_a_margin = df_calc["Actual_Net_Margin"].sum()
tot_b_hours = df_calc["Budget_FTE_Hours"].sum()
tot_a_hours = df_calc["Actual_FTE_Hours"].sum()

# ---------------------------------------------------------
# Executive KPI Row
# ---------------------------------------------------------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    rev_delta = tot_a_rev - tot_b_rev
    st.metric("Total Revenue ($NZD)", f"${tot_a_rev/1e6:.2f}M", f"{rev_delta/1e3:+.1f}k vs Budget")

with kpi2:
    margin_delta = tot_a_margin - tot_b_margin
    st.metric("Net Margin Delivered", f"${tot_a_margin/1e3:.1f}k", f"{margin_delta/1e3:+.1f}k vs Plan")

with kpi3:
    util_rate = (tot_a_hours / tot_b_hours) * 100 if tot_b_hours > 0 else 0
    st.metric("FTE Capacity Utilization", f"{util_rate:.1f}%", f"{util_rate - 100:+.1f}% vs Target")

with kpi4:
    net_margin_pct = (tot_a_margin / tot_a_rev) * 100 if tot_a_rev > 0 else 0
    st.metric("Operating Margin Rate", f"{net_margin_pct:.1f}%", f"Target: {(tot_b_margin/tot_b_rev)*100:.1f}%")

st.divider()

# ---------------------------------------------------------
# Visual Analytics (Tabs)
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📈 Variance Waterfall & Ratios", "🏛️ Divisional Performance", "📑 Automated Executive Brief"])

with tab1:
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        # Waterfall Calculation
        v_rev = tot_a_rev - tot_b_rev
        v_labor = df_calc["Budget_Direct_Labor_Cost"].sum() - df_calc["Actual_Direct_Labor_Cost"].sum()
        v_lab = df_calc["Budget_Lab_OpEx"].sum() - df_calc["Actual_Lab_OpEx"].sum()
        v_dep = df_calc["Budget_Depreciation"].sum() - df_calc["Actual_Depreciation"].sum()
        
        categories = ["Budget Net Margin", "Revenue Realization", "Labor Cost Drift", "Lab OpEx Shifts", "Depreciation/CapEx", "Actual Net Margin"]
        values = [tot_b_margin, v_rev, v_labor, v_lab, v_dep, tot_a_margin]
        measures = ["absolute", "relative", "relative", "relative", "relative", "total"]
        
        fig_waterfall = go.Figure(go.Waterfall(
            name="Net Margin Bridge",
            orientation="v",
            measure=measures,
            x=categories,
            textposition="outside",
            text=[f"${v/1e3:.1f}k" for v in values],
            y=values,
            connector={"line": {"color": "#666"}},
            increasing={"marker": {"color": "#2ca02c"}},
            decreasing={"marker": {"color": "#d62728"}},
            totals={"marker": {"color": "#1f77b4"}}
        ))
        fig_waterfall.update_layout(title="Net Operating Margin Variance Bridge ($NZD)", height=420, template="plotly_white")
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
    with col_right:
        st.subheader("Cost Structure Distribution")
        cost_breakdown = pd.DataFrame({
            "Cost Category": ["Direct Labor", "Lab Consumables OpEx", "Indirect Overhead", "CapEx Depreciation"],
            "Actual Amount ($NZD)": [
                df_calc["Actual_Direct_Labor_Cost"].sum(),
                df_calc["Actual_Lab_OpEx"].sum(),
                df_calc["Actual_Overhead"].sum(),
                df_calc["Actual_Depreciation"].sum()
            ]
        })
        fig_pie = go.Figure(go.Pie(labels=cost_breakdown["Cost Category"], values=cost_breakdown["Actual Amount ($NZD)"], hole=0.45))
        fig_pie.update_layout(height=420, template="plotly_white")
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    div_summary = df_calc.groupby("Division").agg({
        "Budget_Revenue": "sum",
        "Actual_Revenue": "sum",
        "Budget_FTE_Hours": "sum",
        "Actual_FTE_Hours": "sum",
        "Actual_Net_Margin": "sum"
    }).reset_index()
    
    div_summary["Revenue_Realization_%"] = (div_summary["Actual_Revenue"] / div_summary["Budget_Revenue"]) * 100
    div_summary["FTE_Utilization_%"] = (div_summary["Actual_FTE_Hours"] / div_summary["Budget_FTE_Hours"]) * 100
    div_summary["Margin_%"] = (div_summary["Actual_Net_Margin"] / div_summary["Actual_Revenue"]) * 100
    
    fig_div = make_subplots(rows=1, cols=2, subplot_titles=("Revenue: Budget vs Actual by Division", "Scientific FTE Utilization (%)"))
    
    fig_div.add_trace(go.Bar(name="Budget Revenue", x=div_summary["Division"], y=div_summary["Budget_Revenue"], marker_color="#9ecae1"), row=1, col=1)
    fig_div.add_trace(go.Bar(name="Actual Revenue", x=div_summary["Division"], y=div_summary["Actual_Revenue"], marker_color="#2171b5"), row=1, col=1)
    
    fig_div.add_trace(go.Bar(
        name="FTE Utilization %", 
        x=div_summary["Division"], 
        y=div_summary["FTE_Utilization_%"],
        marker_color=np.where(div_summary["FTE_Utilization_%"] >= 95, "#31a354", "#e6550d"),
        text=[f"{v:.1f}%" for v in div_summary["FTE_Utilization_%"]],
        textposition="auto"
    ), row=1, col=2)
    
    fig_div.update_layout(height=420, barmode="group", template="plotly_white")
    st.plotly_chart(fig_div, use_container_width=True)
    
    st.dataframe(
        div_summary[["Division", "Budget_Revenue", "Actual_Revenue", "Revenue_Realization_%", "FTE_Utilization_%", "Margin_%"]].style.format({
            "Budget_Revenue": "${:,.0f}",
            "Actual_Revenue": "${:,.0f}",
            "Revenue_Realization_%": "{:.1f}%",
            "FTE_Utilization_%": "{:.1f}%",
            "Margin_%": "{:.1f}%"
        }),
        use_container_width=True
    )

with tab3:
    st.subheader("Automated Executive Advisory Brief")
    
    direction = "ahead of" if (tot_a_rev - tot_b_rev) >= 0 else "behind"
    
    brief_lines = [
        f"**FINANCE BUSINESS PARTNER EXECUTIVE BRIEFING** | *Bioeconomy Science Research Portfolio*",
        f"*Generated: {date.today().strftime('%d %B %Y')} | Reporting Currency: NZD ($)*\n",
        f"### 1. Portfolio Trajectory",
        f"- Total scientific revenue is currently tracking at **${tot_a_rev/1e6:.2f}M** vs. a budget of **${tot_b_rev/1e6:.2f}M** ({direction} plan by **${abs(tot_a_rev - tot_b_rev)/1e3:.1f}k**).",
        f"- Net Operating Margin delivered is **${tot_a_margin/1e3:.1f}k** compared to budget of **${tot_b_margin/1e3:.1f}k**.",
        f"\n### 2. Operational Capacity & Risk Interventions"
    ]
    
    for _, r in div_summary.iterrows():
        status = "🟢 ON TRACK" if (r["Revenue_Realization_%"] >= 95 and r["FTE_Utilization_%"] >= 93) else "🟠 ATTENTION REQUIRED"
        brief_lines.append(f"**{status} — {r['Division']}**")
        brief_lines.append(f"- Revenue Realization: **{r['Revenue_Realization_%']:.1f}%** | Scientific Capacity: **{r['FTE_Utilization_%']:.1f}%**")
        if r["FTE_Utilization_%"] < 95:
            unrec = (r["Budget_FTE_Hours"] - r["Actual_FTE_Hours"]) * (165.0 + chargeout_slider)
            brief_lines.append(f"- *Advisory Note:* Capacity slippage detected. Estimated **${unrec/1e3:.1f}k** in unrecovered research labor. Recommend shifting unassigned research staff to milestone-critical contestable grant contracts.")
        else:
            brief_lines.append(f"- *Advisory Note:* Strong operational labor absorption maintained without project delivery backlogs.")
        brief_lines.append("")
        
    brief_lines.extend([
        "### 3. Recommendations for Science Directors",
        "1. **Milestone Scheduling:** Align Q3 milestone deliverable sign-offs with monthly billing cycles to eliminate billing lag.",
        "2. **OpEx Procurement:** Consolidate high-cost laboratory consumable purchasing across legacy sites to capture scale discounts.",
        "3. **FTE Rate Alignment:** Periodically benchmark hourly charge-out recovery rates against direct wage drift to protect net operating margins."
    ])
    
    st.markdown("\n".join(brief_lines))
