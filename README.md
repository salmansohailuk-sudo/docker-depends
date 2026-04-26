# Docker Demo — Python + Nginx + MySQL/RDS

This is a rewrite of the original Java/Spring Boot + PostgreSQL project, converted to:

| Layer    | Original                  | This version              |
|----------|---------------------------|---------------------------|
| Backend  | Java 17 + Spring Boot     | Python 3.12 + Flask       |
| Frontend | Nginx (static files only) | Nginx (static + API proxy)|
| Database | PostgreSQL (Docker)       | MySQL 8 (Docker or AWS RDS)|

---

## Project Structure

```
project-root/
├── docker-compose.yml          ← Orchestrates all three containers
│
├── backend/
│   ├── app.py                  ← Flask application (all API logic)
│   ├── requirements.txt        ← Python dependencies
│   └── backend.Dockerfile      ← Builds the Python container
│
├── frontend/
│   ├── index.html              ← UI
│   ├── script.js               ← Frontend JS (uses /api proxy)
│   ├── style.css               ← Styles
│   ├── status-codes.js         ← HTTP status code labels
│   ├── json2html.min.js        ← JSON-to-HTML renderer
│   ├── nginx.conf              ← Nginx config with /api proxy
│   └── frontend.Dockerfile     ← Builds the Nginx container
│
└── database/
    └── 1_init_db.sql           ← Creates the DB schema (MySQL)
```

---

## Option A — Run Locally with Docker Compose (MySQL container)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Step 1 — Copy frontend assets
Copy the following files from the original project into `frontend/`:
- `style.css`
- `status-codes.js`
- `json2html.min.js`

(These are unchanged from the original — only `script.js` and `index.html` were updated.)

### Step 2 — Start the application

```bash
docker-compose up --build
```

Docker Compose will:
1. Start a **MySQL 8** container and wait until it is healthy
2. Start the **Python/Flask** backend, pointing it at the MySQL container
3. Wait until the Flask `/ping` health check passes
4. Start the **Nginx** frontend

### Step 3 — Access the application
Open [http://localhost](http://localhost) in your browser.

### Step 4 — Shut down

```bash
# Ctrl+C if running in foreground, then:
docker-compose down

# To also wipe the MySQL data volume:
docker-compose down -v
```

---

## Option B — Production: Use AWS RDS (MySQL)

### Step 1 — Create an RDS MySQL instance

1. Go to **AWS Console → RDS → Create database**
2. Choose:
   - Engine: **MySQL 8.x**
   - Template: **Free tier** (or your preferred tier)
   - DB instance identifier: `backend-db`
   - Master username: `user`
   - Master password: `<your-strong-password>`
   - Initial database name: `backend_db`
3. Under **Connectivity**, ensure:
   - The RDS instance is in the same VPC as your ECS/EC2 instances, **or**
   - **Publicly accessible = Yes** (for quick testing only — not recommended for production)
4. Add an inbound rule to the RDS **Security Group** allowing port `3306` from your backend's IP / security group
5. Note your **RDS Endpoint** (e.g., `backend-db.xxxx.us-east-1.rds.amazonaws.com`)

### Step 2 — Initialise the database schema

Connect to your RDS instance and run the init SQL:

```bash
mysql -h <YOUR_RDS_ENDPOINT> -P 3306 -u user -p backend_db < database/1_init_db.sql
```

Or use any MySQL client (TablePlus, DBeaver, MySQL Workbench) to run `1_init_db.sql`.

### Step 3 — Remove the local database service

Edit `docker-compose.yml` and:
- Delete the `backend_database` service block
- Remove `depends_on: backend_database` from `backend_app`
- Update the `backend_app` environment variables:

```yaml
  backend_app:
    build:
      dockerfile: backend.Dockerfile
      context: backend/
    ports:
      - "8080:8080"
    environment:
      DB_HOST:     <YOUR_RDS_ENDPOINT>
      DB_PORT:     "3306"
      DB_NAME:     backend_db
      DB_USER:     user
      DB_PASSWORD: <YOUR_RDS_PASSWORD>
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/ping"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s
```

### Step 4 — Build and run

```bash
docker-compose up --build
```

The backend will connect to RDS. The frontend proxies API calls through Nginx as before.

---

## API Endpoints

All endpoints are available on port `8080` (backend directly) or via the Nginx proxy at `/api/*` on port `80`.

| Method | Path    | Description                  |
|--------|---------|------------------------------|
| GET    | /ping   | Health check — returns `pong`|
| GET    | /user   | List all users               |
| POST   | /user   | Create a new user            |

### Example curl commands

```bash
# Health check
curl http://localhost:8080/ping

# Create a user
curl -X POST http://localhost:8080/user \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Harry Potter","email":"harry@potter.com","phone_number":"4123567890"}'

# List all users
curl http://localhost:8080/user
```

---

## How the Nginx Proxy Works

In the original project, the frontend JavaScript called `http://localhost:8080` directly. This breaks when the backend is on a different host (e.g., ECS or EC2).

In this version, Nginx proxies all `/api/*` requests to the backend container:

```
Browser → GET /api/user → Nginx → http://backend_app:8080/user → Flask
```

This means the frontend JavaScript only ever talks to `/api/...` — no hardcoded backend host/port.

---

## Environment Variables (Backend)

| Variable      | Default     | Description              |
|---------------|-------------|--------------------------|
| `DB_HOST`     | `localhost` | MySQL host               |
| `DB_PORT`     | `3306`      | MySQL port               |
| `DB_NAME`     | `backend_db`| Database name            |
| `DB_USER`     | `user`      | Database username        |
| `DB_PASSWORD` | `password`  | Database password        |

---

## Key Differences from the Original

1. **Python Flask** replaces Java/Spring Boot — no JDK or Gradle needed, much faster build times
2. **MySQL** replaces PostgreSQL — compatible with AWS RDS's most common engine
3. **Nginx proxies `/api`** — frontend JS no longer needs a hardcoded `localhost:8080`
4. **SQLAlchemy** handles the ORM and auto-creates the `user_entity` table on startup
5. **Gunicorn** is used as the production WSGI server instead of Flask's dev server
