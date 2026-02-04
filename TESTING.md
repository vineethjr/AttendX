# Testing Guide

## Manual Checklist

1. Create or activate a virtual environment:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
2. Install dependencies:
   - `.venv\Scripts\python -m pip install -r requirements.txt`
3. Initialize the database:
   - `.venv\Scripts\python db\create_db.py`
   - `.venv\Scripts\python db\insert_sample_data.py`
4. Run the app:
   - `.venv\Scripts\python app.py`
5. Login with `admin` / `admin123`.
6. Register a student face:
   - Go to `/face-register`
   - Start camera and click **Capture and Register**
7. Create a schedule entry for today at `/schedule`.
8. Click **Start Camera** on a schedule row and verify:
   - Video opens in a modal
   - Recognized students are listed
   - Attendance is recorded in the DB

## DB Verification

Use SQLite to confirm attendance rows:

```sql
SELECT * FROM Attendance ORDER BY attendance_id DESC LIMIT 5;
```

## API Smoke Tests (Browser Session Required)

These endpoints require an admin session cookie from the browser.

```bash
curl -X POST http://127.0.0.1:5000/face-register/capture \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<YOUR_SESSION_COOKIE>" \
  -d '{"student_id":1,"image":"data:image/jpeg;base64,..."}'

curl -X POST http://127.0.0.1:5000/recognize \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<YOUR_SESSION_COOKIE>" \
  -d '{"schedule_id":1,"image":"data:image/jpeg;base64,..."}'
```
