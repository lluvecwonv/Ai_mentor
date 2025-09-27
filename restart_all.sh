#!/usr/bin/env bash
set -euo pipefail

# AiMentor_edit 시스템 재시작 스크립트
# Usage: ./restart_all.sh [--clean] [--rebuild]
#   --clean     기존 컨테이너와 이미지 정리 후 재시작
#   --rebuild   이미지 재빌드 후 시작

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
NETWORK_NAME="aimentor_edit_default"
ENV_FILE="$PROJECT_DIR/.env"
LLM_AGENT_ENV_FILE="$PROJECT_DIR/ai_modules/llm_agent-main/.env"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 컨테이너/이미지 목록 (해당 범위만 정리)
PROJECT_CONTAINER_NAMES=(
  openwebui llm-agent \
  svc7996 svc7997 svc7998 svc7999 department-mapping
)
# openwebui-proxy removed - nginx proxy disabled to avoid port conflicts
# PROJECT_IMAGE_REPOS는 더 이상 사용하지 않음(이미지 삭제 금지 정책)

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

# .env 파일 로드 (프로젝트 루트)
if [[ -f "$ENV_FILE" ]]; then
    log_info ".env 파일 로드 중: $ENV_FILE"
    set -a  # 자동으로 export
    source "$ENV_FILE"
    set +a  # export 해제
    log_success ".env 파일 로드 완료"
else
    log_warning ".env 파일을 찾을 수 없습니다: $ENV_FILE"
    log_info "기본 환경변수를 사용합니다"
fi

# 필수 환경변수 기본값 설정
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export SQL_QUERY_URL="${SQL_QUERY_URL:-http://svc7999:7999/api/v1/agent}"
export FAISS_SEARCH_URL="${FAISS_SEARCH_URL:-http://svc7997:7997/search}"
export CURRICULUM_PLAN_URL="${CURRICULUM_PLAN_URL:-http://svc7996:7996/chat}"
export DEPARTMENT_MAPPING_URL="${DEPARTMENT_MAPPING_URL:-http://department-mapping:8000/agent}"
export LLM_FALLBACK_URL="${LLM_FALLBACK_URL:-http://svc7998:7998/agent}"
# export LLM_CLIENT_AGENT_URL="${LLM_CLIENT_AGENT_URL:-http://llm-client-agent:8002/agent}"  # 제거됨
export PORT="${PORT:-8001}"
export TZ="${TZ:-Asia/Seoul}"

# LLM Agent 전용 .env 파일 로드 (OPENAI_API_KEY 우선)
if [[ -f "$LLM_AGENT_ENV_FILE" ]]; then
    log_info "LLM Agent .env 파일 로드 중: $LLM_AGENT_ENV_FILE"
    set -a  # 자동으로 export
    source "$LLM_AGENT_ENV_FILE"
    set +a  # export 해제
    log_success "LLM Agent .env 파일 로드 완료"

    # OPENAI_API_KEY 명시적 확인
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        log_success "OPENAI_API_KEY 확인됨 (${#OPENAI_API_KEY}자)"
    else
        log_warning "OPENAI_API_KEY가 비어있습니다"
    fi
else
    log_warning "LLM Agent .env 파일을 찾을 수 없습니다: $LLM_AGENT_ENV_FILE"
    log_info "기본값을 사용합니다"
fi

# 볼륨 마운트 디렉토리 확인 및 생성
verify_volume_mounts() {
    log_info "볼륨 마운트 디렉토리 확인 및 생성 중..."

    # 필요한 디렉토리들
    local required_dirs=(
        "$PROJECT_DIR/ai_modules/llm_agent-main/logs"
        "$PROJECT_DIR/openwebui_new"
    )

    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_info "디렉토리 생성: $dir"
            mkdir -p "$dir" || log_error "디렉토리 생성 실패: $dir"
        else
            log_info "디렉토리 확인됨: $dir"
        fi

        # 권한 확인 (쓰기 가능한지)
        if [[ ! -w "$dir" ]]; then
            log_warning "디렉토리 쓰기 권한 없음: $dir"
            chmod 755 "$dir" 2>/dev/null || log_warning "권한 변경 실패: $dir"
        fi
    done

    log_success "볼륨 마운트 디렉토리 확인 완료"
}

