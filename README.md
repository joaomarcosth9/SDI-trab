# Sistema Distribuído de Consenso

Sistema de eleição de líder e consenso distribuído usando multicast UDP.

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

### Executar processo individual
```bash
ID=1 make run
ID=2 make run
ID=3 make run
```

### Executar múltiplos processos (IDs sequenciais)
```bash
# Executa 3 processos (IDs 1, 2, 3)
make run-n

# Executa 5 processos (IDs 1, 2, 3, 4, 5)
N=5 make run-n
```

### Executar com IDs aleatórios (UUID)
```bash
# Executa 3 processos com IDs aleatórios
make run-uuid

# Executa 5 processos com IDs aleatórios
N=5 make run-uuid
```

### Executar diretamente (sem Makefile)
```bash
python -m src.node --id 42
```

## Monitoramento e Debug

### Monitorar processos em tempo real
```bash
make watch
```

### Matar processos
```bash
# Mata todos os processos
make kill

# Mata apenas o líder (maior PID)
make kill-leader
```

### Limpeza
```bash
# Remove arquivos temporários
make clean
```

## Configuração

Edite `src/config.py` para ajustar timeouts e intervalos.

### Principais parâmetros:
- `MULTICAST_GRP`: IP do grupo multicast (default: 224.1.1.1)
- `MULTICAST_PORT`: Porta UDP (default: 50000)
- `CONSENSUS_INTERVAL`: Intervalo entre rounds de consenso (default: 8s)
- `LEADER_SEARCH_TIMEOUT`: Timeout para iniciar eleição (default: 10s)

## Testando Falhas

### Simular perda de conexão
1. Desconecte o cabo de rede ou desabilite WiFi
2. Observe logs mostrando detecção de desconexão
3. Reconecte - sistema deve se recuperar automaticamente

### Simular crash de processo
```bash
# Mata processo específico
pkill -f "node --id 1"

# Mata líder atual (maior PID)
make kill-leader
```

## Protocolo

1. **Eleição**: Algoritmo Bully - processo com maior ID vence
2. **Heartbeat**: Processos enviam HB periodicamente
3. **Consenso**: Líder coleta valores, todos calculam máximo
4. **Detecção de Falhas**: Timeout de heartbeat detecta processos mortos

## Debug

### Ver logs detalhados
```bash
# Terminal 1
ID=1 make run 2>&1 | tee node1.log

# Terminal 2
ID=2 make run 2>&1 | tee node2.log
```

### Testar com diferentes velocidades
```bash
# Rede lenta
python configure_speed.py slow

# Rede rápida
python configure_speed.py fast
```

## Estrutura

```
src/
├── node.py           # Processo principal
├── config.py         # Configurações
├── communication.py  # Rede multicast
├── election.py       # Algoritmo Bully
├── failure_detection.py  # Detecção de falhas
└── message.py        # Serialização
```
