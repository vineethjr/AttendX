from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import subprocess

app = Flask(__name__)
app.secret_key = "attendx_secret_key"

# TEMP admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_db_connection():
    conn = sqlite3.connect("db/attendance.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/register-student", methods=["GET", "POST"])
def register_student():
    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        roll = request.form["roll"]
        name = request.form["name"]
        dept = request.form["dept"]
        sem = request.form["sem"]

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO Student (roll_no, name, department, semester)
                VALUES (?, ?, ?, ?)
                """,
                (roll, name, dept, sem)
            )

            conn.commit()
            conn.close()

            msg = "Student registered successfully"

        except sqlite3.IntegrityError:
            msg = "Roll number already exists"

        return render_template("register_student.html", msg=msg)

    return render_template("register_student.html")

@app.route("/students")
def view_students():
    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    students = conn.execute("SELECT * FROM Student").fetchall()
    conn.close()

    return render_template("view_students.html", students=students)



@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))


@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        subject_name = request.form["subject"]
        day = request.form["day"]
        start = request.form["start"]
        end = request.form["end"]
        is_free = 1 if "free" in request.form else 0

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO Subject (subject_name) VALUES (?)",
            (subject_name,)
        )

        subject_id = cursor.execute(
            "SELECT subject_id FROM Subject WHERE subject_name = ?",
            (subject_name,)
        ).fetchone()["subject_id"]

        cursor.execute(
            """
            INSERT INTO ClassSchedule
            (subject_id, day, start_time, end_time, is_free_period)
            VALUES (?, ?, ?, ?, ?)
            """,
            (subject_id, day, start, end, is_free)
        )

        conn.commit()
        conn.close()

        return render_template("schedule.html", msg="Schedule saved successfully")

    return render_template("schedule.html")


@app.route("/send-message", methods=["GET", "POST"])
def send_message():
    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        content = request.form["message"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO Message (content) VALUES (?)",
            (content,)
        )

        conn.commit()
        conn.close()

        return render_template("send_message.html", msg="Message sent successfully")

    return render_template("send_message.html")


@app.route("/display-message")
def display_message():
    conn = get_db_connection()
    msg = conn.execute(
        "SELECT content FROM Message ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()

    message = msg["content"] if msg else "No message"

    return render_template("display_message.html", message=message)

from logic.attendance_summary import get_attendance_summary

@app.route("/warnings")
def warnings():
    if "admin" not in session:
        return redirect(url_for("login"))

    subject_warnings, exam_warnings = get_attendance_summary()

    return render_template(
        "warning.html",
        subject_warnings=subject_warnings,
        exam_warnings=exam_warnings
    )


from flask import send_file
from logic.export_excel import export_attendance_excel

@app.route("/export-excel")
def export_excel():
    if "admin" not in session:
        return redirect(url_for("login"))

    file_name = "attendance_report.xlsx"
    export_attendance_excel(file_name)

    return send_file(file_name, as_attachment=True)

import subprocess

@app.route("/face-register", methods=["GET", "POST"])
def face_register():
    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    students = conn.execute("SELECT roll_no, name FROM Student").fetchall()
    conn.close()

    if request.method == "POST":
        roll = request.form["roll"]

        # Get student name from DB
        conn = get_db_connection()
        student = conn.execute("SELECT name FROM Student WHERE roll_no = ?", (roll,)).fetchone()
        conn.close()

        if not student:
            return render_template(
                "face_register.html",
                students=students,
                msg="Student not found"
            )

        name = student[0]

        # Run face capture script
        subprocess.run(
            ["python", "ai/register_student.py", name, roll]
        )

        return render_template(
            "face_register.html",
            students=students,
            msg="Face registration completed successfully"
        )

    return render_template("face_register.html", students=students)

if __name__ == "__main__":
    app.run(debug=True)
