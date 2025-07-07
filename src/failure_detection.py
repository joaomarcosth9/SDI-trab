"""
Módulo de detecção de falhas para o sistema distribuído.

Implementa heartbeat periódico e monitoramento de processos para detectar
falhas por timeout e iniciar eleições quando necessário.
"""

from time import monotonic, sleep
from threading import Thread
from .message import pack
from .config import HEARTBEAT_INT, FAIL_TIMEOUT

def start_heartbeat(node):
    """
    Inicia thread de heartbeat para o processo.
    
    Envia mensagens de heartbeat (HB) periodicamente para todos os processos
    no grupo multicast, permitindo que outros processos saibam que este
    processo está vivo.
    
    Args:
        node: Instância do nó que enviará os heartbeats
        
    Note:
        A thread é marcada como daemon para terminar automaticamente
        quando o processo principal termina.
    """
    def pulse():
        while True:
            success = node.network.send(pack("HB", pid=node.pid))
            if not success:
                node.log("Falha ao enviar heartbeat - rede indisponível", "💔", "red")
            sleep(HEARTBEAT_INT)

    Thread(target=pulse, daemon=True).start()

def start_monitor(node):
    """
    Inicia thread de monitoramento para detecção de falhas.
    
    Monitora continuamente a tabela de processos vivos, removendo processos
    que não enviaram heartbeat dentro do FAIL_TIMEOUT. Inicia eleição se
    o líder atual for detectado como morto.
    
    Args:
        node: Instância do nó que executará o monitoramento
        
    Note:
        A thread é marcada como daemon para terminar automaticamente
        quando o processo principal termina.
    """
    def monitor():
        while True:
            now = monotonic()
            dead = [pid for pid, ts in node.alive.items()
                    if now - ts > FAIL_TIMEOUT]
            for pid in dead:
                node.alive.pop(pid, None)
                node.log(f"Processo {pid} considerado MORTO")
                if pid == node.leader:
                    node.log("Líder caiu ➜ iniciando eleição")
                    node.start_election()
            sleep(1)

    Thread(target=monitor, daemon=True).start()

