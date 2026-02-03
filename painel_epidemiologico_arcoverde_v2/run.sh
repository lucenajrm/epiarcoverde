#!/bin/bash

# Script de execução do Dashboard de Saúde - Arcoverde/PE
# Compatível com Linux Mint 22.3

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Funções de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCESSO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[AVISO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERRO]${NC} $1"
}

# Verificar se Python está instalado
check_python() {
    log_info "Verificando instalação do Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        log_success "Python encontrado: $PYTHON_VERSION"
        return 0
    else
        log_error "Python 3 não encontrado. Por favor, instale o Python 3."
        exit 1
    fi
}

# Verificar/criar ambiente virtual
setup_venv() {
    log_info "Configurando ambiente virtual..."
    
    if [ ! -d "venv" ]; then
        log_info "Criando ambiente virtual..."
        python3 -m venv venv
        log_success "Ambiente virtual criado"
    else
        log_info "Ambiente virtual já existe"
    fi
    
    # Ativar ambiente virtual
    source venv/bin/activate
    log_success "Ambiente virtual ativado"
}

# Instalar dependências
install_deps() {
    log_info "Instalando dependências..."
    
    # Atualizar pip
    pip install --upgrade pip
    
    # Instalar dependências
    pip install -r requirements.txt
    
    log_success "Dependências instaladas"
}

# Criar diretórios necessários
create_dirs() {
    log_info "Criando diretórios..."
    
    mkdir -p data
    mkdir -p cache
    mkdir -p logs
    
    # Configurar permissões seguras no cache
    # 0o700 = apenas proprietário pode acessar
    chmod 700 cache 2>/dev/null || true
    
    log_success "Diretórios criados (cache com permissões restritas)"
}

# Verificar dependências do sistema
check_system_deps() {
    log_info "Verificando dependências do sistema..."
    
    # Verificar libffi-dev (necessário para PySUS)
    if ! dpkg -l | grep -q libffi-dev; then
        log_warning "libffi-dev não encontrado. Instalando..."
        sudo apt-get update
        sudo apt-get install -y libffi-dev
        log_success "libffi-dev instalado"
    else
        log_info "libffi-dev já instalado"
    fi
    
    # Verificar build-essential
    if ! command -v gcc &> /dev/null; then
        log_warning "build-essential não encontrado. Instalando..."
        sudo apt-get install -y build-essential
        log_success "build-essential instalado"
    fi
}

# Executar dashboard
run_dashboard() {
    log_info "Iniciando Dashboard..."
    
    # Configuração de segurança: localhost (127.0.0.1) como padrão
    # Para acesso externo, use: ./run.sh run-external
    SERVER_ADDRESS="127.0.0.1"
    
    log_info "Modo de execução: LOCAL (acesso apenas neste computador)"
    log_info "Acesse: http://localhost:8501"
    log_info "Pressione Ctrl+C para parar"
    echo ""
    
    streamlit run app.py --server.port=8501 --server.address=$SERVER_ADDRESS
}

# Executar dashboard em modo externo (0.0.0.0) - REQUER DOCUMENTAÇÃO
run_dashboard_external() {
    log_warning "=============================================="
    log_warning "MODO DE EXECUÇÃO EXTERNO ATIVADO"
    log_warning "=============================================="
    log_warning "Este modo permite acesso de outros dispositivos."
    log_warning "Use apenas em ambiente institucional com firewall configurado."
    log_warning "Documentação necessária: justificativa de uso em ambiente externo."
    log_warning "=============================================="
    echo ""
    
    read -p "Confirma execução em modo externo? (s/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        log_info "Iniciando Dashboard em modo externo..."
        log_info "Acesse: http://$(hostname -I | awk '{print $1}'):8501"
        log_info "Pressione Ctrl+C para parar"
        echo ""
        
        streamlit run app.py --server.port=8501 --server.address=0.0.0.0
    else
        log_info "Execução cancelada. Iniciando em modo local..."
        run_dashboard
    fi
}