# 프로젝트별 안전한 캐시 정리
clear_project_cache() {
    log_info "프로젝트별 안전한 캐시 정리 중..."

    # 프로젝트 전용 네트워크만 정리 (다른 프로젝트 영향 없음)
    if docker network ls --format '{{.Name}}' | grep -Fxq "$NETWORK_NAME"; then
        # 네트워크에 연결된 컨테이너가 없을 때만 정리
        local connected_containers=$(docker network inspect "$NETWORK_NAME" --format '{{len .Containers}}' 2>/dev/null || echo "0")
        if [[ "$connected_containers" == "0" ]]; then
            log_info "프로젝트 네트워크 정리: $NETWORK_NAME"
            docker network rm "$NETWORK_NAME" 2>/dev/null || log_warning "네트워크 정리 실패"
        else
            log_info "프로젝트 네트워크에 컨테이너가 연결되어 있어 건너뜀"
        fi
    fi

    # 프로젝트 전용 볼륨만 정리 (openwebui 제외)
    log_info "사용하지 않는 프로젝트 볼륨 확인..."
    docker volume ls --format '{{.Name}}' | while read volume_name; do
        if [[ "$volume_name" == *"aimentor"* ]] && [[ "$volume_name" != *"openwebui"* ]]; then
            # 볼륨이 사용 중인지 확인
            local in_use=$(docker ps -a --filter volume="$volume_name" --format '{{.Names}}' | wc -l)
            if [[ "$in_use" == "0" ]]; then
                log_info "미사용 프로젝트 볼륨 제거: $volume_name"
                docker volume rm "$volume_name" 2>/dev/null || log_warning "볼륨 제거 실패: $volume_name"
            fi
        fi
    done

    # 빌드 캐시는 전역이므로 제거하지 않음 (다른 프로젝트에 영향)
    log_info "전역 빌드 캐시는 다른 프로젝트 보호를 위해 유지됨"

    log_success "프로젝트별 안전한 캐시 정리 완료"
}

# 이전 버전 이미지 확인 및 정리
check_old_images() {
    log_info "이전 버전 이미지 확인 중..."

    # 프로젝트 관련 이미지들
    local project_images=(
        "aimentor_edit-llm_agent"
        # "aimentor_edit-llm_client_agent"  # 제거됨
        "aimentor_edit-svc7996"
        "aimentor_edit-svc7997"
        "aimentor_edit-svc7998"
        "aimentor_edit-svc7999"
        "aimentor_edit-department-mapping"
        "openwebui-proxy"
    )

    for image in "${project_images[@]}"; do
        # 같은 이름의 이미지가 여러 개 있는지 확인
        local image_count=$(docker images "$image" --format "{{.ID}}" | wc -l)
        if [[ $image_count -gt 1 ]]; then
            log_warning "$image: 여러 버전 발견 ($image_count개)"
            # 최신 것만 남기고 오래된 것 제거
            docker images "$image" --format "{{.ID}} {{.CreatedAt}}" | sort -k2 | head -n -1 | awk '{print $1}' | while read old_id; do
                if [[ -n "$old_id" ]]; then
                    log_info "오래된 이미지 제거: $image ($old_id)"
                    docker rmi "$old_id" 2>/dev/null || log_warning "이미지 제거 실패: $old_id"
                fi
            done
        else
            log_info "$image: 최신 버전 확인됨"
        fi
    done

    log_success "이전 버전 이미지 확인 완료"
}

# buildx activity 임시 파일만 정리 (전역 prune 금지)
clean_buildx_activity() {
    local bx_dir="$HOME/.docker/buildx/activity"
    if [[ -d "$bx_dir" ]]; then
        log_info "buildx activity 임시파일 정리: $bx_dir"
        rm -f "$bx_dir"/.tmp-* 2>/dev/null || true
    fi
}

# Docker 명령어 확인
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker가 설치되어 있지 않거나 PATH에 없습니다."
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker 데몬이 실행되지 않았습니다."
        exit 1
    fi
}

# Docker Compose 명령어 확인
get_compose_cmd() {
    # 우선 docker-compose 사용 (SSL 이슈 때문에)
    if command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    elif docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    else
        log_error "Docker Compose를 찾을 수 없습니다."
        exit 1
    fi
}

# 네트워크 준비 (개별 docker run 경로에서 필요)
ensure_network() {
    if ! docker network ls --format '{{.Name}}' | grep -Fxq "$NETWORK_NAME"; then
        log_info "도커 네트워크 생성: $NETWORK_NAME"
        docker network create "$NETWORK_NAME" >/dev/null
        log_success "네트워크 생성 완료: $NETWORK_NAME"
    else
        log_info "도커 네트워크 확인됨: $NETWORK_NAME"
    fi
}

