import subprocess, os

GIT = r"C:\Program Files\Git\bin\git.exe"
TOKEN = os.environ.get("GH_TOKEN", "")
if not TOKEN:
    print("ERROR: GH_TOKEN not set")
    exit(1)

url = f"https://x-access-token:{TOKEN}@github.com/2eho/moling.git"
subprocess.run([GIT, "remote", "set-url", "origin", url], check=True)
p = subprocess.run([GIT, "push", "origin", "main"], capture_output=True, text=True, timeout=120)
print(p.stdout)
print(p.stderr, file=__import__("sys").stderr)
exit(p.returncode)
