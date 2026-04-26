// ─────────────────────────────────────────────────────────────────────────────
// Jenkinsfile — Docker Demo CI/CD Pipeline
// Builds, tests, and deploys the Python + Nginx + MySQL app via Docker Compose.
//
// Assumptions:
//   • Jenkins agent has Docker + Docker Compose installed
//   • Jenkins agent has SSH access to your deploy server
//   • The following Jenkins credentials are configured:
//       - "dockerhub-credentials"   → Username/Password (DockerHub login)
//       - "deploy-server-ssh"       → SSH private key for the deploy server
//   • Environment variables below are set in Jenkins → Manage Jenkins →
//     Configure System → Global properties → Environment variables
// ─────────────────────────────────────────────────────────────────────────────

pipeline {

    agent any

    // ── Configurable variables ───────────────────────────────────────────────
    environment {
        DOCKERHUB_USER    = 'your-dockerhub-username'       // ← change this
        BACKEND_IMAGE     = "${DOCKERHUB_USER}/demo-backend"
        FRONTEND_IMAGE    = "${DOCKERHUB_USER}/demo-frontend"
        DEPLOY_SERVER     = 'user@your-server-ip'           // ← change this
        DEPLOY_DIR        = '/opt/docker-demo'              // ← change this
        IMAGE_TAG         = "${env.BUILD_NUMBER}"
    }

    stages {

        // ── 1. Checkout ──────────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                echo '--- Checking out source code ---'
                checkout scm
            }
        }

        // ── 2. Lint / Unit Test ──────────────────────────────────────────────
        stage('Test') {
            steps {
                echo '--- Running Python lint check ---'
                sh '''
                    cd backend
                    pip install --quiet pyflakes
                    python -m pyflakes app.py
                '''
            }
        }

        // ── 3. Build Docker Images ───────────────────────────────────────────
        stage('Build') {
            steps {
                echo '--- Building Docker images ---'
                sh '''
                    docker build \
                        -f backend/backend.Dockerfile \
                        -t ${BACKEND_IMAGE}:${IMAGE_TAG} \
                        -t ${BACKEND_IMAGE}:latest \
                        backend/

                    docker build \
                        -f frontend/frontend.Dockerfile \
                        -t ${FRONTEND_IMAGE}:${IMAGE_TAG} \
                        -t ${FRONTEND_IMAGE}:latest \
                        frontend/
                '''
            }
        }

        // ── 4. Push to DockerHub ─────────────────────────────────────────────
        stage('Push') {
            steps {
                echo '--- Pushing images to DockerHub ---'
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        docker push ${BACKEND_IMAGE}:${IMAGE_TAG}
                        docker push ${BACKEND_IMAGE}:latest

                        docker push ${FRONTEND_IMAGE}:${IMAGE_TAG}
                        docker push ${FRONTEND_IMAGE}:latest
                    '''
                }
            }
        }

        // ── 5. Deploy to Server ──────────────────────────────────────────────
        stage('Deploy') {
            steps {
                echo '--- Deploying to server via SSH ---'
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'deploy-server-ssh',
                    keyFileVariable: 'SSH_KEY'
                )]) {
                    sh '''
                        # Copy docker-compose.yml and the database init script to the server
                        scp -i $SSH_KEY -o StrictHostKeyChecking=no \
                            docker-compose.prod.yml \
                            ${DEPLOY_SERVER}:${DEPLOY_DIR}/docker-compose.yml

                        scp -i $SSH_KEY -o StrictHostKeyChecking=no \
                            database/1_init_db.sql \
                            ${DEPLOY_SERVER}:${DEPLOY_DIR}/database/

                        # Pull latest images and restart containers on the server
                        ssh -i $SSH_KEY -o StrictHostKeyChecking=no ${DEPLOY_SERVER} "
                            cd ${DEPLOY_DIR}
                            docker compose pull
                            docker compose up -d --remove-orphans
                            docker image prune -f
                        "
                    '''
                }
            }
        }
    }

    // ── Post-build notifications ─────────────────────────────────────────────
    post {
        success {
            echo "✅ Pipeline succeeded — build #${env.BUILD_NUMBER} deployed."
        }
        failure {
            echo "❌ Pipeline failed — check the logs above."
        }
        always {
            // Clean up local Docker login session
            sh 'docker logout || true'
        }
    }
}
