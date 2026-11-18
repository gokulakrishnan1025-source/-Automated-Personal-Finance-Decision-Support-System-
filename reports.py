"""Automated report generation (Markdown text, downloadable)."""
from datetime import date


def build_report(month, summary, rows, score, label, recs, forecast=None):
    cur = summary["currency"]
    out = [f"# Personal Finance Report: {month}", f"Generated {date.today():%d %b %Y}", "",
           "## Summary",
           f"- Income: {cur}{summary['income']:,.2f}",
           f"- Total expenses: {cur}{summary['total_expenses']:,.2f}",
           f"- Remaining balance: {cur}{summary['balance']:,.2f}",
           f"- Savings rate: {summary['savings_pct']:.1f}%", "",
           f"## Financial health score: {score}/100 ({label})", "", "## Budget check",
           "| Category | Spent | Limit | Status |", "|---|---|---|---|"]
    out += [f"| {r['category']} | {r['spent']:,.0f} | {r['limit']:,.0f} | {r['status']} |" for r in rows]
    out += ["", "## Recommendations (rule-based, not machine learning)"]
    out += [f"- **{r['priority']}: {r['title']}**: {r['reason']}" for r in recs] or ["- None"]
    if forecast:
        out += ["", f"## Next-month expense forecast: {cur}{forecast[0]:,.0f} ({forecast[1]})"]
    out += ["", "_Automated guidance only; not professional financial advice._"]
    return "\n".join(out)