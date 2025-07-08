"""
Implementação do algoritmo de eleição Bully para sistemas distribuídos.

O algoritmo Bully é usado para eleger um coordenador (líder) em um sistema
distribuído onde processos têm IDs únicos e apenas um pode ser líder.
"""

from threading import Event, Thread
from time import monotonic, sleep
from .message import pack, unpack
from .config import BULLY_TIMEOUT, BULLY_POLL_INTERVAL

def bully(node):
    """
    Implementa o algoritmo de eleição Bully para eleger um líder.
    
    O algoritmo funciona da seguinte forma:
    1. Envia mensagem ELECTION para todos os processos via multicast
    2. Aguarda respostas OK de processos com PID maior
    3. Se recebe OK, para a eleição (processo maior assumirá liderança)
    4. Se não recebe OK no timeout, assume liderança
    
    Args:
        node: Instância do nó que está iniciando a eleição
    """
    node.log("[ELEIÇÃO] Iniciando eleição bully", "red")
    
    # Reseta o flag antes de iniciar eleição
    node.received_ok = False
    
    # Manda por multicast para TODOS 
    node.send("ELECTION", source=node.pid)
    node.log("[ELEIÇÃO] Enviado ELECTION para todos", "yellow")

    # Aguarda por respostas OK
    start_time = monotonic()
    timeout = BULLY_TIMEOUT
    
    while monotonic() - start_time < timeout:
        if node.received_ok:
            node.log("[ELEIÇÃO] Recebido OK de processo maior - parando", "green")
            node.received_ok = False  # Reseta para próxima eleição
            node.log("[ELEIÇÃO] Algoritmo bully finalizado (OK recebido)", "green")
            return
        sleep(BULLY_POLL_INTERVAL)

    # Se chegou aqui, ninguém maior respondeu
    node.log("[ELEIÇÃO] Timeout - nenhum processo maior respondeu", "yellow")
    
    # Inicia consenso de round antes de assumir liderança
    node.log("[ELEIÇÃO] Iniciando consenso de round", "green")
    node.start_round_consensus()
    
    node.log("[ELEIÇÃO] Algoritmo bully finalizado (timeout)", "yellow")

