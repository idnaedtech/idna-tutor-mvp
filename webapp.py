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
    use_tls = os.getenv("GRPC_USE_TLS", "0") == "1"
    if not target:
        return {"ok": False, "error": "GRPC_TARGET not set"}

    try:
        if use_tls:
            channel = grpc.secure_channel(target, grpc.ssl_channel_credentials())
        else:
            channel = grpc.insecure_channel(target)

        grpc.channel_ready_future(channel).result(timeout=3)
        return {"ok": True, "target": target, "tls": use_tls}

    except Exception as e:
        return {
            "ok": False,
            "target": target,
            "tls": use_tls,
            "error_type": type(e).__name__,
            "error": repr(e),
        }
