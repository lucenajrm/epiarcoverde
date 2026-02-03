"""
Configurações do Dashboard de Saúde - Arcoverde/PE

VERSÃO: 2.0
DATA: Fevereiro 2025

DESCRIÇÃO DOS SCRIPTS:
- install.sh: Script de instalação inicial. Configura ambiente virtual,
  instala dependências, cria diretórios e configura permissões seguras.
  Uso: ./install.sh (executar uma vez)

- run.sh: Script de execução diário. Inicia o dashboard, executa atualizações
  manualmente ou inicia o agendador automático.
  Uso: ./run.sh [run|run-external|update|scheduler|status]

- update_scheduler.py: Sistema de atualização automática. Pode executar como
  daemon (background) ou atualização manual única.
  Uso: python update_scheduler.py [--manual|--daemon|--status]
  IMPORTANTE: Sempre executar dentro do ambiente virtual
"""

import os
from pathlib import Path

# Informações da versão
VERSAO = {
    "major": 2,
    "minor": 0,
    "patch": 0,
    "data": "2025-02-03",
    "descricao": "Melhorias de segurança e transparência"
}

# Diretórios
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"

# Criar diretórios se não existirem
for dir_path in [DATA_DIR, CACHE_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Configurações do município
MUNICIPIO = {
    "nome": "Arcoverde",
    "uf": "PE",
    "codigo_ibge": 2601201,
    "codigo_uf": 26,
    "latitude": -8.4182,
    "longitude": -37.0538,
    "regiao": "Nordeste",
    "mesorregiao": "Sertão Pernambucano",
    "microrregiao": "Sertão do Moxotó"
}

# Sistemas de dados de saúde
SISTEMAS = {
    "SIM": {
        "nome": "Sistema de Informação sobre Mortalidade",
        "sigla": "SIM",
        "descricao": "Dados sobre óbitos no território nacional",
        "url": "https://svs.aids.gov.br/dantps/centraisdeconteudos/mortalidade/",
        "anos_disponiveis": list(range(1996, 2025)),
        "principal_indicador": "Óbitos"
    },
    "SINAN": {
        "nome": "Sistema de Informação de Agravos de Notificação",
        "sigla": "SINAN",
        "descricao": "Dados de doenças e agravos de notificação compulsória",
        "url": "https://portalsinan.saude.gov.br/",
        "anos_disponiveis": list(range(2001, 2025)),
        "principal_indicador": "Notificações"
    },
    "SINASC": {
        "nome": "Sistema de Informações sobre Nascidos Vivos",
        "sigla": "SINASC",
        "descricao": "Dados sobre nascimentos no território nacional",
        "url": "https://svs.aids.gov.br/dantps/centraisdeconteudos/nascimentos/",
        "anos_disponiveis": list(range(1994, 2025)),
        "principal_indicador": "Nascimentos"
    }
}

# Doenças do SINAN (principais)
DOENCAS_SINAN = {
    "DENGUE": "Dengue",
    "CHIKUNGUNYA": "Chikungunya",
    "ZIKA": "Zika",
    "FEBRE_AMARELA": "Febre Amarela",
    "MALARIA": "Malária",
    "TUBERCULOSE": "Tuberculose",
    "HANSENIAZE": "Hanseníase",
    "LEISHMANIOSE": "Leishmaniose",
    "SCHISTOSSOMOSE": "Esquistossomose",
    "DOENCA_MENINGOCOCCICA": "Doença Meningocócica",
    "HEPATITES_VIRAIS": "Hepatites Virais",
    "HIV_AIDS": "HIV/AIDS",
    "SIFILIS": "Sífilis",
    "VIOLENCIA_DOMESTICA": "Violência Doméstica",
    "ACIDENTE_TRABALHO": "Acidente de Trabalho"
}

# CIDs principais para análise
CIDS_PRINCIPAIS = [
    "A00-B99",  # Infecções
    "C00-D48",  # Neoplasias
    "E00-E90",  # Endócrinas
    "F00-F99",  # Mentais
    "G00-G99",  # Nervoso
    "I00-I99",  # Circulatório
    "J00-J99",  # Respiratório
    "K00-K93",  # Digestivo
    "O00-O99",  # Gravidez
    "P00-P96",  # Perinatal
    "Q00-Q99",  # Congênitas
    "S00-T98",  # Traumatismos
    "V01-Y98",  # Causas externas
]

# Configurações de cores (tema similar ao CNIE)
TEMA_CORES = {
    "primaria": "#1351B4",
    "secundaria": "#2670E8",
    "terciaria": "#5992ED",
    "sucesso": "#168821",
    "alerta": "#FFCD07",
    "perigo": "#E52207",
    "info": "#155BCB",
    "cinza": "#555555",
    "cinza_claro": "#F8F8F8",
    "branco": "#FFFFFF",
    "preto": "#000000"
}

# Paleta de cores para gráficos
PALETA_GRAFICOS = [
    "#1351B4", "#2670E8", "#5992ED", "#7FB2F0", 
    "#A5C8F3", "#168821", "#FFCD07", "#E52207",
    "#F46A25", "#9B59B6", "#1ABC9C", "#34495E"
]

# Configurações de atualização
ATUALIZACAO = {
    "frequencia": "semanal",
    "dia_semana": "domingo",
    "hora": "03:00",
    "retencao_dias": 90  # Manter cache por 90 dias
}

# APIs
APIS = {
    "ibge_localidades": "https://servicodados.ibge.gov.br/api/v1/localidades",
    "ibge_malhas": "https://servicodados.ibge.gov.br/api/v3/malhas",
    "pysus_ftp": "ftp://ftp.datasus.gov.br"
}

# Faixas etárias padrão
FAIXAS_ETARIAS = {
    "< 1 ano": (0, 0),
    "1-4 anos": (1, 4),
    "5-9 anos": (5, 9),
    "10-14 anos": (10, 14),
    "15-19 anos": (15, 19),
    "20-29 anos": (20, 29),
    "30-39 anos": (30, 39),
    "40-49 anos": (40, 49),
    "50-59 anos": (50, 59),
    "60-69 anos": (60, 69),
    "70-79 anos": (70, 79),
    "80+ anos": (80, 150)
}

# Escolaridade
ESCOLARIDADE = {
    "1": "Nenhuma",
    "2": "1 a 3 anos",
    "3": "4 a 7 anos",
    "4": "8 a 11 anos",
    "5": "12+ anos",
    "9": "Ignorado"
}

# Raça/Cor
RACA_COR = {
    "1": "Branca",
    "2": "Preta",
    "3": "Amarela",
    "4": "Parda",
    "5": "Indígena",
    "9": "Ignorado"
}

# Estado civil
ESTADO_CIVIL = {
    "1": "Solteiro",
    "2": "Casado",
    "3": "Viúvo",
    "4": "Separado",
    "5": "União estável",
    "9": "Ignorado"
}
