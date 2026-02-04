from db_utils import get_db_connection

def calculate_attendance_percentage(student_id, subject_id):
    """
    Calculates attendance percentage for a student in a subject.
    Formula: (classes_attended / total_classes) * 100
    Where classes_attended = number of times status = 1
    total_classes = Subject.total_classes
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total_classes from Subject table
    cursor.execute('''
    SELECT total_classes FROM Subject WHERE subject_id = ?
    ''', (subject_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return 0.0
    total_classes = result[0]

    # Get classes_attended (count of status = 1)
    cursor.execute('''
    SELECT COUNT(*) FROM Attendance
    WHERE student_id = ? AND subject_id = ? AND status = 1
    ''', (student_id, subject_id))
    classes_row = cursor.fetchone()
    classes_attended = classes_row[0] if classes_row else 0

    if total_classes == 0:
        percentage = 0.0
    else:
        percentage = (classes_attended / total_classes) * 100

    conn.close()
    return round(percentage, 2)

# Example usage
if __name__ == "__main__":
    percentage = calculate_attendance_percentage(1, 1)
    print(f"Attendance percentage for Student 1 in Subject 1: {percentage}%")
