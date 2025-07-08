#!/usr/bin/env python3
"""
Script para ajustar velocidade do sistema de consenso

Uso:
    python configure_speed.py --speed slow    # Sistema lento para debug
    python configure_speed.py --speed normal  # Sistema normal
    python configure_speed.py --speed fast    # Sistema rápido
    python configure_speed.py --speed demo    # Sistema demo (muito lento, visual)
"""

import argparse
import os

# Configurações predefinidas com todos os timeouts
CONFIGS = {
    "demo": {  # Muito lento para demonstrações visuais
        # Consenso
        "CONSENSUS_INTERVAL": 20,
        "CONSENSUS_RESPONSE_TIMEOUT": 8,
        "VALUE_PROCESS_DELAY": 3.0,
        "START_CONSENSUS_DELAY": 4.0,
        
        # Eleição
        "BULLY_TIMEOUT": 6,
        "ELECTION_START_DELAY": 1.0,
        "LEADER_DEATH_DELAY": 0.5,
        "BULLY_POLL_INTERVAL": 0.2,
        
        # Liderança
        "LEADER_STARTUP_DELAY": 4,
        
        # Heartbeat e monitoramento
        "HEARTBEAT_INT": 1.0,
        "FAIL_TIMEOUT": 8,
        "MONITOR_INTERVAL": 1.0,
        "MONITOR_STARTUP_GRACE": 10,
        
        # Descoberta
        "HELLO_TIMEOUT": 4,
        
        # Rede
        "NETWORK_RETRY_DELAY": 3,
        "NETWORK_LOG_INTERVAL": 15,
        "LEADER_SEARCH_INTERVAL": 8,
        
        # Outros
        "STARTUP_DELAY": 1.0,
        "MAIN_LOOP_INTERVAL": 2,
        "LISTEN_TIMEOUT": 0.2,
        "STATUS_LOG_INTERVAL": 45
    },
    "slow": {  # Sistema lento para debug
        # Consenso
        "CONSENSUS_INTERVAL": 12,
        "CONSENSUS_RESPONSE_TIMEOUT": 5,
        "VALUE_PROCESS_DELAY": 2.0,
        "START_CONSENSUS_DELAY": 2.5,
        
        # Eleição
        "BULLY_TIMEOUT": 4,
        "ELECTION_START_DELAY": 0.5,
        "LEADER_DEATH_DELAY": 0.3,
        "BULLY_POLL_INTERVAL": 0.15,
        
        # Liderança
        "LEADER_STARTUP_DELAY": 3,
        
        # Heartbeat e monitoramento
        "HEARTBEAT_INT": 0.5,
        "FAIL_TIMEOUT": 6,
        "MONITOR_INTERVAL": 0.5,
        "MONITOR_STARTUP_GRACE": 7,
        
        # Descoberta
        "HELLO_TIMEOUT": 3,
        
        # Rede
        "NETWORK_RETRY_DELAY": 2.5,
        "NETWORK_LOG_INTERVAL": 12,
        "LEADER_SEARCH_INTERVAL": 6,
        
        # Outros
        "STARTUP_DELAY": 0.8,
        "MAIN_LOOP_INTERVAL": 1.5,
        "LISTEN_TIMEOUT": 0.15,
        "STATUS_LOG_INTERVAL": 35
    },
    "normal": {  # Sistema normal (default)
        # Consenso
        "CONSENSUS_INTERVAL": 8,
        "CONSENSUS_RESPONSE_TIMEOUT": 3,
        "VALUE_PROCESS_DELAY": 1.0,
        "START_CONSENSUS_DELAY": 1.5,
        
        # Eleição
        "BULLY_TIMEOUT": 3,
        "ELECTION_START_DELAY": 0.3,
        "LEADER_DEATH_DELAY": 0.1,
        "BULLY_POLL_INTERVAL": 0.1,
        
        # Liderança
        "LEADER_STARTUP_DELAY": 2,
        
        # Heartbeat e monitoramento
        "HEARTBEAT_INT": 0.3,
        "FAIL_TIMEOUT": 4,
        "MONITOR_INTERVAL": 0.3,
        "MONITOR_STARTUP_GRACE": 5,
        
        # Descoberta
        "HELLO_TIMEOUT": 2,
        
        # Rede
        "NETWORK_RETRY_DELAY": 2,
        "NETWORK_LOG_INTERVAL": 10,
        "LEADER_SEARCH_INTERVAL": 5,
        
        # Outros
        "STARTUP_DELAY": 0.5,
        "MAIN_LOOP_INTERVAL": 1,
        "LISTEN_TIMEOUT": 0.1,
        "STATUS_LOG_INTERVAL": 30
    },
    "fast": {  # Sistema rápido
        # Consenso
        "CONSENSUS_INTERVAL": 4,
        "CONSENSUS_RESPONSE_TIMEOUT": 1.5,
        "VALUE_PROCESS_DELAY": 0.4,
        "START_CONSENSUS_DELAY": 0.6,
        
        # Eleição
        "BULLY_TIMEOUT": 2,
        "ELECTION_START_DELAY": 0.15,
        "LEADER_DEATH_DELAY": 0.05,
        "BULLY_POLL_INTERVAL": 0.05,
        
        # Liderança
        "LEADER_STARTUP_DELAY": 1,
        
        # Heartbeat e monitoramento
        "HEARTBEAT_INT": 0.2,
        "FAIL_TIMEOUT": 2.5,
        "MONITOR_INTERVAL": 0.2,
        "MONITOR_STARTUP_GRACE": 3,
        
        # Descoberta
        "HELLO_TIMEOUT": 1,
        
        # Rede
        "NETWORK_RETRY_DELAY": 1,
        "NETWORK_LOG_INTERVAL": 8,
        "LEADER_SEARCH_INTERVAL": 3,
        
        # Outros
        "STARTUP_DELAY": 0.3,
        "MAIN_LOOP_INTERVAL": 0.5,
        "LISTEN_TIMEOUT": 0.05,
        "STATUS_LOG_INTERVAL": 20
    }
}

