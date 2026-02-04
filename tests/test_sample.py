import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_utils import get_db_connection

def calculate_attendance_percentage(student_id, subject_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT total_classes FROM Subject WHERE subject_id = ?', (subject_id,))
    total_classes = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM Attendance WHERE student_id = ? AND subject_id = ? AND status = 1', (student_id, subject_id))
    classes_attended = cursor.fetchone()[0]
    percentage = (classes_attended / total_classes) * 100 if total_classes > 0 else 0
    conn.close()
    return round(percentage, 2)

def check_attendance_eligibility(student_id, subject_id):
    percentage = calculate_attendance_percentage(student_id, subject_id)
    if percentage < 75:
        return "LOW ATTENDANCE"
    else:
        return "ELIGIBLE"

# Test for both students
print("Student 1 (Alice) in Math:")
print(f"Percentage: {calculate_attendance_percentage(1, 1)}%")
print(f"Eligibility: {check_attendance_eligibility(1, 1)}")

print("\nStudent 2 (Bob) in Math:")
print(f"Percentage: {calculate_attendance_percentage(2, 1)}%")
print(f"Eligibility: {check_attendance_eligibility(2, 1)}")
