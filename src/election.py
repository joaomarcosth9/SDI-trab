"""
Implementação do algoritmo de eleição Bully para sistemas distribuídos.

O algoritmo Bully é usado para eleger um coordenador (líder) em um sistema
distribuído onde processos têm IDs únicos e apenas um pode ser líder.
"""

from threading import Event, Thread
from time import monotonic, sleep
from .message import pack, unpack
from .config import BULLY_TIMEOUT

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
    node.log("Iniciando eleição bully - enviando para TODOS os processos", "🔥", "red")
    
    # Reseta o flag antes de iniciar eleição
    node.received_ok = False
    
    # Manda por multicast para TODOS 
    node.send("ELECTION", source=node.pid)
    node.log(f"Enviado ELECTION para todos os processos", "📡", "yellow")

    # Aguarda por respostas OK
    start_time = monotonic()
    timeout = BULLY_TIMEOUT
    
    while monotonic() - start_time < timeout:
        # Verifica se recebeu OK
        if node.received_ok:
            node.log("Recebido OK de processo maior - parando eleição", "✅", "green")
            node.received_ok = False
            node.log("Algoritmo bully finalizado (OK recebido)", "🏁", "green")
            return
        
        # Verifica se já há líder válido (pode ter sido detectado durante eleição)
        if node.leader is not None and node.leader > node.pid:
            node.log(f"Líder {node.leader} detectado durante eleição - cancelando", "🛑", "blue")
            node.log("Algoritmo bully finalizado (líder detectado)", "🏁", "blue")
            return
            
        sleep(0.1)

    # Se chegou aqui, ninguém maior respondeu
    node.log("Timeout da eleição - nenhum processo maior respondeu", "⏰", "yellow")
    
    # Verifica se há processos maiores ANTES de imprimir que vai assumir
    alive_pids = list(node.alive.keys())
    bigger_processes = [pid for pid in alive_pids if pid > node.pid]
    
    if bigger_processes:
        node.log(f"Processos maiores detectados: {bigger_processes} - não assumindo liderança", "⚠️", "yellow")
        node.log("Algoritmo bully finalizado (processos maiores encontrados)", "🏁", "yellow")
        return
    
    # Só agora assume liderança
    node.log("Assumindo liderança", "👑", "green")
    node.become_leader()
    
    node.log("Algoritmo bully finalizado (timeout)", "🏁", "yellow")

