#!/usr/bin/env python3

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
    def __init__(self, pid: int):
        self.pid = pid
        self.network = NetworkManager()
        
        self.state_lock = threading.RLock()
        self.round = ROUND_START
        self.leader = None
        self.alive = {pid: monotonic()}
        
        self.in_election = False
        self.received_ok = False
        
        self.round_votes = {}
        self.round_consensus_timer = None
        
        self.values_received = {}
        self.responses_received = {}
        self.responses_sent = {}
        self.value_timers = {}
        
        self.consensus_timer = None
        self.was_connected = True
        self.shutdown = False
        
        self.log(f"Nó {self.pid} criado com sucesso", "green")

    def log(self, msg: str, color: str = ""):
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
        if not self.network.connected:
            return False
            
        return self.network.send(pack(op, **kv))

    def get_alive_pids(self):
        return [pid for pid in self.alive.keys() if pid != self.pid]
    
    def calculate_current_value(self):
        i = randint(1, 10)
        return i * i * self.pid

    def schedule_next_consensus(self):
        if self.leader != self.pid:
            return
            
        if self.consensus_timer:
            self.consensus_timer.cancel()
            
        self.consensus_timer = threading.Timer(CONSENSUS_INTERVAL, self.start_consensus_round)
        self.consensus_timer.start()

    def start_consensus_round(self):
        if not self.network.connected:
            self.schedule_next_consensus()
            return
            
        with self.state_lock:
            if self.pid != self.leader:
                return
            
            alive_pids = self.get_alive_pids()
            self.log(f"[LÍDER] Iniciando consenso round {self.round} - Processos vivos: {[self.pid] + alive_pids}", "green")
            self.values_received[self.round] = {}
            self.responses_received[self.round] = {}
            
            my_value = self.calculate_current_value()
            self.values_received[self.round][self.pid] = my_value
            self.log(f"[LÍDER] Meu valor: {my_value}", "green")
            
            self.send("START_CONSENSUS", round=self.round)
            
        threading.Timer(CONSENSUS_RESPONSE_TIMEOUT, self.process_consensus_responses).start()
        
        self.schedule_next_consensus()

    def process_consensus_responses(self):
        with self.state_lock:
            if self.pid != self.leader or self.round not in self.responses_received:
                return
            
            responses = list(self.responses_received[self.round].values())
            if not responses:
                return
            
            responses_detail = {pid: resp for pid, resp in self.responses_received[self.round].items()}
            self.log(f"[LÍDER] Respostas recebidas: {responses_detail}", "purple")
            
            response_counts = defaultdict(int)
            for response in responses:
                response_counts[response] += 1
            
            consensus_response = max(response_counts.items(), key=lambda x: x[1])[0]
            votes_detail = dict(response_counts)
            self.log(f"[VOTAÇÃO] Contagem: {votes_detail}", "purple")
            self.log(f"[CONSENSO] Round {self.round}: Resposta = {consensus_response} (votos: {response_counts[consensus_response]})", "purple")
            
            self.round += 1
            self.log(f"[LÍDER] Avançando para round {self.round}", "green")
            self.send("ROUND_UPDATE", round=self.round)

    def start_election(self):
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
        with self.state_lock:
            if self.pid != self.leader:
                return
                
            self.round_votes = {self.pid: self.round}
            alive_pids = self.get_alive_pids()
            
            self.log(f"[LÍDER] Iniciando consenso de round - processos vivos: {alive_pids}", "green")
            
            self.send("ROUND_REQUEST", from_pid=self.pid)
            
        self.round_consensus_timer = threading.Timer(
            ROUND_CONSENSUS_TIMEOUT, 
            lambda: self.process_round_consensus()
        )
        self.round_consensus_timer.start()
    
    def process_round_consensus(self):
        with self.state_lock:
            if self.pid != self.leader:
                return
                
            if not self.round_votes:
                self.log("[CONSENSO ROUND] Nenhum voto recebido, mantendo round atual", "yellow")
                return
                
            round_counts = defaultdict(int)
            for pid, round_vote in self.round_votes.items():
                round_counts[round_vote] += 1
            
            consensus_round = max(round_counts.items(), key=lambda x: x[1])[0]
            
            self.log(f"[CONSENSO ROUND] Votos recebidos: {dict(self.round_votes)}", "purple")
            self.log(f"[CONSENSO ROUND] Contagem: {dict(round_counts)}", "purple") 
            self.log(f"[CONSENSO ROUND] Round escolhido por maioria: {consensus_round} (votos: {round_counts[consensus_round]})", "green")
            
            if self.round != consensus_round:
                old_round = self.round
                self.round = consensus_round
                self.log(f"[CONSENSO ROUND] Líder atualizando round de {old_round} para {self.round}", "green")
                
                self.send("ROUND_UPDATE", round=self.round)
                self.log(f"[CONSENSO ROUND] Enviado ROUND_UPDATE para sincronizar todos no round {self.round}", "green")
            else:
                self.log(f"[CONSENSO ROUND] Round já está correto: {self.round}", "green")

    def become_leader(self):
        if not self.network.connected:
            return
            
        with self.state_lock:
            if self.leader == self.pid:
                return
                
            self.leader = self.pid
            self.in_election = False
            self.log("Assumi liderança", "green")
            
            if self.consensus_timer:
                self.consensus_timer.cancel()
                self.consensus_timer = None
            
            initial_round = self.round
            self.log(f"Assumindo liderança com round inicial {initial_round}", "green")
            
            self.send("LEADER", pid=self.pid, round=initial_round)
            
        threading.Timer(LEADER_STARTUP_DELAY, self.start_round_consensus).start()
        
        threading.Timer(LEADER_STARTUP_DELAY + ROUND_CONSENSUS_TIMEOUT + 0.5, 
                       self.start_consensus_round).start()

    def handle(self, data: bytes):
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
            
            if self.pid == self.leader and self.network.connected:
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
                    
                    if old_round != self.round:
                        rounds_to_remove = [r for r in self.values_received.keys() if r != self.round]
                        for r in rounds_to_remove:
                            self.values_received.pop(r, None)
                            self.responses_received.pop(r, None)
                            self.responses_sent.pop(r, None)
                            
                            if r in self.value_timers:
                                self.value_timers[r].cancel()
                                self.value_timers.pop(r, None)
                                
                        self.log(f"[HELLO_ACK] Limpei estados de {len(rounds_to_remove)} rounds diferentes", "yellow")
                
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
                
                if new_round > self.round:
                    self.round = new_round
                    self.log(f"Líder eleito: {self.leader}, sincronizando para round {self.round}", "green")
                else:
                    self.log(f"Líder eleito: {self.leader}, mantendo round {self.round}", "green")

        elif op == "START_CONSENSUS":
            consensus_round = msg["round"]
            self.log(f"[CONSENSO] Líder iniciou round {consensus_round}", "cyan")
            
            with self.state_lock:
                if consensus_round in self.responses_sent:
                    self.log(f"[CONSENSO] Limpando resposta anterior do round {consensus_round}", "yellow")
                    self.responses_sent.pop(consensus_round, None)
                
                if consensus_round <= self.round:
                    rounds_to_clear = [r for r in self.responses_sent.keys() if r >= consensus_round]
                    for r in rounds_to_clear:
                        self.responses_sent.pop(r, None)
                        self.log(f"[CONSENSO] Limpando estado futuro do round {r}", "yellow")
                
                if consensus_round in self.value_timers:
                    self.value_timers[consensus_round].cancel()
                    self.value_timers.pop(consensus_round, None)
                
                self.values_received[consensus_round] = {}
                
                my_value = self.calculate_current_value()
                self.values_received[consensus_round][self.pid] = my_value
                self.log(f"[CONSENSO] Meu valor gerado: {my_value} (round {consensus_round})", "cyan")
                self.send("VALUE", pid=self.pid, value=my_value, round=consensus_round)
                
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
            
            with self.state_lock:
                rounds_to_clear = [r for r in list(self.responses_sent.keys()) if r < new_round]
                for r in rounds_to_clear:
                    self.values_received.pop(r, None)
                    self.responses_received.pop(r, None) 
                    self.responses_sent.pop(r, None)
                    
                    if r in self.value_timers:
                        self.value_timers[r].cancel()
                        self.value_timers.pop(r, None)
                        
                if rounds_to_clear:
                    self.log(f"[ROUND_UPDATE] Limpei estados de {len(rounds_to_clear)} rounds antigos", "blue")

        elif op == "ROUND_REQUEST":
            from_pid = msg["from_pid"]
            
            if self.leader is None:
                self.log(f"[ROUND_REQUEST] Recebido de {from_pid} mas ainda não há líder", "yellow")
            elif from_pid == self.leader:
                self.log(f"[ROUND_REQUEST] Recebido do líder {from_pid}, respondendo com round {self.round}", "cyan")
                self.send("ROUND_RESPONSE", pid=self.pid, round=self.round, to=from_pid)
            else:
                self.log(f"[ROUND_REQUEST] Ignorando pedido de {from_pid} (líder atual é {self.leader})", "yellow")
            
        elif op == "ROUND_RESPONSE":
            if msg.get("to") == self.pid:
                sender_pid = msg["pid"]
                sender_round = msg["round"]
                
                with self.state_lock:
                    if hasattr(self, 'round_votes'):
                        self.round_votes[sender_pid] = sender_round
                        self.log(f"[ROUND_RESPONSE] Recebido voto: PID {sender_pid} votou round {sender_round}", "yellow")

    def process_maximum_value(self, round_num: int):
        with self.state_lock:
            if round_num not in self.values_received:
                self.log(f"[PROCESS_MAX] Round {round_num} não tem valores recebidos", "red")
                return
            
            if round_num in self.responses_sent:
                self.log(f"[PROCESS_MAX] Já enviou resposta para round {round_num} (valor: {self.responses_sent[round_num]})", "yellow")
                return
                
            values = list(self.values_received[round_num].values())
            if not values:
                return
                
            my_response = max(values)
            
            values_detail = {pid: val for pid, val in self.values_received[round_num].items()}
            self.log(f"[CÁLCULO] Valores recebidos: {values_detail}", "cyan")
            
            self.responses_sent[round_num] = my_response
            
            if self.pid == self.leader:
                if round_num not in self.responses_received:
                    self.responses_received[round_num] = {}
                self.responses_received[round_num][self.pid] = my_response
                self.log(f"[LÍDER] Resposta calculada: {my_response} (round {round_num})", "green")
            else:
                self.log(f"[RESPOSTA] Enviando resposta máxima: {my_response} (round {round_num})", "cyan")
                self.send("RESPONSE", pid=self.pid, response=my_response, round=round_num)
            
            self.value_timers.pop(round_num, None)

    def run(self):
        self.log(f"Iniciando processo", "green")
        
        listener = threading.Thread(target=self.listen, daemon=True)
        listener.start()

        sleep(STARTUP_DELAY)

        self.log("Procurando líder existente...", "yellow")
        self.send("HELLO", pid=self.pid)
        start_heartbeat(self)
        
        sleep(HELLO_TIMEOUT)
        
        if self.leader is None:
            self.log("Nenhum líder encontrado após HELLO inicial", "yellow")
        else:
            self.log(f"Líder {self.leader} encontrado", "green")

        start_monitor(self)
        
        last_status_log = 0
        last_network_log = 0
        last_leader_search = 0
        while not self.shutdown:
            if not self.network.connected:
                if self.was_connected:
                    with self.state_lock:
                        if self.leader == self.pid:
                            self.log("[REDE] Líder perdeu conexão - limpando estado", "red")
                        self.leader = None
                        self.in_election = False
                    
                    last_leader_search = 0
                
                now = monotonic()
                if now - last_network_log > NETWORK_LOG_INTERVAL:
                    self.log("[REDE] Sem conexão - aguardando...", "red")
                    last_network_log = now
                sleep(NETWORK_RETRY_DELAY)
                continue
            
            if not self.was_connected and self.network.connected:
                self.log("[REDE] Reconectado - redescobrir líder", "green")
                
                if self.consensus_timer:
                    self.consensus_timer.cancel()
                    self.consensus_timer = None
                    self.log("[REDE] Timer de consenso cancelado", "yellow")
                    
                if self.round_consensus_timer:
                    self.round_consensus_timer.cancel() 
                    self.round_consensus_timer = None
                    self.log("[REDE] Timer de consenso de round cancelado", "yellow")
                
                self.leader = None
                self.in_election = False
                
                self.values_received.clear()
                self.responses_received.clear()
                self.responses_sent.clear()
                self.round_votes.clear()
                
                for timer in self.value_timers.values():
                    try:
                        timer.cancel()
                    except:
                        pass
                self.value_timers.clear()
                
                self.send("HELLO", pid=self.pid)
                
                last_leader_search = 0
                
                sleep(NETWORK_RETRY_DELAY)
                
            self.was_connected = self.network.connected
            
            if self.leader is None and not self.in_election:
                now = monotonic()
                
                if last_leader_search == 0:
                    last_leader_search = now
                    self.log("Iniciando busca por líder...", "yellow")
                
                search_duration = now - last_leader_search
                
                if search_duration > LEADER_SEARCH_TIMEOUT:
                    self.log(f"Timeout na busca por líder ({search_duration:.1f}s) - iniciando eleição", "red")
                    self.start_election()
                    last_leader_search = 0
                else:
                    remaining = LEADER_SEARCH_TIMEOUT - search_duration
                    self.log(f"Procurando líder... (timeout em {remaining:.1f}s)", "yellow")
                    self.send("HELLO", pid=self.pid)
                    sleep(LEADER_SEARCH_INTERVAL)
            else:
                last_leader_search = 0
            
            now = monotonic()
            if now - last_status_log > STATUS_LOG_INTERVAL:
                with self.state_lock:
                    if self.leader == self.pid and self.network.connected:
                        self.log(f"[LÍDER ATIVO] Round: {self.round}, Processos vivos: {len(self.get_alive_pids())}", "green")
                    elif self.leader is not None:
                        self.log(f"[SEGUIDOR] Líder: {self.leader}, Round: {self.round}", "blue")
                    else:
                        self.log(f"[SEM LÍDER] Aguardando eleição...", "yellow")
                last_status_log = now
                
            sleep(MAIN_LOOP_INTERVAL)

    def listen(self):
        while not self.shutdown:
            result = self.network.receive(65535)
            if result is not None:
                data, _ = result
                self.handle(data)
            else:
                sleep(LISTEN_TIMEOUT)

    def stop(self):
        self.log("Encerrando processo...", "yellow")
        self.shutdown = True
        
        if self.consensus_timer:
            try:
                self.consensus_timer.cancel()
            except:
                pass
                
        if self.round_consensus_timer:
            try:
                self.round_consensus_timer.cancel()
            except:
                pass
            
        for timer in self.value_timers.values():
            try:
                timer.cancel()
            except:
                pass
        
        if self.network and self.network.connected:
            self.network.close()

def main():
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

