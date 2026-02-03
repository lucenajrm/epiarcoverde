"""
Módulo para carregamento e processamento de dados do PySUS e IBGE

SEGURANÇA DO CACHE:
- Formato: Parquet (mais seguro que pickle)
- Permissões: 0o600 (apenas proprietário pode ler/escrever)
- Localização: Diretório 'cache' com permissões restritas
- Metadados: Timestamp e informações de origem dos dados
"""

import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
import time
import os
import stat

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_loader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from config import (
    MUNICIPIO, SISTEMAS, DOENCAS_SINAN, APIS, 
    CACHE_DIR, DATA_DIR, FAIXAS_ETARIAS, CIDS_PRINCIPAIS
)


class IBGEClient:
    """Cliente para API do IBGE"""
    
    def __init__(self):
        self.base_url = APIS["ibge_localidades"]
        self.session = requests.Session()
        
    def get_municipio_info(self, codigo_ibge: int) -> Dict:
        """Obtém informações detalhadas do município"""
        try:
            url = f"{self.base_url}/municipios/{codigo_ibge}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao obter informações do município: {e}")
            return {}
    
    def get_mesorregioes(self, uf: str) -> List[Dict]:
        """Obtém mesorregiões da UF"""
        try:
            url = f"{self.base_url}/estados/{uf}/mesorregioes"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao obter mesorregiões: {e}")
            return []
    
    def get_microrregioes(self, uf: str) -> List[Dict]:
        """Obtém microrregiões da UF"""
        try:
            url = f"{self.base_url}/estados/{uf}/microrregioes"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao obter microrregiões: {e}")
            return []
    
    def get_municipios_uf(self, uf: str) -> List[Dict]:
        """Obtém todos os municípios da UF"""
        try:
            url = f"{self.base_url}/estados/{uf}/municipios"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao obter municípios da UF: {e}")
            return []
    
    def get_geojson_municipio(self, codigo_ibge: int) -> Optional[Dict]:
        """Obtém o GeoJSON do município para mapas"""
        try:
            url = f"{APIS['ibge_malhas']}/municipios/{codigo_ibge}?formato=application/json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao obter GeoJSON: {e}")
            return None