# 기존 컨테이너 정리
cleanup_containers() {
    log_info "기존 컨테이너 정리 중..."
    
    # AiMentor 관련 컨테이너 중지 및 제거
    local containers=("${PROJECT_CONTAINER_NAMES[@]}")
    
    for container in "${containers[@]}"; do
        if docker ps -q -f name="$container" | grep -q .; then
            log_info "컨테이너 $container 중지 중..."
            docker stop "$container" || true
        fi
        
        if docker ps -aq -f name="$container" | grep -q .; then
            log_info "컨테이너 $container 제거 중..."
            docker rm "$container" || true
        fi
    done
    
    # 예상 이름이 아닌 중복 컨테이너 정리 (포트 충돌 방지)
    # llm-agent 이미지로 실행된 컨테이너 중 이름이 'llm-agent'가 아닌 것 제거
    docker ps -a --format '{{.Names}} {{.Image}}' | awk '$2=="aimentor_edit-llm_agent" && $1!="llm-agent" {print $1}' | while read dup; do
        if [[ -n "$dup" ]]; then
            log_info "중복 llm-agent 컨테이너 정리: $dup"
            docker stop "$dup" 2>/dev/null || true
            docker rm "$dup" 2>/dev/null || true
        fi
    done

    # llm-client-agent 이미지로 실행된 컨테이너 중 이름이 'llm-client-agent'가 아닌 것 제거
    docker ps -a --format '{{.Names}} {{.Image}}' | awk '$2=="aimentor_edit-llm_client_agent" && $1!="llm-client-agent" {print $1}' | while read dup; do
        if [[ -n "$dup" ]]; then
            log_info "중복 llm-client-agent 컨테이너 정리: $dup"
            docker stop "$dup" 2>/dev/null || true
            docker rm "$dup" 2>/dev/null || true
        fi
    done

    log_success "컨테이너 정리 완료"
}

# cleanup_project_images 함수는 사용하지 않음(의도적으로 제거)


# 이미지 정리 (dangling 이미지만, 컨테이너는 건드리지 않음)
cleanup_images() {
    log_info "Dangling 이미지 정리 중... (컨테이너는 건드리지 않음)"
    # 태그 없는 레이어만 제거 시도 (사용 중이면 자동 실패하고 건너뜀)
    docker images -f dangling=true -q | xargs -r docker rmi -f 2>/dev/null || true
    log_success "Dangling 이미지 정리 완료"
}

