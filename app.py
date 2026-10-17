from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "expenses.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                monthly_budget REAL NOT NULL DEFAULT 3000
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO settings (id, monthly_budget)
            VALUES (1, 3000)
        """)


@app.route("/", methods=["GET", "POST"])
def index():
    today = date.today().isoformat()
    month = request.args.get("month", today[:7])

    if len(month) != 7 or month[4:5] != "-" or not month[:4].isdigit() or not month[5:].isdigit() or not 1 <= int(month[5:]) <= 12:
        month = today[:7]

    if request.method == "POST":
        action = request.form.get("action", "add")

        try:
            with get_db() as conn:
                if action == "add":
                    amount = float(request.form.get("amount", "0"))
                    category = request.form.get("category", "")
                    expense_date = request.form.get("expense_date", "")
                    description = request.form.get("description", "").strip()

                    if amount <= 0:
                        raise ValueError("Amount must be greater than zero.")

                    if category not in [
                        "Food", "Travel", "Shopping",
                        "Stationery", "Other"
                    ]:
                        raise ValueError("Please select a valid category.")

                    date.fromisoformat(expense_date)

                    conn.execute("""
                        INSERT INTO expenses
                        (amount, category, expense_date, description)
                        VALUES (?, ?, ?, ?)
                    """, (amount, category, expense_date, description))

                    flash("Expense added successfully!")

                elif action == "delete":
                    expense_id = int(request.form.get("expense_id", "0"))
                    conn.execute(
                        "DELETE FROM expenses WHERE id = ?",
                        (expense_id,)
                    )
                    flash("Expense deleted.")

                elif action == "edit":
                    expense_id = int(request.form.get("expense_id", "0"))
                    amount = float(request.form.get("amount", "0"))
                    category = request.form.get("category", "")
                    expense_date = request.form.get("expense_date", "")
                    description = request.form.get("description", "").strip()

                    if amount <= 0:
                        raise ValueError("Amount must be greater than zero.")

                    if category not in [
                        "Food", "Travel", "Shopping",
                        "Stationery", "Other"
                    ]:
                        raise ValueError("Please select a valid category.")

                    date.fromisoformat(expense_date)

                    conn.execute("""
                        UPDATE expenses
                        SET amount = ?, category = ?,
                            expense_date = ?, description = ?
                        WHERE id = ?
                    """, (
                        amount, category, expense_date,
                        description, expense_id
                    ))
                    flash("Expense updated.")

                elif action == "budget":
                    budget = float(request.form.get("monthly_budget", "0"))

                    if budget < 0:
                        raise ValueError("Budget cannot be negative.")

                    conn.execute("""
                        UPDATE settings SET monthly_budget = ?
                        WHERE id = 1
                    """, (budget,))
                    flash("Monthly budget updated.")

                else:
                    raise ValueError("Invalid action.")

        except (ValueError, TypeError):
            flash("Invalid input. Please check your values.")
        except sqlite3.Error:
            flash("Database error. Please try again.")

        return redirect(url_for("index", month=month))

    with get_db() as conn:
        expenses = conn.execute("""
            SELECT * FROM expenses
            WHERE substr(expense_date, 1, 7) = ?
            ORDER BY expense_date DESC, id DESC
        """, (month,)).fetchall()

        total = sum(row["amount"] for row in expenses)

        budget_row = conn.execute("""
            SELECT monthly_budget FROM settings WHERE id = 1
        """).fetchone()

        budget = budget_row["monthly_budget"]
        remaining = budget - total

        category_rows = conn.execute("""
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE substr(expense_date, 1, 7) = ?
            GROUP BY category
            ORDER BY total DESC
        """, (month,)).fetchall()

        edit_id = request.args.get("edit", type=int)
        edit_expense = None

        if edit_id:
            edit_expense = conn.execute(
                "SELECT * FROM expenses WHERE id = ?",
                (edit_id,)
            ).fetchone()

    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        budget=budget,
        remaining=remaining,
        categories=category_rows,
        month=month,
        today=today,
        edit_expense=edit_expense
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)