def validate_config(config):
    """
    Valida configuração para garantir que não há valores contraditórios.
    
    Args:
        config (dict): Configuração a ser validada
        
    Returns:
        bool: True se configuração é válida, False caso contrário
    """
    # Validações de consistência
    if config["FAIL_TIMEOUT"] <= config["HEARTBEAT_INT"] * 3:
        print("⚠️  AVISO: FAIL_TIMEOUT deve ser > 3 * HEARTBEAT_INT para evitar falsos positivos")
        return False
        
    if config["CONSENSUS_RESPONSE_TIMEOUT"] >= config["CONSENSUS_INTERVAL"]:
        print("⚠️  AVISO: CONSENSUS_RESPONSE_TIMEOUT deve ser < CONSENSUS_INTERVAL")
        return False
        
    if config["BULLY_TIMEOUT"] <= config["ELECTION_START_DELAY"]:
        print("⚠️  AVISO: BULLY_TIMEOUT deve ser > ELECTION_START_DELAY")
        return False
        
    if config["VALUE_PROCESS_DELAY"] >= config["CONSENSUS_RESPONSE_TIMEOUT"]:
        print("⚠️  AVISO: VALUE_PROCESS_DELAY deve ser < CONSENSUS_RESPONSE_TIMEOUT")
        return False
        
    if config["MONITOR_STARTUP_GRACE"] <= config["HELLO_TIMEOUT"]:
        print("⚠️  AVISO: MONITOR_STARTUP_GRACE deve ser > HELLO_TIMEOUT")
        return False
        
    return True

def update_config(speed):
    """Atualiza arquivo de configuração"""
    config_path = "src/config.py"
    
    if not os.path.exists(config_path):
        print(f"Erro: Arquivo {config_path} não encontrado!")
        return False
    
    config = CONFIGS[speed]
    
    # Valida configuração antes de aplicar
    if not validate_config(config):
        print(f"\n❌ Configuração '{speed}' tem valores contraditórios!")
        return False
    
    # Lê arquivo atual
    with open(config_path, 'r') as f:
        lines = f.readlines()
    
    # Atualiza configurações
    new_lines = []
    
    for line in lines:
        updated = False
        for key, value in config.items():
            if line.strip().startswith(f"{key} ="):
                # Preserva comentário original se existir
                comment = ""
                if "#" in line:
                    comment = line[line.index("#"):]
                else:
                    comment = f"# {get_description(key)}\n"
                    
                new_lines.append(f"{key} = {value:<14}{comment}")
                updated = True
                break
        if not updated:
            new_lines.append(line)
    
    # Escreve arquivo
    with open(config_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"\n✅ Configuração atualizada para '{speed}':")
    print("\n📊 Principais timeouts:")
    print(f"  - Consenso a cada: {config['CONSENSUS_INTERVAL']}s")
    print(f"  - Heartbeat a cada: {config['HEARTBEAT_INT']}s")
    print(f"  - Falha detectada em: {config['FAIL_TIMEOUT']}s")
    print(f"  - Eleição timeout: {config['BULLY_TIMEOUT']}s")
    
    return True

