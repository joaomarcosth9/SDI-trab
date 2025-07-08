from time import monotonic, sleep
from threading import Thread
from .message import pack
from .config import HEARTBEAT_INT, FAIL_TIMEOUT, MONITOR_INTERVAL, MONITOR_STARTUP_GRACE, LEADER_DEATH_DELAY
import threading

def start_heartbeat(node):
    def pulse():
        while not node.shutdown:
            success = node.network.send(pack("HB", pid=node.pid))
            if not success:
                node.log("[HEARTBEAT] Falha ao enviar - rede indisponível", "red")
            sleep(HEARTBEAT_INT)

    Thread(target=pulse, daemon=True).start()

def start_monitor(node):
    monitor_start_time = monotonic()
    
    def monitor():
        while not node.shutdown:
            try:
                now = monotonic()
                
                if now - monitor_start_time < MONITOR_STARTUP_GRACE:
                    sleep(MONITOR_INTERVAL)
                    continue
                
                to_remove = []
                leader_died = False
                
                for pid, last_seen in list(node.alive.items()):
                    if pid != node.pid and now - last_seen > FAIL_TIMEOUT:
                        to_remove.append(pid)
                        if pid == node.leader:
                            leader_died = True
                
                for pid in to_remove:
                    if pid in node.alive:
                        del node.alive[pid]
                        node.log(f"[MONITOR] Processo {pid} considerado morto", "red")
                
                if leader_died and not node.shutdown:
                    node.log("[MONITOR] Líder caiu - iniciando eleição", "red")
                    threading.Timer(LEADER_DEATH_DELAY, node.start_election).start()
                
            except Exception as e:
                if not node.shutdown:
                    node.log(f"[MONITOR] Erro: {e}", "red")
            
            sleep(MONITOR_INTERVAL)

    Thread(target=monitor, daemon=True).start()

