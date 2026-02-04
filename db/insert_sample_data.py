import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_utils import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Insert sample students
cursor.execute("INSERT OR IGNORE INTO Student (roll_no, name, department) VALUES ('R001', 'Alice Johnson', 'Computer Science')")
cursor.execute("INSERT OR IGNORE INTO Student (roll_no, name, department) VALUES ('R002', 'Bob Smith', 'Mathematics')")

# Insert sample subjects
cursor.execute("INSERT OR IGNORE INTO Subject (subject_name, total_classes) VALUES ('Mathematics', 10)")
cursor.execute("INSERT OR IGNORE INTO Subject (subject_name, total_classes) VALUES ('Science', 8)")

# Insert sample attendance for Alice in Math: 8 attended out of 10 (80%)
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (1, 1, '2023-10-01', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (1, 1, '2023-10-02', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (1, 1, '2023-10-03', 1, 0)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (1, 1, '2023-10-04', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (1, 1, '2023-10-05', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (1, 1, '2023-10-06', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (1, 1, '2023-10-07', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (1, 1, '2023-10-08', 1, 1)")

# For Bob in Math: 6 attended out of 10 (60% - low)
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (2, 1, '2023-10-01', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (2, 1, '2023-10-02', 1, 0)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (2, 1, '2023-10-03', 1, 0)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (2, 1, '2023-10-04', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (2, 1, '2023-10-05', 1, 1)")
cursor.execute("INSERT OR IGNORE INTO Attendance (student_id, subject_id, date, scan_no, status) VALUES (2, 1, '2023-10-06', 1, 1)")

conn.commit()
conn.close()

print("Sample data inserted.")
