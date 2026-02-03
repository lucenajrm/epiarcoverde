# Changelog - Dashboard de Saúde Arcoverde/PE

## [2.0.0] - 2025-02-03

### Segurança

#### 1. Execução em Rede Local
- **Alteração**: O dashboard agora executa em `127.0.0.1` (localhost) por padrão
- **Arquivo**: `run.sh`
- **Motivo**: Prevenir exposição acidental em redes não seguras
- **Uso externo**: Comando `./run.sh run-external` com confirmação explícita

#### 2. Cache e Persistência de Dados
- **Alteração**: Substituição do formato Pickle por Apache Parquet
- **Arquivo**: `data_loader.py`
- **Motivo de segurança**: Parquet é um formato binário seguro que não executa código
- **Permissões**: Arquivos de cache com permissões `0o600` (apenas proprietário)
- **Diretório**: Permissões `0o700` no diretório `cache/`
- **Metadados**: Cada cache inclui timestamp, fonte dos dados e auditoria

#### 3. Dados Simulados
- **Alteração**: Modo demonstração explicitamente identificado
- **Arquivo**: `app.py`, `data_loader.py`
- **Comportamento**:
  - Banner visual amarelo quando modo demonstração está ativo
  - Dados fictícios claramente marcados com flag `_demo_data`
  - Por padrão, modo demonstração está DESATIVADO
  - Erros de conexão são exibidos explicitamente (não silenciados)
- **Ativação**: `set_demo_mode(True)` no `data_loader.py`

#### 4. Atualização Automática
- **Alteração**: Documentação completa do fluxo de atualização
- **Arquivo**: `update_scheduler.py`
- **Melhorias**:
  - Verificação de ambiente virtual antes da execução
  - Documentação do comportamento em caso de falha
  - Registro detalhado de erros no log
  - Continuidade do serviço mesmo com falhas parciais
- **Cron**: Configuração atualizada para usar Python do ambiente virtual

#### 5. Transparência Operacional
- **Alteração**: Informações de fonte de dados visíveis no dashboard
- **Arquivo**: `app.py`
- **Novas informações exibidas**:
  - Fonte dos dados: PySUS (DATASUS) + IBGE
  - Data e hora da última atualização
  - Status do PySUS (conectado/não conectado)
  - Modo de operação (produção/demonstração)
  - Informações técnicas expansíveis

### Documentação

#### Novos Arquivos
- **SECURITY.md**: Documentação completa de segurança do sistema
- **CHANGELOG.md**: Histórico de alterações (este arquivo)

#### Arquivos Atualizados
- **README.md**: Atualizado com informações de segurança e novos comandos
- **config.py**: Adicionada versão e descrição dos scripts
- **install.sh**: Configuração de permissões seguras no cache
- **run.sh**: Novo comando `run-external` e status de segurança

### Scripts

#### install.sh
- Configura permissões `0o700` no diretório `cache/` durante instalação
- Configura cron usando Python do ambiente virtual
- Exibe resumo de segurança ao final da instalação

#### run.sh
- Novo comando `run-external` para acesso de rede (com confirmação)
- Comando `run` agora usa `127.0.0.1` por padrão
- Status exibe informações de permissões do cache
- Ajuda atualizada com informações de segurança

#### update_scheduler.py
- Documentação extensa do fluxo de atualização
- Verificação de ambiente virtual
- Histórico de atualizações
- Comportamento documentado em caso de falha

### Estrutura de Cache

```
cache/
├── {key}.parquet          # Dados em formato Parquet (seguro)
├── {key}_meta.json        # Metadados (timestamp, fonte, etc.)
└── ...
```

**Permissões:**
- Diretório: `0o700` (rwx------)
- Arquivos: `0o600` (rw-------)

### Metadados do Cache

```json
{
  "timestamp": "2025-02-03T10:30:00",
  "key": "sim_2601201_2024",
  "source": "pysus",
  "records": 1234,
  "columns": ["ano", "mes", "sexo", ...],
  "data_file": "sim_2601201_2024.parquet",
  "version": "1.0"
}
```

---

## [1.0.0] - 2025-01-XX

### Versão Inicial
- Dashboard interativo com dados do SIM, SINAN e SINASC
- Integração com PySUS e IBGE
- Visualizações com Plotly
- Mapas com Folium
- Cache em formato Pickle
- Atualização automática básica

---

## Checklist de Validação

Para validar as melhorias de segurança:

- [ ] Executar `./run.sh run` - deve iniciar em localhost (127.0.0.1)
- [ ] Executar `./run.sh run-external` - deve solicitar confirmação
- [ ] Verificar permissões do cache: `ls -la cache/` (deve mostrar drwx------)
- [ ] Verificar formato dos arquivos de cache: `ls cache/` (deve mostrar .parquet)
- [ ] Verificar banner de modo demonstração (se ativado)
- [ ] Verificar informações de fonte de dados na sidebar
- [ ] Executar `./run.sh status` - deve mostrar informações de segurança
- [ ] Ler `SECURITY.md` para entender as medidas de segurança

---

**Coordenação da Vigilância Epidemiológica**  
**Município de Arcoverde – PE**
