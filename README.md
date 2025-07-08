# Sistema Distribuído de Consenso com Algoritmo Bully

Este projeto implementa um sistema distribuído que combina algoritmo de eleição Bully com protocolo de consenso para coordenar decisões entre múltiplos processos.

## 🏗️ Arquitetura do Sistema

O sistema é composto por processos distribuídos que se comunicam via multicast UDP, implementando:

- **Algoritmo de Eleição Bully**: Para eleger um líder entre os processos
- **Protocolo de Consenso**: Para decidir valores por maioria
- **Detecção de Falhas**: Para monitorar processos ativos
- **Comunicação Multicast**: Para coordenação entre processos

## 📁 Estrutura de Arquivos

```
src/
├── node.py                 # Processo principal (classe Node)
├── election.py            # Algoritmo de eleição Bully
├── failure_detection.py   # Detecção de falhas e heartbeat
├── communication.py       # Comunicação multicast
├── message.py            # Serialização de mensagens
└── config.py             # Configurações do sistema

configure_speed.py         # Script para ajustar velocidade
Makefile                  # Comandos para execução
requirements.txt          # Dependências Python
```

### Descrição dos Arquivos

#### `src/node.py`
Arquivo principal que implementa a classe `Node` - o processo distribuído. Contém:
- Lógica de inicialização e descoberta de líder
- Handlers para diferentes tipos de mensagens
- Coordenação do protocolo de consenso
- Gerenciamento de estado do processo

#### `src/election.py`
Implementa o algoritmo de eleição Bully:
- Envia mensagens ELECTION para processos com PID maior
- Aguarda respostas OK de processos superiores
- Assume liderança se nenhum processo maior responder

#### `src/failure_detection.py`
Sistema de detecção de falhas:
- Envia heartbeats periódicos para todos os processos
- Monitora processos ativos baseado em timeout
- Inicia eleição quando o líder falha

#### `src/communication.py`
Configuração de comunicação multicast:
- Cria socket UDP para multicast
- Configura endereço e porta do grupo multicast
- Funções para envio de mensagens

#### `src/message.py`
Serialização de mensagens:
- Empacota mensagens em formato JSON
- Desempacota mensagens recebidas
- Formatação padronizada para comunicação

#### `src/config.py`
Configurações do sistema:
- Timeouts e intervalos
- Endereços de multicast
- Parâmetros do protocolo de consenso

## 🚀 Como Executar

### Pré-requisitos
- Python 3.7+
- Sistema operacional Linux/macOS/WSL

### Instalação
```bash
# Instalar dependências (se houver)
pip install -r requirements.txt
```

### Execução Manual
```bash
# Executar um processo com PID específico
python -m src.node --id 1

# Executar múltiplos processos em terminais separados
python -m src.node --id 1 --nodes 3
python -m src.node --id 2 --nodes 3
python -m src.node --id 3 --nodes 3
```

### Execução Automática
```bash
# Executar 3 processos automaticamente
N=3 make run-n

# Executar 5 processos automaticamente
N=5 make run-n
```

### Configuração de Velocidade
```bash
# Sistema lento (para debugging)
python configure_speed.py --speed slow

# Sistema normal
python configure_speed.py --speed normal

# Sistema rápido
python configure_speed.py --speed fast

# Mostrar configurações disponíveis
python configure_speed.py --show
```

## 🔄 Fluxo de Execução

### 1. Inicialização do Processo
1. **Criação do socket multicast** para comunicação
2. **Envio de HELLO** para descobrir líder existente
3. **Aguarda HELLO_ACK**
4. **Se não recebe resposta**: inicia eleição Bully
5. **Inicia threads** de heartbeat e monitoramento

### 2. Algoritmo de Eleição Bully
1. **Processo envia ELECTION** via multicast para todos
2. **Processos com PID maior** respondem com OK
3. **Se recebe OK**: para a eleição e aguarda novo líder
4. **Se não recebe OK**: assume liderança e envia LEADER

### 3. Protocolo de Consenso (Executado pelo Líder)
1. **Líder consulta round atual** de todos os processos
2. **Faz consenso por maioria** do round atual
3. **Inicia rodada de consenso** periodicamente:
   - Envia START_CONSENSUS
   - Processos calculam valores e enviam VALUE
   - Processos calculam resposta (máximo) e enviam RESPONSE
   - Líder faz consenso final por maioria das respostas

