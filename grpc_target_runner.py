import os
import threading
from fastapi import FastAPI
import uvicorn

from main import serve  # your gRPC serve() in main.py

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"ok": True}

def run_grpc():
    # Run gRPC on a fixed internal port
    # IMPORTANT: main.py must bind to GRPC_PORT, not PORT (we change that next)
    serve()

def run_http():
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    t = threading.Thread(target=run_grpc, daemon=True)
    t.start()
    run_http()
