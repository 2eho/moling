#!/usr/bin/env python3
"""Push to GitHub - handles encoding errors properly."""
import subprocess, os

os.chdir(r"C:\Users\Admin\Desktop\MolingProject")
GIT = r"C:\Program Files\Git\bin\git.exe"
TOKEN = os.environ.get("GH_TOKEN", "")

# Push with GH_TOKEN
env = {**os.environ, "GH_TOKEN": TOKEN}
p = subprocess.run([GIT, "push", "origin", "main"],
                    capture_output=True, timeout=180, env=env)

# Decode with errors='replace' to handle non-UTF8 chars
stdout = p.stdout.decode("utf-8", errors="replace")
stderr = p.stderr.decode("utf-8", errors="replace")

print("STDOUT:")
print(stdout or "(empty)")
print("STDERR:")
print(stderr or "(empty)")
print(f"\nReturn code: {p.returncode}")

if p.returncode == 0:
    print("\n✅ Push successful!")
else:
    print(f"\n❌ Push failed (code {p.returncode})")
