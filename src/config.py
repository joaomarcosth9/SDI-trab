"""
Configurações do sistema distribuído de consenso.

Este arquivo define todas as constantes e parâmetros utilizados pelo sistema,
incluindo configurações de rede, timeouts e intervalos para diferentes operações.
"""

# Configurações de rede multicast
MULTICAST_GRP  = "224.1.1.1"  # Endereço IP do grupo multicast
MULTICAST_PORT = 50000         # Porta para comunicação multicast

# Timeouts básicos do sistema
HEARTBEAT_INT   = 0.3      # Intervalo entre heartbeats 
FAIL_TIMEOUT    = 4        # Timeout para considerar processo morto (mais tempo)
HELLO_TIMEOUT   = 2        # Timeout para aguardar HELLO_ACK (mais tempo para descoberta)
BULLY_TIMEOUT   = 3        # Timeout para aguardar resposta na eleição
ROUND_START     = 0        # Round inicial do sistema

# Timeouts do protocolo de consenso
CONSENSUS_INTERVAL = 8        # tempo entre rodadas de consenso (evita sobreposição)
ROUND_QUERY_TIMEOUT = 4       # tempo para aguardar respostas de round 
VALUE_PROCESS_DELAY = 0.5     # delay para processar valores recebidos (diminuído)
RESPONSE_PROCESS_DELAY = 0.5  # delay para processar respostas recebidas (diminuído)
LEADER_QUERY_DELAY = 2        # delay para consultar round após virar líder 
LEADER_CONSENSUS_DELAY = 2    # delay para iniciar consenso após consultar round

