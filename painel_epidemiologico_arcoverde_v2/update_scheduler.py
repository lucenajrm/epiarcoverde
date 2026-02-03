"""
Sistema de atualização automática de dados
Atualiza os dados semanalmente

FLUXO DE ATUALIZAÇÃO:
1. Verifica conexão com PySUS
2. Tenta baixar dados de cada sistema (SIM, SINAN, SINASC)
3. Salva no cache em formato Parquet
4. Registra metadados da atualização
5. Limpa cache antigo

COMPORTAMENTO EM CASO DE FALHA:
- Erro de conexão: Registra no log, mantém cache existente
- Erro de dados: Pula o ano/sistema problemático, continua com os demais
- Falha total: Notifica via log, próxima tentativa no próximo ciclo

CONFIGURAÇÃO DO AMBIENTE VIRTUAL:
O agendador deve ser executado dentro do ambiente virtual para garantir
que todas as dependências estejam disponíveis.

Exemplo de cron com ambiente virtual:
0 3 * * 0 cd /caminho/do/dashboard && /caminho/do/dashboard/venv/bin/python update_scheduler.py --manual
"""

import schedule
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import threading
import subprocess
import sys
import os

# Configurar path para importar módulos do projeto
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config import ATUALIZACAO, DATA_DIR, CACHE_DIR
from data_loader import data_loader, DataCache

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataUpdateScheduler:
    """
    Agendador de atualização de dados
    
    RESPONSABILIDADES:
    - Executar atualizações periódicas dos dados
    - Gerenciar falhas e retries
    - Manter logs de auditoria
    - Limpar cache antigo
    
    GARANTIAS:
    - Se uma atualização falhar, o cache anterior é preservado
    - Falhas são registradas em logs para diagnóstico
    - O sistema continua operando mesmo com falhas parciais
    """
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_update = None
        self.next_update = None
        self.update_history = []  # Histórico de atualizações
        
    def update_all_data(self):
        """
        Atualiza todos os dados dos sistemas
        
        FLUXO:
        1. Verifica disponibilidade do PySUS
        2. Para cada sistema (SIM, SINAN, SINASC):
           - Tenta baixar dados de cada ano
           - Salva no cache em formato Parquet
           - Registra sucesso ou falha
        3. Limpa cache antigo
        
        COMPORTAMENTO EM FALHA:
        - Falha em um ano/sistema: Continua com os demais
        - Falha total: Registra erro, mantém cache existente
        """
        logger.info("=" * 60)
        logger.info("INICIANDO ATUALIZAÇÃO DE DADOS")
        logger.info("=" * 60)
        
        update_record = {
            'timestamp': datetime.now(),
            'status': 'started',
            'systems': {},
            'errors': []
        }
        
        try:
            # Verificar disponibilidade do PySUS
            if not data_loader.is_pysus_available():
                msg = "PySUS não disponível. Atualização abortada."
                logger.error(msg)
                update_record['errors'].append(msg)
                update_record['status'] = 'failed'
                self.update_history.append(update_record)
                return
            
            ano_atual = datetime.now().year
            anos = list(range(2020, ano_atual + 1))
            
            sistemas = ['SIM', 'SINAN', 'SINASC']
            
            for sistema in sistemas:
                logger.info(f"Atualizando dados do {sistema}...")
                sistema_record = {
                    'anos_processados': 0,
                    'anos_com_erro': 0,
                    'total_registros': 0
                }
                
                for ano in anos:
                    try:
                        if sistema == 'SIM':
                            df = data_loader.get_sim_data(ano, force_refresh=True)
                        elif sistema == 'SINAN':
                            df = data_loader.get_sinan_data(ano, force_refresh=True)
                        elif sistema == 'SINASC':
                            df = data_loader.get_sinasc_data(ano, force_refresh=True)
                        
                        registros = len(df) if df is not None else 0
                        sistema_record['anos_processados'] += 1
                        sistema_record['total_registros'] += registros
                        
                        logger.info(f"  ✓ {sistema} {ano}: {registros} registros")
                        
                    except Exception as e:
                        error_msg = f"Erro ao atualizar {sistema} {ano}: {e}"
                        logger.error(f"  ✗ {error_msg}")
                        sistema_record['anos_com_erro'] += 1
                        update_record['errors'].append(error_msg)
                        # Continua com o próximo ano (não aborta tudo)
                
                update_record['systems'][sistema] = sistema_record
                logger.info(f"{sistema}: {sistema_record['anos_processados']} anos processados, "
                           f"{sistema_record['anos_com_erro']} erros")
            
            # Limpar cache antigo
            self.clear_old_cache()
            
            # Atualizar timestamps
            self.last_update = datetime.now()
            self.next_update = self._calculate_next_update()
            
            # Determinar status final
            if update_record['errors']:
                update_record['status'] = 'partial'
                logger.warning("Atualização concluída com ALGUNS ERROS")
            else:
                update_record['status'] = 'success'
                logger.info("Atualização concluída com SUCESSO")
            
            self.update_history.append(update_record)
            
            logger.info(f"Próxima atualização: {self.next_update}")
            logger.info("=" * 60)
            
        except Exception as e:
            error_msg = f"Erro CRÍTICO na atualização: {e}"
            logger.error(error_msg)
            update_record['errors'].append(error_msg)
            update_record['status'] = 'failed'
            self.update_history.append(update_record)
    
    def _calculate_next_update(self) -> datetime:
        """Calcula próxima atualização baseada na configuração"""
        dias_semana = {
            'domingo': 0, 'segunda': 1, 'terca': 2, 'quarta': 3,
            'quinta': 4, 'sexta': 5, 'sabado': 6
        }
        
        dia_alvo = dias_semana.get(ATUALIZACAO['dia_semana'], 6)
        hora_alvo = int(ATUALIZACAO['hora'].split(':')[0])
        minuto_alvo = int(ATUALIZACAO['hora'].split(':')[1])
        
        agora = datetime.now()
        dias_ate = (dia_alvo - agora.weekday()) % 7
        
        if dias_ate == 0 and agora.hour >= hora_alvo:
            dias_ate = 7
        
        proxima = agora + timedelta(days=dias_ate)
        proxima = proxima.replace(hour=hora_alvo, minute=minuto_alvo, second=0, microsecond=0)
        
        return proxima
    
    def clear_old_cache(self):
        """
        Limpa cache antigo baseado na configuração de retenção
        
        Remove arquivos de cache mais antigos que o período configurado
        em ATUALIZACAO['retencao_dias']
        """
        try:
            cache = DataCache()
            cache_info = cache.get_cache_info()
            
            logger.info(f"Limpando cache antigo (retenção: {ATUALIZACAO['retencao_dias']} dias)")
            logger.info(f"Cache atual: {cache_info['total_data_files']} arquivos, "
                       f"{cache_info['total_size_mb']} MB")
            
            limite = datetime.now() - timedelta(days=ATUALIZACAO['retencao_dias'])
            
            removidos = 0
            for meta_file in CACHE_DIR.glob("*_meta.json"):
                try:
                    import json
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    cache_time = datetime.fromisoformat(metadata.get('timestamp', datetime.now().isoformat()))
                    
                    if cache_time < limite:
                        # Remover arquivo de dados
                        data_file = CACHE_DIR / metadata.get('data_file', '')
                        if data_file.exists():
                            data_file.unlink()
                        # Remover metadados
                        meta_file.unlink()
                        removidos += 1
                        logger.info(f"Cache removido: {meta_file.stem}")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar cache {meta_file}: {e}")
            
            logger.info(f"Limpeza concluída: {removidos} arquivos removidos")
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
    
    def job(self):
        """Tarefa de atualização executada pelo agendador"""
        logger.info("Executando tarefa agendada de atualização")
        self.update_all_data()
    
    def start(self):
        """
        Inicia o agendador
        
        CONFIGURAÇÃO:
        - Executa a primeira atualização imediatamente
        - Agenda próximas execuções conforme configuração
        - Inicia thread em background para verificação periódica
        """
        if self.running:
            logger.warning("Agendador já está em execução")
            return
        
        logger.info("=" * 60)
        logger.info("INICIANDO AGENDADOR DE ATUALIZAÇÃO")
        logger.info("=" * 60)
        
        # Configurar agendamento
        dia = ATUALIZACAO['dia_semana']
        hora = ATUALIZACAO['hora']
        
        logger.info(f"Configuração: {dia} às {hora}")
        logger.info(f"Frequência: {ATUALIZACAO['frequencia']}")
        
        if dia == 'domingo':
            schedule.every().sunday.at(hora).do(self.job)
        elif dia == 'segunda':
            schedule.every().monday.at(hora).do(self.job)
        elif dia == 'terca':
            schedule.every().tuesday.at(hora).do(self.job)
        elif dia == 'quarta':
            schedule.every().wednesday.at(hora).do(self.job)
        elif dia == 'quinta':
            schedule.every().thursday.at(hora).do(self.job)
        elif dia == 'sexta':
            schedule.every().friday.at(hora).do(self.job)
        elif dia == 'sabado':
            schedule.every().saturday.at(hora).do(self.job)
        
        self.running = True
        self.next_update = self._calculate_next_update()
        
        # Executar primeira atualização
        logger.info("Executando atualização inicial...")
        self.job()
        
        # Iniciar thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info(f"Agendador iniciado. Próxima atualização: {self.next_update}")
        logger.info("=" * 60)
    
    def _run_scheduler(self):
        """Loop do agendador - executa em thread separada"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
    
    def stop(self):
        """Para o agendador de forma segura"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Agendador parado")
    
    def get_status(self) -> dict:
        """Retorna status completo do agendador"""
        return {
            'running': self.running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'next_update': self.next_update.isoformat() if self.next_update else None,
            'frequency': ATUALIZACAO['frequencia'],
            'day': ATUALIZACAO['dia_semana'],
            'time': ATUALIZACAO['hora'],
            'update_history_count': len(self.update_history),
            'pysus_available': data_loader.is_pysus_available()
        }
    
    def get_update_history(self) -> list:
        """Retorna histórico de atualizações"""
        return self.update_history


