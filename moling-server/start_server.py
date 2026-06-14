"""start_server.py — 启动 uvicorn 并将日志写入文件供调试"""
import sys, os, subprocess, pathlib

log_dir = pathlib.Path("C:/Users/Admin/AppData/Local/Temp")
out_file = log_dir / "uvicorn_out.log"
err_file = log_dir / "uvicorn_err.log"

print(f"Starting server... stdout→{out_file}  stderr→{err_file}")

with open(out_file, "w") as fout, open(err_file, "w") as ferr:
    proc = subprocess.Popen(
        [
            "venv/Scripts/python.exe",
            "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8001",
            "--log-level", "info",
        ],
        cwd="C:/Users/Admin/Desktop/MolingProject/moling-server",
        stdout=fout,
        stderr=ferr,
    )
    print(f"Server PID: {proc.pid}")
    print(f"Waiting 8s for startup...")
    import time; time.sleep(8)

    # Check if still running
    ret = proc.poll()
    if ret is not None:
        print(f"Server exited with code {ret}")
    else:
        print("Server is running.")
