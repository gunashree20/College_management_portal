import os
import sqlite3
from pathlib import Path
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, jsonify
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-classroom-demo-key")

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(
    os.environ.get("DATABASE_PATH", str(BASE_DIR / "instance" / "events.db"))
)

EVENTS = [
    "Code Sprint",
    "AI Innovators",
    "Robo Challenge",
    "Web Creators",
    "Cyber Quest",
    "Project Pitch",
]


def get_db():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                department TEXT NOT NULL,
                year TEXT NOT NULL,
                event TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Registered',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email, event)
            )
        """)


init_db()


@app.route("/")
def home():
    with get_db() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM registrations"
        ).fetchone()[0]

        event_count = db.execute(
            "SELECT COUNT(DISTINCT event) FROM registrations"
        ).fetchone()[0]

    return render_template(
        "index.html",
        total=total,
        event_count=event_count,
        events=EVENTS
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "").strip()
        event = request.form.get("event", "").strip()

        if not all([name, email, department, year, event]):
            flash("Please complete every field.", "error")
            return redirect(url_for("register"))

        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.", "error")
            return redirect(url_for("register"))

        if event not in EVENTS:
            flash("Please select a valid event.", "error")
            return redirect(url_for("register"))

        if year not in ["1st Year", "2nd Year", "3rd Year", "4th Year"]:
            flash("Please select a valid year.", "error")
            return redirect(url_for("register"))

        try:
            with get_db() as db:
                db.execute("""
                    INSERT INTO registrations
                    (name, email, department, year, event)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, email, department, year, event))

            flash("Registration successful! See you at TECHNOVA.", "success")

        except sqlite3.IntegrityError:
            flash("This email is already registered for that event.", "error")

        return redirect(url_for("register"))

    return render_template("register.html", events=EVENTS)


@app.route("/admin")
def admin():
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = "SELECT * FROM registrations WHERE 1=1"
    params = []

    if search:
        query += """
            AND (
                name LIKE ? OR email LIKE ?
                OR department LIKE ? OR event LIKE ?
            )
        """
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])

    if status_filter in ["Registered", "Attended", "Cancelled"]:
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY created_at DESC"

    with get_db() as db:
        registrations = db.execute(query, params).fetchall()

        total = db.execute(
            "SELECT COUNT(*) FROM registrations"
        ).fetchone()[0]

        registered = db.execute(
            "SELECT COUNT(*) FROM registrations WHERE status='Registered'"
        ).fetchone()[0]

        attended = db.execute(
            "SELECT COUNT(*) FROM registrations WHERE status='Attended'"
        ).fetchone()[0]

        event_stats = db.execute("""
            SELECT event, COUNT(*) AS count
            FROM registrations
            GROUP BY event
            ORDER BY count DESC, event
        """).fetchall()

    return render_template(
        "admin.html",
        registrations=registrations,
        total=total,
        registered=registered,
        attended=attended,
        event_stats=event_stats,
        search=search,
        status_filter=status_filter
    )


@app.route("/admin/status/<int:registration_id>", methods=["POST"])
def update_status(registration_id):
    status = request.form.get("status", "")

    if status not in ["Registered", "Attended", "Cancelled"]:
        flash("Invalid registration status.", "error")
        return redirect(url_for("admin"))

    with get_db() as db:
        result = db.execute(
            "UPDATE registrations SET status = ? WHERE id = ?",
            (status, registration_id)
        )

    if result.rowcount:
        flash("Registration status updated.", "success")
    else:
        flash("Registration not found.", "error")

    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:registration_id>", methods=["POST"])
def delete_registration(registration_id):
    with get_db() as db:
        result = db.execute(
            "DELETE FROM registrations WHERE id = ?",
            (registration_id,)
        )

    if result.rowcount:
        flash("Registration deleted.", "success")
    else:
        flash("Registration not found.", "error")

    return redirect(url_for("admin"))


@app.route("/health")
def health():
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return jsonify(status="ok", application="TECHNOVA Portal")
    except sqlite3.Error:
        return jsonify(status="error"), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
