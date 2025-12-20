#!/usr/bin/env python3
"""Start both gRPC and FastAPI servers"""
import subprocess
import time
import sys

# Start gRPC server
grpc_proc = subprocess.Popen([sys.executable, "main.py"])
time.sleep(2)

# Start FastAPI/uvicorn server (blocking)
subprocess.run([sys.executable, "-m", "uvicorn", "webapp:app", "--host", "0.0.0.0", "--port", "5000"])
