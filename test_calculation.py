import io, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finance_calculations import (InputError, calculate_summary, safe_percentage,
                                  months_to_goal, goal_progress)
from budget_analysis import (plan_budget, check_budget, rank_categories,
                             overspending_alerts, budget_adherence)
from financial_health import health_score, classify
from ai_recommendations import generate_recommendations
from expense_prediction import predict_next
import data_manager

EX = {"Food": 4000, "Travel": 2000, "Shopping": 3000, "Education": 2000, "Other": 1000}


class Calc(unittest.TestCase):
    def test_example_from_brief(self):
        s = calculate_summary(25000, EX)
        self.assertEqual((s["total_expenses"], s["balance"], s["savings_pct"]), (12000, 13000, 52.0))

    def test_changes_with_input(self):
        self.assertEqual(calculate_summary(30000, EX)["balance"], 18000)

    def test_invalid_inputs(self):
        for bad in (-5, "", None, "abc", 0, float("nan")):
            with self.assertRaises(InputError):
                calculate_summary(bad, EX)
        with self.assertRaises(InputError):
            calculate_summary(1000, {"Food": -1})

    def test_division_by_zero_safe(self):
        self.assertEqual(safe_percentage(5, 0), 0.0)

    def test_recursion_goal(self):
        self.assertEqual(months_to_goal(10000, 0, 1000), 10)
        self.assertIsNone(months_to_goal(10000, 0, 0))
        self.assertLess(months_to_goal(100000, 0, 1000, 12), months_to_goal(100000, 0, 1000))
        self.assertEqual(goal_progress(200, 50), 25.0)


class Budget(unittest.TestCase):
    def setUp(self):
        self.rows = check_budget(EX, plan_budget(25000))
        self.by = {r["category"]: r["status"] for r in self.rows}

    def test_status(self):
        self.assertEqual((self.by["Food"], self.by["Education"], self.by["Other"]),
                         ("Over", "Within", "Near"))

    def test_ranking_lambda(self):
        self.assertEqual(rank_categories(EX, 2), [("Food", 4000), ("Shopping", 3000)])

    def test_alerts_and_adherence(self):
        self.assertEqual(len([r for r in self.rows if r["status"] == "Over"]), 3)
        self.assertAlmostEqual(budget_adherence(self.rows), 0.4)
        self.assertTrue(overspending_alerts(self.rows)[0].startswith("Shopping"))


class Health(unittest.TestCase):
    def test_score_example(self):
        s = calculate_summary(25000, EX)
        adh = budget_adherence(check_budget(EX, plan_budget(25000)))
        score, label, _ = health_score(s["savings_pct"], adh, expense_pct=s["expense_pct"])
        self.assertEqual((score, label), (82.0, "Excellent"))

    def test_bounds(self):
        self.assertEqual(health_score(-50, 0, expense_pct=150)[0], 0.0)
        self.assertEqual(classify(59.9), "Fair")

    def test_recs_match_input(self):
        s = calculate_summary(25000, EX)
        titles = " ".join(r["title"] for r in
                          generate_recommendations(s, check_budget(EX, plan_budget(25000))))
        self.assertIn("Shopping", titles)
        self.assertNotIn("Education", titles)
        deficit = calculate_summary(1000, {"Food": 2000})
        self.assertEqual(generate_recommendations(deficit, [])[0]["title"], "Expenses exceed income")


class Predict(unittest.TestCase):
    def test_trend_and_average(self):
        self.assertEqual(predict_next([100, 200, 300])[0], 400.0)
        self.assertEqual(predict_next([100, 200])[0], 150.0)
        with self.assertRaises(ValueError):
            predict_next([])


class Storage(unittest.TestCase):
    def test_roundtrip_and_csv(self):
        c = data_manager.connect()
        data_manager.save_record(c, "2026-10", 25000, EX)
        recs = data_manager.load_records(c)
        self.assertEqual(recs[0]["expenses"]["Food"], 4000)
        c2 = data_manager.connect()
        self.assertEqual(data_manager.import_csv(c2, io.StringIO(data_manager.records_to_csv(recs))), 1)
        data_manager.delete_record(c, "2026-10")
        self.assertEqual(data_manager.load_records(c), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)