def get_description(key):
    """
    Retorna descrição do parâmetro de configuração.
    
    Args:
        key (str): Nome do parâmetro de configuração
        
    Returns:
        str: Descrição do parâmetro ou string vazia se não encontrado
    """
    descriptions = {
        # Consenso
        "CONSENSUS_INTERVAL": "Intervalo entre rodadas de consenso",
        "CONSENSUS_RESPONSE_TIMEOUT": "Timeout para processar respostas de consenso",
        "VALUE_PROCESS_DELAY": "Delay para processar valores recebidos",
        "START_CONSENSUS_DELAY": "Delay para processar valores no START_CONSENSUS",
        
        # Eleição
        "BULLY_TIMEOUT": "Timeout para aguardar resposta na eleição",
        "ELECTION_START_DELAY": "Delay para iniciar eleição após receber ELECTION",
        "LEADER_DEATH_DELAY": "Delay para iniciar eleição após líder morrer",
        "BULLY_POLL_INTERVAL": "Intervalo de polling no algoritmo bully",
        
        # Liderança
        "LEADER_STARTUP_DELAY": "Delay para iniciar consenso após virar líder",
        
        # Heartbeat e monitoramento
        "HEARTBEAT_INT": "Intervalo entre heartbeats",
        "FAIL_TIMEOUT": "Timeout para considerar processo morto",
        "MONITOR_INTERVAL": "Intervalo de verificação do monitor",
        "MONITOR_STARTUP_GRACE": "Período de carência inicial do monitor",
        
        # Descoberta
        "HELLO_TIMEOUT": "Timeout para aguardar HELLO_ACK",
        
        # Rede
        "NETWORK_RETRY_DELAY": "Delay entre tentativas de reconexão",
        "NETWORK_LOG_INTERVAL": "Intervalo para log de status de rede",
        "LEADER_SEARCH_INTERVAL": "Intervalo para procurar líder",
        
        # Outros
        "STARTUP_DELAY": "Delay inicial ao iniciar processo",
        "MAIN_LOOP_INTERVAL": "Intervalo do loop principal",
        "LISTEN_TIMEOUT": "Timeout para recepção de mensagens",
        "STATUS_LOG_INTERVAL": "Intervalo para log de status"
    }
    return descriptions.get(key, "")

def main():
    """
    Função principal do script de configuração.
    
    Processa argumentos da linha de comando e executa a configuração
    de velocidade do sistema ou mostra as configurações disponíveis.
    
    Args (linha de comando):
        --speed: Velocidade do sistema ('demo', 'slow', 'normal', 'fast')
        --show: Mostra configurações disponíveis sem alterar arquivos
    """
    parser = argparse.ArgumentParser(description="Ajusta velocidade do sistema de consenso")
    parser.add_argument("--speed", choices=["demo", "slow", "normal", "fast"], 
                       help="Velocidade do sistema")
    parser.add_argument("--show", action="store_true", 
                       help="Mostra configurações disponíveis")
    
    args = parser.parse_args()
    
    if args.show or not args.speed:
        print("🚀 Configurações de velocidade disponíveis:\n")
        for speed, config in CONFIGS.items():
            print(f"{speed.upper()}:")
            print(f"  - Consenso a cada: {config['CONSENSUS_INTERVAL']}s")
            print(f"  - Heartbeat a cada: {config['HEARTBEAT_INT']}s") 
            print(f"  - Detecção de falha: {config['FAIL_TIMEOUT']}s")
            print(f"  - Tempo de eleição: {config['BULLY_TIMEOUT']}s\n")
        
        if not args.speed:
            print("Use --speed [demo|slow|normal|fast] para configurar")
        return
    
    if update_config(args.speed):
        print(f"\n🎯 Sistema configurado para '{args.speed}'!")
        print("🔄 Reinicie os nós para aplicar as mudanças.")
    else:
        print("❌ Erro ao atualizar configuração.")

if __name__ == "__main__":
    main() 