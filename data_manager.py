"""SQLite storage. The app uses an in-memory database per browser session, so
records are private to the visitor and vanish when the session ends; use CSV
export/import to keep them."""
import json
import sqlite3
import pandas as pd


def connect(path=":memory:"):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS records(month TEXT PRIMARY KEY, income REAL, expenses TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS goals(name TEXT PRIMARY KEY, target REAL, saved REAL, monthly REAL)")
    return conn


def save_record(conn, month, income, expenses):
    conn.execute("REPLACE INTO records VALUES(?,?,?)", (month, income, json.dumps(expenses)))
    conn.commit()


def load_records(conn):
    """Return list of {month, income, expenses} sorted by month."""
    rows = conn.execute("SELECT month, income, expenses FROM records ORDER BY month").fetchall()
    return [{"month": m, "income": i, "expenses": json.loads(e)} for m, i, e in rows]


def delete_record(conn, month):
    conn.execute("DELETE FROM records WHERE month=?", (month,))
    conn.commit()


def save_goal(conn, name, target, saved, monthly):
    conn.execute("REPLACE INTO goals VALUES(?,?,?,?)", (name, target, saved, monthly))
    conn.commit()


def load_goals(conn):
    return [dict(zip(("name", "target", "saved", "monthly"), r))
            for r in conn.execute("SELECT * FROM goals ORDER BY name")]


def delete_goal(conn, name):
    conn.execute("DELETE FROM goals WHERE name=?", (name,))
    conn.commit()


def records_to_csv(records):
    flat = [{"month": r["month"], "income": r["income"], **r["expenses"]} for r in records]
    return pd.DataFrame(flat).to_csv(index=False)


def import_csv(conn, file_like):
    """Load records from a CSV made by records_to_csv. Returns rows imported."""
    df = pd.read_csv(file_like)
    if not {"month", "income"} <= set(df.columns):
        raise ValueError("CSV needs 'month' and 'income' columns.")
    for _, row in df.iterrows():
        cats = {c: float(row[c]) for c in df.columns if c not in ("month", "income") and pd.notna(row[c])}
        save_record(conn, str(row["month"]), float(row["income"]), cats)
    return len(df)


DEMO_RECORDS = [  # clearly labelled demo data
    ("2026-08", 25000, {"Rent": 6000, "Food": 3800, "Travel": 1800, "Shopping": 2200, "Education": 2000, "Bills": 1500, "Entertainment": 800, "Other": 900}),
    ("2026-09", 25000, {"Rent": 6000, "Food": 4000, "Travel": 2000, "Shopping": 2800, "Education": 2000, "Bills": 1500, "Entertainment": 1000, "Other": 1000}),
    ("2026-10", 25000, {"Rent": 6000, "Food": 4200, "Travel": 2100, "Shopping": 3400, "Education": 2000, "Bills": 1600, "Entertainment": 1200, "Other": 1000}),
]


def load_demo(conn):
    for month, income, cats in DEMO_RECORDS:
        save_record(conn, month, income, cats)