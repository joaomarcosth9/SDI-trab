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
    1. Verifica se já existe um líder válido maior que o processo atual
    2. Envia mensagem ELECTION para todos os processos via multicast
    3. Aguarda respostas OK de processos com PID maior
    4. Se recebe OK, para a eleição (processo maior assumirá liderança)
    5. Se não recebe OK no timeout, assume liderança
    
    Args:
        node: Instância do nó que está iniciando a eleição
        
    Note:
        Este algoritmo assume que:
        - Processos com PID maior têm prioridade para liderança
        - Comunicação é realizada via multicast
        - Apenas um líder pode existir por vez
        
    Comportamento:
        - Se já existe líder válido maior: cancela eleição
        - Se recebe OK durante eleição: para e aguarda novo líder
        - Se timeout sem OK: assume liderança e envia LEADER
    """
    # Se já há um líder válido e sou menor, não preciso me eleger
    if node.leader is not None and node.pid < node.leader:
        node.log(f"Já existe líder {node.leader} maior que eu - cancelando eleição", "🛑", "blue")
        return
    
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
        if node.received_ok:
            node.log("Recebido OK de processo maior - parando eleição", "✅", "green")
            node.received_ok = False  # Reseta para próxima eleição
            node.log("Algoritmo bully finalizado (OK recebido)", "🏁", "green")
            return
        sleep(0.1)

    # Se chegou aqui, ninguém maior respondeu
    node.log("Timeout da eleição - nenhum processo maior respondeu", "⏰", "yellow")
    
    # Verifica novamente se não há líder maior antes de assumir
    if node.leader is None or node.pid > node.leader:
        node.log("Assumindo liderança", "👑", "green")
        node.become_leader()
    else:
        node.log(f"Líder {node.leader} já existe - não assumindo liderança", "🙅", "blue")
    
    node.log("Algoritmo bully finalizado (timeout)", "🏁", "yellow")

