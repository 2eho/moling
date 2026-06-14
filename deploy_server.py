#!/usr/bin/env python3
"""SSH into server and deploy moling project."""
import paramiko, os, sys

IP   = "124.222.163.79"
USER = "root"
PWD  = "tyc13360956216.."

print(f"[CONNECT] SSH {USER}@{IP}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(IP, username=USER, password=PWD,
             timeout=15, allow_agent=False, look_for_keys=False)
print("✅  Connected!\n")

def run(cmd, desc, timeout=60):
    print(f"[STEP] {desc}")
    print(f"  $ {cmd}")
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        rc  = stdout.channel.recv_exit_status()
        if out.strip():
            for line in out.strip().splitlines():
                print(f"  {line}")
        if err.strip() and rc != 0:
            for line in err.strip().splitlines():
                print(f"  [ERR] {line}")
        if rc != 0:
            print(f"  ⚠️  exit {rc}")
        else:
            print(f"  ✅ Done")
    except Exception as e:
        print(f"  ❌ {e}")
    print()

# 1. Docker
run("which docker || (curl -fsSL https://get.docker.com | bash && systemctl enable docker && systemctl start docker)",
    "Check/Install Docker", 180)

# 2. docker compose
run("docker compose version || apt update && apt install -y docker-compose-plugin",
    "Check/Install docker-compose", 120)

# 3. Clone
run("cd ~ && [ -d moling ] || git clone https://github.com/2eho/moling.git",
    "Clone repo", 60)

# 4. Pull
run("cd ~/moling && git pull",
    "Pull latest", 30)

# 5. .env
run("cd ~/moling && [ -f moling-server/.env ] || cp moling-server/.env.example moling-server/.env",
    "Create .env", 10)

# 6. Start
run("cd ~/moling && docker compose up -d",
    "Start all services", 180)

# 7. Status
run("cd ~/moling && docker compose ps",
    "Service status", 15)

# 8. Recent logs
run("cd ~/moling && docker compose logs --tail=30 2>&1 | head -50",
    "Recent logs", 15)

print("="*50)
print("✅  Deployment complete!")
print("="*50)
print(f"\n🌐  Frontend:  http://{IP}:3000")
print(f"📚  API docs: http://{IP}:8000/docs")
print(f"🔧  Admin:   http://{IP}:3000/admin")
print(f"\nSSH: ssh root@{IP}")
print(f"Password: {PWD}")

ssh.close()
