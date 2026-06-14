#!/usr/bin/env python3
"""Push to GitHub. Exact same method as last successful push."""
import subprocess, os

os.chdir(r"C:\Users\Admin\Desktop\MolingProject")
GIT = r"C:\Program Files\Git\bin\git.exe"
GH = r"C:\Users\Admin\AppData\Local\Temp\gh_cli\bin\gh.exe"
TOKEN = os.environ.get("GH_TOKEN", "")

# 1. credential helper with forward slashes
subprocess.run([GIT, "config", "--global", "credential.helper",
    "!C:/Users/Admin/AppData/Local/Temp/gh_cli/bin/gh.exe auth git-credential"],
    check=True)

# 2. Write hosts.yml
appdata = os.environ.get("APPDATA", r"C:\Users\Admin\AppData\Roaming")
os.makedirs(os.path.join(appdata, "gh"), exist_ok=True)
with open(os.path.join(appdata, "gh", "hosts.yml"), "w") as f:
    f.write(f"github.com:\n  user: 2eho\n  oauth_token: {TOKEN}\n  git_protocol: https\n")

# 3. HTTPS remote
subprocess.run([GIT, "remote", "set-url", "origin", "https://github.com/2eho/moling.git"], check=True)

# 4. Push
env = {**os.environ, "GH_TOKEN": TOKEN, "PATH": os.environ.get("PATH","") + r";C:\Program Files\Git\bin"}
p = subprocess.run([GIT, "push", "origin", "main"], capture_output=True, text=True, timeout=180, env=env)

print("STDERR:")
print(p.stderr or "(empty)")
print(f"\nReturn code: {p.returncode}")

if p.returncode == 0:
    print("\n✅ Push successful!")
else:
    print(f"\n❌ Push failed (code {p.returncode})")