### 4. Detecção de Falhas
1. **Heartbeats periódicos** (a cada 200ms)
2. **Monitoramento de timeout** (5 segundos)
3. **Quando líder falha**: processos ativos iniciam eleição
4. **Remoção de processos mortos** da lista de ativos

## 🗂️ Tipos de Mensagens

### Descoberta e Eleição
- `HELLO`: Descoberta de líder existente
- `HELLO_ACK`: Resposta do líder com round atual
- `ELECTION`: Inicia processo de eleição
- `OK`: Resposta de processo maior na eleição
- `LEADER`: Anuncia novo líder eleito

### Consenso
- `START_CONSENSUS`: Líder inicia rodada de consenso
- `VALUE`: Processo envia valor calculado
- `RESPONSE`: Processo envia resposta (máximo dos valores)
- `ROUND_QUERY`: Líder pergunta round atual
- `ROUND_RESPONSE`: Resposta com round atual
- `ROUND_UPDATE`: Líder atualiza round de todos

### Monitoramento
- `HB`: Heartbeat para detecção de falhas

## ⚙️ Configurações

### Timeouts Básicos
- `HEARTBEAT_INT`: 0.2s - Intervalo entre heartbeats
- `FAIL_TIMEOUT`: 5s - Timeout para considerar processo morto
- `HELLO_TIMEOUT`: 2s - Timeout para receber HELLO_ACK
- `BULLY_TIMEOUT`: 5s - Timeout para receber OK na eleição

### Timeouts de Consenso
- `CONSENSUS_INTERVAL`: 15s - Intervalo entre rodadas de consenso
- `ROUND_QUERY_TIMEOUT`: 6s - Timeout para consulta de round
- `VALUE_PROCESS_DELAY`: 2s - Delay para processar valores
- `RESPONSE_PROCESS_DELAY`: 2s - Delay para processar respostas
- `LEADER_QUERY_DELAY`: 3s - Delay para consultar round após virar líder
- `LEADER_CONSENSUS_DELAY`: 3s - Delay para iniciar consenso após consulta

### Multicast
- `MULTICAST_GRP`: 224.1.1.1 - Endereço do grupo multicast
- `MULTICAST_PORT`: 50000 - Porta do multicast

## 🔧 Características Técnicas

### Tolerância a Falhas
- Detecção automática de falhas de processos
- Reeleição automática quando líder falha
- Consenso por maioria resiliente a falhas minoritárias

## 🐛 Debugging

### Logs Coloridos
O sistema produz logs coloridos com emojis para facilitar debugging:
- 🚀 **Verde**: Inicialização e sucessos
- 🔥 **Vermelho**: Eleições e eventos críticos
- 👑 **Verde**: Eventos de liderança
- 🎯 **Roxo**: Consenso e decisões
- ⚠️ **Amarelo**: Timeouts e avisos
- 📤📥 **Roxo**: Envio e recebimento de mensagens

### Monitoramento
- Cada processo mostra PID, estado atual e ações tomadas
- Timestamps implícitos para rastrear sequência de eventos
- Logs de consenso mostram valores e votos detalhados

## 📊 Exemplo de Execução

```bash
# Terminal 1
python -m src.node --id 1
[PID 1] 🚀 Iniciando processo com PID 1
[PID 1] 🔍 Enviando HELLO para descobrir líder
[PID 1] 🔥 Sem HELLO_ACK ➜ iniciando eleição
[PID 1] 👑 Assumiu liderança

# Terminal 2
python -m src.node --id 2
[PID 2] 🚀 Iniciando processo com PID 2
[PID 2] 🔍 Enviando HELLO para descobrir líder
[PID 2] 🔗 Conectado ao líder 1 (round 0)

# Terminal 3
python -m src.node --id 3
[PID 3] 🚀 Iniciando processo com PID 3
[PID 3] 🔍 Enviando HELLO para descobrir líder
[PID 3] 🔥 Sem HELLO_ACK ➜ iniciando eleição
[PID 3] 👑 Assumiu liderança (PID maior)
```
