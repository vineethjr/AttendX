from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import base64
from datetime import date, datetime, timedelta
import io
import logging
import os
import sqlite3
import time

import numpy as np
from flask_cors import CORS
from db_utils import get_db_connection

app = Flask(__name__)
app.secret_key = "attendx_secret_key"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
session_cookie_domain = os.getenv("ATTENDX_SESSION_COOKIE_DOMAIN")
if session_cookie_domain:
    app.config["SESSION_COOKIE_DOMAIN"] = session_cookie_domain

# cors_origins = os.getenv("ATTENDX_CORS_ORIGINS", "https://attendx-future.vercel.app")
# CORS(
#     app,
#     supports_credentials=True,
#     origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
# )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("attendx")

try:
    import face_recognition  # type: ignore
    FACE_RECOGNITION_AVAILABLE = True
except Exception as exc:  # pragma: no cover - environment dependent
    face_recognition = None
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition import failed: %s", exc)

FACE_CACHE = {"loaded_at": 0.0, "items": []}
FACE_CACHE_TTL_SECONDS = 60
RECOGNITION_MIN_INTERVAL_SECONDS = 2.0
LAST_RECOGNITION_BY_IP = {}

# TEMP admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def ensure_schema():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS StudentFace (
                student_id INTEGER PRIMARY KEY,
                encoding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES Student(student_id)
            )
            """
        )

        table = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='Attendance'"
        ).fetchone()
        if table:
            columns = [row[1] for row in cursor.execute("PRAGMA table_info(Attendance)").fetchall()]
            if "schedule_id" not in columns:
                cursor.execute("ALTER TABLE Attendance ADD COLUMN schedule_id INTEGER")

            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_schedule
                ON Attendance(student_id, schedule_id, date)
                """
            )

        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Schema check failed: %s", exc)


def json_error(message, status=400):
    return jsonify({"status": "error", "message": message}), status


def require_admin_json():
    if "admin" not in session:
        return json_error("Unauthorized", 401)
    return None


def wants_json():
    if request.is_json:
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept or "json" in accept


def decode_image_data_url(data_url):
    if not data_url or "," not in data_url:
        return None
    try:
        _, encoded = data_url.split(",", 1)
        return base64.b64decode(encoded)
    except Exception:
        return None


def load_face_cache(force=False):
    now = time.time()
    if not force and FACE_CACHE["items"] and (now - FACE_CACHE["loaded_at"]) < FACE_CACHE_TTL_SECONDS:
        return FACE_CACHE["items"]

    try:
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT sf.student_id, s.roll_no, s.name, sf.encoding
            FROM StudentFace sf
            JOIN Student s ON s.student_id = sf.student_id
            """
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError as exc:
        logger.warning("Failed to load face cache: %s", exc)
        return FACE_CACHE["items"]

    items = []
    for row in rows:
        if row["encoding"] is None:
            continue
        encoding = np.frombuffer(row["encoding"], dtype=np.float64)
        if encoding.shape[0] != 128:
            logger.warning("Invalid face encoding length for student_id=%s", row["student_id"])
            continue
        items.append(
            {
                "student_id": row["student_id"],
                "roll_no": row["roll_no"],
                "name": row["name"],
                "encoding": encoding,
            }
        )

    FACE_CACHE["loaded_at"] = now
    FACE_CACHE["items"] = items
    return items


def fetch_schedule_for_day(day):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            cs.schedule_id,
            cs.subject_id,
            s.subject_name,
            cs.start_time,
            cs.end_time,
            cs.is_free_period
        FROM ClassSchedule cs
        JOIN Subject s ON cs.subject_id = s.subject_id
        WHERE cs.day = ?
        ORDER BY cs.start_time
        """,
        (day,),
    )
    rows = cursor.fetchall()
    conn.close()

    schedules = []
    for row in rows:
        schedules.append(
            {
                "id": row["schedule_id"],
                "subject_id": row["subject_id"],
                "subject_name": row["subject_name"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "free_period": bool(row["is_free_period"]),
            }
        )
    return schedules


def compute_scan_no(schedule_id, day, cursor):
    cursor.execute(
        "SELECT schedule_id FROM ClassSchedule WHERE day = ? ORDER BY start_time",
        (day,),
    )
    schedule_ids = [row["schedule_id"] for row in cursor.fetchall()]
    scan_no = schedule_ids.index(schedule_id) + 1 if schedule_id in schedule_ids else 1
    if scan_no > 4:
        logger.warning("Scan number capped at 4 for schedule_id=%s", schedule_id)
        scan_no = 4
    return scan_no


def mark_schedule_attendance(student_id, subject_id, schedule_id, scan_no):
    today = date.today().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO Attendance
            (student_id, subject_id, date, scan_no, status, schedule_id)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (student_id, subject_id, today, scan_no, schedule_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


ensure_schema()


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


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"status": "ok"})

    logger.info("API login failed for username=%s", username)
    return json_error("Invalid credentials", 401)


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("admin", None)
    return jsonify({"status": "ok"})


