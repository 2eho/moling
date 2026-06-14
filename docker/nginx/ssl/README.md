# SSL 证书目录

## 生产部署前需要放置以下 SSL 证书文件到此目录

### 必需文件

| 文件名 | 说明 |
|--------|------|
| `fullchain.pem` | 完整的 SSL 证书链文件（包含中间证书） |
| `privkey.pem` | SSL 证书私钥文件（请妥善保管，切勿泄露） |

### 获取证书

**方式一：Let's Encrypt（免费推荐）**
```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 申请证书（替换为实际域名）
sudo certbot --nginx -d yourdomain.com

# 证书文件位于 /etc/letsencrypt/live/yourdomain.com/
# 将 fullchain.pem 和 privkey.pem 复制到此目录
```

**方式二：商业 SSL 证书**
- 从证书提供商（如 DigiCert、GlobalSign、阿里云等）购买
- 下载 Nginx 格式的证书文件
- 将证书文件和私钥文件放到此目录

### 文件权限

确保私钥文件权限正确：
```bash
chmod 600 privkey.pem
```

### 验证配置

放置证书后，在 `docker/nginx/nginx.conf` 中取消 HTTPS 部分的注释，然后验证：
```bash
docker-compose -f docker/docker-compose.yml config
docker-compose exec frontend nginx -t
```

---

**最后更新：** 2026-06-15
