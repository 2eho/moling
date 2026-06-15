# 墨灵部署指南

## 首次部署

```bash
# 1. 将 Nginx 配置复制到系统目录
sudo cp deploy/nginx/moling.conf /etc/nginx/conf.d/
sudo nginx -s reload

# 2. 构建并启动所有服务
docker compose up -d --build

# 3. 验证
curl http://localhost:8000/api/v1/health
```

## 更新部署

```bash
git pull origin main

# 如果 Nginx 配置有更新
sudo cp deploy/nginx/moling.conf /etc/nginx/conf.d/
sudo nginx -s reload

# 重新构建并启动
docker compose up -d --build
```
