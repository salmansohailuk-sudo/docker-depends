# Jenkins CI/CD Setup Guide

## What the pipeline does

```
Git push
  │
  ├─ [1] Checkout   pulls latest code from Git
  ├─ [2] Test       pyflakes lint check on app.py
  ├─ [3] Build      docker build backend + frontend images from source
  ├─ [4] Push       docker push both images to DockerHub (:<build#> and :latest)
  └─ [5] Cleanup    docker image prune (keeps agent disk tidy)
```

Images are built fresh from the repo on every run — nothing is pulled from DockerHub during the build.

---

## Prerequisites

- Jenkins server with Docker installed on the same machine (or agent)
- A [DockerHub](https://hub.docker.com) account
- Your project in a Git repository (GitHub, GitLab, Bitbucket, etc.)

---

## Step 1 — Install Jenkins

### Option A — Docker (quickest way to get started)

```bash
docker run -d \
  --name jenkins \
  -p 8888:8080 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
```

> Mounting `/var/run/docker.sock` lets Jenkins run Docker commands on the host machine.

Get the first-time admin password:

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open **http://localhost:8888**, paste the password, and follow the setup wizard.

### Option B — Install directly on Ubuntu/Debian

```bash
sudo apt update && sudo apt install -y openjdk-17-jdk

curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
  | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null

echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/" \
  | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

sudo apt update && sudo apt install -y jenkins
sudo systemctl start jenkins

# Add Jenkins to the docker group so it can run docker commands
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

---

## Step 2 — Install Jenkins Plugins

Go to **Manage Jenkins → Plugins → Available plugins** and install:

| Plugin | Why |
|---|---|
| Pipeline | Reads the Jenkinsfile |
| Git | Clones your repository |
| Docker Pipeline | `docker build` / `docker push` steps |
| SSH Agent | SSH into servers (optional, not used in this pipeline) |
| Credentials Binding | Injects secrets safely into shell steps |

Click **Install** then restart Jenkins.

---

## Step 3 — Add Your DockerHub Credential

Go to **Manage Jenkins → Credentials → System → Global credentials → Add Credential**

| Field | Value |
|---|---|
| Kind | Username with password |
| Username | your DockerHub username |
| Password | your DockerHub password or Access Token |
| ID | `dockerhub-credentials` ← must match exactly |

> **Tip:** Use a DockerHub Access Token instead of your real password:
> DockerHub → Account Settings → Security → New Access Token

---

## Step 4 — Update the Jenkinsfile

Open `Jenkinsfile` and change **one line**:

```groovy
DOCKERHUB_USER = 'your-dockerhub-username'   // ← put your actual username here
```

That's it. The image names (`demo-backend`, `demo-frontend`) and everything else
are built from that one variable.

---

## Step 5 — Create the Pipeline Job in Jenkins

1. Click **New Item**
2. Name it (e.g. `docker-demo`) → select **Pipeline** → click **OK**
3. Scroll to the **Pipeline** section at the bottom:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: your repo URL
   - Branch Specifier: `*/main`  (or `*/master`)
   - Script Path: `Jenkinsfile`
4. Click **Save**

---

## Step 6 — Run It

Click **Build Now** on the job page.

Watch the **Stage View** — each box turns green on success, red on failure.
Click any stage box to see its console output.

On success your images will be on DockerHub:

```
hub.docker.com/r/<your-username>/demo-backend
hub.docker.com/r/<your-username>/demo-frontend
```

---

## Step 7 (Optional) — Auto-trigger on Git Push

### GitHub webhook

1. In your GitHub repo: **Settings → Webhooks → Add webhook**
   - Payload URL: `http://<your-jenkins-host>:8888/github-webhook/`
   - Content type: `application/json`
   - Events: **Just the push event**
2. In the Jenkins job: **Configure → Build Triggers** → tick **GitHub hook trigger for GITScm polling**

Now every `git push` to `main` automatically kicks off the pipeline.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `docker: command not found` | Docker isn't installed on the Jenkins agent, or Jenkins user isn't in the `docker` group: `sudo usermod -aG docker jenkins && sudo systemctl restart jenkins` |
| `unauthorized` on docker push | The credential ID in Jenkins doesn't match `dockerhub-credentials` in the Jenkinsfile |
| `pyflakes: command not found` | The Test stage installs it with pip — make sure `pip` / Python 3 is on the agent |
| Stage View not showing | Install the **Pipeline: Stage View** plugin |
