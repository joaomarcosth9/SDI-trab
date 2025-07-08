"""
Módulo de detecção de falhas para o sistema distribuído.

Implementa heartbeat periódico e monitoramento de processos para detectar
falhas por timeout e iniciar eleições quando necessário.
"""

from time import monotonic, sleep
from threading import Thread
from .message import pack
from .config import HEARTBEAT_INT, FAIL_TIMEOUT, MONITOR_INTERVAL, MONITOR_STARTUP_GRACE, LEADER_DEATH_DELAY
import threading

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
        while not node.shutdown:
            success = node.network.send(pack("HB", pid=node.pid))
            if not success:
                node.log("[HEARTBEAT] Falha ao enviar - rede indisponível", "red")
            sleep(HEARTBEAT_INT)

    Thread(target=pulse, daemon=True).start()

def start_monitor(node):
    """
    Inicia thread de monitoramento para detecção de falhas.
    """
    # Tempo de inicialização do monitor
    monitor_start_time = monotonic()
    
    def monitor():
        while not node.shutdown:
            try:
                now = monotonic()
                
                # Carência inicial após iniciar monitor
                # (para não marcar processos como mortos durante descoberta inicial)
                if now - monitor_start_time < MONITOR_STARTUP_GRACE:
                    sleep(MONITOR_INTERVAL)
                    continue
                
                # Lista de processos para remover
                to_remove = []
                leader_died = False
                
                # Verifica quem está morto
                for pid, last_seen in list(node.alive.items()):
                    if pid != node.pid and now - last_seen > FAIL_TIMEOUT:
                        to_remove.append(pid)
                        if pid == node.leader:
                            leader_died = True
                
                # Remove os mortos
                for pid in to_remove:
                    if pid in node.alive:
                        del node.alive[pid]
                        node.log(f"[MONITOR] Processo {pid} considerado morto", "red")
                
                # Se líder morreu, inicia eleição
                if leader_died and not node.shutdown:
                    node.log("[MONITOR] Líder caiu - iniciando eleição", "red")
                    threading.Timer(LEADER_DEATH_DELAY, node.start_election).start()
                
            except Exception as e:
                if not node.shutdown:
                    node.log(f"[MONITOR] Erro: {e}", "red")
            
            sleep(MONITOR_INTERVAL)

    Thread(target=monitor, daemon=True).start()

