#!/usr/bin/env python3
"""SSH into server and deploy moling project."""
import paramiko, os, sys

IP = "124.222.163.79"
# Try both possible username/password combinations
creds = [
    ("opencloud", "tyc13360956216.."),
    ("tyc", "13360956216.."),
    ("root", "tyc13360956216.."),
]

for user, pwd in creds:
    print(f"\n[TRY] user={user}, pwd={pwd}")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(IP, username=user, password=pwd, timeout=10)
        print(f"✅ Connected as {user}!")
        
        # Run a test command
        stdin, stdout, stderr = ssh.exec_command("whoami && pwd")
        print(stdout.read().decode())
        ssh.close()
        break
    except Exception as e:
        print(f"❌ Failed: {e}")
else:
    print("\n❌ All credentials failed. Please check username/password.")
    sys.exit(1)
