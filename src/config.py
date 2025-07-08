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
FAIL_TIMEOUT    = 4        # Timeout para considerar processo morto
HELLO_TIMEOUT   = 2        # Timeout para aguardar HELLO_ACK
BULLY_TIMEOUT   = 3        # Timeout para aguardar resposta na eleição
ROUND_START     = 0        # Round inicial do sistema

# Timeouts do protocolo de consenso
CONSENSUS_INTERVAL = 8              # Intervalo entre rodadas de consenso
CONSENSUS_RESPONSE_TIMEOUT = 3      # Timeout para processar respostas de consenso
VALUE_PROCESS_DELAY = 1.0           # Delay para processar valores recebidos
START_CONSENSUS_DELAY = 1.5         # Delay para processar valores no START_CONSENSUS

# Timeouts de eleição
ELECTION_TIMEOUT = 2.0          # Timeout geral de eleição
ELECTION_START_DELAY = 0.5      # Delay para iniciar eleição após receber ELECTION
ROUND_CONSENSUS_TIMEOUT = 1.0   # Timeout para coletar votos de round
LEADER_DEATH_DELAY = 0.1        # Delay para iniciar eleição após líder morrer
BULLY_POLL_INTERVAL = 0.1       # Intervalo de polling no algoritmo bully

# Timeouts de liderança
LEADER_TIMEOUT = 3.0            # Timeout para considerar líder morto
LEADER_STARTUP_DELAY = 2        # Delay para iniciar consenso após virar líder

# Timeouts de monitoramento
MONITOR_INTERVAL = 0.3          # Intervalo de verificação do monitor
MONITOR_STARTUP_GRACE = 5       # Período de carência inicial do monitor

# Timeouts de rede e reconexão
NETWORK_RETRY_DELAY = 2         # Delay entre tentativas de reconexão
NETWORK_LOG_INTERVAL = 10       # Intervalo para log de status de rede
LEADER_SEARCH_INTERVAL = 3      # Intervalo para procurar líder
LEADER_SEARCH_TIMEOUT = 10      # Timeout máximo para procurar líder antes de iniciar eleição

# Outros timeouts
STARTUP_DELAY = 0.5             # Delay inicial ao iniciar processo
MAIN_LOOP_INTERVAL = 1          # Intervalo do loop principal
LISTEN_TIMEOUT = 0.1            # Timeout para recepção de mensagens
STATUS_LOG_INTERVAL = 30        # Intervalo para log de status

