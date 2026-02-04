from db_utils import get_db_connection

def get_attendance_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Step 1: Get final attendance per subject
    cursor.execute("""
        SELECT
            s.roll_no,
            sub.subject_name,
            COUNT(DISTINCT a.date) AS total_classes,
            SUM(
                CASE
                    WHEN (
                        SELECT SUM(status)
                        FROM Attendance a2
                        WHERE a2.student_id = a.student_id
                          AND a2.subject_id = a.subject_id
                          AND a2.date = a.date
                    ) >= 3
                    THEN 1
                    ELSE 0
                END
            ) AS present_classes
        FROM Attendance a
        JOIN Student s ON a.student_id = s.student_id
        JOIN Subject sub ON a.subject_id = sub.subject_id
        GROUP BY a.student_id, a.subject_id
    """)

    subject_records = cursor.fetchall()

    subject_warnings = []
    overall_data = {}

    # Step 2: Process subject-wise attendance
    for roll_no, subject, total, present in subject_records:
        percentage = (present / total) * 100 if total > 0 else 0

        subject_warnings.append({
            "roll_no": roll_no,
            "subject": subject,
            "percentage": round(percentage, 2),
            "status": "WARNING" if percentage < 75 else "OK"
        })

        # Collect data for overall attendance
        if roll_no not in overall_data:
            overall_data[roll_no] = {"present": 0, "total": 0}

        overall_data[roll_no]["present"] += present
        overall_data[roll_no]["total"] += total

    # Step 3: Calculate overall attendance
    exam_warnings = []

    for roll_no, data in overall_data.items():
        overall_percentage = (
            (data["present"] / data["total"]) * 100
            if data["total"] > 0 else 0
        )

        exam_warnings.append({
            "roll_no": roll_no,
            "overall_percentage": round(overall_percentage, 2),
            "exam_status": "NOT ELIGIBLE" if overall_percentage < 75 else "ELIGIBLE"
        })

    conn.close()

    return subject_warnings, exam_warnings
