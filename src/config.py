MULTICAST_GRP  = "224.1.1.1"
MULTICAST_PORT = 50000

# Timeouts básicos
HEARTBEAT_INT   = 0.2      # segundos
FAIL_TIMEOUT    = 5      # sem HB => morto
HELLO_TIMEOUT   = 2      # espera HELLO_ACK
BULLY_TIMEOUT   = 5      # espera resposta da eleição
ROUND_START     = 0

# Timeouts do protocolo de consenso
CONSENSUS_INTERVAL = 15       # tempo entre rodadas de consenso
ROUND_QUERY_TIMEOUT = 6       # tempo para aguardar respostas de round
VALUE_PROCESS_DELAY = 2       # delay para processar valores recebidos
RESPONSE_PROCESS_DELAY = 2       # delay para processar respostas recebidas
LEADER_QUERY_DELAY = 3       # delay para consultar round após virar líder
LEADER_CONSENSUS_DELAY = 3       # delay para iniciar consenso após consultar round

