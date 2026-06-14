#!/usr/bin/env python3
"""Push to GitHub - method: gh credential helper (the proven working method)."""
import subprocess, os, shutil

os.chdir(r"C:\Users\Admin\Desktop\MolingProject")
GIT = r"C:\Program Files\Git\bin\git.exe"
GH = r"C:\Users\Admin\AppData\Local\Temp\gh_cli\bin\gh.exe"
TOKEN = os.environ.get("GH_TOKEN", "")

# Verify gh.exe exists
if not os.path.exists(GH):
    print(f"[ERROR] gh.exe not found at {GH}")
    # Try to find it
    for root, dirs, files in os.walk(r"C:\Users\Admin\AppData\Local\Temp"):
        for f in files:
            if f == "gh.exe":
                GH = os.path.join(root, f)
                print(f"[FOUND] gh.exe at {GH}")
                break
        if os.path.exists(GH):
            break

# Convert to forward slashes for git config
gh_forward = GH.replace("\\", "/")
cred_helper = f"!{gh_forward} auth git-credential"
print(f"[INFO] credential.helper = {cred_helper}")

# Set it
subprocess.run([GIT, "config", "--global", "credential.helper", cred_helper], check=True)

# Verify
r = subprocess.run([GIT, "config", "--global", "--get", "credential.helper"],
                    capture_output=True, text=True)
print(f"[VERIFY] {r.stdout.strip()}")

# Set GH_TOKEN
env = {**os.environ, "GH_TOKEN": TOKEN, "PATH": os.environ.get("PATH", "") + r";C:\Program Files\Git\bin"}

# Also write hosts.yml for gh CLI
appdata = os.environ.get("APPDATA", r"C:\Users\Admin\AppData\Roaming")
gh_config_dir = os.path.join(appdata, "gh")
os.makedirs(gh_config_dir, exist_ok=True)
hosts_yml = os.path.join(gh_config_dir, "hosts.yml")
with open(hosts_yml, "w") as f:
    f.write(f"github.com:\n  user: 2eho\n  oauth_token: {TOKEN}\n  git_protocol: https\n")
print(f"[OK] Wrote {hosts_yml}")

# Test gh auth status
print("\n[TEST] gh auth status...")
p_test = subprocess.run([GH, "auth", "status", "--hostname", "github.com"],
                        capture_output=True, text=True, env={**env, "PATH": env["PATH"]})
print(f"  stdout: {p_test.stdout.strip()}")
print(f"  stderr: {p_test.stderr.strip()}")
print(f"  exit: {p_test.returncode}")

# Push
print("\n[PUSH] git push origin main...\n")
p = subprocess.run(
    [GIT, "push", "origin", "main", "-v"],
    capture_output=True, text=True, timeout=180, env=env,
)
print("STDERR:")
for line in (p.stderr or "").splitlines():
    print(f"  {line}")
print(f"\nReturn code: {p.returncode}")

if p.returncode == 0:
    print("\n✅ Push successful!")
else:
    print(f"\n❌ Push failed (code {p.returncode})")
