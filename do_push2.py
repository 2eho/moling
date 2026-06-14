#!/usr/bin/env python3
"""Push to GitHub - method: write .git-credentials file then push."""
import subprocess, os

os.chdir(r"C:\Users\Admin\Desktop\MolingProject")
GIT = r"C:\Program Files\Git\bin\git.exe"
TOKEN = os.environ.get("GH_TOKEN", "")

# Write .git-credentials with token
cred_path = os.path.expanduser(r"~\.git-credentials")
with open(cred_path, "w", encoding="utf-8") as f:
    f.write(f"https://oauth2:{TOKEN}@github.com\n")
print(f"[OK] Wrote {cred_path}")

# Set credential.helper to store
subprocess.run([GIT, "config", "--global", "credential.helper", "store"], check=True)
print("[OK] credential.helper = store")

# Verify remote URL is HTTPS
r = subprocess.run([GIT, "remote", "get-url", "origin"], capture_output=True, text=True)
print(f"[INFO] Remote URL: {r.stdout.strip()}")

# Push
print("\nPushing to origin main...\n")
p = subprocess.run(
    [GIT, "push", "origin", "main", "-v"],
    capture_output=True, text=True, timeout=180,
)

print("STDERR:")
print(p.stderr or "(empty)")
print(f"\nReturn code: {p.returncode}")

if p.returncode == 0:
    print("\n✅ Push successful!")
else:
    print(f"\n❌ Push failed (code {p.returncode})")
    # Try with token in URL directly
    print("\n[RETRY] Trying with token in URL directly...")
    url = f"https://oauth2:{TOKEN}@github.com/2eho/moling.git"
    p2 = subprocess.run(
        [GIT, "push", url, "main", "-v"],
        capture_output=True, text=True, timeout=180,
    )
    print("STDERR:")
    print(p2.stderr or "(empty)")
    print(f"\nReturn code: {p2.returncode}")