@app.route("/api/session", methods=["GET"])
def api_session():
    return jsonify({"status": "ok", "authenticated": "admin" in session})


@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))

    metrics = {
        "total_students": 0,
        "active_classes": 0,
        "running_now": 0,
        "attendance_rate": 0,
        "warnings": 0,
    }
    attendance_trend = []
    donut = {
        "present": 0,
        "late": 0,
        "absent": 0,
        "center_value": "0%",
        "center_label": "No data",
        "empty": True,
    }
    upcoming_classes = []
    alerts = []

    conn = None
    try:
        today_name = datetime.today().strftime("%A")
        conn = get_db_connection()
        cursor = conn.cursor()

        metrics["total_students"] = cursor.execute(
            "SELECT COUNT(*) FROM Student"
        ).fetchone()[0]

        metrics["active_classes"] = cursor.execute(
            """
            SELECT COUNT(*)
            FROM ClassSchedule
            WHERE day = ? AND is_free_period = 0
            """,
            (today_name,),
        ).fetchone()[0]

        metrics["running_now"] = cursor.execute(
            """
            SELECT COUNT(*)
            FROM ClassSchedule
            WHERE day = ?
              AND is_free_period = 0
              AND time(start_time) <= time('now','localtime')
              AND time(end_time) >= time('now','localtime')
            """,
            (today_name,),
        ).fetchone()[0]

        upcoming_rows = cursor.execute(
            """
            SELECT s.subject_name, cs.start_time, cs.end_time
            FROM ClassSchedule cs
            JOIN Subject s ON s.subject_id = cs.subject_id
            WHERE cs.day = ?
              AND cs.is_free_period = 0
              AND time(cs.start_time) >= time('now','localtime')
            ORDER BY time(cs.start_time) ASC
            LIMIT 2
            """,
            (today_name,),
        ).fetchall()
        upcoming_classes = [
            {
                "subject": row["subject_name"],
                "time": f"{row['start_time']} - {row['end_time']}",
            }
            for row in upcoming_rows
        ]

        # Attendance trend for last 7 days (oldest -> newest)
        trend_dates = [
            date.today() - timedelta(days=offset)
            for offset in range(6, -1, -1)
        ]
        for d in trend_dates:
            date_str = d.isoformat()
            row = cursor.execute(
                """
                SELECT
                    SUM(CASE WHEN total_present >= 3 THEN 1 ELSE 0 END) AS present_count,
                    COUNT(*) AS total_count
                FROM (
                    SELECT student_id, subject_id, date, SUM(status) AS total_present
                    FROM Attendance
                    WHERE date = ?
                    GROUP BY student_id, subject_id, date
                ) AS daily
                """,
                (date_str,),
            ).fetchone()
            present_count = row[0] or 0
            total_count = row[1] or 0
            percent = round((present_count / total_count) * 100) if total_count else 0
            attendance_trend.append(
                {
                    "label": d.strftime("%a"),
                    "value": percent,
                    "muted": total_count == 0,
                }
            )

        start_date = (date.today() - timedelta(days=6)).isoformat()
        mix_row = cursor.execute(
            """
            SELECT
                SUM(CASE WHEN total_present >= 3 THEN 1 ELSE 0 END) AS present_count,
                SUM(CASE WHEN total_present BETWEEN 1 AND 2 THEN 1 ELSE 0 END) AS late_count,
                SUM(CASE WHEN total_present = 0 THEN 1 ELSE 0 END) AS absent_count,
                COUNT(*) AS total_count
            FROM (
                SELECT student_id, subject_id, date, SUM(status) AS total_present
                FROM Attendance
                WHERE date >= ?
                GROUP BY student_id, subject_id, date
            ) AS totals
            """,
            (start_date,),
        ).fetchone()

        present_count = mix_row[0] or 0
        late_count = mix_row[1] or 0
        absent_count = mix_row[2] or 0
        total_count = mix_row[3] or 0

        if total_count:
            present_pct = round((present_count / total_count) * 100)
            late_pct = round((late_count / total_count) * 100)
            absent_pct = max(0, 100 - present_pct - late_pct)
            donut = {
                "present": present_pct,
                "late": late_pct,
                "absent": absent_pct,
                "center_value": f"{present_pct}%",
                "center_label": "Present",
                "empty": False,
            }
            metrics["attendance_rate"] = present_pct

        subject_warnings, exam_warnings = get_attendance_summary()
        metrics["warnings"] = sum(
            1 for warning in exam_warnings if warning["exam_status"] == "NOT ELIGIBLE"
        )

        warning_by_subject = {}
        for warning in subject_warnings:
            if warning["status"] != "WARNING":
                continue
            subject = warning["subject"]
            warning_by_subject[subject] = warning_by_subject.get(subject, 0) + 1

        alerts = [
            {
                "title": f"{subject} / {count} students",
                "subtitle": "Below 75% attendance",
                "status": "Action",
                "tone": "danger",
            }
            for subject, count in sorted(
                warning_by_subject.items(), key=lambda item: item[1], reverse=True
            )[:2]
        ]

    except sqlite3.OperationalError as exc:
        logger.warning("Dashboard metrics failed: %s", exc)
    finally:
        if conn:
            conn.close()

    if not attendance_trend:
        fallback_dates = [
            date.today() - timedelta(days=offset)
            for offset in range(6, -1, -1)
        ]
        attendance_trend = [
            {"label": d.strftime("%a"), "value": 0, "muted": True}
            for d in fallback_dates
        ]

    return render_template(
        "dashboard.html",
        metrics=metrics,
        attendance_trend=attendance_trend,
        donut=donut,
        upcoming_classes=upcoming_classes,
        alerts=alerts,
    )

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

