// =============================================================================
// Jenkinsfile — Docker Demo CI/CD Pipeline
//
// WHAT THIS PIPELINE DOES (in order):
//   1. Checkout   — pulls the latest code from your Git repo
//   2. Test       — runs a quick Python syntax/lint check on app.py
//   3. Build      — builds the backend and frontend Docker images locally
//                   on the Jenkins agent (images are built from source, not pulled)
//   4. Push       — logs into DockerHub and pushes both images
//   5. Cleanup    — removes dangling local images to keep the agent disk tidy
//
// BEFORE YOUR FIRST RUN — two things to change:
//   • DOCKERHUB_USER  →  your DockerHub username  (line ~30)
//   • Add a Jenkins credential called "dockerhub-credentials" (see JENKINS_SETUP.md)
// =============================================================================

pipeline {

    // "agent any" — run this pipeline on whichever Jenkins agent is available.
    // The agent machine must have Docker installed and the docker daemon running.
    agent any

    // ── Global environment variables ─────────────────────────────────────────
    // Defined once here and automatically available in every stage as $VAR_NAME
    // in shell steps, or as env.VAR_NAME in Groovy code.
    environment {

        // ── CHANGE THIS to your DockerHub username ────────────────────────
        DOCKERHUB_USER = 'your-dockerhub-username'

        // Image names follow the DockerHub format: <username>/<repo-name>
        // These get pushed to hub.docker.com/r/<DOCKERHUB_USER>/demo-backend etc.
        BACKEND_IMAGE  = "${DOCKERHUB_USER}/demo-backend"
        FRONTEND_IMAGE = "${DOCKERHUB_USER}/demo-frontend"

        // Tag each image with the Jenkins build number (e.g. "7") so every build
        // produces a unique, traceable image. We ALSO tag with "latest" so
        // docker pull always gets the most recent version.
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {

        // ── STAGE 1: CHECKOUT ─────────────────────────────────────────────────
        // Jenkins clones / pulls your Git repository onto the agent workspace.
        // "checkout scm" uses whatever Git repo + branch you configure in the job.
        // After this stage the full project folder is available on the agent.
        stage('Checkout') {
            steps {
                echo '=== Stage 1: Checking out source code ==='
                checkout scm
            }
        }

        // ── STAGE 2: TEST ─────────────────────────────────────────────────────
        // A lightweight Python lint check using pyflakes.
        // pyflakes catches syntax errors and undefined variable names without
        // needing a running database or any other service.
        // Extend this stage later to run pytest, coverage reports, etc.
        // If this step fails, the pipeline stops and stages 3-5 are skipped.
        stage('Test') {
            steps {
                echo '=== Stage 2: Running Python lint check ==='
                sh '''
                    # Install pyflakes onto the agent — fast (~1 second).
                    # "--quiet" suppresses the "already installed" noise on re-runs.
                    pip install --quiet pyflakes

                    # Check app.py for syntax errors and undefined names.
                    # A non-zero exit code fails this stage and halts the pipeline.
                    python -m pyflakes backend/app.py

                    echo "Lint passed — no syntax errors found in app.py"
                '''
            }
        }

        // ── STAGE 3: BUILD ────────────────────────────────────────────────────
        // Builds both Docker images locally on the Jenkins agent using the
        // Dockerfiles that live inside the repo. Nothing is pulled from DockerHub
        // at this point — we are purely building from source.
        //
        // Each image is tagged TWICE in the same docker build command:
        //   :<build-number>  →  unique, immutable tag tied to this exact build
        //   :latest          →  floating tag, always points to the newest build
        stage('Build') {
            steps {
                echo '=== Stage 3: Building Docker images from source ==='
                sh '''
                    echo "--- Building BACKEND image ---"
                    # Flags:
                    #   -f backend/backend.Dockerfile  → which Dockerfile to use
                    #   -t ${BACKEND_IMAGE}:${IMAGE_TAG}  → tag with build number
                    #   -t ${BACKEND_IMAGE}:latest        → also tag as latest
                    #   backend/                          → build context (files Docker can access)
                    docker build \
                        -f backend/backend.Dockerfile \
                        -t ${BACKEND_IMAGE}:${IMAGE_TAG} \
                        -t ${BACKEND_IMAGE}:latest \
                        backend/

                    echo "--- Building FRONTEND image ---"
                    docker build \
                        -f frontend/frontend.Dockerfile \
                        -t ${FRONTEND_IMAGE}:${IMAGE_TAG} \
                        -t ${FRONTEND_IMAGE}:latest \
                        frontend/

                    echo "--- Images now available locally ---"
                    # Filter docker images output to only show ours
                    docker images | grep -E "REPOSITORY|demo-backend|demo-frontend"
                '''
            }
        }

        // ── STAGE 4: PUSH ─────────────────────────────────────────────────────
        // Authenticates with DockerHub using the Jenkins credential you stored,
        // then pushes both images (both tags) to your DockerHub account.
        //
        // "withCredentials" is a Jenkins wrapper that:
        //   1. Looks up the stored secret by its ID ("dockerhub-credentials")
        //   2. Injects it as temporary env vars (DOCKER_USER, DOCKER_PASS)
        //   3. Masks the values in console output so the password is never visible
        //   4. Deletes the env vars after the block exits
        stage('Push') {
            steps {
                echo '=== Stage 4: Pushing images to DockerHub ==='
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials', // ← ID must match what you created in Jenkins
                    usernameVariable: 'DOCKER_USER',        // becomes $DOCKER_USER inside the sh block
                    passwordVariable: 'DOCKER_PASS'         // becomes $DOCKER_PASS inside the sh block
                )]) {
                    sh '''
                        # Log in to DockerHub.
                        # "--password-stdin" reads the password from stdin instead of a CLI arg,
                        # which prevents it appearing in the OS process list or shell history.
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        echo "--- Pushing BACKEND images ---"
                        # Push the build-number tag — gives you an immutable history on DockerHub
                        docker push ${BACKEND_IMAGE}:${IMAGE_TAG}
                        # Push the "latest" tag — makes "docker pull demo-backend" get this build
                        docker push ${BACKEND_IMAGE}:latest

                        echo "--- Pushing FRONTEND images ---"
                        docker push ${FRONTEND_IMAGE}:${IMAGE_TAG}
                        docker push ${FRONTEND_IMAGE}:latest

                        echo "--- All images pushed successfully ---"
                        echo "  DockerHub: hub.docker.com/r/${DOCKERHUB_USER}/demo-backend"
                        echo "  DockerHub: hub.docker.com/r/${DOCKERHUB_USER}/demo-frontend"
                    '''
                }
            }
        }

        // ── STAGE 5: CLEANUP ──────────────────────────────────────────────────
        // Removes "dangling" images — these are intermediate build layers that
        // Docker creates during "docker build" but no longer has a tag pointing
        // to them. They show up as "<none>:<none>" in "docker images".
        // Without pruning, these accumulate and fill up the agent's disk.
        // "|| true" means: even if prune finds nothing to delete, don't fail the stage.
        stage('Cleanup') {
            steps {
                echo '=== Stage 5: Pruning dangling Docker images ==='
                sh '''
                    # "-f" = force (no interactive confirmation prompt)
                    docker image prune -f || true
                    echo "Cleanup complete."
                '''
            }
        }
    }

    // ── Post-build actions ────────────────────────────────────────────────────
    // These blocks run AFTER all stages finish, regardless of success or failure.
    // They are checked in order: success / failure / always.
    post {

        // Runs only when every stage completed with exit code 0.
        success {
            echo "✅ Pipeline #${env.BUILD_NUMBER} succeeded!"
            echo "Images on DockerHub:"
            echo "  ${BACKEND_IMAGE}:${IMAGE_TAG}  and  ${BACKEND_IMAGE}:latest"
            echo "  ${FRONTEND_IMAGE}:${IMAGE_TAG}  and  ${FRONTEND_IMAGE}:latest"
        }

        // Runs only when any stage exited with a non-zero code.
        failure {
            echo "❌ Pipeline #${env.BUILD_NUMBER} failed. Scroll up to find the red stage."
        }

        // Runs unconditionally — good place to log out of Docker so credentials
        // are not left active on the agent between builds.
        always {
            sh 'docker logout || true'
            echo "Docker session closed."
        }
    }
}
