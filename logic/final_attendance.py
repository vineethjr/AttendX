from db_utils import get_db_connection

def get_final_attendance():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            s.roll_no,
            sub.subject_name,
            a.date,
            SUM(a.status) AS present_count
        FROM Attendance a
        JOIN Student s ON a.student_id = s.student_id
        JOIN Subject sub ON a.subject_id = sub.subject_id
        GROUP BY a.student_id, a.subject_id, a.date
    """)

    records = cursor.fetchall()
    conn.close()

    final_result = []

    for roll_no, subject, date, present_count in records:
        final_status = "PRESENT" if present_count >= 3 else "ABSENT"
        final_result.append({
            "roll_no": roll_no,
            "subject": subject,
            "date": date,
            "present_count": present_count,
            "final_status": final_status
        })

    return final_result
