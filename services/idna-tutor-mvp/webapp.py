from fastapi import FastAPI
import os
import grpc

app = FastAPI()

print("### RUNNING CLEAN BASELINE WEBAPP ###")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/grpc_ping")
def grpc_ping():
    target = os.getenv("GRPC_TARGET")
    if not target:
        return {"ok": False, "error": "GRPC_TARGET not set"}

    try:
        channel = grpc.insecure_channel(target)
        grpc.channel_ready_future(channel).result(timeout=3)
        return {"ok": True, "target": target}
    except Exception as e:
        return {"ok": False, "target": target, "error": str(e)}
