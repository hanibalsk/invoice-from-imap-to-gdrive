#!/bin/bash

# Run the server status script in the background
python /app/run.py &

# Run the server api
gunicorn -w 4 -b 0.0.0.0:7667 --timeout 400 "api:app" &

# Wait for all scripts to complete
wait