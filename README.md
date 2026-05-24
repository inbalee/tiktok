# TikTok User Lookup UI

A web interface and JSON API to search TikTok profiles, keywords, videos, and comments. Built on top of [TikTok-User-Info-Scraper](https://github.com/N4rr34n6/TikTok-User-Info-Scraper).

## Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5001](http://localhost:5001). API docs: [http://localhost:5001/docs](http://localhost:5001/docs)

## Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Production stack with nginx on port 80:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## EC2 deployment

### 1. Launch an EC2 instance

- AMI: Amazon Linux 2023 or Ubuntu 22.04+
- Instance type: `t3.small` or larger recommended
- Security group inbound rules:
  - `22` SSH (your IP)
  - `80` HTTP (0.0.0.0/0 or your IP)
- Storage: 20 GB+

Optional: paste `deploy/ec2-user-data.sh` into **User data** at launch to install Docker automatically.

### 2. Bootstrap the server

```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_IP
sudo bash deploy/ec2-setup.sh
```

Log out and back in so Docker group membership applies.

### 3. Deploy

**Local (default):**
```bash
bash deploy/deploy.sh
```

**Remote EC2:**
```bash
export EC2_HOST=YOUR_EC2_IP
export SSH_KEY=~/.ssh/your-key.pem
bash deploy/deploy.sh
```

The script rsyncs the project, builds the image, and starts:

- `app` on port 5001 (internal)
- `nginx` on port 80 (public)

### 4. Verify

```bash
curl http://YOUR_EC2_IP/openapi.json
curl "http://YOUR_EC2_IP/api/search?q=dance"
```

Open `http://YOUR_EC2_IP/` in a browser.

## API

All endpoints return JSON:

```json
{ "success": true, "data": { ... } }
```

| Endpoint | Description |
|---|---|
| `GET /api/user/{username}` | User profile |
| `GET /api/search?q=` | Keyword search |
| `GET /api/video/metadata?url=` | Video metadata |
| `GET /api/video/{video_id}/comments` | Video comments |

Swagger UI: `/docs`

## Notes

- Only **public** TikTok accounts can be looked up
- Scraping depends on TikTok's page structure and may break if they change it
- The original CLI scraper is available in the `scraper/` directory

## License

The underlying scraper is licensed under AGPL-3.0. See [scraper/LICENSE](scraper/LICENSE).
