# Jenkins CI/CD Pipeline — Setup Guide

This guide walks you through setting up Jenkins to automatically build, push,
and deploy the Docker Demo app every time you push to your Git repository.

---

## What the Pipeline Does

```
Git Push
   │
   ▼
[1] Checkout     — pulls your source code
[2] Test         — runs a Python lint check on app.py
[3] Build        — builds backend and frontend Docker images
[4] Push         — pushes images to DockerHub (tagged with build number + "latest")
[5] Deploy       — SSHs into your server, pulls new images, restarts containers
```

---

## Prerequisites

| What                      | Where to get it                                      |
|---------------------------|------------------------------------------------------|
| Jenkins server            | Your own server, EC2, or [jenkins.io](https://www.jenkins.io/doc/book/installing/) |
| Docker + Docker Compose   | Installed on the Jenkins agent machine               |
| DockerHub account         | [hub.docker.com](https://hub.docker.com)             |
| Deploy server             | Any Linux VM / EC2 with Docker + Docker Compose      |
| Git repository            | GitHub, GitLab, Bitbucket, etc.                      |

---

## Step 1 — Install Jenkins

### Option A — Docker (quickest)
```bash
docker run -d \
  --name jenkins \
  -p 8888:8080 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
```
Mounting `/var/run/docker.sock` lets Jenkins run Docker commands on your host.

Open [http://localhost:8888](http://localhost:8888), retrieve the initial admin password:
```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### Option B — Linux server (apt)
```bash
sudo apt update && sudo apt install -y openjdk-17-jdk
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | sudo tee \
  /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/ | sudo tee \
  /etc/apt/sources.list.d/jenkins.list > /dev/null
sudo apt update && sudo apt install -y jenkins
sudo systemctl start jenkins
```

---

## Step 2 — Install Required Jenkins Plugins

Go to **Manage Jenkins → Plugins → Available plugins** and install:

- ✅ **Pipeline** (usually pre-installed)
- ✅ **Git**
- ✅ **Docker Pipeline**
- ✅ **SSH Agent**
- ✅ **Credentials Binding**

Click **Install without restart**, then restart Jenkins.

---

## Step 3 — Add Credentials

Go to **Manage Jenkins → Credentials → System → Global credentials → Add Credential**

### Credential 1 — DockerHub login
| Field          | Value                         |
|----------------|-------------------------------|
| Kind           | Username with password        |
| Username       | your DockerHub username        |
| Password       | your DockerHub password/token  |
| ID             | `dockerhub-credentials`       |

> **Tip**: Use a DockerHub **Access Token** instead of your password:
> DockerHub → Account Settings → Security → New Access Token

### Credential 2 — Deploy server SSH key
| Field          | Value                              |
|----------------|------------------------------------|
| Kind           | SSH Username with private key      |
| ID             | `deploy-server-ssh`                |
| Username       | The SSH user on your deploy server |
| Private Key    | Paste your private key (PEM format)|

If you don't have an SSH key pair yet:
```bash
ssh-keygen -t ed25519 -C "jenkins-deploy"
# Copy public key to your deploy server:
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@your-server-ip
```

---

## Step 4 — Prepare Your Deploy Server

SSH into your deploy server and run:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install -y docker-compose-plugin

# Create the app directory
sudo mkdir -p /opt/docker-demo/database
sudo chown -R $USER:$USER /opt/docker-demo
```

---

## Step 5 — Update the Jenkinsfile

Open `Jenkinsfile` and set these two values:

```groovy
DOCKERHUB_USER = 'your-dockerhub-username'   // ← your DockerHub username
DEPLOY_SERVER  = 'user@your-server-ip'        // ← SSH target (user@host)
DEPLOY_DIR     = '/opt/docker-demo'           // ← directory on the server
```

Also update `docker-compose.prod.yml`:
```yaml
image: your-dockerhub-username/demo-backend:latest
image: your-dockerhub-username/demo-frontend:latest
DB_HOST: YOUR_RDS_ENDPOINT
DB_PASSWORD: YOUR_RDS_PASSWORD
```

---

## Step 6 — Create the Jenkins Pipeline Job

1. Click **New Item**
2. Enter a name (e.g., `docker-demo`)
3. Select **Pipeline** → click **OK**
4. Scroll to **Pipeline** section:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: your repo URL (e.g., `https://github.com/you/docker-demo.git`)
   - Branch: `*/main` (or `*/master`)
   - Script Path: `Jenkinsfile`
5. Click **Save**

---

## Step 7 — Add a Webhook (Auto-trigger on Push)

### GitHub
1. Go to your repo → **Settings → Webhooks → Add webhook**
2. Payload URL: `http://YOUR_JENKINS_URL:8888/github-webhook/`
3. Content type: `application/json`
4. Events: **Just the push event**
5. Click **Add webhook**

In Jenkins, under the job → **Configure → Build Triggers**, check:
**GitHub hook trigger for GITScm polling**

### GitLab / Bitbucket
Similar — use the Jenkins URL with `/gitlab-webhook/plugin` or the Bitbucket plugin.

---

## Step 8 — Run the Pipeline

Click **Build Now** on your pipeline job. Watch the stages execute in the **Stage View**.

On success, your app is live at `http://your-server-ip`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker: command not found` on Jenkins agent | Install Docker on the agent; add Jenkins user to `docker` group: `sudo usermod -aG docker jenkins` |
| `Permission denied` pushing to DockerHub | Check the `dockerhub-credentials` ID matches exactly in Jenkinsfile |
| SSH deploy step fails | Verify the public key is in `~/.ssh/authorized_keys` on the deploy server |
| Backend can't reach RDS | Check RDS security group allows port 3306 from the server's IP |
| `pyflakes` not found | The test stage installs it on the fly; ensure `pip` is available on the agent |

---

## Pipeline Summary (one-pager)

```
Repo push
    │
    ▼
Jenkins picks up change (webhook)
    │
    ├─[Test]──── pyflakes lint on app.py
    │
    ├─[Build]─── docker build backend → demo-backend:42 + :latest
    │            docker build frontend → demo-frontend:42 + :latest
    │
    ├─[Push]──── docker push to DockerHub (both images, both tags)
    │
    └─[Deploy]── scp docker-compose.prod.yml to server
                 ssh → docker compose pull + up -d
                 Old containers replaced, zero manual steps needed
```