@app.route("/students", methods=["GET", "POST"])
def view_students():
    if request.method == "POST":
        return api_create_student()

    if wants_json():
        return api_students()

    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    students = conn.execute("SELECT * FROM Student").fetchall()
    conn.close()

    return render_template("view_students.html", students=students)


@app.route("/api/students", methods=["GET"])
def api_students():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM Student ORDER BY roll_no").fetchall()
    conn.close()

    students = [
        {
            "student_id": row["student_id"],
            "roll_no": row["roll_no"],
            "name": row["name"],
            "department": row["department"],
            "semester": row["semester"],
        }
        for row in rows
    ]

    return jsonify({"status": "ok", "students": students})


@app.route("/api/students", methods=["POST"])
def api_create_student():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    roll = (data.get("roll_no") or "").strip()
    name = (data.get("name") or "").strip()
    dept = (data.get("department") or "").strip()
    sem = (data.get("semester") or "").strip()

    if not roll or not name:
        return json_error("Roll number and name are required.", 400)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Student (roll_no, name, department, semester)
            VALUES (?, ?, ?, ?)
            """,
            (roll, name, dept, sem),
        )
        student_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify(
            {
                "status": "ok",
                "student": {
                    "student_id": student_id,
                    "roll_no": roll,
                    "name": name,
                    "department": dept,
                    "semester": sem,
                },
            }
        )
    except sqlite3.IntegrityError:
        return json_error("Roll number already exists.", 409)



@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))


@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    if request.method == "POST" and request.is_json:
        return api_create_schedule()

    if request.method == "GET" and wants_json():
        return api_schedule()

    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        subject_name = (request.form.get("subject") or "").strip()
        day = request.form.get("day") or datetime.today().strftime("%A")
        start = request.form.get("start")
        end = request.form.get("end")
        is_free = 1 if request.form.get("free") else 0

        if not subject_name or not start or not end:
            schedules = fetch_schedule_for_day(day)
            return render_template(
                "schedule.html",
                day=day,
                days=DAY_NAMES,
                schedules=schedules,
                error="All fields are required to save a schedule.",
            )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO Subject (subject_name, total_classes) VALUES (?, 0)",
            (subject_name,),
        )

        row = cursor.execute(
            "SELECT subject_id FROM Subject WHERE subject_name = ?",
            (subject_name,)
        ).fetchone()

        if not row:
            conn.close()
            schedules = fetch_schedule_for_day(day)
            return render_template(
                "schedule.html",
                day=day,
                days=DAY_NAMES,
                schedules=schedules,
                error=f"Subject not found: {subject_name}",
            )

        subject_id = row["subject_id"]

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

        return redirect(url_for("schedule", day=day, saved=1))

    day = request.args.get("day") or datetime.today().strftime("%A")
    if day not in DAY_NAMES:
        day = datetime.today().strftime("%A")
    schedules = fetch_schedule_for_day(day)
    msg = "Schedule saved successfully" if request.args.get("saved") else None
    return render_template(
        "schedule.html",
        day=day,
        days=DAY_NAMES,
        schedules=schedules,
        msg=msg,
    )


@app.route("/api/schedule", methods=["GET"])
def api_schedule():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    day = request.args.get("day") or datetime.today().strftime("%A")
    if day not in DAY_NAMES:
        day = datetime.today().strftime("%A")
    schedules = fetch_schedule_for_day(day)
    return jsonify({"status": "ok", "day": day, "schedules": schedules})


@app.route("/schedule/today", methods=["GET"])
def api_schedule_today():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    day = datetime.today().strftime("%A")
    schedules = fetch_schedule_for_day(day)
    return jsonify({"status": "ok", "day": day, "schedules": schedules})


@app.route("/api/schedule", methods=["POST"])
def api_create_schedule():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    subject_name = (data.get("subject_name") or "").strip()
    day = data.get("day") or datetime.today().strftime("%A")
    start = data.get("start_time")
    end = data.get("end_time")
    is_free = 1 if data.get("is_free_period") else 0

    if not subject_name or not start or not end:
        return json_error("All fields are required.", 400)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO Subject (subject_name, total_classes) VALUES (?, 0)",
        (subject_name,),
    )
    row = cursor.execute(
        "SELECT subject_id FROM Subject WHERE subject_name = ?",
        (subject_name,),
    ).fetchone()

    if not row:
        conn.close()
        return json_error(f"Subject not found: {subject_name}", 404)

    subject_id = row["subject_id"]
    cursor.execute(
        """
        INSERT INTO ClassSchedule
        (subject_id, day, start_time, end_time, is_free_period)
        VALUES (?, ?, ?, ?, ?)
        """,
        (subject_id, day, start, end, is_free),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {
            "status": "ok",
            "schedule": {
                "subject_id": subject_id,
                "subject_name": subject_name,
                "day": day,
                "start_time": start,
                "end_time": end,
                "is_free_period": bool(is_free),
            },
        }
    )


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


@app.route("/api/messages", methods=["POST"])
def api_send_message():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return json_error("Message content is required.", 400)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Message (content) VALUES (?)", (content,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


@app.route("/messages", methods=["POST"])
def messages_json():
    return api_send_message()


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
    if wants_json():
        return api_warnings()

    if "admin" not in session:
        return redirect(url_for("login"))

    subject_warnings, exam_warnings = get_attendance_summary()

    return render_template(
        "warning.html",
        subject_warnings=subject_warnings,
        exam_warnings=exam_warnings
    )


@app.route("/api/warnings")
def api_warnings():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    subject_warnings, exam_warnings = get_attendance_summary()
    return jsonify(
        {
            "status": "ok",
            "subject_warnings": subject_warnings,
            "exam_warnings": exam_warnings,
        }
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


@app.route("/api/reports/export")
def api_export_excel():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    file_name = "attendance_report.xlsx"
    export_attendance_excel(file_name)
    return send_file(file_name, as_attachment=True)


@app.route("/reports/export")
def reports_export_excel():
    return api_export_excel()

@app.route("/face-register", methods=["GET"])
def face_register():
    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    students = conn.execute(
        "SELECT student_id, roll_no, name FROM Student ORDER BY roll_no"
    ).fetchall()
    conn.close()

    return render_template("face_register.html", students=students)


@app.route("/face-register/capture", methods=["POST"])
def face_register_capture():
    if "admin" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    if not FACE_RECOGNITION_AVAILABLE:
        return jsonify(
            {
                "status": "error",
                "message": "face_recognition is not available. Install it to register faces.",
            }
        ), 500

    payload = request.get_json(silent=True) or {}
    student_id = payload.get("student_id")
    image_data = payload.get("image")

    try:
        student_id = int(student_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid student selection."}), 400

    if not image_data:
        return jsonify({"status": "error", "message": "No image provided."}), 400

    image_bytes = decode_image_data_url(image_data)
    if not image_bytes:
        return jsonify({"status": "error", "message": "Invalid image data."}), 400

    image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        return jsonify({"status": "error", "message": "No face detected."}), 400

    encoding = encodings[0]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO StudentFace (student_id, encoding) VALUES (?, ?)",
            (student_id, sqlite3.Binary(encoding.tobytes())),
        )
        conn.commit()
    except sqlite3.OperationalError as exc:
        logger.error("Face registration DB error: %s", exc)
        return jsonify({"status": "error", "message": "Database is locked. Try again."}), 500
    finally:
        if conn:
            conn.close()

    load_face_cache(force=True)
    logger.info("Face registered for student_id=%s", student_id)
    return jsonify({"status": "ok"})


@app.route("/api/face-register/capture", methods=["POST"])
def api_face_register_capture():
    return face_register_capture()


@app.route("/recognize", methods=["POST"])
def recognize():
    if "admin" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    if not FACE_RECOGNITION_AVAILABLE:
        return jsonify(
            {
                "status": "error",
                "message": "face_recognition is not available. Install it to use recognition.",
            }
        ), 500

    payload = request.get_json(silent=True) or {}
    schedule_id = payload.get("schedule_id")
    image_data = payload.get("image")

    try:
        schedule_id = int(schedule_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid schedule id."}), 400

    if not image_data:
        return jsonify({"status": "error", "message": "No image provided."}), 400

    ip = request.remote_addr or "unknown"
    now = time.time()
    last = LAST_RECOGNITION_BY_IP.get(ip, 0)
    if (now - last) < RECOGNITION_MIN_INTERVAL_SECONDS:
        return jsonify({"status": "error", "message": "Please slow down."}), 429
    LAST_RECOGNITION_BY_IP[ip] = now

    image_bytes = decode_image_data_url(image_data)
    if not image_bytes:
        return jsonify({"status": "error", "message": "Invalid image data."}), 400

    image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    face_locations = face_recognition.face_locations(image)
    encodings = face_recognition.face_encodings(image, face_locations)

    if not encodings:
        return jsonify({"status": "ok", "recognized": [], "message": "No face detected."}), 200

    known_faces = load_face_cache()
    if not known_faces:
        return jsonify(
            {"status": "error", "message": "No registered faces available."}
        ), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        schedule = cursor.execute(
            """
            SELECT schedule_id, subject_id, day, is_free_period
            FROM ClassSchedule
            WHERE schedule_id = ?
            """,
            (schedule_id,),
        ).fetchone()

        if not schedule:
            return jsonify({"status": "error", "message": "Schedule not found."}), 404

        if schedule["is_free_period"]:
            return jsonify(
                {
                    "status": "ok",
                    "recognized": [],
                    "message": "Free period. Attendance not recorded.",
                }
            ), 200

        scan_no = compute_scan_no(schedule_id, schedule["day"], cursor)
        subject_id = schedule["subject_id"]
    except sqlite3.OperationalError as exc:
        logger.error("Recognition DB error: %s", exc)
        return jsonify({"status": "error", "message": "Database is locked. Try again."}), 500
    finally:
        if conn:
            conn.close()

    known_encodings = [face["encoding"] for face in known_faces]
    recognized_names = []
    recognized_ids = set()

    for encoding in encodings:
        matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.5)
        if True in matches:
            match_index = matches.index(True)
            match = known_faces[match_index]
            student_id = match["student_id"]
            if student_id in recognized_ids:
                continue
            recognized_ids.add(student_id)

            inserted = mark_schedule_attendance(student_id, subject_id, schedule_id, scan_no)
            if inserted:
                recognized_names.append(match["name"])
                logger.info(
                    "Attendance recorded: student_id=%s schedule_id=%s",
                    student_id,
                    schedule_id,
                )

    if recognized_names:
        return jsonify(
            {"status": "ok", "recognized": recognized_names, "message": "Attendance updated."}
        )

    return jsonify(
        {"status": "ok", "recognized": [], "message": "No matches found."}
    )


@app.route("/api/recognize", methods=["POST"])
def api_recognize():
    return recognize()


@app.route("/attendance", methods=["POST"])
def api_attendance():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    payload = request.get_json(silent=True) or {}
    schedule_id = payload.get("schedule_id")
    student_ids = payload.get("student_ids") or []

    if not student_ids and payload.get("student_id") is not None:
        student_ids = [payload.get("student_id")]

    try:
        schedule_id = int(schedule_id)
        student_ids = [int(sid) for sid in student_ids]
    except (TypeError, ValueError):
        return json_error("Invalid schedule or student selection.", 400)

    if not student_ids:
        return json_error("No students provided.", 400)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        schedule = cursor.execute(
            """
            SELECT schedule_id, subject_id, day, is_free_period
            FROM ClassSchedule
            WHERE schedule_id = ?
            """,
            (schedule_id,),
        ).fetchone()

        if not schedule:
            return json_error("Schedule not found.", 404)

        if schedule["is_free_period"]:
            return jsonify(
                {
                    "status": "ok",
                    "inserted": [],
                    "message": "Free period. Attendance not recorded.",
                }
            )

        scan_no = compute_scan_no(schedule_id, schedule["day"], cursor)
        subject_id = schedule["subject_id"]
    except sqlite3.OperationalError as exc:
        logger.error("Attendance DB error: %s", exc)
        return json_error("Database is locked. Try again.", 500)
    finally:
        if conn:
            conn.close()

    inserted = []
    for student_id in student_ids:
        if mark_schedule_attendance(student_id, subject_id, schedule_id, scan_no):
            inserted.append(student_id)

    return jsonify({"status": "ok", "inserted": inserted})

if __name__ == "__main__":
    app.run(debug=True)
