import sqlite3
from datetime import date

def mark_scan(roll_no, subject_name, scan_no, status):
    today = date.today().isoformat()

    conn = sqlite3.connect("db/attendance.db")
    cursor = conn.cursor()

    # Get student_id
    student = cursor.execute(
        "SELECT student_id FROM Student WHERE roll_no=?",
        (roll_no,)
    ).fetchone()

    if not student:
        conn.close()
        return False

    student_id = student[0]

    # Get subject_id
    cursor.execute(
    "INSERT OR IGNORE INTO Subject (subject_name) VALUES (?)",
    (subject_name,)
)


    subject_id = cursor.execute(
        "SELECT subject_id FROM Subject WHERE subject_name=?",
        (subject_name,)
    ).fetchone()[0]

    # Insert scan record (unique per scan)
    try:
        cursor.execute(
            """
            INSERT INTO Attendance
            (student_id, subject_id, date, scan_no, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, subject_id, today, scan_no, status)
        )
    except sqlite3.IntegrityError:
        pass  # scan already recorded

    conn.commit()
    conn.close()
    return True
