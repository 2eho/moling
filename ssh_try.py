#!/usr/bin/env python3
"""SSH into server - try all credential combinations."""
import paramiko, sys

IP = "124.222.163.79"

# All possible combinations
creds = [
    ("root",      "tyc13360956216.."),
    ("tyc",       "13360956216.."),
    ("opencloud", "tyc13360956216.."),
    ("root",      "13360956216.."),
    ("tyc",       "tyc13360956216.."),
]

for user, pwd in creds:
    print(f"[TRY] user={user}, pwd='{pwd}' ...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(IP, username=user, password=pwd, timeout=10,
                    allow_agent=False, look_for_keys=False)
        print(f"  ✅ SUCCESS! user={user}, pwd='{pwd}'")
        stdin, stdout, stderr = ssh.exec_command("whoami && hostname")
        print(f"  Host: {stdout.read().decode().strip()}")
        ssh.close()
        break
    except Exception as e:
        print(f"  ❌ {e}")
else:
    print("\n❌ All combinations failed. Please check credentials.")
    sys.exit(1)
