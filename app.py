"""Automated Personal Finance Decision Support System: Streamlit UI.
All calculations live in the other modules; this file only collects input and displays results."""
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import data_manager as dm
from ai_recommendations import generate_recommendations
from budget_analysis import (DEFAULT_BUDGET_PCT, budget_adherence, check_budget,
                             overspending_alerts, plan_budget, rank_categories)
from expense_prediction import predict_next
from finance_calculations import (CURRENCY, InputError, calculate_summary, goal_progress,
                                  months_to_goal, validate_amount)
from financial_health import health_score
from reports import build_report

st.set_page_config(page_title="Finance Decision Support", page_icon="₹", layout="wide")
st.markdown(f"<style>{(Path(__file__).parent / 'assets' / 'style.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)
if "conn" not in st.session_state:          # private, in-memory database per visitor
    st.session_state.conn = dm.connect()
conn = st.session_state.conn
CATS = list(DEFAULT_BUDGET_PCT)
TAG_RULE = '<span class="tag tag-rule">Rule-based logic</span>'
TAG_STAT = '<span class="tag tag-stat">Statistical model</span>'
COLORS = ["#0B7A75", "#10243E", "#D08A1E", "#B3392F", "#5B8DB8", "#7A9E7E", "#8C6BB1", "#9AA5B1"]


def analyse(rec):
    """Run the full pipeline for one stored record."""
    s = calculate_summary(rec["income"], rec["expenses"])
    rows = check_budget(s["expenses"], plan_budget(s["income"]))
    score, label, parts = health_score(s["savings_pct"], budget_adherence(rows), expense_pct=s["expense_pct"])
    return s, rows, score, label, parts


def pick_record(key):
    records = dm.load_records(conn)
    if not records:
        st.info("No records yet. Open **Add monthly record** or load the demo data from **Home**.")
        return None
    month = st.selectbox("Month", [r["month"] for r in records], index=len(records) - 1, key=key)
    return next(r for r in records if r["month"] == month)


PAGES = ["Home", "Add monthly record", "Spending analysis", "Budget planner", "Health and advice",
         "Expense forecast", "Savings goals", "Dashboard", "Reports"]
page = st.sidebar.radio("Navigate", PAGES)
st.sidebar.caption("Records stay in your browser session only. Download a CSV to keep them.")

# ---------------------------------------------------------------- Home
if page == "Home":
    st.markdown('<div class="hero"><h1>Know where your money goes, then decide what to change.</h1>'
                '<p>Enter your monthly income and expenses. The system calculates your savings, checks '
                'budgets, scores your financial health and suggests next steps.</p></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("Load demo data (3 sample months)"):
        dm.load_demo(conn)
        st.success("Demo data loaded. It is sample data, not real records.")
    c2.markdown("**How each feature works**")
    c2.markdown(f"{TAG_RULE} budgets, alerts, health score, recommendations<br>"
                f"{TAG_STAT} expense forecast (least-squares trend)<br>"
                "No feature here uses machine learning or a paid AI service.", unsafe_allow_html=True)
    st.markdown('<p class="note">Never enter bank passwords or card numbers; none are needed. '
                'Recommendations are automated guidance, not professional financial advice.</p>',
                unsafe_allow_html=True)

# ---------------------------------------------------------------- Add record
elif page == "Add monthly record":
    st.header("Add monthly record")
    month = st.text_input("Month (YYYY-MM)", value="2026-11")
    income = st.number_input(f"Monthly income ({CURRENCY})", min_value=0.0, step=500.0)
    cols = st.columns(4)
    exp = {c: cols[i % 4].number_input(f"{c} ({CURRENCY})", min_value=0.0, step=100.0, key=f"e_{c}")
           for i, c in enumerate(CATS)}
    if st.button("Calculate and save"):
        try:
            if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month.strip()):
                raise InputError("Month must look like 2026-11.")
            s = calculate_summary(income, exp)
            dm.save_record(conn, month.strip(), s["income"], s["expenses"])
            a, b, c = st.columns(3)
            a.metric("Total expenses", f"{CURRENCY}{s['total_expenses']:,.0f}")
            b.metric("Remaining balance", f"{CURRENCY}{s['balance']:,.0f}")
            c.metric("Savings rate", f"{s['savings_pct']:.1f}%")
            st.success(f"Saved {month.strip()}.")
        except InputError as err:
            st.error(str(err))
    records = dm.load_records(conn)
    if records:
        st.subheader("Saved records")
        st.dataframe(pd.DataFrame([{"month": r["month"], "income": r["income"], **r["expenses"]}
                                   for r in records]), use_container_width=True)
        d1, d2, d3 = st.columns(3)
        d1.download_button("Download CSV", dm.records_to_csv(records), "records.csv", "text/csv")
        target = d2.selectbox("Delete month", [r["month"] for r in records])
        if d2.button("Delete record"):
            dm.delete_record(conn, target)
            st.rerun()
    up = st.file_uploader("Import a CSV exported from this app", type="csv")
    if up and st.button("Import CSV"):
        try:
            st.success(f"Imported {dm.import_csv(conn, up)} record(s).")
        except Exception as err:  # malformed files can fail in many ways
            st.error(f"Could not import: {err}")

# ---------------------------------------------------------------- Analysis
elif page == "Spending analysis":
    st.header("Smart spending analysis")
    rec = pick_record("an_m")
    if rec:
        s = calculate_summary(rec["income"], rec["expenses"])
        ranked = rank_categories(s["expenses"])
        if ranked:
            df = pd.DataFrame(ranked, columns=["Category", "Spent"])
            df["Share of expenses %"] = (df["Spent"] / s["total_expenses"] * 100).round(1)
            st.markdown(f"Highest spending: **{ranked[0][0]}** ({CURRENCY}{ranked[0][1]:,.0f})")
            st.dataframe(df, use_container_width=True)
            st.plotly_chart(px.pie(df, names="Category", values="Spent", hole=.5,
                                   color_discrete_sequence=COLORS), use_container_width=True)
        else:
            st.info("This month has no expenses recorded.")

# ---------------------------------------------------------------- Budget
elif page == "Budget planner":
    st.header("Monthly budget planner and alerts")
    rec = pick_record("bp_m")
    if rec:
        st.caption("Set each category's limit as a percentage of income (defaults leave 20% for savings).")
        cols = st.columns(4)
        pct = {c: cols[i % 4].number_input(f"{c} %", 0.0, 100.0, float(DEFAULT_BUDGET_PCT[c]), 1.0, key=f"p_{c}")
               for i, c in enumerate(CATS)}
        if sum(pct.values()) > 100:
            st.error("Limits add up to more than 100% of income.")
        else:
            rows = check_budget(rec["expenses"], plan_budget(rec["income"], pct))
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
            alerts = overspending_alerts(rows)
            for a in alerts:
                (st.error if "over by" in a else st.warning)(a)
            if not alerts:
                st.success("Every category is within budget.")
            st.markdown(TAG_RULE, unsafe_allow_html=True)

# ---------------------------------------------------------------- Health
elif page == "Health and advice":
    st.header("Financial health and recommendations")
    rec = pick_record("ha_m")
    if rec:
        s, rows, score, label, parts = analyse(rec)
        st.metric("Financial health score", f"{score} / 100", label)
        st.progress(min(int(score), 100))
        st.dataframe(pd.DataFrame(parts.items(), columns=["Component", "Points"]), use_container_width=True)
        st.subheader("Recommendations")
        st.markdown(TAG_RULE + ' <span class="note">Each item is a Python decision rule applied to your numbers.</span>',
                    unsafe_allow_html=True)
        for r in generate_recommendations(s, rows):
            st.markdown(f"**{r['priority']} priority: {r['title']}**  \n{r['reason']}")
        st.caption("Automated guidance only; not professional financial advice.")

# ---------------------------------------------------------------- Forecast
elif page == "Expense forecast":
    st.header("Expense forecast")
    records = dm.load_records(conn)
    if not records:
        st.info("Add at least one monthly record to forecast.")
    else:
        totals = [calculate_summary(r["income"], r["expenses"])["total_expenses"] for r in records]
        value, method = predict_next(totals)
        st.metric("Predicted next-month expenses", f"{CURRENCY}{value:,.0f}")
        st.markdown(f"{TAG_STAT} Method: {method}", unsafe_allow_html=True)
        hist = pd.DataFrame({"Month": [r["month"] for r in records] + ["Next (forecast)"],
                             "Expenses": totals + [value]})
        st.plotly_chart(px.line(hist, x="Month", y="Expenses", markers=True,
                                color_discrete_sequence=COLORS), use_container_width=True)
        st.subheader("By category")
        table = [{"Category": c, "Forecast": predict_next([r["expenses"].get(c, 0) for r in records])[0]}
                 for c in CATS]
        st.dataframe(pd.DataFrame(table), use_container_width=True)
        if len(records) < 3:
            st.caption("With fewer than 3 months the forecast is a plain average. Add more months for a trend.")

# ---------------------------------------------------------------- Goals
elif page == "Savings goals":
    st.header("Savings goal tracker")
    with st.form("goal"):
        g1, g2 = st.columns(2)
        name = g1.text_input("Goal name")
        target = g2.number_input(f"Target ({CURRENCY})", min_value=0.0, step=1000.0)
        saved = g1.number_input(f"Saved so far ({CURRENCY})", min_value=0.0, step=500.0)
        monthly = g2.number_input(f"Monthly saving ({CURRENCY})", min_value=0.0, step=500.0)
        if st.form_submit_button("Save goal"):
            try:
                if not name.strip():
                    raise InputError("Goal name is required.")
                dm.save_goal(conn, name.strip(), validate_amount(target, "Target", allow_zero=False),
                             validate_amount(saved, "Saved amount"), validate_amount(monthly, "Monthly saving"))
            except InputError as err:
                st.error(str(err))
    rate = st.number_input("Expected yearly return % (0 = none)", 0.0, 30.0, 0.0, 0.5)
    for g in dm.load_goals(conn):
        m = months_to_goal(g["target"], g["saved"], g["monthly"], rate)
        st.markdown(f"**{g['name']}**: {goal_progress(g['target'], g['saved']):.0f}% of {CURRENCY}{g['target']:,.0f}")
        st.progress(int(goal_progress(g["target"], g["saved"])))
        st.caption("Goal reached." if m == 0 else f"About {m} months to go." if m
                   else "Increase the monthly saving to ever reach this goal.")
        if st.button("Delete", key=f"d_{g['name']}"):
            dm.delete_goal(conn, g["name"])
            st.rerun()

# ---------------------------------------------------------------- Dashboard
elif page == "Dashboard":
    st.header("Dashboard")
    records = dm.load_records(conn)
    if not records:
        st.info("Add a record or load demo data to see the dashboard.")
    else:
        s, rows, score, label, _ = analyse(records[-1])
        a, b, c, d = st.columns(4)
        a.metric("Income", f"{CURRENCY}{s['income']:,.0f}")
        b.metric("Expenses", f"{CURRENCY}{s['total_expenses']:,.0f}")
        c.metric("Savings rate", f"{s['savings_pct']:.1f}%")
        d.metric("Health score", f"{score}", label)
        trend = pd.DataFrame([{"Month": r["month"], "Income": r["income"],
                               "Expenses": sum(r["expenses"].values())} for r in records])
        st.plotly_chart(px.bar(trend, x="Month", y=["Income", "Expenses"], barmode="group",
                               color_discrete_sequence=COLORS), use_container_width=True)
        st.plotly_chart(px.bar(pd.DataFrame(rows), x="category", y=["spent", "limit"], barmode="group",
                               title=f"Spent vs budget limit ({records[-1]['month']})",
                               color_discrete_sequence=COLORS[2:]), use_container_width=True)

# ---------------------------------------------------------------- Reports
elif page == "Reports":
    st.header("Automated report")
    rec = pick_record("rp_m")
    if rec:
        s, rows, score, label, _ = analyse(rec)
        history = [calculate_summary(r["income"], r["expenses"])["total_expenses"] for r in dm.load_records(conn)]
        text = build_report(rec["month"], s, rows, score, label, generate_recommendations(s, rows),
                            predict_next(history))
        st.markdown(text)
        st.download_button("Download report (.md)", text, f"report_{rec['month']}.md", "text/markdown")