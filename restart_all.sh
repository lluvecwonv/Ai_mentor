#!/usr/bin/env bash
set -euo pipefail

# AiMentor_edit 시스템 재시작 스크립트 (간소화 버전)
# Usage: ./restart_all.sh [--clean] [--rebuild] [--logs]
#   --clean     기존 컨테이너와 볼륨 정리 후 재시작
#   --rebuild   이미지 재빌드 후 시작
#   --logs      실행 후 로그 표시

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Docker Compose 명령어 확인
get_compose_cmd() {
    if command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    elif docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    else
        log_error "Docker Compose를 찾을 수 없습니다."
        exit 1
    fi
}

# 환경변수 로드
load_env() {
    local env_file="$PROJECT_DIR/.env"
    if [[ -f "$env_file" ]]; then
        log_info ".env 파일 로드 중"
        set -a
        source "$env_file"
        set +a
    else
        log_warning ".env 파일이 없습니다. 기본값을 사용합니다."
    fi
}

# 서비스 상태 확인
check_services() {
    log_info "서비스 상태 확인 중..."

    local services=(
        "openwebui:8080"
        "llm-agent:8001"
        "curriculum:7996"
        "vector-search:7997"
        "llm-client:7998"
        "tool-sql:7999"
        "department-mapping:8000"
    )

    local healthy=0
    local total=${#services[@]}

    for service in "${services[@]}"; do
        local name="${service%:*}"
        local port="${service#*:}"

        if curl -sf "http://localhost:$port" >/dev/null 2>&1; then
            log_success "✓ $name ($port) - 정상"
            ((healthy++))
        else
            log_warning "✗ $name ($port) - 비정상"
        fi
    done

    log_info "서비스 상태: $healthy/$total 정상"
}

# 메인 재시작 함수
restart_services() {
    local compose_cmd
    compose_cmd=$(get_compose_cmd)

    local CLEAN=false
    local REBUILD=false
    local SHOW_LOGS=false

    # 인자 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN=true
                shift
                ;;
            --rebuild)
                REBUILD=true
                shift
                ;;
            --logs)
                SHOW_LOGS=true
                shift
                ;;
            -h|--help)
                echo "사용법: $0 [옵션]"
                echo "옵션:"
                echo "  --clean     기존 컨테이너와 볼륨 정리 후 재시작"
                echo "  --rebuild   이미지 재빌드 후 시작"
                echo "  --logs      실행 후 로그 표시"
                echo "  -h, --help  도움말 표시"
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                echo "사용법: $0 [--clean] [--rebuild] [--logs]"
                exit 1
                ;;
        esac
    done

    log_info "AI Mentor 시스템 재시작 시작..."

    # 환경변수 로드
    load_env

    # 기존 서비스 중지
    if [[ "$CLEAN" == true ]]; then
        log_info "기존 컨테이너와 볼륨 정리 중..."
        $compose_cmd down --volumes --remove-orphans
    else
        log_info "기존 서비스 중지 중..."
        $compose_cmd down
    fi

    # 서비스 시작
    if [[ "$REBUILD" == true ]]; then
        log_info "이미지 재빌드 후 서비스 시작..."
        $compose_cmd up -d --build
    else
        log_info "서비스 시작 중..."
        $compose_cmd up -d
    fi

    # 잠시 대기
    log_info "서비스 초기화 대기 중..."
    sleep 10

    # 서비스 상태 확인
    check_services

    # 로그 표시
    if [[ "$SHOW_LOGS" == true ]]; then
        log_info "서비스 로그 표시 (Ctrl+C로 종료)"
        $compose_cmd logs -f
    fi

    log_success "AI Mentor 시스템 재시작 완료!"
    log_info "웹 인터페이스: http://localhost:8080"
    log_info "API 문서: http://localhost:8001/docs"
}

# Docker Compose 파일 확인
check_compose_file() {
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Docker Compose 파일을 찾을 수 없습니다: $COMPOSE_FILE"
        exit 1
    fi
}

# 메인 함수
main() {
    log_info "=== AI Mentor 시스템 재시작 스크립트 ==="

    # 사전 확인
    check_compose_file

    # 재시작 실행
    restart_services "$@"
}

# 스크립트 실행
main "$@"