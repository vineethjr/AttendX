# AttendX Frontend Integration Notes

These endpoints are intended for the Vercel frontend (`attendx-future.vercel.app`).

## Environment

- `NEXT_PUBLIC_API_BASE_URL` should point to the Flask backend HTTPS URL.
- Frontend fetch calls must include `credentials: "include"` so the session cookie is sent.

## CORS / Cookies

The backend enables CORS for `https://attendx-future.vercel.app` and sets:

- `SESSION_COOKIE_SAMESITE=None`
- `SESSION_COOKIE_SECURE=True`

If you need local testing, set:

```
SESSION_COOKIE_SECURE=false
ATTENDX_CORS_ORIGINS=http://localhost:3000
```

## API Endpoints

### Auth
- `POST /api/login` → `{ username, password }`
- `POST /api/logout`

### Students
- `GET /api/students`
- `POST /api/students` → `{ roll_no, name, department, semester }`

### Schedule
- `GET /api/schedule?day=Tuesday`
- `POST /api/schedule` → `{ subject_name, day, start_time, end_time, is_free_period }`

### Face Registration
- `POST /api/face-register/capture` → `{ student_id, image }`

### Recognition
- `POST /api/recognize` → `{ schedule_id, image }`

### Warnings
- `GET /api/warnings`

### Messages
- `POST /api/messages` → `{ content }`

### Reports
- `GET /api/reports/export` → downloads Excel file
