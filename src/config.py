"""
Configurações do sistema distribuído de consenso.

Este arquivo define todas as constantes e parâmetros utilizados pelo sistema,
incluindo configurações de rede, timeouts e intervalos para diferentes operações.
"""

# Configurações de rede multicast
MULTICAST_GRP  = "224.1.1.1"  # Endereço IP do grupo multicast
MULTICAST_PORT = 50000         # Porta para comunicação multicast

# Timeouts básicos do sistema
HEARTBEAT_INT   = 0.2      # Intervalo entre heartbeats (segundos)
FAIL_TIMEOUT    = 5        # Timeout para considerar processo morto (segundos)
HELLO_TIMEOUT   = 2        # Timeout para aguardar HELLO_ACK (segundos)
BULLY_TIMEOUT   = 5        # Timeout para aguardar resposta na eleição (segundos)
ROUND_START     = 0        # Round inicial do sistema

# Timeouts do protocolo de consenso
CONSENSUS_INTERVAL = 15       # Intervalo entre rodadas de consenso (segundos)
ROUND_QUERY_TIMEOUT = 6       # Timeout para aguardar respostas de round (segundos)
VALUE_PROCESS_DELAY = 2       # Delay para processar valores recebidos (segundos)
RESPONSE_PROCESS_DELAY = 2    # Delay para processar respostas recebidas (segundos)
LEADER_QUERY_DELAY = 3        # Delay para consultar round após virar líder (segundos)
LEADER_CONSENSUS_DELAY = 3    # Delay para iniciar consenso após consultar round (segundos)