# Instância global
scheduler = DataUpdateScheduler()


def run_manual_update():
    """Executa atualização manual única"""
    print("=" * 60)
    print("ATUALIZAÇÃO MANUAL DE DADOS")
    print("=" * 60)
    print()
    
    # Verificar ambiente virtual
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  AVISO: Ambiente virtual não detectado!")
        print("Recomenda-se ativar o ambiente virtual antes de executar.")
        print()
        print("Para ativar:")
        print("  source venv/bin/activate")
        print()
        resposta = input("Deseja continuar mesmo assim? (s/n): ")
        if resposta.lower() != 's':
            print("Operação cancelada.")
            return
    
    scheduler.update_all_data()
    
    print()
    print("=" * 60)
    print("Atualização concluída!")
    print("=" * 60)


def run_scheduler_daemon():
    """Executa o agendador como daemon (em background)"""
    print("=" * 60)
    print("AGENDADOR DE ATUALIZAÇÃO AUTOMÁTICA")
    print("=" * 60)
    print()
    
    # Verificar ambiente virtual
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  AVISO: Ambiente virtual não detectado!")
        print("O agendador deve ser executado dentro do ambiente virtual.")
        print()
        print("Uso correto:")
        print("  source venv/bin/activate")
        print("  python update_scheduler.py --daemon")
        print()
        print("Ou via script:")
        print("  ./run.sh scheduler")
        print()
        resposta = input("Deseja continuar mesmo assim? (s/n): ")
        if resposta.lower() != 's':
            print("Operação cancelada.")
            return
    
    print(f"Configuração: {ATUALIZACAO['dia_semana']} às {ATUALIZACAO['hora']}")
    print(f"Frequência: {ATUALIZACAO['frequencia']}")
    print()
    print("Pressione Ctrl+C para parar")
    print("=" * 60)
    print()
    
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print("\nParando agendador...")
        scheduler.stop()
        print("Agendador parado.")


