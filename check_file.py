#!/usr/bin/env python3
import subprocess, os
os.chdir(r"C:\Users\Admin\Desktop\MolingProject")
GIT = r"C:\Program Files\Git\bin\git.exe"

# Run git status on the specific file
r = subprocess.run([GIT, "status", "--short", "moling-web/src/app/settings/Settings.module.css"],
                    capture_output=True, text=True)
print(f"status: [{r.stdout.strip()}] [{r.stderr.strip()}]")

# Check if file exists relative to git root
r = subprocess.run([GIT, "ls-files", "--others", "--exclude-standard",
                    "moling-web/src/app/settings/Settings.module.css"],
                    capture_output=True, text=True)
print(f"untracked: [{r.stdout.strip()}]")

# Try to add the file
r = subprocess.run([GIT, "add", "-v", "moling-web/src/app/settings/Settings.module.css"],
                    capture_output=True, text=True)
print(f"add: [{r.stdout.strip()}] [{r.stderr.strip()}] rc={r.returncode}")

# Check status again
r = subprocess.run([GIT, "status", "--short"],
                    capture_output=True, text=True)
print(f"status after add:\n{r.stdout[:200] if r.stdout else '(empty)'}")
