# Dashboard de Saúde - Arcoverde/PE

Dashboard interativo para visualização de dados de saúde pública do município de Arcoverde, Pernambuco, integrando dados do PySUS (SIM, SINAN, SINASC) com informações geoespaciais do IBGE.

**Versão:** 2.0 | **Última atualização:** Fevereiro 2025

---

## 📋 Características

- **Dados integrados**: SIM (Mortalidade), SINAN (Notificações), SINASC (Nascimentos)
- **Geolocalização**: Integração com API do IBGE para mapas e localização
- **Visualizações interativas**: Gráficos dinâmicos com Plotly
- **Filtros avançados**: Por período, doença, faixa etária, etc.
- **Atualização automática**: Sistema de atualização semanal dos dados
- **Interface em português**: Totalmente localizado para o Brasil
- **Segurança reforçada**: Cache em formato seguro, execução localhost por padrão

---

## 🚀 Instalação

### Pré-requisitos

- Linux Mint 22.3 (ou Ubuntu/Debian compatível)
- Python 3.8+
- pip
- libffi-dev (instalado automaticamente pelo script)

### Instalação Rápida

```bash
# Clone ou extraia o projeto
cd dashboard_arcoverde

# Execute a configuração inicial
./run.sh setup
```

### Instalação Manual

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Criar diretórios
mkdir -p data cache logs

# Configurar permissões seguras no cache
chmod 700 cache
```

---

## 💻 Uso

### Iniciar o Dashboard (Modo Seguro - Localhost)

```bash
./run.sh run
```

O dashboard estará disponível em: **http://localhost:8501**

Acesso permitido apenas neste computador (127.0.0.1).

### Iniciar em Modo Externo (Requer Confirmação)

```bash
./run.sh run-external
```

⚠️ **Atenção:** Este modo permite acesso de outros dispositivos na rede. Use apenas em ambiente institucional com firewall configurado.

### Comandos Disponíveis

```bash
./run.sh setup         # Configuração inicial
./run.sh run           # Iniciar dashboard (localhost - padrão seguro)
./run.sh run-external  # Iniciar com acesso externo (requer confirmação)
./run.sh update        # Atualização manual dos dados
./run.sh scheduler     # Iniciar agendador de atualização automática
./run.sh status        # Verificar status
./run.sh help          # Ajuda
```

---

## 📊 Funcionalidades

### 1. SIM - Sistema de Informação sobre Mortalidade
- Evolução temporal de óbitos
- Distribuição por sexo, idade e raça/cor
- Principais causas de óbito (CID)
- Heatmap mensal

### 2. SINAN - Sistema de Informação de Agravos de Notificação
- Notificações por doença
- Evolução temporal
- Distribuição demográfica
- Acompanhamento de surtos

### 3. SINASC - Sistema de Informações sobre Nascidos Vivos
- Estatísticas de nascimentos
- Indicadores de saúde materno-infantil
- Peso ao nascer
- Tipo de parto

### 4. Análise Comparativa
- Comparação entre sistemas
- Tendências ao longo do tempo
- Correlações entre indicadores

### 5. Mapa Geoespacial
- Localização do município
- Informações do IBGE
- Dados geográficos integrados

---

## 🔒 Segurança

### Cache Seguro

O sistema utiliza **Apache Parquet** para armazenamento de cache:

- ✅ Formato binário seguro (não executa código)
- ✅ Permissões restritas (0o600)
- ✅ Metadados de auditoria
- ✅ Validação de integridade

Consulte [SECURITY.md](SECURITY.md) para detalhes completos.

### Execução em Rede

| Modo | Endereço | Acesso | Uso |
|------|----------|--------|-----|
| Padrão | 127.0.0.1 | Local apenas | Desenvolvimento/Testes |
| Externo | 0.0.0.0 | Rede | Ambiente institucional com firewall |

### Modo Demonstração

Para testes sem conexão com PySUS:

```python
from data_loader import set_demo_mode
set_demo_mode(True)
```

⚠️ **Atenção:** Dados fictícios - não use para análise real.

---

## 🔄 Atualização Automática

### Agendador Integrado

```bash
# Iniciar agendador (executa em background)
./run.sh scheduler
```

### Configuração do Cron (Recomendado)

```bash
# Editar crontab
crontab -e

