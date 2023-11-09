#!/bin/bash
exec gunicorn -b :5000 --workers=1 --threads=3 --timeout 120 --log-level=info --access-logfile - --error-logfile - "portal:app"
