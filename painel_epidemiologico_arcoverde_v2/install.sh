#!/bin/bash

# Script de instalação do Dashboard de Saúde - Arcoverde/PE
# Para Linux Mint 22.3 / Ubuntu 22.04+

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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

print_banner() {
    echo ""
    echo "========================================"
    echo "  Dashboard de Saúde - Arcoverde/PE"
    echo "  Instalação Automática"
    echo "========================================"
    echo ""
}

# Verificar sistema operacional
check_os() {
    log_info "Verificando sistema operacional..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VERSION=$VERSION_ID
        log_info "Sistema detectado: $OS $VERSION"
        
        if [[ "$OS" != *"Linux Mint"* ]] && [[ "$OS" != *"Ubuntu"* ]]; then
            log_warning "Sistema não testado. Continuando mesmo assim..."
        fi
    else
        log_error "Não foi possível detectar o sistema operacional"
        exit 1
    fi
}

# Atualizar sistema
update_system() {
    log_info "Atualizando lista de pacotes..."
    sudo apt-get update -qq
    log_success "Sistema atualizado"
}

# Instalar dependências do sistema
install_system_deps() {
    log_info "Instalando dependências do sistema..."
    
    PACKAGES="
        python3
        python3-pip
        python3-venv
        python3-dev
        libffi-dev
        build-essential
        libssl-dev
        curl
        wget
        git
    "
    
    sudo apt-get install -y -qq $PACKAGES
    log_success "Dependências do sistema instaladas"
}

# Verificar Python
setup_python() {
    log_info "Configurando Python..."
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python versão: $PYTHON_VERSION"
    
    # Verificar versão mínima (3.8)
    REQUIRED_VERSION="3.8"
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
        log_error "Python 3.8 ou superior é necessário"
        exit 1
    fi
    
    log_success "Python OK"
}

# Criar ambiente virtual
setup_venv() {
    log_info "Configurando ambiente virtual..."
    
    if [ -d "venv" ]; then
        log_warning "Ambiente virtual já existe. Removendo..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    log_success "Ambiente virtual criado"
}

# Instalar dependências Python
install_python_deps() {
    log_info "Instalando dependências Python..."
    
    source venv/bin/activate
    
    # Atualizar pip
    pip install --quiet --upgrade pip
    
    # Instalar dependências
    pip install --quiet -r requirements.txt
    
    log_success "Dependências Python instaladas"
}

# Criar diretórios necessários
create_directories() {
    log_info "Criando diretórios..."
    
    mkdir -p data
    mkdir -p cache
    mkdir -p logs
    
    # Configurar permissões seguras no diretório de cache
    # 0o700 = apenas proprietário pode ler, escrever e executar
    chmod 700 cache
    
    log_success "Diretórios criados (cache com permissões restritas)"
}

# Configurar permissões
setup_permissions() {
    log_info "Configurando permissões..."
    
    chmod +x run.sh
    chmod +x install.sh
    
    # Garantir permissões restritas no cache
    if [ -d "cache" ]; then
        chmod 700 cache
        log_info "Permissões do cache: 0o700 (restrito)"
    fi
    
    log_success "Permissões configuradas"
}

# Testar instalação
test_installation() {
    log_info "Testando instalação..."
    
    source venv/bin/activate
    
    # Testar imports
    python3 << EOF
import sys
sys.path.insert(0, '.')
try:
    import config
    print("✓ config.py")
    import data_loader
    print("✓ data_loader.py")
    import visualizations
    print("✓ visualizations.py")
    print("\n✅ Todos os módulos carregados com sucesso!")
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)
EOF
    
    log_success "Testes passaram"
}

# Criar atalho na área de trabalho
create_desktop_shortcut() {
    log_info "Criando atalho na área de trabalho..."
    
    DESKTOP_DIR="$HOME/Desktop"
    if [ -d "$DESKTOP_DIR" ]; then
        cat > "$DESKTOP_DIR/Dashboard-Saude-Arcoverde.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Dashboard de Saúde - Arcoverde
Comment=Painel de dados de saúde pública
Exec=bash -c "cd $SCRIPT_DIR && ./run.sh run"
Icon=$SCRIPT_DIR/icon.png
Terminal=true
Categories=Health;Medical;
EOF
        chmod +x "$DESKTOP_DIR/Dashboard-Saude-Arcoverde.desktop"
        log_success "Atalho criado na área de trabalho"
    else
        log_warning "Diretório da área de trabalho não encontrado"
    fi
}

# Configurar atualização automática (cron)
setup_autoupdate() {
    log_info "Configurando atualização automática..."
    
    read -p "Deseja configurar atualização automática semanal? (s/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        # Adicionar ao crontab usando o Python do ambiente virtual
        # IMPORTANTE: Usar o caminho completo do Python do venv
        VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
        (crontab -l 2>/dev/null; echo "0 3 * * 0 cd $SCRIPT_DIR && $VENV_PYTHON update_scheduler.py --manual >> logs/cron.log 2>&1") | crontab -
        log_success "Atualização automática configurada (domingos 3h)"
        log_info "Comando cron: 0 3 * * 0 cd $SCRIPT_DIR && $VENV_PYTHON update_scheduler.py --manual"
        log_info "⚠️  IMPORTANTE: O agendador usa o Python do ambiente virtual"
    else
        log_info "Atualização automática não configurada"
    fi
}

# Resumo da instalação
show_summary() {
    echo ""
    echo "========================================"
    echo "  Instalação Concluída!"
    echo "========================================"
    echo ""
    echo "🔒 SEGURANÇA:"
    echo "  • Cache configurado com permissões restritas (0o700)"
    echo "  • Formato Parquet (mais seguro que pickle)"
    echo "  • Execução localhost (127.0.0.1) por padrão"
    echo ""
    echo "Para iniciar o dashboard (modo seguro - localhost):"
    echo "  cd $SCRIPT_DIR"
    echo "  ./run.sh run"
    echo ""
    echo "Acesso local:"
    echo "  http://localhost:8501"
    echo ""
    echo "Comandos úteis:"
    echo "  ./run.sh setup        - Reconfigurar"
    echo "  ./run.sh run          - Iniciar (localhost)"
    echo "  ./run.sh run-external - Iniciar (acesso externo)"
    echo "  ./run.sh update       - Atualizar dados"
    echo "  ./run.sh status       - Verificar status"
    echo ""
    echo "Documentação:"
    echo "  cat README.md"
    echo "  cat SECURITY.md"
    echo ""
}

# Main
main() {
    print_banner
    
    check_os
    update_system
    install_system_deps
    setup_python
    setup_venv
    install_python_deps
    create_directories
    setup_permissions
    test_installation
    create_desktop_shortcut
    setup_autoupdate
    
    show_summary
}

# Executar
main "$@"