def show_status():
    """Mostra status do agendador"""
    status = scheduler.get_status()
    
    print("=" * 60)
    print("STATUS DO AGENDADOR")
    print("=" * 60)
    print()
    print(f"Status: {'✅ Executando' if status['running'] else '⏹️  Parado'}")
    print(f"PySUS: {'✅ Disponível' if status['pysus_available'] else '❌ Indisponível'}")
    print()
    print("Agendamento:")
    print(f"  Frequência: {status['frequency']}")
    print(f"  Dia: {status['day']}")
    print(f"  Hora: {status['time']}")
    print()
    print("Atualizações:")
    if status['last_update']:
        last = datetime.fromisoformat(status['last_update'])
        print(f"  Última: {last.strftime('%d/%m/%Y %H:%M')}")
    else:
        print(f"  Última: Nenhuma")
    
    if status['next_update']:
        next_up = datetime.fromisoformat(status['next_update'])
        print(f"  Próxima: {next_up.strftime('%d/%m/%Y %H:%M')}")
    
    print(f"  Total no histórico: {status['update_history_count']}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Gerenciador de atualização de dados - Dashboard Arcoverde/PE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLOS DE USO:
  # Atualização manual (executa uma vez)
  python update_scheduler.py --manual
  
  # Iniciar agendador em background
  python update_scheduler.py --daemon
  
  # Verificar status
  python update_scheduler.py --status

CONFIGURAÇÃO DO CRON (atualização semanal):
  # Editar crontab
  crontab -e
  
  # Adicionar linha (domingo 3h da manhã)
  0 3 * * 0 cd /caminho/do/dashboard && venv/bin/python update_scheduler.py --manual >> logs/cron.log 2>&1

NOTAS:
  - Sempre execute dentro do ambiente virtual
  - Logs são salvos em logs/scheduler.log
  - Cache é mantido em formato Parquet (seguro)
        """
    )
    
    parser.add_argument('--manual', action='store_true', 
                        help='Executa atualização manual única')
    parser.add_argument('--daemon', action='store_true', 
                        help='Executa como daemon (background)')
    parser.add_argument('--status', action='store_true', 
                        help='Mostra status do agendador')
    
    args = parser.parse_args()
    
    if args.manual:
        run_manual_update()
    elif args.daemon:
        run_scheduler_daemon()
    elif args.status:
        show_status()
    else:
        parser.print_help()
