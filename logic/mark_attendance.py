import sqlite3
from datetime import date
from db_utils import get_db_connection

def mark_scan(roll_no, subject_name, scan_no, status):
    today = date.today().isoformat()

    conn = get_db_connection()
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
        "INSERT OR IGNORE INTO Subject (subject_name, total_classes) VALUES (?, 0)",
        (subject_name,)
    )


    subject_row = cursor.execute(
        "SELECT subject_id FROM Subject WHERE subject_name=?",
        (subject_name,)
    ).fetchone()

    if not subject_row:
        conn.close()
        return False

    subject_id = subject_row[0]

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
