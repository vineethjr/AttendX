from db_utils import get_db_connection

def subject_attendance(student_id, subject_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    total_row = cursor.execute(
        "SELECT COUNT(DISTINCT date) FROM Attendance WHERE subject_id=?",
        (subject_id,)
    ).fetchone()
    total = total_row[0] if total_row else 0

    present_row = cursor.execute(
        """
        SELECT COUNT(DISTINCT date)
        FROM Attendance
        WHERE subject_id=? AND student_id=? AND status=1
        """,
        (subject_id, student_id)
    ).fetchone()
    present = present_row[0] if present_row else 0

    conn.close()

    if total == 0:
        return 0

    return round((present / total) * 100, 2)


def overall_attendance(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    total_row = cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT subject_id, date
            FROM Attendance
            WHERE student_id=?
        )
        """,
        (student_id,)
    ).fetchone()
    total = total_row[0] if total_row else 0

    present_row = cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT subject_id, date
            FROM Attendance
            WHERE student_id=? AND status=1
        )
        """,
        (student_id,)
    ).fetchone()
    present = present_row[0] if present_row else 0

    conn.close()

    if total == 0:
        return 0

    return round((present / total) * 100, 2)
