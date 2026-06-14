#!/usr/bin/env python3
import paramiko, os

IP = "124.222.163.79"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(IP, username="root", password=os.environ.get("SERVER_PWD", ""), timeout=15)

cmds = [
    "cd /opt/moling && git status",
    "cd /opt/moling && git log --oneline -3",
    "cd /opt/moling && GIT_TRACE=1 git pull origin main 2>&1 || echo '---FALLBACK---' && git fetch origin main && git log --oneline HEAD..origin/main",
]

for cmd in cmds:
    print(f"$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out)
    if err.strip(): print(f"[ERR] {err}")

ssh.close()
