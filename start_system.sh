#!/bin/bash

# Start the FastAPI Backend
echo "Starting Backend..."
cd ~/Thesis_RSS/server
source .venv/bin/activate
# Run uvicorn in the background
uvicorn app.main:app --reload --port 8000 & 
BACKEND_PID=$!

# Wait a moment for the ML model and SQLite to initialize
sleep 3

# Start the React Frontend
echo "Starting Frontend..."
cd ~/Thesis_RSS/client
npm run dev &
FRONTEND_PID=$!

# Keep the script running to manage both processes
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
