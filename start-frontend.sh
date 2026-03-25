#!/bin/bash
cd /Users/gopalpatwa/opt/m365-data-protection/frontend
exec npx vite --port "${PORT:-5173}"
