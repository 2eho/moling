#!/usr/bin/env python3
import os

base = r"C:\Users\Admin\Desktop\MolingProject\moling-web\src\app"
print("=== app directory contents ===")
for item in os.listdir(base):
    full = os.path.join(base, item)
    print(f"  {'[DIR]' if os.path.isdir(full) else '[FILE]'} {item}")

print("\n=== settings directory contents ===")
settings_dir = os.path.join(base, "settings")
for item in os.listdir(settings_dir):
    full = os.path.join(settings_dir, item)
    print(f"  {'[DIR]' if os.path.isdir(full) else '[FILE]'} {item}")

# Check actual path vs git path
print(f"\n=== Git-aware paths ===")
import subprocess
GIT = r"C:\Program Files\Git\bin\git.exe"
os.chdir(r"C:\Users\Admin\Desktop\MolingProject")

# Get tracked files in settings dir
r = subprocess.run([GIT, "ls-files", "moling-web/src/app/settings/"], capture_output=True, text=True)
tracked = [l.strip() for l in r.stdout.splitlines() if l.strip()]
print(f"Tracked files in settings/: {tracked}")

# Check if there's a .gitignore inside settings
gitignore = os.path.join(settings_dir, ".gitignore")
if os.path.exists(gitignore):
    print(f"\nWARNING: .gitignore exists in settings directory!")
    with open(gitignore) as f:
        print(f.read())
else:
    print(f"\nNo .gitignore in settings directory")

# Check if settings directory itself is ignored
r = subprocess.run([GIT, "check-ignore", "moling-web/src/app/settings"], capture_output=True, text=True)
print(f"Is settings dir ignored? rc={r.returncode} {r.stdout.strip()}")

r = subprocess.run([GIT, "check-ignore", "moling-web/src/app/settings/Settings.module.css"], capture_output=True, text=True)
print(f"Is file ignored? rc={r.returncode} {r.stdout.strip()}")

# Check all gitignore files
r = subprocess.run([GIT, "config", "--get", "core.excludesFile"], capture_output=True, text=True)
print(f"Global excludesFile: {r.stdout.strip()}")

r = subprocess.run([GIT, "ls-files", "--others", "--directory", "moling-web/src/app/"], capture_output=True, text=True)
print(f"\nAll untracked in app/:\n{r.stdout[:500]}")
