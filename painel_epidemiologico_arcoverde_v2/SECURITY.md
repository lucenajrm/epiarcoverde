# Documentação de Segurança - Dashboard de Saúde Arcoverde/PE

## 1. Visão Geral

Este documento descreve as medidas de segurança implementadas no Dashboard de Saúde de Arcoverde/PE, com foco especial no sistema de cache e persistência de dados.

## 2. Sistema de Cache

### 2.1 Formato de Armazenamento

**ANTES (Inseguro):**
- Formato: Pickle (`.pkl`)
- Risco: Execução arbitrária de código
- Permissões: Padrão do sistema

**DEPOIS (Seguro):**
- Formato: Apache Parquet (`.parquet`)
- Vantagem: Formato binário seguro, não executa código
- Permissões: `0o600` (apenas proprietário)

### 2.2 Estrutura do Cache

```
cache/
├── {key}.parquet          # Dados em formato seguro
├── {key}_meta.json        # Metadados (timestamp, fonte, etc.)
└── ...
```

### 2.3 Permissões de Arquivos

| Componente | Permissões | Descrição |
|------------|------------|-----------|
| Diretório `cache/` | `0o700` | Apenas proprietário pode acessar |
| Arquivos `.parquet` | `0o600` | Apenas proprietário pode ler/escrever |
| Arquivos `_meta.json` | `0o600` | Apenas proprietário pode ler/escrever |

### 2.4 Metadados Armazenados

Cada entrada de cache inclui:
```json
{
  "timestamp": "2025-01-15T10:30:00",
  "key": "sim_2601201_2024",
  "source": "pysus",
  "records": 1234,
  "columns": ["ano", "mes", "sexo", ...],
  "data_file": "sim_2601201_2024.parquet",
  "version": "1.0"
}
```

## 3. Execução em Rede

### 3.1 Modo Padrão (Seguro)

```bash
./run.sh run
```

- Endereço: `127.0.0.1` (localhost)
- Acesso: Apenas máquina local
- Uso: Desenvolvimento e testes locais

### 3.2 Modo Externo (Documentado)

```bash
./run.sh run-external
```

- Endereço: `0.0.0.0` (todas as interfaces)
- Acesso: Rede externa permitida
- Requisitos:
  - Confirmação explícita do usuário
  - Firewall configurado
  - Documentação de justificativa

## 4. Modo Demonstração

### 4.1 Ativação

```python
from data_loader import set_demo_mode
set_demo_mode(True)  # Ativa modo demonstração
```

### 4.2 Características

- Dados são **FICTÍCIOS** e gerados aleatoriamente
- Aviso visual explícito no dashboard
- Não deve ser usado para análise epidemiológica real
- Útil para demonstrações e testes de interface

### 4.3 Comportamento em Produção

Por padrão, o modo demonstração está **DESATIVADO**:
- Falhas de conexão geram erros explícitos
- Não há fallback silencioso para dados simulados
- O usuário é notificado de problemas de conexão

## 5. Atualização Automática

### 5.1 Fluxo de Atualização

1. Verifica disponibilidade do PySUS
2. Tenta baixar dados de cada sistema
3. Salva no cache em formato Parquet
4. Registra metadados
5. Limpa cache antigo

### 5.2 Comportamento em Falha

| Tipo de Falha | Comportamento |
|---------------|---------------|
| Erro de conexão | Registra no log, mantém cache existente |
| Erro em um ano | Pula o ano, continua com os demais |
| Falha total | Notifica via log, tenta no próximo ciclo |

### 5.3 Configuração do Cron

```bash
# Com ambiente virtual (recomendado)
0 3 * * 0 cd /caminho/do/dashboard && venv/bin/python update_scheduler.py --manual
```

## 6. Logs e Auditoria

### 6.1 Arquivos de Log

- `logs/data_loader.log`: Operações de carregamento de dados
- `logs/scheduler.log`: Operações do agendador

### 6.2 Informações Registradas

- Timestamp de operações
- Fonte dos dados (PySUS, cache, simulado)
- Erros e exceções
- Status de atualizações

## 7. Recomendações de Segurança

### 7.1 Sistema Operacional

1. Execute com usuário não-root
2. Configure firewall (ufw/iptables)
3. Mantenha o sistema atualizado
4. Use antivírus se disponível

### 7.2 Permissões de Arquivos

```bash
# Verificar permissões do cache
ls -la cache/

# Corrigir permissões se necessário
chmod 700 cache/
chmod 600 cache/*
```

### 7.3 Backup

Recomenda-se backup regular do diretório `cache/`:
```bash
# Backup diário
 tar -czf backup_cache_$(date +%Y%m%d).tar.gz cache/
```

## 8. Checklist de Segurança

- [ ] Cache usando formato Parquet (não pickle)
- [ ] Permissões 0o600 nos arquivos de cache
- [ ] Permissões 0o700 no diretório de cache
- [ ] Execução em localhost por padrão
- [ ] Modo demonstração claramente identificado
- [ ] Logs de auditoria configurados
- [ ] Atualização automática usando ambiente virtual
- [ ] Documentação de procedimentos

## 9. Contato e Suporte

Para questões de segurança:
- Coordenação da Vigilância Epidemiológica
- Município de Arcoverde – PE

---

**Versão:** 2.0  
**Última atualização:** Fevereiro 2025
