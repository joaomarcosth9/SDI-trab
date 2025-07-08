from threading import Event, Thread
from time import monotonic, sleep
from .message import pack, unpack
from .config import BULLY_TIMEOUT, BULLY_POLL_INTERVAL

def bully(node):
    node.log("[ELEIÇÃO] Iniciando eleição bully", "red")
    
    node.received_ok = False
    
    node.send("ELECTION", source=node.pid)
    node.log("[ELEIÇÃO] Enviado ELECTION para todos", "yellow")

    start_time = monotonic()
    timeout = BULLY_TIMEOUT
    
    while monotonic() - start_time < timeout:
        if node.received_ok:
            node.log("[ELEIÇÃO] Recebido OK de processo maior - parando", "green")
            node.received_ok = False
            node.log("[ELEIÇÃO] Algoritmo bully finalizado (OK recebido)", "green")
            return
        sleep(BULLY_POLL_INTERVAL)

    node.log("[ELEIÇÃO] Timeout - nenhum processo maior respondeu", "yellow")
    
    node.log("[ELEIÇÃO] Assumindo liderança", "green")
    node.become_leader()
    
    node.log("[ELEIÇÃO] Algoritmo bully finalizado (timeout)", "yellow")

