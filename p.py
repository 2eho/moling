#!/usr/bin/env python3
import subprocess, os
os.chdir(r"C:\Users\Admin\Desktop\MolingProject")
env = {**os.environ, "GH_TOKEN": os.environ.get("GH_TOKEN", "")}
p = subprocess.run([r"C:\Program Files\Git\bin\git.exe", "push", "origin", "main"],
                    capture_output=True, timeout=180, env=env)
o = p.stdout.decode("utf-8", errors="replace")
e = p.stderr.decode("utf-8", errors="replace")
print(o + e)
print(f"EXIT: {p.returncode}")
