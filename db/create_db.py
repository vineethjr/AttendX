import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_utils import get_db_connection

# Step 3: Create SQLite database file
# This connects to 'attendance.db' in the db folder. If the file doesn't exist, SQLite creates it.
conn = get_db_connection()
cursor = conn.cursor()

print("SQLite database file created.")

# Step 4: Create Student table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Student (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department TEXT,
    semester TEXT
)
''')
print("Student table created.")

# Step 5: Create Subject table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Subject (
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name TEXT NOT NULL,
    total_classes INTEGER NOT NULL DEFAULT 0
)
''')

print("Subject table created.")

# Face encoding table (one encoding per student)
cursor.execute('''
CREATE TABLE IF NOT EXISTS StudentFace (
    student_id INTEGER PRIMARY KEY,
    encoding BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Student(student_id)
)
''')

print("StudentFace table created.")


# Step 6: Create Attendance table
# Attendance table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    scan_no INTEGER NOT NULL CHECK (scan_no BETWEEN 1 AND 4),
    status INTEGER NOT NULL CHECK (status IN (0, 1)),
    schedule_id INTEGER,
    FOREIGN KEY (student_id) REFERENCES Student(student_id),
    FOREIGN KEY (subject_id) REFERENCES Subject(subject_id),
    UNIQUE(student_id, subject_id, date, scan_no)
)
''')

print("Attendance table created.")

cursor.execute('''
CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_schedule
ON Attendance(student_id, schedule_id, date)
''')

print("Attendance schedule index created.")

# Class Schedule table
cursor.execute('''
CREATE TABLE IF NOT EXISTS ClassSchedule (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER,
    day TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_free_period INTEGER NOT NULL CHECK (is_free_period IN (0,1)),
    FOREIGN KEY (subject_id) REFERENCES Subject(subject_id)
)
''')

print("ClassSchedule table created.")

# Message table (for classroom display)
cursor.execute('''
CREATE TABLE IF NOT EXISTS Message (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

print("Message table created.")




# Commit and close
conn.commit()
conn.close()

print("Database setup complete.")