# Executar atualização manual
run_update() {
    log_info "Executando atualização manual..."
    python3 update_scheduler.py --manual
}

# Executar agendador
run_scheduler() {
    log_info "Iniciando agendador de atualização..."
    python3 update_scheduler.py --daemon
}

# Mostrar ajuda
show_help() {
    echo ""
    echo "Dashboard de Saúde - Arcoverde/PE"
    echo ""
    echo "Uso: ./run.sh [comando]"
    echo ""
    echo "Comandos:"
    echo "  setup         - Configura o ambiente (instala dependências)"
    echo "  run           - Executa o dashboard (localhost - padrão seguro)"
    echo "  run-external  - Executa com acesso externo (requer confirmação)"
    echo "  update        - Executa atualização manual dos dados"
    echo "  scheduler     - Inicia o agendador de atualização automática"
    echo "  status        - Mostra status do sistema"
    echo "  help          - Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  ./run.sh setup    # Configuração inicial"
    echo "  ./run.sh run      # Inicia o dashboard (localhost)"
    echo ""
    echo "Segurança:"
    echo "  Por padrão, o dashboard executa apenas em localhost (127.0.0.1)"
    echo "  para acesso local. Use 'run-external' apenas em ambiente"
    echo "  institucional com firewall configurado."
    echo ""
}

# Mostrar status
show_status() {
    log_info "Status do Dashboard"
    echo ""
    
    # Verificar ambiente virtual
    if [ -d "venv" ]; then
        log_success "Ambiente virtual: OK"
    else
        log_warning "Ambiente virtual: Não criado"
    fi
    
    # Verificar diretórios
    if [ -d "data" ] && [ -d "cache" ] && [ -d "logs" ]; then
        log_success "Diretórios: OK"
    else
        log_warning "Diretórios: Incompletos"
    fi
    
    # Verificar permissões do cache
    if [ -d "cache" ]; then
        CACHE_PERMS=$(stat -c "%a" cache 2>/dev/null || stat -f "%Lp" cache 2>/dev/null || echo "unknown")
        if [ "$CACHE_PERMS" = "700" ]; then
            log_success "Permissões do cache: OK (0o700)"
        else
            log_warning "Permissões do cache: $CACHE_PERMS (recomendado: 700)"
        fi
    fi
    
    # Contar arquivos de cache
    if [ -d "cache" ]; then
        CACHE_COUNT=$(ls -1 cache/*.parquet 2>/dev/null | wc -l)
        log_info "Arquivos em cache: $CACHE_COUNT"
    fi
    
    # Verificar logs
    if [ -f "logs/scheduler.log" ]; then
        log_info "Últimas entradas do log:"
        tail -n 5 logs/scheduler.log
    fi
    
    echo ""
    log_info "Para iniciar: ./run.sh run"
    log_info "Documentação: cat README.md | cat SECURITY.md"
}

# Configuração completa
setup() {
    echo ""
    echo "========================================"
    echo "  Dashboard de Saúde - Arcoverde/PE"
    echo "  Configuração Inicial"
    echo "========================================"
    echo ""
    
    check_python
    check_system_deps
    setup_venv
    create_dirs
    install_deps
    
    echo ""
    log_success "Configuração concluída!"
    echo ""
    log_info "Para iniciar o dashboard, execute: ./run.sh run"
    echo ""
}

# Main
case "${1:-run}" in
    setup)
        setup
        ;;
    run)
        check_python
        setup_venv
        create_dirs
        run_dashboard
        ;;
    run-external)
        check_python
        setup_venv
        create_dirs
        run_dashboard_external
        ;;
    update)
        check_python
        setup_venv
        run_update
        ;;
    scheduler)
        check_python
        setup_venv
        run_scheduler
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Comando desconhecido: $1"
        show_help
        exit 1
        ;;
esac
