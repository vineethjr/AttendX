# RUNLOG

Date: 2026-02-03

## Commands Executed

1. `Get-ChildItem -Force` (in `d:\Attendx`)
2. `Get-ChildItem -Force` (in `d:\Attendx\AttendX`)
3. `rg -n "schedule|face|attendance|cursor.execute|fetchone|sqlite" app.py logic templates -S`
4. `Get-Content app.py`
5. `Get-Content templates\schedule.html`
6. `Get-Content templates\face_register.html`
7. `Get-ChildItem -Force ai`
8. `Get-Content ai\register_student.py`
9. `Get-Content ai\face_recognition_live.py`
10. `Get-ChildItem -Force db`
11. `Get-Content db\create_db.py`
12. `Get-Content db\insert_sample_data.py`
13. `Get-Content logic\mark_attendance.py`
14. `Get-ChildItem -Force static`
15. `Get-ChildItem -Force static\js`
16. `Get-Content static\js\ui.js`
17. `Get-Content static\css\style.css`
18. `Get-Content requirements.txt`
19. `Get-ChildItem -Force templates`
20. `Get-Content logic\attendance_summary.py`
21. `Get-Content README.md`
22. `Get-Content tests\test_sample.py`
23. `git status -sb`

### Environment Setup

24. `python -m venv .venv`
25. `.venv\Scripts\python -m pip install -r requirements.txt`
    - First attempt timed out; second attempt succeeded.
26. `.venv\Scripts\python db\create_db.py`
    - Success: tables created.
27. `.venv\Scripts\python db\insert_sample_data.py`
    - Failed: `sqlite3.OperationalError: database is locked`
28. `.venv\Scripts\python app.py`
    - Timed out (server process was running; no console output captured).

### Reproduction Attempts

29. PowerShell heredoc attempt for a Flask test-client reproduction (failed due to PowerShell parsing).
30. Test-client reproduction via stdin:
    - Result: `sqlite3.OperationalError: database is locked`
31. `Get-Process | Where-Object { $_.ProcessName -like 'python*' }`
32. `Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*.exe' } | Select-Object ProcessId, CommandLine`
    - Observed multiple running `python app.py` processes, likely holding DB locks.

### Post-change Dependency Update

33. `.venv\Scripts\python -m pip install -r requirements.txt`
    - Installed `Flask-WTF` and `python-dotenv`.

## Notes

- The original `/schedule` TypeError could not be reproduced during this session because the SQLite DB was locked by multiple running `app.py` processes.
- The root cause was identified in code as indexing the result of `fetchone()` without a `None` check after an ignored `INSERT` into `Subject` (due to `total_classes` NOT NULL).
- Pre-fix stack frame (from code path and screenshot): `app.py` `schedule()` line with `subject_id = cursor.execute(...).fetchone()["subject_id"]`.