class DataCache:
    """
    Sistema de cache seguro para dados
    
    MELHORIAS DE SEGURANÇA:
    - Formato Parquet (seguro, não executa código)
    - Permissões 0o600 (apenas proprietário)
    - Metadados em JSON (auditoria)
    - Validação de integridade
    """
    
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        # Configurar permissões restritas no diretório de cache
        os.chmod(self.cache_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        logger.info(f"Cache inicializado em: {self.cache_dir} (permissões: 0o700)")
        
    def _get_cache_path(self, key: str) -> Tuple[Path, Path]:
        """Retorna caminhos para dados e metadados"""
        safe_key = key.replace('/', '_').replace('\\', '_')
        data_path = self.cache_dir / f"{safe_key}.parquet"
        meta_path = self.cache_dir / f"{safe_key}_meta.json"
        return data_path, meta_path
    
    def _set_file_permissions(self, filepath: Path):
        """Define permissões restritas no arquivo (apenas proprietário)"""
        try:
            os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            logger.warning(f"Não foi possível definir permissões em {filepath}: {e}")
    
    def get(self, key: str, max_age_hours: int = 168) -> Optional[pd.DataFrame]:  # 168h = 1 semana
        """Obtém dados do cache se válidos"""
        data_path, meta_path = self._get_cache_path(key)
        
        if not data_path.exists() or not meta_path.exists():
            return None
        
        try:
            # Ler metadados
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Verificar idade do cache
            cache_time_str = metadata.get('timestamp')
            if cache_time_str:
                cache_time = datetime.fromisoformat(cache_time_str)
                age = datetime.now() - cache_time
                if age > timedelta(hours=max_age_hours):
                    logger.info(f"Cache expirado para {key} (idade: {age})")
                    return None
            
            # Carregar dados do Parquet
            df = pd.read_parquet(data_path)
            
            logger.info(f"Dados recuperados do cache: {key} ({len(df)} registros)")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao ler cache {key}: {e}")
            return None
    
    def set(self, key: str, df: pd.DataFrame, source: str = "unknown"):
        """Salva dados no cache com metadados"""
        data_path, meta_path = self._get_cache_path(key)
        
        try:
            # Salvar dados em formato Parquet
            df.to_parquet(data_path, index=False, compression='snappy')
            self._set_file_permissions(data_path)
            
            # Salvar metadados em JSON
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'key': key,
                'source': source,
                'records': len(df),
                'columns': list(df.columns),
                'data_file': str(data_path.name),
                'version': '1.0'
            }
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            self._set_file_permissions(meta_path)
            
            logger.info(f"Dados salvos no cache: {key} ({len(df)} registros, fonte: {source})")
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache {key}: {e}")
    
    def get_metadata(self, key: str) -> Optional[Dict]:
        """Obtém metadados de um cache"""
        _, meta_path = self._get_cache_path(key)
        
        if not meta_path.exists():
            return None
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler metadados de {key}: {e}")
            return None
    
    def list_all(self) -> List[Dict]:
        """Lista todos os caches com seus metadados"""
        caches = []
        for meta_file in self.cache_dir.glob("*_meta.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    caches.append(metadata)
            except Exception as e:
                logger.warning(f"Erro ao ler {meta_file}: {e}")
        return caches
    
    def clear(self):
        """Limpa todo o cache"""
        for cache_file in self.cache_dir.glob("*.parquet"):
            cache_file.unlink()
        for meta_file in self.cache_dir.glob("*_meta.json"):
            meta_file.unlink()
        logger.info("Cache limpo completamente")
    
    def get_cache_info(self) -> Dict:
        """Retorna informações sobre o estado do cache"""
        total_files = len(list(self.cache_dir.glob("*.parquet")))
        total_meta = len(list(self.cache_dir.glob("*_meta.json")))
        
        # Calcular tamanho total
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*"))
        
        return {
            'cache_dir': str(self.cache_dir),
            'permissions': oct(self.cache_dir.stat().st_mode)[-3:],
            'total_data_files': total_files,
            'total_meta_files': total_meta,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }


class PySUSDataLoader:
    """Carregador de dados do PySUS"""
    
    def __init__(self, demo_mode: bool = False):
        self.cache = DataCache()
        self.ibge = IBGEClient()
        self._pysus_available = self._check_pysus()
        self._demo_mode = demo_mode
        self._last_update_info = {
            'timestamp': None,
            'source': None,
            'status': 'not_initialized'
        }
        
    def _check_pysus(self) -> bool:
        """Verifica se PySUS está disponível"""
        try:
            import pysus
            logger.info(f"PySUS versão {pysus.__version__} disponível")
            return True
        except ImportError:
            logger.warning("PySUS não instalado.")
            return False
    
    def _generate_simulated_data(self, sistema: str, ano: int) -> pd.DataFrame:
        """
        Gera dados simulados para demonstração quando PySUS não está disponível
        
        IMPORTANTE: Estes dados são FICTÍCIOS e devem ser usados apenas para
        demonstração do funcionamento do dashboard. NÃO use para análise real.
        """
        logger.warning(f"[MODO DEMONSTRAÇÃO] Gerando dados simulados para {sistema} - {ano}")
        
        np.random.seed(ano + hash(sistema) % 10000)
        n_records = np.random.randint(50, 500)
        
        if sistema == "SIM":
            data = {
                'ano': [ano] * n_records,
                'mes': np.random.randint(1, 13, n_records),
                'sexo': np.random.choice(['M', 'F'], n_records),
                'idade': np.random.exponential(45, n_records).astype(int),
                'raca_cor': np.random.choice(['1', '2', '3', '4', '5'], n_records, p=[0.4, 0.1, 0.02, 0.45, 0.03]),
                'escolaridade': np.random.choice(['1', '2', '3', '4', '5', '9'], n_records),
                'estado_civil': np.random.choice(['1', '2', '3', '4', '5', '9'], n_records),
                'causa_basica': np.random.choice(CIDS_PRINCIPAIS[:8], n_records),
                'ocupacao': np.random.choice(['', '99999'], n_records, p=[0.7, 0.3]),
                'local_obito': np.random.choice([1, 2, 3, 4, 5], n_records, p=[0.5, 0.3, 0.1, 0.05, 0.05]),
                'assistencia_medica': np.random.choice([1, 2, 9], n_records, p=[0.8, 0.15, 0.05]),
            }
        elif sistema == "SINAN":
            doencas = list(DOENCAS_SINAN.keys())[:8]
            data = {
                'ano': [ano] * n_records,
                'mes': np.random.randint(1, 13, n_records),
                'semana_notificacao': np.random.randint(1, 53, n_records),
                'sexo': np.random.choice(['M', 'F'], n_records),
                'idade': np.random.exponential(35, n_records).astype(int),
                'raca_cor': np.random.choice(['1', '2', '3', '4', '5'], n_records, p=[0.4, 0.1, 0.02, 0.45, 0.03]),
                'escolaridade': np.random.choice(['0', '1', '2', '3', '4', '5', '9'], n_records),
                'doenca': np.random.choice(doencas, n_records),
                'evolucao': np.random.choice(['1', '2', '3', '4', '9'], n_records, p=[0.7, 0.15, 0.05, 0.05, 0.05]),
                'encerramento': np.random.choice([1, 2], n_records, p=[0.9, 0.1]),
            }
        elif sistema == "SINASC":
            data = {
                'ano': [ano] * n_records,
                'mes': np.random.randint(1, 13, n_records),
                'sexo': np.random.choice(['M', 'F', 'I'], n_records, p=[0.51, 0.48, 0.01]),
                'peso': np.random.normal(3200, 500, n_records).astype(int),
                'gestacao_semanas': np.random.normal(38, 2, n_records).astype(int),
                'idade_mae': np.random.normal(27, 7, n_records).astype(int),
                'raca_cor_mae': np.random.choice(['1', '2', '3', '4', '5'], n_records, p=[0.4, 0.1, 0.02, 0.45, 0.03]),
                'escolaridade_mae': np.random.choice(['0', '1', '2', '3', '4', '5'], n_records),
                'consultas_pre_natal': np.random.choice(['1', '2', '3', '4', '5', '6', '7', '8', '9'], n_records),
                'tipo_parto': np.random.choice(['1', '2', '9'], n_records, p=[0.6, 0.35, 0.05]),
                'apgar_1': np.random.choice(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'], n_records),
                'apgar_5': np.random.choice(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'], n_records),
            }
        else:
            data = {}
        
        df = pd.DataFrame(data)
        df['codigo_municipio'] = MUNICIPIO['codigo_ibge']
        df['municipio'] = MUNICIPIO['nome']
        df['uf'] = MUNICIPIO['uf']
        df['_demo_data'] = True  # Flag para identificar dados simulados
        
        return df
    
    def _handle_pysus_error(self, sistema: str, ano: int, error: Exception) -> pd.DataFrame:
        """
        Trata erros do PySUS de acordo com o modo de operação
        
        Em produção: levanta exceção para não mascarar erros
        Em demonstração: retorna dados simulados com aviso
        """
        error_msg = str(error)
        logger.error(f"Erro ao carregar {sistema} {ano}: {error_msg}")
        
        if self._demo_mode:
            logger.warning(f"Modo demonstração ativo. Retornando dados simulados para {sistema}.")
            return self._generate_simulated_data(sistema, ano)
        else:
            # Em produção, não usar dados simulados silenciosamente
            raise ConnectionError(
                f"Falha na conexão com PySUS para {sistema} ({ano}). "
                f"Erro: {error_msg}. "
                f"Verifique a conexão com a internet e a disponibilidade do DATASUS."
            )
    
    def get_sim_data(self, ano: int, force_refresh: bool = False) -> pd.DataFrame:
        """Obtém dados do SIM (Sistema de Informação sobre Mortalidade)"""
        cache_key = f"sim_{MUNICIPIO['codigo_ibge']}_{ano}"
        
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._last_update_info = {
                    'timestamp': datetime.now(),
                    'source': 'cache',
                    'status': 'success'
                }
                return cached
        
        try:
            if self._pysus_available:
                from pysus.online_data.SIM import download
                # Download para o estado de Pernambuco
                df = download(MUNICIPIO['uf'], ano)
                # Filtrar para Arcoverde
                df = df[df['CODMUNOCOR'] == str(MUNICIPIO['codigo_ibge'])]
                source = 'pysus'
            else:
                if self._demo_mode:
                    df = self._generate_simulated_data("SIM", ano)
                    source = 'simulated'
                else:
                    raise ConnectionError("PySUS não disponível e modo demonstração desativado.")
            
            self.cache.set(cache_key, df, source=source)
            self._last_update_info = {
                'timestamp': datetime.now(),
                'source': source,
                'status': 'success'
            }
            return df
            
        except Exception as e:
            return self._handle_pysus_error("SIM", ano, e)
    
    def get_sinan_data(self, ano: int, doenca: str = None, force_refresh: bool = False) -> pd.DataFrame:
        """Obtém dados do SINAN (Sistema de Informação de Agravos de Notificação)"""
        cache_key = f"sinan_{MUNICIPIO['codigo_ibge']}_{ano}_{doenca or 'all'}"
        
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._last_update_info = {
                    'timestamp': datetime.now(),
                    'source': 'cache',
                    'status': 'success'
                }
                return cached
        
        try:
            if self._pysus_available:
                from pysus.online_data.SINAN import download
                if doenca:
                    df = download(doenca, ano)
                else:
                    # Download de doença mais comum como exemplo
                    df = download("DENGUE", ano)
                # Filtrar para Arcoverde
                df = df[df['ID_MUNICIP'] == str(MUNICIPIO['codigo_ibge'])]
                source = 'pysus'
            else:
                if self._demo_mode:
                    df = self._generate_simulated_data("SINAN", ano)
                    source = 'simulated'
                else:
                    raise ConnectionError("PySUS não disponível e modo demonstração desativado.")
            
            self.cache.set(cache_key, df, source=source)
            self._last_update_info = {
                'timestamp': datetime.now(),
                'source': source,
                'status': 'success'
            }
            return df
            
        except Exception as e:
            return self._handle_pysus_error("SINAN", ano, e)
    
    def get_sinasc_data(self, ano: int, force_refresh: bool = False) -> pd.DataFrame:
        """Obtém dados do SINASC (Sistema de Informações sobre Nascidos Vivos)"""
        cache_key = f"sinasc_{MUNICIPIO['codigo_ibge']}_{ano}"
        
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._last_update_info = {
                    'timestamp': datetime.now(),
                    'source': 'cache',
                    'status': 'success'
                }
                return cached
        
        try:
            if self._pysus_available:
                from pysus.online_data.SINASC import download
                df = download(MUNICIPIO['uf'], ano)
                # Filtrar para Arcoverde
                df = df[df['CODMUNNASC'] == str(MUNICIPIO['codigo_ibge'])]
                source = 'pysus'
            else:
                if self._demo_mode:
                    df = self._generate_simulated_data("SINASC", ano)
                    source = 'simulated'
                else:
                    raise ConnectionError("PySUS não disponível e modo demonstração desativado.")
            
            self.cache.set(cache_key, df, source=source)
            self._last_update_info = {
                'timestamp': datetime.now(),
                'source': source,
                'status': 'success'
            }
            return df
            
        except Exception as e:
            return self._handle_pysus_error("SINASC", ano, e)
    
    def get_multi_years_data(self, sistema: str, anos: List[int], **kwargs) -> pd.DataFrame:
        """Obtém dados de múltiplos anos e concatena"""
        dfs = []
        
        for ano in anos:
            try:
                if sistema.upper() == "SIM":
                    df = self.get_sim_data(ano, **kwargs)
                elif sistema.upper() == "SINAN":
                    df = self.get_sinan_data(ano, **kwargs)
                elif sistema.upper() == "SINASC":
                    df = self.get_sinasc_data(ano, **kwargs)
                else:
                    continue
                
                if df is not None and len(df) > 0:
                    dfs.append(df)
                    
            except Exception as e:
                logger.error(f"Erro ao carregar {sistema} para {ano}: {e}")
                # Em modo não-demo, propagar o erro
                if not self._demo_mode:
                    raise
        
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()
    
    def get_last_update_info(self) -> Dict:
        """Retorna informações sobre a última atualização"""
        return self._last_update_info.copy()
    
    def is_demo_mode(self) -> bool:
        """Retorna se está em modo demonstração"""
        return self._demo_mode
    
    def is_pysus_available(self) -> bool:
        """Retorna se PySUS está disponível"""
        return self._pysus_available


# Instância global do loader
# Por padrão, modo demonstração DESATIVADO (segurança)
data_loader = PySUSDataLoader(demo_mode=False)


def set_demo_mode(enabled: bool = True):
    """
    Ativa/desativa modo demonstração
    
    ATENÇÃO: Modo demonstração usa dados FICTÍCIOS.
    Use apenas para testes e demonstrações do funcionamento do dashboard.
    """
    global data_loader
    data_loader = PySUSDataLoader(demo_mode=enabled)
    logger.warning(f"Modo demonstração {'ATIVADO' if enabled else 'DESATIVADO'}")


# Funções auxiliares para processamento de dados

def calcular_faixa_etaria(idade: int) -> str:
    """Calcula a faixa etária a partir da idade"""
    for faixa, (min_idade, max_idade) in FAIXAS_ETARIAS.items():
        if min_idade <= idade <= max_idade:
            return faixa
    return "Não informado"


def processar_cid(codigo: str) -> Dict:
    """Processa código CID e retorna informações"""
    if pd.isna(codigo) or codigo == '':
        return {'capitulo': 'Não informado', 'descricao': 'Não informado'}
    
    # Mapeamento simplificado de CIDs
    cid_map = {
        'A': ('I', 'Algumas doenças infecciosas e parasitárias'),
        'B': ('I', 'Algumas doenças infecciosas e parasitárias'),
        'C': ('II', 'Neoplasias'),
        'D': ('II', 'Neoplasias e doenças do sangue'),
        'E': ('IV', 'Doenças endócrinas, nutricionais e metabólicas'),
        'F': ('V', 'Transtornos mentais e comportamentais'),
        'G': ('VI', 'Doenças do sistema nervoso'),
        'H': ('VII-VIII', 'Doenças do olho e ouvido'),
        'I': ('IX', 'Doenças do aparelho circulatório'),
        'J': ('X', 'Doenças do aparelho respiratório'),
        'K': ('XI', 'Doenças do aparelho digestivo'),
        'L': ('XII', 'Doenças da pele'),
        'M': ('XIII', 'Doenças do sistema osteomuscular'),
        'N': ('XIV', 'Doenças do aparelho geniturinário'),
        'O': ('XV', 'Gravidez, parto e puerpério'),
        'P': ('XVI', 'Afecções originadas no período perinatal'),
        'Q': ('XVII', 'Malformações congênitas'),
        'R': ('XVIII', 'Sintomas e achados anormais'),
        'S': ('XIX', 'Lesões, envenenamentos'),
        'T': ('XIX', 'Lesões, envenenamentos'),
        'V': ('XX', 'Causas externas'),
        'W': ('XX', 'Causas externas'),
        'X': ('XX', 'Causas externas'),
        'Y': ('XX', 'Causas externas'),
    }
    
    primeira_letra = str(codigo)[0].upper() if codigo else ''
    info = cid_map.get(primeira_letra, ('XXI', 'Outras condições'))
    
    return {
        'capitulo': info[0],
        'descricao': info[1],
        'codigo_original': codigo
    }


def agregar_por_periodo(df: pd.DataFrame, coluna_data: str = 'mes', 
                        coluna_valor: str = None) -> pd.DataFrame:
    """Agrega dados por período"""
    if coluna_valor:
        return df.groupby(coluna_data)[coluna_valor].sum().reset_index()
    return df.groupby(coluna_data).size().reset_index(name='quantidade')


def calcular_taxas(df: pd.DataFrame, populacao: int, 
                   coluna_contagem: str = 'quantidade') -> pd.DataFrame:
    """Calcula taxas por 100.000 habitantes"""
    df['taxa_100mil'] = (df[coluna_contagem] / populacao) * 100000
    return df
