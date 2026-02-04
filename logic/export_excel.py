from openpyxl import Workbook
from db_utils import get_db_connection
from logic.calculate_attendance import subject_attendance, overall_attendance

def export_attendance_excel(file_path="attendance_report.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Overall Attendance"

    ws.append([
        "Roll No",
        "Name",
        "Department",
        "Semester",
        "Overall Attendance (%)"
    ])

    conn = get_db_connection()
    cursor = conn.cursor()

    students = cursor.execute("SELECT * FROM Student").fetchall()

    for s in students:
        overall = overall_attendance(s["student_id"])
        ws.append([
            s["roll_no"],
            s["name"],
            s["department"],
            s["semester"],
            overall
        ])

    conn.close()

    add_subject_wise_sheets(wb)
    wb.save(file_path)


def add_subject_wise_sheets(wb):
    conn = get_db_connection()
    cursor = conn.cursor()

    subjects = cursor.execute("SELECT * FROM Subject").fetchall()
    students = cursor.execute("SELECT * FROM Student").fetchall()

    for sub in subjects:
        ws = wb.create_sheet(title=sub["subject_name"])
        ws.append(["Roll No", "Name", "Attendance %"])

        for s in students:
            percent = subject_attendance(
                s["student_id"], sub["subject_id"]
            )
            ws.append([
                s["roll_no"],
                s["name"],
                percent
            ])

    conn.close()
