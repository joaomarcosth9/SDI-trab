#!/usr/bin/env python3
"""
Módulo principal do sistema distribuído de consenso.

Implementa a classe Node que representa um processo no sistema distribuído,
incluindo algoritmo de eleição Bully, protocolo de consenso e detecção de falhas.
"""

import argparse, threading
from time import monotonic, sleep
from random import randint
from collections import defaultdict
from .config import *
from .communication import NetworkManager
from .message import pack, unpack
from .failure_detection import start_heartbeat, start_monitor
from .election import bully

class Node:
    """
    Representa um processo no sistema distribuído de consenso.
    
    Thread-safe implementation usando RLock para coordenação interna.
    """
    
    def __init__(self, pid: int):
        """
        Inicializa um novo nó do sistema distribuído.
        
        Args:
            pid (int): ID único do processo (deve ser positivo)
        """
        self.pid = pid
        self.network = NetworkManager()
        
        # Estado do protocolo - protegido por lock
        self.state_lock = threading.RLock()
        self.round = ROUND_START
        self.leader = None
        self.alive = {pid: monotonic()}
        
        # Estado de eleição
        self.in_election = False
        self.received_ok = False
        
        # Coleta de rounds durante eleição
        self.round_votes = {}  # {pid: round} para consenso de round
        self.round_consensus_timer = None
        
        # Estado de consenso
        self.values_received = {}
        self.responses_received = {}
        self.responses_sent = {}  # Rastreia respostas já enviadas
        self.value_timers = {}  # Rastreia timers por round
        
        # Timer para consenso periódico
        self.consensus_timer = None

        # Controle de estado da rede
        self.was_connected = True
        
        # Flag de shutdown
        self.shutdown = False
        
        self.log(f"Nó {self.pid} criado com sucesso", "green")

    def log(self, msg: str, color: str = ""):
        """
        Exibe mensagem de log colorida para o processo.
        
        Args:
            msg (str): Mensagem a ser exibida
            color (str): Cor do texto ('red', 'green', 'yellow', 'blue', etc.)
        """
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "purple": "\033[95m",
            "cyan": "\033[96m",
            "reset": "\033[0m"
        }
        
        color_code = colors.get(color, "")
        reset_code = colors["reset"]
        
        import time
        timestamp = time.strftime("%H:%M:%S")
        prefix = "♔ " if self.leader == self.pid else "○ "
        print(f"[{timestamp}] [PID {self.pid}] {color_code}{prefix}{msg}{reset_code}", flush=True)

    def send(self, op: str, **kv):
        """
        Envia uma mensagem via multicast usando o NetworkManager.
        
        Args:
            op (str): Tipo da operação/mensagem
            **kv: Campos adicionais da mensagem
        """
        if not self.network.connected:
            return False
            
        return self.network.send(pack(op, **kv))

    def get_alive_pids(self):
        """
        Retorna lista de PIDs vivos (excluindo o próprio).
        
        Returns:
            list[int]: Lista de PIDs dos processos vivos
        """
        return [pid for pid in self.alive.keys() if pid != self.pid]
    
    def calculate_current_value(self):
        """
        Calcula o valor atual do processo para o consenso.
        
        Returns:
            int: Valor calculado (função do PID e número aleatório)
        """
        i = randint(1, 10)
        return i * i * self.pid

    def schedule_next_consensus(self):
        """
        Agenda a próxima rodada de consenso.
        """
        if self.consensus_timer:
            self.consensus_timer.cancel()
            
        self.consensus_timer = threading.Timer(CONSENSUS_INTERVAL, self.start_consensus_round)
        self.consensus_timer.start()

    def start_consensus_round(self):
        """
        Inicia uma rodada de consenso (chamado pelo líder).
        """
        if not self.network.connected:
            # Reagenda se não há rede
            self.schedule_next_consensus()
            return
            
        with self.state_lock:
            if self.pid != self.leader:
                return
            
            alive_pids = self.get_alive_pids()
            self.log(f"[LÍDER] Iniciando consenso round {self.round} - Processos vivos: {[self.pid] + alive_pids}", "green")
            self.values_received[self.round] = {}
            self.responses_received[self.round] = {}
            
            # Adiciona próprio valor
            my_value = self.calculate_current_value()
            self.values_received[self.round][self.pid] = my_value
            self.log(f"[LÍDER] Meu valor: {my_value}", "green")
            
            # Envia sinal para todos calcularem valores
            self.send("START_CONSENSUS", round=self.round)
            
        # Agenda processamento de respostas
        threading.Timer(CONSENSUS_RESPONSE_TIMEOUT, self.process_consensus_responses).start()
        
        # IMPORTANTE: Agenda próximo round IMEDIATAMENTE
        self.schedule_next_consensus()

    def process_consensus_responses(self):
        """
        Processa respostas e finaliza round (líder).
        """
        with self.state_lock:
            if self.pid != self.leader or self.round not in self.responses_received:
                return
            
            responses = list(self.responses_received[self.round].values())
            if not responses:
                return
            
            # Log detalhado das respostas recebidas
            responses_detail = {pid: resp for pid, resp in self.responses_received[self.round].items()}
            self.log(f"[LÍDER] Respostas recebidas: {responses_detail}", "purple")
            
            # Faz consenso por maioria
            response_counts = defaultdict(int)
            for response in responses:
                response_counts[response] += 1
            
            consensus_response = max(response_counts.items(), key=lambda x: x[1])[0]
            votes_detail = dict(response_counts)
            self.log(f"[VOTAÇÃO] Contagem: {votes_detail}", "purple")
            self.log(f"[CONSENSO] Round {self.round}: Resposta = {consensus_response} (votos: {response_counts[consensus_response]})", "purple")
            
            # Avança para próximo round
            self.round += 1
            self.log(f"[LÍDER] Avançando para round {self.round}", "green")
            self.send("ROUND_UPDATE", round=self.round)

    def start_election(self):
        """
        Inicia processo de eleição Bully.
        """
        if not self.network.connected:
            return
            
        with self.state_lock:
            if self.in_election:
                return
                
            self.in_election = True
            self.leader = None
            self.received_ok = False
            
        self.log("Iniciando eleição", "red")
        bully(self)
        
        with self.state_lock:
            if self.leader != self.pid:
                self.in_election = False

    def start_round_consensus(self):
        """
        Inicia coleta de rounds para consenso antes de assumir liderança.
        """
        with self.state_lock:
            # Limpa votos anteriores
            self.round_votes = {self.pid: self.round}  # Inclui próprio voto
            alive_pids = self.get_alive_pids()
            
            self.log(f"[ELEIÇÃO] Coletando rounds dos processos vivos: {alive_pids}", "yellow")
            
            # Solicita round de todos os processos vivos
            self.send("ROUND_REQUEST", from_pid=self.pid)
            
        # Agenda processamento dos votos
        self.round_consensus_timer = threading.Timer(
            ROUND_CONSENSUS_TIMEOUT, 
            lambda: self.process_round_consensus()
        )
        self.round_consensus_timer.start()
    
    def process_round_consensus(self):
        """
        Processa votos de round e assume liderança com round consensado.
        """
        with self.state_lock:
            if not self.round_votes:
                # Se não recebeu votos, usa próprio round
                self.become_leader()
                return
                
            # Conta votos por round
            round_counts = defaultdict(int)
            for pid, round_vote in self.round_votes.items():
                round_counts[round_vote] += 1
            
            # Encontra round com mais votos (maioria)
            consensus_round = max(round_counts.items(), key=lambda x: x[1])[0]
            
            self.log(f"[CONSENSO ROUND] Votos recebidos: {dict(self.round_votes)}", "yellow")
            self.log(f"[CONSENSO ROUND] Contagem: {dict(round_counts)}", "yellow") 
            self.log(f"[CONSENSO ROUND] Round escolhido por maioria: {consensus_round}", "green")
            
            # Atualiza próprio round para o consensado
            old_round = self.round
            self.round = consensus_round
            
            if old_round != self.round:
                self.log(f"[CONSENSO ROUND] Atualizando round de {old_round} para {self.round}", "green")
        
        # Agora assume liderança com round consensado
        self.become_leader()

    def become_leader(self):
        """
        Assume liderança do sistema.
        """
        if not self.network.connected:
            return
            
        with self.state_lock:
            if self.leader == self.pid:
                return
                
            self.leader = self.pid
            self.in_election = False
            self.log("Assumi liderança", "green")
            
            # Pega o maior round conhecido (incluindo o próprio)
            # para garantir que não volta no tempo
            max_round = self.round
            self.log(f"Assumindo liderança com round {max_round}", "green")
            
            self.send("LEADER", pid=self.pid, round=max_round)
            
        # Inicia consenso após um delay
        threading.Timer(LEADER_STARTUP_DELAY, self.start_consensus_round).start()

    def handle(self, data: bytes):
        """
        Processa mensagem recebida via multicast.
        
        Args:
            data (bytes): Dados da mensagem recebida
        """
        msg = unpack(data)
        op = msg["op"]

        if op == "HELLO":
            sender_pid = msg["pid"]
            is_new = sender_pid not in self.alive
            self.alive[sender_pid] = monotonic()
            
            if is_new:
                self.log(f"[HELLO] Novo processo descoberto: {sender_pid}", "green")
            else:
                self.log(f"[HELLO] Recebido de processo {sender_pid}", "yellow")
            
            if self.pid == self.leader:
                self.send("HELLO_ACK", pid=self.pid, round=self.round, to=sender_pid)
                self.log(f"[HELLO_ACK] Enviado para processo {sender_pid} (round {self.round})", "green")

        elif op == "HELLO_ACK":
            if self.pid == msg["to"]:
                with self.state_lock:
                    self.in_election = False
                    self.leader = msg["pid"]
                    old_round = self.round
                    self.round = msg["round"]
                    self.alive[msg["pid"]] = monotonic()
                    
                    # Limpa estados antigos se mudou de round
                    if old_round != self.round:
                        # Remove dados de rounds antigos
                        rounds_to_remove = [r for r in self.values_received.keys() if r < self.round]
                        for r in rounds_to_remove:
                            self.values_received.pop(r, None)
                            self.responses_received.pop(r, None)
                            self.responses_sent.pop(r, None)
                            
                            # Cancela timers antigos
                            if r in self.value_timers:
                                self.value_timers[r].cancel()
                                self.value_timers.pop(r, None)
                
                self.log(f"Conectado ao líder {self.leader}, round {self.round}", "green")

        elif op == "HB":
            self.alive[msg["pid"]] = monotonic()

        elif op == "ELECTION":
            src = msg["source"]
            if self.pid > src:
                self.log(f"[ELECTION] Recebido de {src} - sou maior, enviando OK", "yellow")
                self.send("OK", to=src)
                threading.Timer(ELECTION_START_DELAY, self.start_election).start()
            elif self.pid < src:
                self.log(f"[ELECTION] Recebido de {src} - sou menor, ignorando", "blue")

        elif op == "OK":
            if msg.get("to") == self.pid:
                self.log(f"[OK] Recebido na eleição", "green")
                self.received_ok = True
                if self.leader == self.pid:
                    self.leader = None

        elif op == "LEADER":
            leader_pid = msg["pid"]
            new_round = msg.get("round", self.round)
            
            with self.state_lock:
                self.in_election = False
                self.leader = leader_pid
                self.alive[leader_pid] = monotonic()
                
                # Atualiza para o round do novo líder se for maior
                if new_round > self.round:
                    self.round = new_round
                    self.log(f"Líder eleito: {self.leader}, sincronizando para round {self.round}", "green")
                else:
                    self.log(f"Líder eleito: {self.leader}, mantendo round {self.round}", "green")

        elif op == "START_CONSENSUS":
            consensus_round = msg["round"]
            self.log(f"[CONSENSO] Líder iniciou round {consensus_round}", "cyan")
            
            with self.state_lock:
                if consensus_round not in self.values_received:
                    self.values_received[consensus_round] = {}
                
                # Calcula e envia valor
                my_value = self.calculate_current_value()
                self.values_received[consensus_round][self.pid] = my_value
                self.log(f"[CONSENSO] Meu valor gerado: {my_value} (round {consensus_round})", "cyan")
                self.send("VALUE", pid=self.pid, value=my_value, round=consensus_round)
                
                # Agenda processamento para este round específico (como se fosse um VALUE)
                if consensus_round not in self.value_timers:
                    timer = threading.Timer(START_CONSENSUS_DELAY, lambda: self.process_maximum_value(consensus_round))
                    timer.start()
                    self.value_timers[consensus_round] = timer

        elif op == "VALUE":
            round_num = msg["round"]
            sender_pid = msg["pid"]
            value = msg["value"]
            
            with self.state_lock:
                if round_num not in self.values_received:
                    self.values_received[round_num] = {}
                
                self.values_received[round_num][sender_pid] = value
                self.log(f"[VALUE] Recebido valor {value} do processo {sender_pid} (round {round_num})", "purple")
                
                # Agenda processamento apenas se ainda não foi agendado para este round
                if round_num not in self.value_timers:
                    timer = threading.Timer(VALUE_PROCESS_DELAY, lambda: self.process_maximum_value(round_num))
                    timer.start()
                    self.value_timers[round_num] = timer

        elif op == "RESPONSE":
            with self.state_lock:
                if self.pid == self.leader:
                    round_num = msg["round"]
                    sender_pid = msg["pid"]
                    response = msg["response"]
                    
                    if round_num not in self.responses_received:
                        self.responses_received[round_num] = {}
                        
                    self.responses_received[round_num][sender_pid] = response
                    self.log(f"[RESPONSE] Líder recebeu resposta {response} do processo {sender_pid} (round {round_num})", "purple")

        elif op == "ROUND_UPDATE":
            new_round = msg["round"]
            old_round = self.round
            self.round = new_round
            self.log(f"[ROUND_UPDATE] Atualizando round de {old_round} para {new_round}", "blue")

        elif op == "ROUND_REQUEST":
            # Responde com próprio round quando solicitado
            from_pid = msg["from_pid"]
            self.log(f"[ROUND_REQUEST] Recebido de {from_pid}, respondendo com round {self.round}", "yellow")
            self.send("ROUND_RESPONSE", pid=self.pid, round=self.round, to=from_pid)
            
        elif op == "ROUND_RESPONSE":
            # Coleta votos de round durante eleição
            if msg.get("to") == self.pid:
                sender_pid = msg["pid"]
                sender_round = msg["round"]
                
                with self.state_lock:
                    if hasattr(self, 'round_votes'):  # Verifica se está coletando votos
                        self.round_votes[sender_pid] = sender_round
                        self.log(f"[ROUND_RESPONSE] Recebido voto: PID {sender_pid} votou round {sender_round}", "yellow")

    def process_maximum_value(self, round_num: int):
        """
        Processa valores recebidos e calcula resposta.
        """
        with self.state_lock:
            if round_num not in self.values_received:
                return
            
            # Verifica se já enviou resposta para este round
            if round_num in self.responses_sent:
                return
                
            values = list(self.values_received[round_num].values())
            if not values:
                return
                
            my_response = max(values)
            
            # Log detalhado dos valores e resposta
            values_detail = {pid: val for pid, val in self.values_received[round_num].items()}
            self.log(f"[CÁLCULO] Valores recebidos: {values_detail}", "cyan")
            
            # Marca como enviada antes de enviar
            self.responses_sent[round_num] = my_response
            
            # Se sou o líder, adiciono diretamente. Caso contrário, envio via rede
            if self.pid == self.leader:
                if round_num not in self.responses_received:
                    self.responses_received[round_num] = {}
                self.responses_received[round_num][self.pid] = my_response
                self.log(f"[LÍDER] Resposta calculada: {my_response} (round {round_num})", "green")
            else:
                self.log(f"[RESPOSTA] Enviando resposta máxima: {my_response} (round {round_num})", "cyan")
                # Envia resposta para o líder
                self.send("RESPONSE", pid=self.pid, response=my_response, round=round_num)
            
            # Limpa timer usado
            self.value_timers.pop(round_num, None)

    def run(self):
        """
        Executa o loop principal do processo distribuído.
        """
        self.log(f"Iniciando processo", "green")
        
        # Inicia thread de escuta
        listener = threading.Thread(target=self.listen, daemon=True)
        listener.start()

        sleep(STARTUP_DELAY)

        # Tenta descobrir líder
        self.log("Procurando líder existente...", "yellow")
        self.send("HELLO", pid=self.pid)
        start_heartbeat(self)
        
        sleep(HELLO_TIMEOUT)
        
        # Se não encontrou líder, inicia eleição
        if self.leader is None:
            self.log("Nenhum líder encontrado - iniciando eleição", "yellow")
            self.start_election()
        else:
            self.log(f"Líder {self.leader} encontrado", "green")

        start_monitor(self)
        
        # Loop principal simplificado
        last_status_log = 0
        last_network_log = 0
        while not self.shutdown:
            # Aguarda reconexão se desconectado
            if not self.network.connected:
                now = monotonic()
                if now - last_network_log > NETWORK_LOG_INTERVAL:
                    self.log("[REDE] Sem conexão - aguardando...", "red")
                    last_network_log = now
                sleep(NETWORK_RETRY_DELAY)
                continue
            
            # Se reconectou, redescobre líder
            if not self.was_connected and self.network.connected:
                self.log("[REDE] Reconectado - redescobrir líder", "green")
                self.leader = None
                self.send("HELLO", pid=self.pid)
                sleep(NETWORK_RETRY_DELAY)
                
            self.was_connected = self.network.connected
            
            # Se não tem líder, tenta descobrir
            if self.leader is None and not self.in_election:
                self.log("Procurando líder...", "yellow")
                self.send("HELLO", pid=self.pid)
                sleep(LEADER_SEARCH_INTERVAL)
            
            # Log periódico de status
            now = monotonic()
            if now - last_status_log > STATUS_LOG_INTERVAL:
                with self.state_lock:
                    if self.leader == self.pid:
                        self.log(f"[LÍDER ATIVO] Round: {self.round}, Processos vivos: {len(self.get_alive_pids())}", "green")
                    elif self.leader is not None:
                        self.log(f"[SEGUIDOR] Líder: {self.leader}, Round: {self.round}", "blue")
                last_status_log = now
                
            sleep(MAIN_LOOP_INTERVAL)

    def listen(self):
        """
        Loop de escuta de mensagens multicast.
        """
        while not self.shutdown:
            result = self.network.receive(65535)
            if result is not None:
                data, _ = result
                self.handle(data)
            else:
                sleep(LISTEN_TIMEOUT)

    def stop(self):
        """
        Sinaliza para parar todas as threads e cancela timers.
        """
        self.log("Encerrando processo...", "yellow")
        self.shutdown = True
        
        # Cancela timer de consenso se existir
        if self.consensus_timer:
            try:
                self.consensus_timer.cancel()
            except:
                pass
                
        # Cancela timer de consenso de round se existir
        if self.round_consensus_timer:
            try:
                self.round_consensus_timer.cancel()
            except:
                pass
            
        # Cancela todos os timers de valores
        for timer in self.value_timers.values():
            try:
                timer.cancel()
            except:
                pass
        
        # Desconecta da rede
        if self.network and self.network.connected:
            self.network.close()

def main():
    """
    Função principal que inicializa e executa um nó do sistema.
    
    Processa argumentos da linha de comando e cria uma instância
    do Node com os parâmetros especificados.
    
    Args (linha de comando):
        --id: ID único do processo (obrigatório)
    """
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True)
    args = ap.parse_args()
    
    print(f"[INICIO] Iniciando sistema com PID {args.id}")
    
    node = None
    try:
        node = Node(pid=args.id)
        node.run()
    except KeyboardInterrupt:
        print(f"[SAÍDA] Processo {args.id} interrompido pelo usuário")
        if node:
            node.stop()
        sys.exit(0)
    except Exception as e:
        print(f"[ERRO] Processo {args.id} falhou: {e}")
        import traceback
        traceback.print_exc()
        if node:
            node.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()

