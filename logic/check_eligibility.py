from db_utils import get_db_connection

def check_attendance_eligibility(student_id, subject_id):
    """
    Checks if a student's attendance in a subject is eligible.
    Calculates percentage, then applies rule:
    If < 75%, output "LOW ATTENDANCE"
    Else, output "ELIGIBLE"
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total_classes
    cursor.execute('SELECT total_classes FROM Subject WHERE subject_id = ?', (subject_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return "NO SUBJECT FOUND"
    total_classes = result[0]

    # Get classes_attended
    cursor.execute('SELECT COUNT(*) FROM Attendance WHERE student_id = ? AND subject_id = ? AND status = 1', (student_id, subject_id))
    classes_row = cursor.fetchone()
    classes_attended = classes_row[0] if classes_row else 0

    percentage = (classes_attended / total_classes) * 100 if total_classes > 0 else 0

    if percentage < 75:
        result = "LOW ATTENDANCE"
    else:
        result = "ELIGIBLE"

    conn.close()
    return result

# Example usage
if __name__ == "__main__":
    status = check_attendance_eligibility(1, 1)
    print(f"Eligibility for Student 1 in Subject 1: {status}")