# 개별 컨테이너 재빌드
rebuild_individual_containers() {
    log_info "개별 컨테이너 재빌드 시작..."

    # 볼륨 마운트 디렉토리 확인
    verify_volume_mounts

    # 네트워크 확인
    ensure_network

    # 이전 버전 이미지 확인 및 정리
    check_old_images

    # 빌드 환경 정리
    clean_buildx_activity

    # 공간 문제 회피: BuildKit 비활성화 (activity 파일 쓰기 최소화)
    export DOCKER_BUILDKIT=0
    export COMPOSE_DOCKER_CLI_BUILD=0
    log_info "DOCKER_BUILDKIT=0 환경으로 빌드 진행"

    # AI 서비스들 재빌드 및 시작
    log_info "svc7996 (curriculum) 컨테이너 재빌드 중..."
    cd "$PROJECT_DIR/ai_modules/curriculum-main"
    docker build --no-cache -t aimentor_edit-svc7996 . || log_error "svc7996 빌드 실패"
    docker run -d --name svc7996 --network="$NETWORK_NAME" -p 7996:7996 \
        -e PORT=7996 -e TZ=Asia/Seoul --restart unless-stopped \
        aimentor_edit-svc7996 || log_error "svc7996 시작 실패"

    log_info "svc7997 (faiss_search) 컨테이너 재빌드 중..."
    cd "$PROJECT_DIR/ai_modules/faiss_search-main"
    docker build --no-cache -t aimentor_edit-svc7997 . || log_error "svc7997 빌드 실패"
    docker run -d --name svc7997 --network="$NETWORK_NAME" -p 7997:7997 \
        -e PORT=7997 -e TZ=Asia/Seoul \
        -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
        -e DB_HOST="${DB_HOST}" \
        -e DB_PASSWORD="${DB_PASSWORD}" \
        -e VECTOR_DB_PASSWORD="${VECTOR_DB_PASSWORD}" \
        -v "$PROJECT_DIR/ai_modules/faiss_search-main/logs:/app/logs" \
        --restart unless-stopped \
        aimentor_edit-svc7997 || log_error "svc7997 시작 실패"

    log_info "svc7998 (tool_dumb) 컨테이너 재빌드 중..."
    cd "$PROJECT_DIR/ai_modules/tool_dumb-main"
    docker build --no-cache -t aimentor_edit-svc7998 . || log_error "svc7998 빌드 실패"
    docker run -d --name svc7998 --network="$NETWORK_NAME" -p 7998:7998 \
        -e PORT=7998 -e TZ=Asia/Seoul --restart unless-stopped \
        aimentor_edit-svc7998 || log_error "svc7998 시작 실패"

    log_info "svc7999 (tool_sql) 컨테이너 재빌드 중..."
    cd "$PROJECT_DIR/ai_modules/tool_sql-main"
    docker build --no-cache -t aimentor_edit-svc7999 . || log_error "svc7999 빌드 실패"
    docker run -d --name svc7999 --network="$NETWORK_NAME" -p 7999:7999 \
        -e PORT=7999 -e TZ=Asia/Seoul \
        -e DB_HOST="${DB_HOST}" \
        -e DB_PASSWORD="${DB_PASSWORD}" \
        --restart unless-stopped \
        aimentor_edit-svc7999 || log_error "svc7999 시작 실패"

    log_info "department-mapping 컨테이너 재빌드 중..."
    cd "$PROJECT_DIR/ai_modules/department_mapping-main"
    docker build --no-cache -t aimentor_edit-department-mapping . || log_error "department-mapping 빌드 실패"
    docker run -d --name department-mapping --network="$NETWORK_NAME" -p 8000:8000 \
        -e PORT=8000 -e TZ=Asia/Seoul --restart unless-stopped \
        aimentor_edit-department-mapping || log_error "department-mapping 시작 실패"

    # llm-client-agent 재빌드 (독립적인 LLM 클라이언트 모듈)
    log_info "llm-client-agent 컨테이너 재빌드 중..."
    cd "$PROJECT_DIR/ai_modules/llm_client_agent"
    if [[ -f "Dockerfile" ]]; then
        docker build --no-cache -t aimentor_edit-llm_client_agent . || log_error "llm-client-agent 빌드 실패"
        # 빌드 후 잠시 대기
        sleep 2
        docker run -d --name llm-client-agent --network="$NETWORK_NAME" -p 8002:8002 \
            -e PORT=8002 -e TZ=Asia/Seoul --restart unless-stopped \
            aimentor_edit-llm_client_agent || log_error "llm-client-agent 시작 실패"
    else
        log_warning "llm-client-agent Dockerfile이 없습니다. 건너뜀"
    fi

    # llm-agent 재빌드 (의존 서비스들이 시작된 후)
    log_info "llm-agent 컨테이너 재빌드 중..."
    cd "$PROJECT_DIR/ai_modules/llm_agent-main"
    docker build --no-cache -t aimentor_edit-llm_agent . || log_error "llm-agent 빌드 실패"
    docker run -d --name llm-agent -p 8001:8001 --network="$NETWORK_NAME" \
        -v "$PROJECT_DIR/ai_modules/llm_agent-main/logs:/app/logs" \
        -v "$PROJECT_DIR/ai_modules/llm_client_agent:/app/llm_client_agent" \
        -e PORT=${PORT:-8001} -e TZ=${TZ:-Asia/Seoul} \
        -e LOG_LEVEL=DEBUG \
        -e USE_UNIFIED_LANGGRAPH=true \
        -e USE_LANGGRAPH=false \
        -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
        -e SQL_QUERY_URL=${SQL_QUERY_URL:-http://svc7999:7999/api/v1/agent} \
        -e FAISS_SEARCH_URL=${FAISS_SEARCH_URL:-http://svc7997:7997/search} \
        -e CURRICULUM_PLAN_URL=${CURRICULUM_PLAN_URL:-http://svc7996:7996/chat} \
        -e DEPARTMENT_MAPPING_URL=${DEPARTMENT_MAPPING_URL:-http://department-mapping:8000/agent} \
        -e LLM_FALLBACK_URL=${LLM_FALLBACK_URL:-http://svc7998:7998/agent} \
        -e LLM_CLIENT_AGENT_URL=${LLM_CLIENT_AGENT_URL:-http://llm-client-agent:8002/agent} \
        --restart unless-stopped aimentor_edit-llm_agent || log_error "llm-agent 시작 실패"

    # OpenWebUI + Reverse Proxy (마지막에)
    log_info "OpenWebUI 컨테이너 시작 중..."

    # OpenWebUI 데이터 디렉토리 확인 및 생성
    log_info "OpenWebUI 데이터 디렉토리 생성 중..."
    mkdir -p "$PROJECT_DIR/openwebui_new"

    # 기존 컨테이너 정리 (있다면)
    if docker ps -aq -f name=openwebui | grep -q .; then
        log_info "기존 openwebui 컨테이너 정리 중..."
        docker stop openwebui || true
        docker rm openwebui || true
    fi

    # 서비스 안정화 대기
    log_info "서비스 안정화 대기 중..."
    sleep 3

    # OpenWebUI 컨테이너 시작 (공식 이미지 사용, WebSocket 비활성화)
    log_info "OpenWebUI 컨테이너 시작 중..."
    docker run -d --name openwebui --network="$NETWORK_NAME" \
        -p 8080:8080 \
        -e TZ=Asia/Seoul \
        -e WEBUI_AUTH=false \
        -e AUTHENTICATION=false \
        -e ENABLE_LOGIN=false \
        -e ENABLE_SIGNUP=false \
        -e ALLOW_ANONYMOUS=${ALLOW_ANONYMOUS:-true} \
        -e PUBLIC_MODE=${PUBLIC_MODE:-true} \
        -e ENABLE_ADMIN_PANEL=${ENABLE_ADMIN_PANEL:-false} \
        -e RATE_LIMIT_RPM=${RATE_LIMIT_RPM:-60} \
        -e WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY:-} \
        -e WEBUI_AUTH_TRUSTED_EMAIL_HEADER=${WEBUI_AUTH_TRUSTED_EMAIL_HEADER:-} \
        -e ENABLE_OAUTH_SIGNUP=${ENABLE_OAUTH_SIGNUP:-false} \
        -e ENABLE_LDAP=${ENABLE_LDAP:-false} \
        -e BYPASS_MODEL_VALIDATION=${BYPASS_MODEL_VALIDATION:-true} \
        -e USER_PERMISSIONS_CHAT_DELETION=${USER_PERMISSIONS_CHAT_DELETION:-true} \
        -e USER_PERMISSIONS_CHAT_EDITING=${USER_PERMISSIONS_CHAT_EDITING:-true} \
        -e USER_PERMISSIONS_CHAT_TEMPORARY=${USER_PERMISSIONS_CHAT_TEMPORARY:-true} \
        -e OPENAI_API_BASE_URL=http://llm-agent:8001 \
        -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
        -e ENABLE_TITLE_GENERATION=false \
        -e ENABLE_TAGS_GENERATION=false \
        -e ENABLE_SEARCH=false \
        -e ENABLE_ADMIN=false \
        -e ENABLE_MODEL_FILTER=false \
        -e ENABLE_COMMUNITY_SHARING=false \
        -e ENABLE_USER_IMPORT=false \
        -e ENABLE_MESSAGE_RATING=false \
        -e ENABLE_WEB_SEARCH=false \
        -e ENABLE_RAG_WEB_SEARCH=false \
        -e SHOW_ADMIN_DETAILS=false \
        -e DEFAULT_USER_ROLE=user \
        -e USE_WEBSOCKET=false \
        -e WEBSOCKET_ENABLED=false \
        -e OLLAMA_BASE_URL= \
        -e ENABLE_OLLAMA_API=false \
        -v "$PROJECT_DIR/openwebui_new:/app/backend/data" \
        --restart unless-stopped \
        ghcr.io/open-webui/open-webui:main || log_error "OpenWebUI 시작 실패"

    # Reverse Proxy 비활성화 - 포트 충돌 방지
    # log_info "Reverse Proxy(openwebui-proxy) 이미지 빌드 중..."
    # cd "$PROJECT_DIR/reverse-proxy"
    # docker build --no-cache -t openwebui-proxy . || log_error "openwebui-proxy 빌드 실패"
    # docker run -d --name openwebui-proxy --network="$NETWORK_NAME" -p 8080:8080 \
    #     -e TZ=Asia/Seoul --restart unless-stopped \
    #     openwebui-proxy || log_error "openwebui-proxy 시작 실패"


    cd "$PROJECT_DIR"
    log_success "개별 컨테이너 재빌드 완료"
}

# 개별 컨테이너 시작
start_individual_containers() {
    log_info "개별 컨테이너 시작..."
    ensure_network

    # AI 서비스들 먼저 시작
    docker run -d --name svc7996 --network="$NETWORK_NAME" -p 7996:7996 \
        -e PORT=7996 -e TZ=Asia/Seoul --restart unless-stopped \
        aimentor_edit-svc7996 || log_error "svc7996 시작 실패"

    docker run -d --name svc7997 --network="$NETWORK_NAME" -p 7997:7997 \
        -e PORT=7997 -e TZ=Asia/Seoul \
        -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
        -e DB_HOST="${DB_HOST}" \
        -e DB_PASSWORD="${DB_PASSWORD}" \
        -e VECTOR_DB_PASSWORD="${VECTOR_DB_PASSWORD}" \
        -v "$PROJECT_DIR/ai_modules/faiss_search-main/logs:/app/logs" \
        --restart unless-stopped \
        aimentor_edit-svc7997 || log_error "svc7997 시작 실패"

    docker run -d --name svc7998 --network="$NETWORK_NAME" -p 7998:7998 \
        -e PORT=7998 -e TZ=Asia/Seoul --restart unless-stopped \
        aimentor_edit-svc7998 || log_error "svc7998 시작 실패"

    docker run -d --name svc7999 --network="$NETWORK_NAME" -p 7999:7999 \
        -e PORT=7999 -e TZ=Asia/Seoul \
        -e DB_HOST="${DB_HOST}" \
        -e DB_PASSWORD="${DB_PASSWORD}" \
        --restart unless-stopped \
        aimentor_edit-svc7999 || log_error "svc7999 시작 실패"

    docker run -d --name department-mapping --network="$NETWORK_NAME" -p 8000:8000 \
        -e PORT=8000 -e TZ=Asia/Seoul --restart unless-stopped \
        aimentor_edit-department-mapping || log_error "department-mapping 시작 실패"

    # LLM Client Agent 먼저 시작
    if docker images -q aimentor_edit-llm_client_agent | grep -q .; then
        docker run -d --name llm-client-agent --network="$NETWORK_NAME" -p 8002:8002 \
            -e PORT=8002 -e TZ=Asia/Seoul --restart unless-stopped \
            aimentor_edit-llm_client_agent || log_error "llm-client-agent 시작 실패"
    fi

    # LLM Agent (의존 서비스들이 시작된 후)
    docker run -d --name llm-agent -p 8001:8001 --network="$NETWORK_NAME" \
        -v "$PROJECT_DIR/ai_modules/llm_agent-main/logs:/app/logs" \
        -v "$PROJECT_DIR/ai_modules/llm_client_agent:/app/llm_client_agent" \
        -e PORT=${PORT:-8001} -e TZ=${TZ:-Asia/Seoul} \
        -e LOG_LEVEL=DEBUG \
        -e USE_UNIFIED_LANGGRAPH=true \
        -e USE_LANGGRAPH=false \
        -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
        -e SQL_QUERY_URL=${SQL_QUERY_URL:-http://svc7999:7999/api/v1/agent} \
        -e FAISS_SEARCH_URL=${FAISS_SEARCH_URL:-http://svc7997:7997/search} \
        -e CURRICULUM_PLAN_URL=${CURRICULUM_PLAN_URL:-http://svc7996:7996/chat} \
        -e DEPARTMENT_MAPPING_URL=${DEPARTMENT_MAPPING_URL:-http://department-mapping:8000/agent} \
        -e LLM_FALLBACK_URL=${LLM_FALLBACK_URL:-http://svc7998:7998/agent} \
        -e LLM_CLIENT_AGENT_URL=${LLM_CLIENT_AGENT_URL:-http://llm-client-agent:8002/agent} \
        --restart unless-stopped aimentor_edit-llm_agent || log_error "llm-agent 시작 실패"

    # OpenWebUI (마지막에 시작)
    # OpenWebUI 데이터 디렉토리 확인 및 생성
    log_info "OpenWebUI 데이터 디렉토리 생성 중..."
    mkdir -p "$PROJECT_DIR/openwebui_new"

    # 기존 컨테이너 정리 (있다면)
    if docker ps -aq -f name=openwebui | grep -q .; then
        log_info "기존 openwebui 컨테이너 정리 중..."
        docker stop openwebui || true
        docker rm openwebui || true
    fi

    # 서비스 안정화 대기
    log_info "서비스 안정화 대기 중..."
    sleep 2

    # OpenWebUI 컨테이너 시작 (공식 이미지 사용, WebSocket 비활성화)
    log_info "OpenWebUI 컨테이너 시작 중..."
    docker run -d --name openwebui --network="$NETWORK_NAME" \
        -p 8080:8080 \
        -e TZ=Asia/Seoul \
        -e WEBUI_AUTH=false \
        -e AUTHENTICATION=false \
        -e ENABLE_LOGIN=false \
        -e ENABLE_SIGNUP=false \
        -e ALLOW_ANONYMOUS=${ALLOW_ANONYMOUS:-true} \
        -e PUBLIC_MODE=${PUBLIC_MODE:-true} \
        -e ENABLE_ADMIN_PANEL=${ENABLE_ADMIN_PANEL:-false} \
        -e RATE_LIMIT_RPM=${RATE_LIMIT_RPM:-60} \
        -e WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY:-} \
        -e WEBUI_AUTH_TRUSTED_EMAIL_HEADER=${WEBUI_AUTH_TRUSTED_EMAIL_HEADER:-} \
        -e ENABLE_OAUTH_SIGNUP=${ENABLE_OAUTH_SIGNUP:-false} \
        -e ENABLE_LDAP=${ENABLE_LDAP:-false} \
        -e BYPASS_MODEL_VALIDATION=${BYPASS_MODEL_VALIDATION:-true} \
        -e USER_PERMISSIONS_CHAT_DELETION=${USER_PERMISSIONS_CHAT_DELETION:-true} \
        -e USER_PERMISSIONS_CHAT_EDITING=${USER_PERMISSIONS_CHAT_EDITING:-true} \
        -e USER_PERMISSIONS_CHAT_TEMPORARY=${USER_PERMISSIONS_CHAT_TEMPORARY:-true} \
        -e OPENAI_API_BASE_URL=http://llm-agent:8001 \
        -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
        -e ENABLE_TITLE_GENERATION=false \
        -e ENABLE_TAGS_GENERATION=false \
        -e ENABLE_SEARCH=false \
        -e ENABLE_ADMIN=false \
        -e ENABLE_MODEL_FILTER=false \
        -e ENABLE_COMMUNITY_SHARING=false \
        -e ENABLE_USER_IMPORT=false \
        -e ENABLE_MESSAGE_RATING=false \
        -e ENABLE_WEB_SEARCH=false \
        -e ENABLE_RAG_WEB_SEARCH=false \
        -e SHOW_ADMIN_DETAILS=false \
        -e DEFAULT_USER_ROLE=user \
        -e USE_WEBSOCKET=false \
        -e WEBSOCKET_ENABLED=false \
        -e OLLAMA_BASE_URL= \
        -e ENABLE_OLLAMA_API=false \
        -v "$PROJECT_DIR/openwebui_new:/app/backend/data" \
        --restart unless-stopped \
        ghcr.io/open-webui/open-webui:main || log_error "OpenWebUI 시작 실패"

    # Reverse Proxy 비활성화 - 포트 충돌 방지
    # docker run -d --name openwebui-proxy --network="$NETWORK_NAME" -p 8080:8080 \
    #     -e TZ=Asia/Seoul --restart unless-stopped \
    #     openwebui-proxy || log_error "openwebui-proxy 시작 실패"


    log_success "개별 컨테이너 시작 완료"
}

# 서비스 시작
start_services() {
    local compose_cmd
    compose_cmd=$(get_compose_cmd)
    
    log_info "서비스 시작 중..."
    log_info "Compose 파일: $COMPOSE_FILE"
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "docker-compose.yml 파일을 찾을 수 없습니다: $COMPOSE_FILE"
        exit 1
    fi
    
    # 서비스 시작
    if [[ "$REBUILD" == true ]]; then
        log_info "이미지 재빌드 후 서비스 시작..."
        if ! $compose_cmd -f "$COMPOSE_FILE" up -d --build 2>/dev/null; then
            log_warning "Docker Compose 명령 실패. 개별 Docker 명령으로 대체 시도..."
            # 개별 컨테이너 재빌드 및 시작
            rebuild_individual_containers
            return
        fi
    else
        log_info "기존 이미지로 서비스 시작..."
        if ! $compose_cmd -f "$COMPOSE_FILE" up -d 2>/dev/null; then
            log_warning "Docker Compose 명령 실패. 개별 Docker 명령으로 대체 시도... (이미지 재빌드)"
            # compose 실패 시 이미지가 없을 수 있으므로 재빌드 경로 사용
            rebuild_individual_containers
            return
        fi
    fi

    # Compose 성공처럼 보여도 핵심 컨테이너가 없으면 폴백 실행
    if ! docker ps -q -f name=openwebui | grep -q .; then
        log_warning "Compose 이후 핵심 컨테이너 미감지 → 개별 재빌드로 폴백"
        rebuild_individual_containers
        return
    fi

    log_success "서비스 시작 완료!"
}

# 컨테이너 상세 상태 확인
check_container_health() {
    local container_name="$1"
    local port="$2"

    if ! docker ps -q -f name="$container_name" | grep -q .; then
        log_error "$container_name: 컨테이너가 실행되지 않음"
        return 1
    fi

    # 컨테이너 상태 확인
    local status=$(docker inspect "$container_name" --format '{{.State.Status}}' 2>/dev/null)
    if [[ "$status" != "running" ]]; then
        log_error "$container_name: 상태가 running이 아님 ($status)"
        return 1
    fi

    # 볼륨 마운트 확인 (llm-agent의 경우)
    if [[ "$container_name" == "llm-agent" ]]; then
        local mounts=$(docker inspect "$container_name" --format '{{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}' 2>/dev/null)
        if [[ "$mounts" == *"/logs:/app/logs"* ]]; then
            log_info "$container_name: 볼륨 마운트 확인됨"
        else
            log_warning "$container_name: 볼륨 마운트 누락 가능"
        fi
    fi

    # 포트 바인딩 확인
    if [[ -n "$port" ]]; then
        local port_bindings=$(docker port "$container_name" "$port" 2>/dev/null)
        if [[ -n "$port_bindings" ]]; then
            log_success "$container_name (포트 $port): 실행 중 - $port_bindings"
        else
            log_warning "$container_name: 포트 $port 바인딩 누락"
        fi
    else
        log_success "$container_name: 실행 중"
    fi

    return 0
}

# 서비스 상태 확인
check_services() {
    log_info "서비스 상태 확인 중..."

    local services=("openwebui:8080" "llm-agent:8001" "llm-client-agent:8002" "svc7996:7996" "svc7997:7997" "svc7998:7998" "svc7999:7999" "department-mapping:8000")
    local all_healthy=true

    for service in "${services[@]}"; do
        local name=$(echo "$service" | cut -d: -f1)
        local port=$(echo "$service" | cut -d: -f2)

        if ! check_container_health "$name" "$port"; then
            all_healthy=false
        fi
    done

    if [[ "$all_healthy" == true ]]; then
        log_success "모든 서비스가 정상적으로 실행 중입니다!"
    else
        log_warning "일부 서비스에 문제가 있습니다."
    fi
}

# 간단 HTTP 헬스체크 (프록시 경유)
wait_for_proxy() {
    local url="http://localhost:8080/api/models"
    local retries=30
    local delay=1
    log_info "프록시 응답 대기: $url"
    for i in $(seq 1 $retries); do
        if command -v curl >/dev/null 2>&1; then
            if curl -sf -m 2 "$url" >/dev/null; then
                log_success "프록시 응답 확인됨 (시도 $i)"
                return 0
            fi
        fi
        sleep $delay
    done
    log_warning "프록시 응답 확인 실패 (30초 경과)"
    return 1
}

# SQL 서비스 워밍업 (헬스콜)
warmup_sql_service() {
    local url="http://localhost:7999/api/v1/health"
    local retries=20
    local delay=1
    log_info "SQL 서비스 워밍업(헬스콜) 시작: $url"

    if ! command -v curl >/dev/null 2>&1; then
        log_warning "curl 이 없어 워밍업을 건너뜁니다"
        return 0
    fi

    for i in $(seq 1 $retries); do
        if curl -sf -m 3 "$url" >/dev/null; then
            log_success "SQL 서비스 워밍업 완료 (시도 $i)"
            return 0
        fi
        sleep $delay
    done
    log_warning "SQL 서비스 워밍업 실패 (${retries}회 시도)"
    return 1
}

# 서비스 정보 출력
show_service_info() {
    echo ""
    log_info "=" * 60
    log_info "AiMentor_edit 서비스 정보"
    log_info "=" * 60
    echo ""
    log_info "🌐 Web UI (OpenWebUI):"
    echo "   URL: http://localhost:8080"
    echo ""
    log_info "🤖 AI 서비스들:"
    echo "   - LLM Agent (메인):   http://localhost:8001"
    echo "   - LLM Client Agent:   http://localhost:8002"
    echo "   - Curriculum:         http://localhost:7996"
    echo "   - FAISS Search:       http://localhost:7997"
    echo "   - Tool Fallback:      http://localhost:7998"
    echo "   - Tool SQL:           http://localhost:7999"
    echo "   - Department Map:     http://localhost:8000"
    echo ""
    log_info "📊 로그 확인 명령어:"
    # echo "   docker logs openwebui-proxy -f"
    echo "   docker logs openwebui -f"
    echo "   docker logs llm-agent -f"
    echo "   docker logs llm-client-agent -f"
    echo "   docker logs svc7996 -f"
    echo "   docker logs svc7997 -f"
    echo "   docker logs svc7998 -f"
    echo "   docker logs svc7999 -f"
    echo "   docker logs department-mapping -f"
    echo ""
    log_info "🛑 서비스 중지 명령어:"
    echo "   docker stop openwebui llm-agent llm-client-agent svc7996 svc7997 svc7998 svc7999 department-mapping"
    echo ""
    log_info "=" * 60
}

# 메인 함수
main() {
    local CLEAN=false
    local REBUILD=false
    local CACHE_CLEAN=false

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
            --cache-clean)
                CACHE_CLEAN=true
                shift
                ;;
            -h|--help)
                echo "AiMentor_edit 시스템 재시작 스크립트"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --clean       기존 컨테이너와 이미지 정리 후 재시작"
                echo "  --rebuild     이미지 재빌드 후 시작"
                echo "  --cache-clean 프로젝트별 안전한 캐시 정리 (다른 프로젝트에 영향 없음)"
                echo "  -h, --help    도움말 표시"
                echo ""
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                echo "사용법: $0 [--clean] [--rebuild] [--cache-clean]"
                exit 1
                ;;
        esac
    done
    
    log_info "AiMentor_edit 시스템 재시작을 시작합니다..."
    log_info "옵션 - Clean: $CLEAN, Rebuild: $REBUILD, Cache-Clean: $CACHE_CLEAN"
    echo ""

    # Docker 확인
    check_docker

    # 볼륨 마운트 디렉토리 미리 확인 (모든 경우에 실행)
    verify_volume_mounts

    # 프로젝트별 안전한 캐시 정리 (옵션에 따라)
    if [[ "$CACHE_CLEAN" == true ]]; then
        clear_project_cache
    fi

    # 기존 서비스 정리 (필요한 경우)
    if [[ "$CLEAN" == true ]]; then
        cleanup_containers
        # 요청에 따라 프로젝트 이미지는 유지, dangling 이미지만 정리
        cleanup_images
        # Clean 옵션 시 이전 버전 이미지도 정리
        check_old_images
    else
        cleanup_containers
    fi
    
    # 서비스 시작
    start_services
    
    # SQL 워밍업 (헬스콜)
    warmup_sql_service || true

    # 잠시 대기
    log_info "서비스 시작 대기 중... (10초)"
    sleep 10
    # 프록시 헬스체크 (가능 시)
    wait_for_proxy || true
    
    # 서비스 상태 확인
    check_services
    
    # 서비스 정보 출력
    show_service_info
    
    log_success "AiMentor_edit 시스템 재시작 완료! 🎉"
}

# 스크립트 실행
main "$@"
