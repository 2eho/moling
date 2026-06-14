#!/usr/bin/env python3
"""Add all relevant files to git staging area."""
import subprocess, os

os.chdir(r"C:\Users\Admin\Desktop\MolingProject")
GIT = r"C:\Program Files\Git\bin\git.exe"

# Core source + config
core = [
    "moling-server/app/",
    "moling-web/src/",
    "docker/",
    ".github/",
    "docker-compose.yml",
    ".env.example",
    "overview.md",
]

# Prototype HTML files
htmls = [
    "002_99fdae6f_moling-import.html",
    "002_c971de65_moling-admin.html",
    "003_1e4d402c_moling-new-project.html",
    "004_f05ef162_moling-projects.html",
    "005_8cb15f06_moling-landing.html",
    "006_aff4bd4f_moling-vaults.html",
    "007_e4390c03_moling-settings.html",
    "008_8e2010d7_moling-workspace.html",
    "010_d04ccd3d_moling-auth.html",
    "011_fcba0216_moling-404.html",
    "013_9f52f376_moling-pricing.html",
    "014_ae2d3222_moling-notifications.html",
]

# Documentation .md files (use wildcard via git)
print("=== Adding core files ===")
for f in core:
    r = subprocess.run([GIT, "add", f], capture_output=True, text=True)
    print(f"  {f}: {r.returncode}")

print("=== Adding HTML prototypes ===")
for f in htmls:
    r = subprocess.run([GIT, "add", f], capture_output=True, text=True)
    print(f"  {f}: {r.returncode}")

print("=== Adding all .md files ===")
r = subprocess.run([GIT, "add", "*.md"], capture_output=True, text=True)
print(f"  *.md: {r.returncode} {r.stderr[:80] if r.stderr else ''}")

print("=== Staged files ===")
r = subprocess.run([GIT, "status", "--short"], capture_output=True, text=True)
for line in r.stdout.splitlines():
    if line.startswith("A ") or line.startswith("M "):
        print(f"  {line}")
