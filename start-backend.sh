#!/bin/bash
cd /Users/gopalpatwa/opt/m365-data-protection/backend
exec /Users/gopalpatwa/opt/m365-data-protection/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
