#!/bin/bash
# Start both gRPC and FastAPI servers
python main.py &
sleep 2
python -m uvicorn webapp:app --host 0.0.0.0 --port 5000
