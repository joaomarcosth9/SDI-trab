#!/usr/bin/env python3
import argparse, threading
from time import monotonic, sleep
from random import randint
from collections import defaultdict
from .config import *
from .communication import create_socket, send
from .message import pack, unpack
from .failure_detection import start_heartbeat, start_monitor
from .election import bully

class Node:
    def __init__(self, pid: int, total: int):
        self.pid        = pid
        self.total      = total
        self.sock       = create_socket()
        self.round      = ROUND_START
        self.leader     = None     # pid
        self.alive      = {pid: monotonic()}
        self.received_ok = False
        
        # Consenso
        self.values_received = {}        # round -> {pid: value}
        self.responses_received = {}     # round -> {pid: response}
        self.round_responses = {}        # {pid: round} para consenso de round
        self.consensus_in_progress = False
        self.round_query_in_progress = False

    # util
    def log(self, msg: str, emoji: str = "ℹ️", color: str = ""):
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "purple": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
            "reset": "\033[0m",
            "bold": "\033[1m"
        }
        
        color_code = colors.get(color, "")
        reset_code = colors["reset"] if color else ""
        bold_code = colors["bold"]
        
        print(f"{bold_code}[{color_code}PID {self.pid}{reset_code}{bold_code}]{reset_code} {emoji} {color_code}{msg}{reset_code}", flush=True)

    # network
    def send(self, op: str, **kv):
        if op in ["OK", "ELECTION", "LEADER"]:
            recipient = kv.get("to", "ALL")
            self.log(f"Enviando {op} para {recipient}", "📤", "purple")
        send(self.sock, pack(op, **kv))

    def get_alive_pids(self):
        """Retorna lista de PIDs vivos (excluindo o próprio)"""
        return [pid for pid in self.alive.keys() if pid != self.pid]

    def calculate_current_value(self):
        """Calcula o valor atual do processo"""
        i = randint(1, 10)
        return i * i * self.pid

    def start_consensus_round(self):
        """Inicia uma rodada de consenso (chamado pelo líder)"""
        if self.pid != self.leader:
            return
            
        self.log(f"Iniciando consenso para round {self.round}", "🚀", "green")
        self.consensus_in_progress = True
        self.values_received[self.round] = {}
        self.responses_received[self.round] = {}
        
        # Envia sinal para todos calcularem e enviarem seus valores
        self.send("START_CONSENSUS", round=self.round)

    def process_maximum_value(self):
        """Processa valores recebidos e calcula resposta"""
        if self.round not in self.values_received:
            return
            
        alive_pids = set(self.alive.keys())
        received_pids = set(self.values_received[self.round].keys())
        
        # Verifica se recebeu valores de todos os processos vivos
        if not alive_pids.issubset(received_pids):
            return
            
        # Calcula resposta (máximo de todos os valores)
        values = list(self.values_received[self.round].values())
        my_response = max(values)
        
        self.log(f"Valores recebidos: {values}, Resposta: {my_response}", "🧮", "cyan")
        
        # Envia resposta para o líder
        self.log(f"Enviando resposta {my_response} para o líder", "📤", "cyan")
        self.send("RESPONSE", pid=self.pid, response=my_response, round=self.round)

    def process_consensus_responses(self):
        """Processa respostas e faz consenso final (líder)"""
        if self.pid != self.leader or self.round not in self.responses_received:
            return
            
        alive_pids = set(self.alive.keys())
        received_pids = set(self.responses_received[self.round].keys())
        
        # Verifica se recebeu respostas de todos os processos vivos
        if not alive_pids.issubset(received_pids):
            return
            
        # Faz consenso por maioria
        responses = list(self.responses_received[self.round].values())
        response_counts = defaultdict(int)
        
        for response in responses:
            response_counts[response] += 1
            
        # Escolhe a resposta com maior número de votos
        consensus_response = max(response_counts.items(), key=lambda x: x[1])[0]
        
        self.log(f"CONSENSO ROUND {self.round}: Resposta = {consensus_response} (votos: {dict(response_counts)})", "🎯", "purple")
        
        # Avança para o próximo round
        self.round += 1
        self.send("ROUND_UPDATE", round=self.round)
        
        self.consensus_in_progress = False
        
        # Agenda próxima rodada de consenso
        threading.Timer(CONSENSUS_INTERVAL, self.start_consensus_round).start()

    def query_current_round(self):
        """Líder pergunta qual round estamos (quando assume liderança)"""
        if self.pid != self.leader:
            return
            
        self.log("Consultando round atual dos processos", "🔍", "blue")
        self.round_query_in_progress = True
        self.round_responses = {}
        
        # Adiciona seu próprio round
        self.round_responses[self.pid] = self.round
        
        # Pergunta para todos
        self.send("ROUND_QUERY")
        
        # Aguarda respostas por alguns segundos
        threading.Timer(ROUND_QUERY_TIMEOUT, self.process_round_consensus).start()

    def process_round_consensus(self):
        """Faz consenso do round atual por maioria"""
        if not self.round_query_in_progress or self.pid != self.leader:
            return
            
        # Faz consenso por maioria dos rounds reportados
        rounds = list(self.round_responses.values())
        if not rounds:
            return
            
        round_counts = defaultdict(int)
        for round_num in rounds:
            round_counts[round_num] += 1
            
        # Escolhe o round com maior número de votos
        consensus_round = max(round_counts.items(), key=lambda x: x[1])[0]
        
        self.round = consensus_round
        self.log(f"CONSENSO DE ROUND: Round atual = {consensus_round} (votos: {dict(round_counts)})", "⚡", "yellow")
        
        # Informa novo round para todos
        self.send("ROUND_UPDATE", round=self.round)
        
        self.round_query_in_progress = False
        
        # Inicia primeira rodada de consenso
        threading.Timer(LEADER_CONSENSUS_DELAY, self.start_consensus_round).start()

    # election helpers
    def start_election(self):
        self.log("Iniciando processo de eleição", "🗳️", "red")
        self.received_ok = False
        bully(self)

    def become_leader(self):
        if self.leader == self.pid:
            self.log("Já sou o líder - ignorando", "🤴", "blue")
            return
            
        self.leader = self.pid
        self.log("Assumiu liderança", "👑", "green")
        self.send("LEADER", pid=self.pid, round=self.round)
        
        # Quando vira líder, consulta round atual
        threading.Timer(LEADER_QUERY_DELAY, self.query_current_round).start()

    # handlers
    def handle(self, data: bytes):
        msg = unpack(data)
        op  = msg["op"]

        if op == "HELLO":
            self.alive[msg["pid"]] = monotonic()
            self.log(f"Recebido HELLO do processo {msg['pid']}", "👋", "yellow")
            if self.pid == self.leader:
                self.send("HELLO_ACK", pid=self.pid, round=self.round, to=msg["pid"])
                self.log(f"Enviando HELLO_ACK para {msg['pid']}", "✋", "green")

        elif op == "HELLO_ACK":
            if self.pid == msg["to"]:
                self.leader = msg["pid"]
                self.round  = msg["round"]
                self.alive[msg["pid"]] = monotonic()
                self.log(f"Conectado ao líder {self.leader} (round {self.round})", "🔗", "green")
            else:
                self.log(f"Processo {msg['to']} voltou a VIDA", "🔄", "cyan")

        elif op == "HB":
            self.alive[msg["pid"]] = monotonic()

        elif op == "ELECTION":
            src = msg["source"]
            self.log(f"Recebida eleição de {src}", "🗳️", "red")
            if self.pid > src:
                self.log(f"Sou maior que {src} - enviando OK para {src} e iniciando eleição", "✅", "yellow")
                self.send("OK", to=src)
                # Pequeno delay para evitar condições de corrida
                threading.Timer(0.1, self.start_election).start()
            elif self.pid < src:
                self.log(f"Sou menor que {src} - ignorando eleição", "🙈", "blue")

        elif op == "OK":
            if msg.get("to") == self.pid:
                self.log(f"Recebido OK na eleição (direcionado para mim)", "✅", "green")
                self.received_ok = True
                # Se eu era líder e recebi OK, não sou mais
                if self.leader == self.pid:
                    self.log("Deixando de ser líder após receber OK", "👑➡️", "yellow")
                    self.leader = None
            else:
                self.log(f"Recebido OK na eleição (não era para mim: {msg.get('to')})", "📨", "blue")

        elif op == "LEADER":
            self.leader = msg["pid"]
            self.round  = msg["round"]
            self.alive[msg["pid"]] = monotonic()
            self.received_ok = False  # Cancela qualquer eleição em andamento
            self.log(f"Líder eleito: {self.leader} (round {self.round}) - cancelando eleições", "🗳️", "green")

        elif op == "START_CONSENSUS":
            # Líder iniciou consenso
            consensus_round = msg["round"]
            self.log(f"Líder iniciou consenso para round {consensus_round}", "🎯", "green")
            if consensus_round not in self.values_received:
                self.values_received[consensus_round] = {}
                
            # Calcula e envia valor
            my_value = self.calculate_current_value()
            self.values_received[consensus_round][self.pid] = my_value
            self.log(f"Calculei valor {my_value} para enviar", "💰", "cyan")
            self.send("VALUE", pid=self.pid, value=my_value, round=consensus_round)

        elif op == "VALUE":
            # Recebeu valor de outro processo
            round_num = msg["round"]
            self.log(f"Recebido valor {msg['value']} do processo {msg['pid']} (round {round_num})", "📥", "purple")
            if round_num not in self.values_received:
                self.values_received[round_num] = {}
                
            self.values_received[round_num][msg["pid"]] = msg["value"]
            
            # Verifica se pode processar consenso
            threading.Timer(VALUE_PROCESS_DELAY, self.process_maximum_value).start()

        elif op == "RESPONSE":
            # Líder recebeu resposta
            if self.pid == self.leader:
                round_num = msg["round"]
                self.log(f"Recebida resposta {msg['response']} do processo {msg['pid']} (round {round_num})", "📩", "purple")
                if round_num not in self.responses_received:
                    self.responses_received[round_num] = {}
                    
                self.responses_received[round_num][msg["pid"]] = msg["response"]
                
                # Verifica se pode processar consenso final
                threading.Timer(RESPONSE_PROCESS_DELAY, self.process_consensus_responses).start()

        elif op == "ROUND_QUERY":
            # Líder perguntou qual round estamos
            self.send("ROUND_RESPONSE", pid=self.pid, round=self.round)

        elif op == "ROUND_RESPONSE":
            # Recebeu resposta de round
            if self.pid == self.leader and self.round_query_in_progress:
                self.round_responses[msg["pid"]] = msg["round"]

        elif op == "ROUND_UPDATE":
            # Líder informou novo round
            self.round = msg["round"]
            self.log(f"Round atualizado para {self.round}", "📊", "blue")

    # main loop --------------------------
    def run(self):
        self.log(f"Iniciando processo com PID {self.pid} (total: {self.total})", "🚀", "green")
        listener = threading.Thread(target=self.listen, daemon=True)
        listener.start()

        # discovery
        self.log("Enviando HELLO para descobrir líder", "🔍", "yellow")
        self.send("HELLO", pid=self.pid)
        start_heartbeat(self)

        sleep(HELLO_TIMEOUT)
        if self.leader is None:
            self.log("Sem HELLO_ACK ➜ iniciando eleição", "🔥", "red")
            self.start_election()

        start_monitor(self)

        # nó vivo indefinidamente
        while True:
            sleep(1)

    def listen(self):
        while True:
            data, _ = self.sock.recvfrom(65535)
            self.handle(data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id",     type=int, required=True)
    ap.add_argument("--nodes",  type=int, default=0, help="apenas para log")
    args = ap.parse_args()
    node = Node(pid=args.id, total=args.nodes or args.id)
    node.run()

if __name__ == "__main__":
    main()

