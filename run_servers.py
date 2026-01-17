#!/usr/bin/env python3
"""Start both gRPC and FastAPI servers for Railway deployment with graceful shutdown."""
import subprocess
import signal
import time
import sys
import os
import atexit

# Get port from Railway environment (defaults to 8000 for local dev)
web_port = os.environ.get("PORT", "8000")
grpc_port = os.environ.get("GRPC_PORT", "50051")

# Set GRPC_TARGET for webapp to connect to gRPC server
os.environ["GRPC_TARGET"] = f"localhost:{grpc_port}"

# Track child processes for cleanup
grpc_proc = None
web_proc = None
_shutting_down = False


def cleanup_children():
    """Terminate child processes gracefully."""
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True

    print("[run_servers] Cleaning up child processes...", flush=True)

    for name, proc in [("gRPC", grpc_proc), ("Web", web_proc)]:
        if proc and proc.poll() is None:
            print(f"[run_servers] Sending SIGTERM to {name} (pid={proc.pid})...", flush=True)
            try:
                proc.terminate()
            except Exception as e:
                print(f"[run_servers] Error terminating {name}: {e}", flush=True)

    # Wait for graceful shutdown (up to 15 seconds total)
    deadline = time.time() + 15
    for name, proc in [("gRPC", grpc_proc), ("Web", web_proc)]:
        if proc and proc.poll() is None:
            remaining = max(0, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
                print(f"[run_servers] {name} exited gracefully", flush=True)
            except subprocess.TimeoutExpired:
                print(f"[run_servers] {name} did not exit, sending SIGKILL...", flush=True)
                proc.kill()
                proc.wait()

    print("[run_servers] Cleanup complete", flush=True)


def signal_handler(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    sig_name = signal.Signals(signum).name
    print(f"\n[run_servers] Received {sig_name}, initiating shutdown...", flush=True)
    cleanup_children()
    sys.exit(0)


# Register cleanup handlers
atexit.register(cleanup_children)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Start gRPC server (from services/idna-grpc/)
grpc_env = os.environ.copy()
grpc_env["GRPC_PORT"] = grpc_port
grpc_proc = subprocess.Popen(
    [sys.executable, "services/idna-grpc/main.py"],
    env=grpc_env
)
print(f"[run_servers] gRPC server starting on port {grpc_port} (pid={grpc_proc.pid})...", flush=True)

# Wait for gRPC to be ready (check every 0.5s, up to 10s)
for i in range(20):
    time.sleep(0.5)
    if grpc_proc.poll() is not None:
        print(f"[run_servers] ERROR: gRPC server exited with code {grpc_proc.returncode}", flush=True)
        sys.exit(1)
    # Could add gRPC health check here in future
    if i >= 5:  # After 2.5s, assume ready
        break

print(f"[run_servers] gRPC server ready", flush=True)
print(f"[run_servers] Starting FastAPI on port {web_port}...", flush=True)

# Start FastAPI/uvicorn server
web_proc = subprocess.Popen([
    sys.executable, "-m", "uvicorn",
    "webapp:app",
    "--host", "0.0.0.0",
    "--port", web_port
])

print(f"[run_servers] FastAPI starting (pid={web_proc.pid})...", flush=True)

# Monitor both processes
try:
    while True:
        # Check gRPC
        if grpc_proc.poll() is not None:
            print(f"[run_servers] gRPC server exited with code {grpc_proc.returncode}", flush=True)
            cleanup_children()
            sys.exit(grpc_proc.returncode or 1)

        # Check Web
        if web_proc.poll() is not None:
            print(f"[run_servers] Web server exited with code {web_proc.returncode}", flush=True)
            cleanup_children()
            sys.exit(web_proc.returncode or 1)

        time.sleep(1)

except KeyboardInterrupt:
    print("\n[run_servers] KeyboardInterrupt received", flush=True)
    cleanup_children()
    sys.exit(0)
