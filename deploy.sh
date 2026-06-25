#!/bin/bash
#
# Agent Evaluation Platform - Deploy Script
# ==========================================
#
# Usage:
#   ./deploy.sh              # Full deploy: build + start all services
#   ./deploy.sh build        # Build images only
#   ./deploy.sh stop         # Stop all services
#   ./deploy.sh logs         # Tail logs
#   ./deploy.sh status       # Check service status
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── Check prerequisites ──
check_prereqs() {
    if ! command -v docker &>/dev/null; then
        err "Docker is not installed."
        echo "  Install: https://docs.docker.com/get-docker/"
        exit 1
    fi
    if ! docker compose version &>/dev/null 2>&1; then
        err "Docker Compose V2 is not available."
        echo "  Install: https://docs.docker.com/compose/install/"
        exit 1
    fi
    log "Prerequisites OK: Docker $(docker --version | awk '{print $3}' | tr -d ',')"
}

# ─── Ensure .env exists ──
ensure_env() {
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            warn "Created .env from .env.example"
            warn "Edit .env to set your SECRET_KEY and OPENAI_API_KEY before production use."
        fi
    fi
}

# ─── Generate secure secret key ──
gen_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || \
    openssl rand -base64 48 2>/dev/null || \
    echo "CHANGE-ME-TO-A-RANDOM-STRING"
}

# ═══════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════

cmd_deploy() {
    check_prereqs
    ensure_env

    # Auto-generate SECRET_KEY if still using default
    if grep -q "change-me-to-a-random" .env 2>/dev/null; then
        SECRET=$(gen_secret)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|change-me-to-a-random-64-char-string|$SECRET|" .env
        else
            sed -i "s|change-me-to-a-random-64-char-string|$SECRET|" .env
        fi
        log "Generated secure SECRET_KEY"
    fi

    echo ""
    log "Building and starting all services..."
    echo ""

    docker compose build --parallel
    docker compose up -d

    echo ""
    log "Waiting for services to be healthy..."
    sleep 8

    # Run migrations
    docker compose exec django python manage.py migrate --noinput 2>/dev/null || true

    # Create superuser
    docker compose exec django python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@agent-eval.local', 'admin123')
    print('Created superuser: admin / admin123')
" 2>/dev/null || true

    echo ""
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "  Deployment Complete!"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "  ${BLUE}Frontend:${NC}    http://localhost:3000"
    echo -e "  ${BLUE}Backend:${NC}     http://localhost:8000"
    echo -e "  ${BLUE}MLflow:${NC}      http://localhost:5000"
    echo -e "  ${BLUE}Admin:${NC}       http://localhost:8000/admin/"
    echo ""
    echo -e "  ${YELLOW}Login:${NC}       admin / admin123"
    echo ""
    log "Check logs:  ./deploy.sh logs"
    log "Stop:        ./deploy.sh stop"
    log "Status:      ./deploy.sh status"
    echo ""
}

cmd_build() {
    check_prereqs
    log "Building Docker images..."
    docker compose build --parallel
    log "Build complete."
}

cmd_stop() {
    log "Stopping all services..."
    docker compose down
    log "All services stopped."
}

cmd_logs() {
    docker compose logs -f --tail=50
}

cmd_status() {
    echo ""
    log "Service Status:"
    echo ""
    docker compose ps
    echo ""
}

# ═══════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════

CMD="${1:-deploy}"

case "$CMD" in
    deploy)  cmd_deploy  ;;
    build)   cmd_build   ;;
    stop)    cmd_stop    ;;
    logs)    cmd_logs    ;;
    status)  cmd_status  ;;
    *)
        echo "Agent Evaluation Platform - Deploy Script"
        echo ""
        echo "Usage:"
        echo "  ./deploy.sh          Full deploy (build + start)"
        echo "  ./deploy.sh build    Build images only"
        echo "  ./deploy.sh stop     Stop all services"
        echo "  ./deploy.sh logs     Tail service logs"
        echo "  ./deploy.sh status   Check service status"
        echo ""
        ;;
esac
