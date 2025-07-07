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
CONSENSUS_INTERVAL = 3       # tempo entre rodadas de consenso
ROUND_QUERY_TIMEOUT = 2       # tempo para aguardar respostas de round
VALUE_PROCESS_DELAY = 0.5       # delay para processar valores recebidos
RESPONSE_PROCESS_DELAY = 0.5       # delay para processar respostas recebidas
LEADER_QUERY_DELAY = 1       # delay para consultar round após virar líder
LEADER_CONSENSUS_DELAY = 1       # delay para iniciar consenso após consultar round