# Adicionar linha para atualização semanal (domingo 3h)
# IMPORTANTE: Use o Python do ambiente virtual
0 3 * * 0 cd /caminho/do/dashboard && venv/bin/python update_scheduler.py --manual >> logs/cron.log 2>&1
```

### Comportamento em Falha

- **Erro de conexão**: Registra no log, mantém cache existente
- **Erro parcial**: Pula o item problemático, continua com os demais
- **Falha total**: Notifica via log, tenta no próximo ciclo

---

## 🗂️ Estrutura do Projeto

```
dashboard_arcoverde/
├── app.py                 # Aplicação principal Streamlit
├── config.py              # Configurações
├── data_loader.py         # Carregamento de dados PySUS/IBGE
├── visualizations.py      # Gráficos e visualizações
├── update_scheduler.py    # Agendador de atualização
├── requirements.txt       # Dependências Python
├── run.sh                 # Script de execução
├── install.sh             # Script de instalação
├── README.md              # Este arquivo
├── SECURITY.md            # Documentação de segurança
├── data/                  # Dados baixados
├── cache/                 # Cache de dados (formato Parquet)
└── logs/                  # Logs do sistema
```

---

## 📦 Dependências Principais

- **streamlit**: Framework do dashboard
- **pandas**: Manipulação de dados
- **plotly**: Gráficos interativos
- **folium**: Mapas geoespaciais
- **pysus**: Acesso aos dados do DATASUS
- **requests**: API do IBGE
- **pyarrow**: Suporte ao formato Parquet

---

## 🔧 Solução de Problemas

### Erro: libffi-dev não encontrado

```bash
sudo apt-get update
sudo apt-get install -y libffi-dev build-essential
```

### Erro: Permissão negada no run.sh

```bash
chmod +x run.sh
chmod +x install.sh
```

### Dados não carregam

1. Verifique conexão com internet
2. Execute atualização manual: `./run.sh update`
3. Verifique logs em `logs/scheduler.log`
4. Verifique se PySUS está disponível na sidebar do dashboard

### PySUS não instalado

```bash
source venv/bin/activate
pip install pysus
```

### Problemas de Permissão no Cache

```bash
# Verificar permissões
ls -la cache/

# Corrigir permissões
chmod 700 cache/
chmod 600 cache/*
```

---

## 📈 Fontes de Dados

- **PySUS/DATASUS**: https://datasus.saude.gov.br/
- **IBGE Localidades**: https://servicodados.ibge.gov.br/api/docs/localidades
- **IBGE Malhas**: https://servicodados.ibge.gov.br/api/docs/malhas

---

## 📝 Licença

Este projeto é de uso público para fins de saúde pública e transparência governamental.

---

## 🤝 Contribuições

Contribuições são bem-vindas! Para sugestões ou reportar problemas, entre em contato com a Coordenação da Vigilância Epidemiológica.

---

## 📞 Suporte

Para dúvidas sobre:
- **PySUS**: https://pysus.readthedocs.io/
- **Streamlit**: https://docs.streamlit.io/
- **DATASUS**: https://datasus.saude.gov.br/

---

## 📋 Histórico de Versões

### v2.0 (Fevereiro 2025)
- ✅ Execução localhost (127.0.0.1) por padrão
- ✅ Cache em formato Parquet (mais seguro que pickle)
- ✅ Permissões restritas no cache (0o600)
- ✅ Modo demonstração explicitamente identificado
- ✅ Transparência de fonte de dados no dashboard
- ✅ Documentação de segurança adicionada
- ✅ Melhorias no tratamento de erros

### v1.0 (Janeiro 2025)
- Versão inicial do dashboard

---

**Desenvolvido para a Secretaria de Saúde de Arcoverde/PE**

*Coordenação da Vigilância Epidemiológica*
