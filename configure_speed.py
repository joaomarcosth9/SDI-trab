#!/usr/bin/env python3
"""
Script para ajustar velocidade do sistema de consenso

Uso:
    python configure_speed.py --speed slow    # Sistema lento para debug
    python configure_speed.py --speed normal  # Sistema normal
    python configure_speed.py --speed fast    # Sistema rápido
"""

import argparse
import os

# Configurações predefinidas
CONFIGS = {
    "slow": {
        "CONSENSUS_INTERVAL": 15,
        "ROUND_QUERY_TIMEOUT": 6,
        "VALUE_PROCESS_DELAY": 2,
        "RESPONSE_PROCESS_DELAY": 2,
        "LEADER_QUERY_DELAY": 3,
        "LEADER_CONSENSUS_DELAY": 3
    },
    "normal": {
        "CONSENSUS_INTERVAL": 8,
        "ROUND_QUERY_TIMEOUT": 4,
        "VALUE_PROCESS_DELAY": 1,
        "RESPONSE_PROCESS_DELAY": 1,
        "LEADER_QUERY_DELAY": 2,
        "LEADER_CONSENSUS_DELAY": 2
    },
    "fast": {
        "CONSENSUS_INTERVAL": 3,
        "ROUND_QUERY_TIMEOUT": 2,
        "VALUE_PROCESS_DELAY": 0.5,
        "RESPONSE_PROCESS_DELAY": 0.5,
        "LEADER_QUERY_DELAY": 1,
        "LEADER_CONSENSUS_DELAY": 1
    }
}

def update_config(speed):
    """Atualiza arquivo de configuração"""
    config_path = "src/config.py"
    
    if not os.path.exists(config_path):
        print(f"Erro: Arquivo {config_path} não encontrado!")
        return False
    
    # Lê arquivo atual
    with open(config_path, 'r') as f:
        lines = f.readlines()
    
    # Atualiza configurações
    config = CONFIGS[speed]
    new_lines = []
    
    for line in lines:
        updated = False
        for key, value in config.items():
            if line.strip().startswith(f"{key} ="):
                new_lines.append(f"{key} = {value}       # {get_description(key)}\n")
                updated = True
                break
        if not updated:
            new_lines.append(line)
    
    # Escreve arquivo
    with open(config_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"Configuração atualizada para '{speed}':")
    for key, value in config.items():
        print(f"  {key} = {value}")
    
    return True

def get_description(key):
    """Retorna descrição do parâmetro"""
    descriptions = {
        "CONSENSUS_INTERVAL": "tempo entre rodadas de consenso",
        "ROUND_QUERY_TIMEOUT": "tempo para aguardar respostas de round",
        "VALUE_PROCESS_DELAY": "delay para processar valores recebidos",
        "RESPONSE_PROCESS_DELAY": "delay para processar respostas recebidas",
        "LEADER_QUERY_DELAY": "delay para consultar round após virar líder",
        "LEADER_CONSENSUS_DELAY": "delay para iniciar consenso após consultar round"
    }
    return descriptions.get(key, "")

def main():
    parser = argparse.ArgumentParser(description="Ajusta velocidade do sistema de consenso")
    parser.add_argument("--speed", choices=["slow", "normal", "fast"], required=True,
                       help="Velocidade do sistema")
    parser.add_argument("--show", action="store_true", help="Mostra configurações disponíveis")
    
    args = parser.parse_args()
    
    if args.show:
        print("Configurações disponíveis:")
        for speed, config in CONFIGS.items():
            print(f"\n{speed.upper()}:")
            for key, value in config.items():
                print(f"  {key} = {value}")
        return
    
    if update_config(args.speed):
        print(f"\nSistema configurado para '{args.speed}'!")
        print("Reinicie os nós para aplicar as mudanças.")
    else:
        print("Erro ao atualizar configuração.")

if __name__ == "__main__":
    main() 