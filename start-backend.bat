@echo off
set DATABASE_URL=sqlite+aiosqlite:///./test.db
set JWT_SECRET=test-secret
set ENVIRONMENT=development
set CORS_ORIGINS=*
set ENABLE_METRICS=false
cd C:\Users\Admin\Desktop\MolingProject\moling-server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level warning
