#!/usr/bin/env python3
"""Push to GitHub using gh CLI credential helper (the working method)."""
import subprocess, os

os.chdir(r"C:\Users\Admin\Desktop\MolingProject")
GIT = r"C:\Program Files\Git\bin\git.exe"

# Ensure credential.helper is set with forward slashes
subprocess.run([GIT, "config", "--global", "credential.helper",
    "!C:/Users/Admin/AppData/Local/Temp/gh_cli/bin/gh.exe auth git-credential"],
    check=True)
print("[OK] credential.helper set")

# Push with GH_TOKEN in environment
env = {**os.environ, "GH_TOKEN": "ghp_BRMjeIQ7iuJqHsempSR6HW7Ky0HZ6p3TQXH"}
print("\nPushing to origin main...\n")

p = subprocess.run(
    [GIT, "push", "origin", "main", "-v"],
    capture_output=True, text=True,
    timeout=180,
    env=env,
)

print("STDOUT:")
print(p.stdout or "(empty)")
print("STDERR:")
print(p.stderr or "(empty)")
print(f"\nReturn code: {p.returncode}")

if p.returncode == 0:
    print("\n✅ Push successful!")
else:
    print(f"\n❌ Push failed (code {p.returncode})")
