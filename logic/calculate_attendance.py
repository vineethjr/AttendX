import sqlite3

def subject_attendance(student_id, subject_id):
    conn = sqlite3.connect("db/attendance.db")
    cursor = conn.cursor()

    total = cursor.execute(
        "SELECT COUNT(DISTINCT date) FROM Attendance WHERE subject_id=?",
        (subject_id,)
    ).fetchone()[0]

    present = cursor.execute(
        """
        SELECT COUNT(DISTINCT date)
        FROM Attendance
        WHERE subject_id=? AND student_id=? AND status=1
        """,
        (subject_id, student_id)
    ).fetchone()[0]

    conn.close()

    if total == 0:
        return 0

    return round((present / total) * 100, 2)


def overall_attendance(student_id):
    conn = sqlite3.connect("db/attendance.db")
    cursor = conn.cursor()

    total = cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT subject_id, date
            FROM Attendance
            WHERE student_id=?
        )
        """,
        (student_id,)
    ).fetchone()[0]

    present = cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT subject_id, date
            FROM Attendance
            WHERE student_id=? AND status=1
        )
        """,
        (student_id,)
    ).fetchone()[0]

    conn.close()

    if total == 0:
        return 0

    return round((present / total) * 100, 2)
