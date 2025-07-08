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
        
        # Estado de consenso
        self.consensus_in_progress = False
        self.round_query_in_progress = False
        self.values_received = {}
        self.responses_received = {}
        self.round_responses = {}

        # Controle de estado da rede
        self.was_connected = True  # Assume conectado na inicialização
        
        # Log de criação bem-sucedida
        self.log(f"✅ Nó {self.pid} criado com sucesso", "✅", "green")
        
        # Log de configuração de timeouts
        from .config import CONSENSUS_INTERVAL, LEADER_QUERY_DELAY, LEADER_CONSENSUS_DELAY
        self.log(f"⚙️ Timeouts: CONSENSUS_INTERVAL={CONSENSUS_INTERVAL}s, LEADER_QUERY_DELAY={LEADER_QUERY_DELAY}s, LEADER_CONSENSUS_DELAY={LEADER_CONSENSUS_DELAY}s", "⚙️", "blue")

    # util
    def log(self, msg: str, emoji: str = "ℹ️", color: str = ""):
        """
        Exibe mensagem de log colorida com emoji para o processo.
        
        Args:
            msg (str): Mensagem a ser exibida
            emoji (str): Emoji para prefixar a mensagem
            color (str): Cor do texto ('red', 'green', 'yellow', 'blue', etc.)
        """
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
        
        import time
        timestamp = time.strftime("%H:%M:%S") + f":{int(time.time() * 1000) % 1000:03d}"
        print(f"[{timestamp}] {bold_code}[{color_code}PID {self.pid}{reset_code}{bold_code}]{reset_code} {emoji} {color_code}{msg}{reset_code}", flush=True)

    # network
    def send(self, op: str, **kv):
        """
        Envia uma mensagem via multicast usando o NetworkManager.
        
        Args:
            op (str): Tipo da operação/mensagem
            **kv: Campos adicionais da mensagem
        """
        # VERIFICAÇÃO CRÍTICA: Não envia se não há conexão
        if not self.network.connected:
            return False
            
        if op in ["OK", "ELECTION", "LEADER"]:
            recipient = kv.get("to", "ALL")
            self.log(f"Enviando {op} para {recipient}", "📤", "purple")
        
        success = self.network.send(pack(op, **kv))
        if not success:
            self.log(f"Falha ao enviar {op} - rede indisponível", "❌", "red")
                
        return success

    def get_alive_pids(self):
        """
        Retorna lista de PIDs vivos (excluindo o próprio).
        
        Returns:
            list[int]: Lista de PIDs dos processos vivos
        """
        return [pid for pid in self.alive.keys() if pid != self.pid]
    
    def clear_consensus_state(self):
        """
        Limpa estados de consenso para ressincronização.
        
        Chamado quando líder muda ou processo se reconecta.
        """
        self.consensus_in_progress = False
        self.round_query_in_progress = False
        
        # Limpa dados de rounds antigos para evitar travamentos
        current_round = self.round
        old_rounds = [r for r in self.values_received.keys() if r < current_round - 1]
        for old_round in old_rounds:
            self.values_received.pop(old_round, None)
            self.responses_received.pop(old_round, None)
        
        self.log("Estados de consenso limpos para ressincronização", "🧹", "blue")

    def calculate_current_value(self):
        """
        Calcula o valor atual do processo para o consenso.
        
        Returns:
            int: Valor calculado (função do PID e número aleatório)
        """
        i = randint(1, 10)
        return i * i * self.pid

    def start_consensus_round(self):
        """
        Inicia uma rodada de consenso (chamado pelo líder).
        
        O líder envia sinal START_CONSENSUS para todos os processos
        calcularem e enviarem seus valores.
        """
        self.log("🎯 start_consensus_round() chamado", "🎯", "cyan")
        
        # VERIFICAÇÃO CRÍTICA: Só inicia consenso se há conexão
        if not self.network.connected:
            self.log("❌ Sem rede - não pode iniciar consenso", "🔌", "red")
            return
            
        with self.state_lock:
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                self.log("Eleição em andamento - pausando consenso", "⏸️", "yellow")
                return
                
            if self.pid != self.leader:
                self.log(f"Não sou líder (líder atual: {self.leader}) - ignorando start_consensus_round", "🙅", "yellow")
                return
            
            self.log(f"Iniciando consenso para round {self.round}", "🚀", "green")
            self.log(f"🔥 LÍDER EXECUTANDO CONSENSO - Round {self.round}", "🔥", "green")
            self.consensus_in_progress = True
            self.values_received[self.round] = {}
            self.responses_received[self.round] = {}
            
            # Envia sinal para todos calcularem e enviarem seus valores
            self.send("START_CONSENSUS", round=self.round)

    def process_maximum_value(self):
        """
        Processa valores recebidos e calcula resposta.
        
        Verifica se recebeu valores de todos os processos vivos,
        calcula o máximo e envia resposta para o líder (apenas uma vez).
        """
        with self.state_lock:
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                return
                
            if self.round not in self.values_received:
                return
            
            alive_pids = set(self.alive.keys())
            received_pids = set(self.values_received[self.round].keys())
            
            # Verifica se recebeu valores de todos os processos vivos
            # OU se esperou tempo suficiente (para evitar travamentos)
            if not alive_pids.issubset(received_pids):
                # Se está esperando há muito tempo, processa com o que tem
                if len(received_pids) == 0:
                    return
                    
            # Calcula resposta (máximo de todos os valores)
            values = list(self.values_received[self.round].values())
            if not values:
                return
                
            my_response = max(values)
            
            self.log(f"Valores recebidos: {values}, Resposta: {my_response}", "🧮", "cyan")
            
            # Envia resposta para o líder (marca como enviada)
            self.log(f"Enviando resposta {my_response} para o líder", "📤", "cyan")
            self.send("RESPONSE", pid=self.pid, response=my_response, round=self.round)

    def process_consensus_responses(self):
        """
        Processa respostas e faz consenso final (líder).
        
        Verifica se recebeu respostas de todos os processos vivos,
        faz consenso por maioria e avança para o próximo round.
        """
        with self.state_lock:
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                return
                
            if self.pid != self.leader or self.round not in self.responses_received:
                return
            
            alive_pids = set(self.alive.keys())
            received_pids = set(self.responses_received[self.round].keys())
            
            # Processa se tem pelo menos uma resposta (para evitar travamentos)
            responses = list(self.responses_received[self.round].values())
            if not responses:
                return
            
            # Faz consenso por maioria
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
            self.log(f"⏰ Próximo round de consenso agendado em {CONSENSUS_INTERVAL}s", "⏰", "green")

    def query_current_round(self):
        """
        Líder pergunta qual round estamos (quando assume liderança).
        
        Consulta todos os processos sobre o round atual e agenda
        processamento do consenso de round.
        """
        self.log("🔍 query_current_round() chamado", "🔍", "cyan")
        
        # VERIFICAÇÃO CRÍTICA: Só faz query se há conexão
        if not self.network.connected:
            self.log("❌ Sem rede - não pode fazer query de round", "🔌", "red")
            return
            
        with self.state_lock:
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                self.log("Eleição em andamento - pausando query de round", "⏸️", "yellow")
                return
                
            if self.pid != self.leader:
                self.log(f"Não sou líder (líder atual: {self.leader}) - ignorando query_current_round", "🙅", "yellow")
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
            self.log(f"⏰ Processamento de consenso de round agendado em {ROUND_QUERY_TIMEOUT}s", "⏰", "blue")

    def process_round_consensus(self):
        """
        Faz consenso do round atual por maioria.
        
        Processa respostas da consulta de round, escolhe o round
        por maioria e inicia primeira rodada de consenso.
        """
        self.log("⚡ process_round_consensus() chamado", "⚡", "cyan")
        
        with self.state_lock:
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                return
                
            if not self.round_query_in_progress or self.pid != self.leader:
                if self.pid != self.leader:
                    self.log(f"Não sou líder (líder atual: {self.leader}) - ignorando process_round_consensus", "🙅", "yellow")
                elif not self.round_query_in_progress:
                    self.log("Query de round não está em andamento - ignorando process_round_consensus", "🙅", "yellow")
                return
            
            # Faz consenso por maioria dos rounds reportados
            rounds = list(self.round_responses.values())
            if not rounds:
                # Se não tem respostas, usa round atual mesmo
                rounds = [self.round]
            
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
            self.log(f"⏰ Primeira rodada de consenso agendada em {LEADER_CONSENSUS_DELAY}s", "⏰", "green")

    # election helpers
    def start_election(self):
        """
        Inicia processo de eleição Bully.
        
        Só inicia eleição quando:
        - Líder atual morreu/não responde
        - Não há líder conhecido
        - HÁ CONEXÃO DE REDE
        """
        # VERIFICAÇÃO CRÍTICA: Só inicia eleição se há conexão
        if not self.network.connected:
            self.log("❌ Sem rede - não pode iniciar eleição", "🔌", "red")
            return
            
        with self.state_lock:
            # Evita eleições simultâneas
            if self.in_election:
                self.log("Eleição já em andamento - ignorando", "🔄", "yellow")
                return
                
            self.in_election = True  # MARCA que eleição começou
            self.leader = None
            self.log(f"Iniciando processo de eleição", "🗳️", "red")
            self.received_ok = False
            
        # Chama bully fora do lock para evitar deadlock
        bully(self)
        
        # Reseta flag após eleição (só se não virou líder)
        with self.state_lock:
            if self.leader != self.pid:
                self.in_election = False

    def become_leader(self):
        """
        Assume liderança do sistema.
        
        Assume liderança se ninguém maior respondeu na eleição.
        """
        # VERIFICAÇÃO CRÍTICA: Só assume liderança se há conexão
        if not self.network.connected:
            self.log("❌ Sem rede - não pode assumir liderança", "🔌", "red")
            return
            
        with self.state_lock:
            if self.leader == self.pid:
                self.log("Já sou o líder - ignorando", "🤴", "blue")
                return
                
            self.leader = self.pid
            self.in_election = False  # Eleição terminou - sou o líder
            self.log("Assumiu liderança", "👑", "green")
            self.log(f"🎉 AGORA SOU O LÍDER! - Round atual: {self.round}", "🎉", "green")
            self.send("LEADER", pid=self.pid, round=self.round)
            
        # Quando vira líder, consulta round atual
        threading.Timer(LEADER_QUERY_DELAY, self.query_current_round).start()
        self.log(f"⏰ Query de round inicial agendada em {LEADER_QUERY_DELAY}s", "⏰", "blue")

    # handlers
    def handle(self, data: bytes):
        """
        Processa mensagem recebida via multicast.
        
        Args:
            data (bytes): Dados da mensagem recebida
        """
        msg = unpack(data)
        op  = msg["op"]

        if op == "HELLO":
            sender_pid = msg["pid"]
            
            # Atualiza timestamp sempre (mesmo durante eleições)
            self.alive[sender_pid] = monotonic()
            self.log(f"Recebido HELLO do processo {sender_pid}", "👋", "yellow")
            
            # Responde IMEDIATAMENTE se é o líder (mesmo durante eleições)
            if self.pid == self.leader:
                self.send("HELLO_ACK", pid=self.pid, round=self.round, to=sender_pid)
                self.log(f"Enviando HELLO_ACK para {sender_pid}", "✋", "green")

        elif op == "HELLO_ACK":
            # HELLO_ACK sempre funciona (importante para descoberta)
            if self.pid == msg["to"]:
                # Processo encontrou líder - sincroniza estado COMPLETAMENTE
                with self.state_lock:
                    self.in_election = False  # Cancela eleição se encontrou líder
                    self.received_ok = False
                    self.leader = msg["pid"]
                    self.round = msg["round"]
                    self.alive[msg["pid"]] = monotonic()
                
                self.log(f"Conectado ao líder {self.leader} (round {self.round})", "🔗", "green")
                
                # Limpa TUDO para ressincronização completa
                self.clear_consensus_state()
                
                # Força ressincronização de estado
                self.values_received.clear()
                self.responses_received.clear()
                self.round_responses.clear()
                
            else:
                self.log(f"Processo {msg['to']} reconectou ao sistema", "🔄", "cyan")

        elif op == "HB":
            # HB sempre funciona (heartbeat é fundamental)
            self.alive[msg["pid"]] = monotonic()

        elif op == "ELECTION":
            # ELECTION sempre funciona (crítico para eleições)
            src = msg["source"]
            if self.pid > src:
                self.log(f"Sou maior que {src} - enviando OK e iniciando eleição", "✅", "yellow")
                self.send("OK", to=src)
                threading.Timer(0.3, self.start_election).start()
            elif self.pid < src:
                self.log(f"Sou menor que {src} - ignorando eleição", "🙈", "blue")
            else:
                self.log(f"Recebi eleição de mim mesmo - ignorando", "🤔", "blue")

        elif op == "OK":
            # OK sempre funciona (crítico para eleições)
            if msg.get("to") == self.pid:
                self.log(f"Recebido OK na eleição", "✅", "green")
                self.received_ok = True
                if self.leader == self.pid:
                    self.log("Deixando de ser líder após receber OK", "👑➡️", "yellow")
                    self.leader = None
            else:
                self.log(f"OK não era para mim", "📨", "blue")

        elif op == "LEADER":
            # LEADER sempre funciona (crítico para eleições)
            # Novo líder foi eleito - sincroniza estado
            leader_pid = msg["pid"]
                
            # Sincroniza com novo líder
            self.in_election = False  # Eleição terminou
            self.received_ok = False
            self.leader = leader_pid
            self.alive[leader_pid] = monotonic()
            
            self.log(f"Líder eleito: {self.leader} (round {self.round})", "🗳️", "green")
            self.clear_consensus_state()

        elif op == "START_CONSENSUS":
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                self.log("Eleição em andamento - ignorando START_CONSENSUS", "⏸️", "yellow")
                return
                
            # Líder iniciou consenso
            consensus_round = msg["round"]
            
            self.log(f"Líder iniciou consenso para round {consensus_round}", "🎯", "green")
            
            with self.state_lock:
                if consensus_round not in self.values_received:
                    self.values_received[consensus_round] = {}
                
                # Calcula e envia valor (marca como enviado)
                my_value = self.calculate_current_value()
                self.values_received[consensus_round][self.pid] = my_value
                self.log(f"Calculei valor {my_value} para enviar", "💰", "cyan")
                self.send("VALUE", pid=self.pid, value=my_value, round=consensus_round)

        elif op == "VALUE":
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                self.log("Eleição em andamento - ignorando VALUE", "⏸️", "yellow")
                return
                
            # Recebeu valor de outro processo
            round_num = msg["round"]
            self.log(f"Recebido valor {msg['value']} do processo {msg['pid']} (round {round_num})", "📥", "purple")
            with self.state_lock:
                if round_num not in self.values_received:
                    self.values_received[round_num] = {}
                
                self.values_received[round_num][msg["pid"]] = msg["value"]
                
                # Verifica se pode processar consenso
                threading.Timer(VALUE_PROCESS_DELAY, self.process_maximum_value).start()

        elif op == "RESPONSE":
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                self.log("Eleição em andamento - ignorando RESPONSE", "⏸️", "yellow")
                return
                
            # Líder recebeu resposta
            with self.state_lock:
                if self.pid == self.leader:
                    round_num = msg["round"]
                    self.log(f"Recebida resposta {msg['response']} do processo {msg['pid']} (round {round_num})", "📩", "purple")
                    if round_num not in self.responses_received:
                        self.responses_received[round_num] = {}
                        
                    self.responses_received[round_num][msg["pid"]] = msg["response"]
                    
                    # Verifica se pode processar consenso final
                    threading.Timer(RESPONSE_PROCESS_DELAY, self.process_consensus_responses).start()

        elif op == "ROUND_QUERY":
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                self.log("Eleição em andamento - ignorando ROUND_QUERY", "⏸️", "yellow")
                return
                
            # Líder perguntou qual round estamos
            self.log(f"Enviando ROUND_RESPONSE = {self.round}", "📩", "purple")
            self.send("ROUND_RESPONSE", pid=self.pid, round=self.round)

        elif op == "ROUND_RESPONSE":
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                self.log("Eleição em andamento - ignorando ROUND_RESPONSE", "⏸️", "yellow")
                return
                
            # Recebeu resposta de round
            with self.state_lock:
                if self.pid == self.leader and self.round_query_in_progress:
                    self.round_responses[msg["pid"]] = msg["round"]

        elif op == "ROUND_UPDATE":
            # PAUSA: Respeita eleições em andamento
            if self.in_election:
                self.log("Eleição em andamento - ignorando ROUND_UPDATE", "⏸️", "yellow")
                return
                
            # Líder informou novo round
            self.round = msg["round"]
            self.log(f"Round atualizado para {self.round}", "📊", "blue")

    # main loop --------------------------
    def run(self):
        """
        Executa o loop principal do processo distribuído.
        
        Sequência de inicialização:
        1. Inicia thread de escuta de mensagens
        2. Envia HELLO para descobrir líder existente
        3. Aguarda resposta OU atividade de líder
        4. Só inicia eleição se realmente não há líder ativo
        5. Inicia heartbeat e monitoramento
        
        Loop principal com prioridades:
        1. REDE: Aguarda conexão se desconectado
        2. RECONEXÃO: Envia HELLO quando rede volta
        3. ELEIÇÃO: Monitora eleições em andamento
        4. DESCOBERTA: Procura líder se não tem nenhum
        """
        self.log(f"Iniciando processo com PID {self.pid}", "🚀", "green")
        
        # Inicia thread de escuta
        self.log("🎯 Iniciando thread de escuta de mensagens", "🎯", "blue")
        listener = threading.Thread(target=self.listen, daemon=True)
        listener.start()

        # Pequena pausa para sincronizar com a rede
        self.log("⏳ Aguardando sincronização com a rede...", "⏳", "yellow")
        sleep(0.5)

        # discovery
        self.log("🔍 Enviando HELLO para descobrir líder", "🔍", "yellow")
        self.send("HELLO", pid=self.pid)
        
        self.log("💓 Iniciando sistema de heartbeat", "💓", "cyan")
        start_heartbeat(self)

        # Aguarda resposta inicial
        self.log(f"⏱️ Aguardando resposta inicial por {HELLO_TIMEOUT}s", "⏱️", "blue")
        sleep(HELLO_TIMEOUT)
        
        # Se não encontrou líder, aguarda um pouco mais para detectar atividade
        if self.leader is None:
            self.log("👀 Aguardando atividade de líder na rede...", "👀", "yellow")
            sleep(3)  # Tempo adicional para detectar consensos, heartbeats, etc.
        
        # Só inicia eleição se realmente não há líder
        need_election = False
        with self.state_lock:
            if self.leader is None:
                need_election = True
        
        if need_election:
            self.log("🚨 Nenhum líder detectado ➜ iniciando eleição", "🚨", "red")
            self.start_election()
        else:
            self.log(f"✅ Líder {self.leader} encontrado - sem necessidade de eleição", "✅", "green")

        # Só inicia monitor após descoberta inicial
        self.log("🛡️ Iniciando sistema de monitoramento de falhas", "🛡️", "cyan")
        start_monitor(self)

        self.log("🔄 Entrando no loop principal do sistema", "🔄", "green")
        
        # nó vivo indefinidamente
        last_network_log = 0  # Para evitar spam de logs
        last_status_log = 0   # Para logs de status periódicos
        last_problem_log = 0  # Para logs de problemas do líder
        
        while True:
            now = monotonic()
            
            # PRIORIDADE 1: Verifica se está conectado à rede
            if not self.network.connected:
                # Log apenas a cada 10 segundos para evitar spam
                if now - last_network_log > 10:
                    self.log("❌ Sem conexão de rede - aguardando reconexão", "🔌", "red")
                    last_network_log = now
                sleep(2)
                continue
            
            # PRIORIDADE 2: Se reconectou, envia HELLO para redescobrir rede
            if not self.was_connected and self.network.connected:
                self.log("✅ Rede reconectada - enviando HELLO para redescobrir", "🔌", "green")
                self.leader = None  # Reseta líder para redescobrir
                self.send("HELLO", pid=self.pid)
                sleep(2)  # Aguarda resposta
                
            # Atualiza estado da rede para próxima iteração
            self.was_connected = self.network.connected
            
            # PRIORIDADE 3: Durante eleição, apenas monitora
            if self.in_election:
                self.log("Eleição em andamento - aguardando resolução", "⏸️", "red")
                sleep(1)
                continue

            # PRIORIDADE 4: Se não tem líder, tenta descobrir
            if self.leader is None:
                self.log("Sem líder - enviando HELLO para descobrir", "🔍", "yellow")
                self.send("HELLO", pid=self.pid)
                sleep(5)  # Aguarda 5 segundos antes de tentar novamente
            elif self.leader is not None:
                # Log periódico de status quando tem líder
                if now - last_status_log > 30:  # A cada 30 segundos
                    alive_count = len(self.get_alive_pids())
                    consensus_status = "ativo" if self.consensus_in_progress else "aguardando"
                    query_status = "ativo" if self.round_query_in_progress else "aguardando"
                    
                    # Se sou o líder, mostro meu status detalhado
                    if self.leader == self.pid:
                        if self.consensus_in_progress:
                            self.log(f"👑 LÍDER EXECUTANDO CONSENSO - Round: {self.round}, Processos: {alive_count}", "👑", "green")
                        elif self.round_query_in_progress:
                            self.log(f"👑 LÍDER FAZENDO QUERY - Round: {self.round}, Processos: {alive_count}", "👑", "blue")
                        else:
                            self.log(f"👑 LÍDER AGUARDANDO - Round: {self.round}, Processos: {alive_count} (próximo consenso em breve)", "👑", "yellow")
                    else:
                        self.log(f"💖 Sistema ativo - Líder: {self.leader}, Round: {self.round}, Processos: {alive_count}", "💖", "green")
                    
                    last_status_log = now
                    
                # Se sou o líder e não há consenso nem query em andamento, algo está errado
                # elif self.leader == self.pid and not self.consensus_in_progress and not self.round_query_in_progress:
                #     if now - last_problem_log > 20:  # A cada 20 segundos
                #         self.log("🚨 PROBLEMA: Líder sem consenso nem query em andamento - fazendo query de round para recuperar", "🚨", "red")
                #         last_problem_log = now
                #         self.query_current_round()

                else:
                    # Pequena pausa para não sobrecarregar CPU
                    pass
                
                sleep(1)  # Se tem líder, verifica menos frequentemente
            else:
                self.log("⚠️ Estado indefinido - tentando eleição", "⚠️", "yellow")
                bully(self)
                sleep(1)
                
        # Este log só aparece se o loop while sair (não deveria acontecer)
        self.log("🚨 CRÍTICO: Loop principal terminou inesperadamente!", "🚨", "red")
        self.log(f"📊 Estado final - Líder: {self.leader}, Round: {self.round}, Processos vivos: {len(self.get_alive_pids())}", "📊", "cyan")

    def listen(self):
        """
        Loop de escuta de mensagens multicast.
        
        Recebe mensagens do socket multicast e as processa
        através do método handle(). Executa indefinidamente
        em thread separada.
        """
        self.log("🎧 Iniciando escuta de mensagens multicast", "🎧", "cyan")
        last_activity_log = 0  # Para logs de atividade periódicos
        message_count = 0
        
        while True:
            result = self.network.receive(65535)
            if result is not None:
                data, _ = result
                message_count += 1
                self.handle(data)
            else:
                # Pequena pausa quando não há dados ou erro de rede
                sleep(0.1)
                
                # Log periódico de atividade da thread de escuta
                now = monotonic()
                if now - last_activity_log > 60:  # A cada 60 segundos
                    self.log(f"🎧 Thread de escuta ativa - {message_count} mensagens processadas", "🎧", "cyan")
                    last_activity_log = now
                    message_count = 0  # Reset do contador
                    
        # Este log só aparece se o loop while sair (não deveria acontecer)
        self.log("🚨 CRÍTICO: Loop de escuta terminou inesperadamente!", "🚨", "red")
        self.log(f"📊 Total de mensagens processadas: {message_count}", "📊", "cyan")

def main():
    """
    Função principal que inicializa e executa um nó do sistema.
    
    Processa argumentos da linha de comando e cria uma instância
    do Node com os parâmetros especificados.
    
    Args (linha de comando):
        --id: ID único do processo (obrigatório)
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--id",     type=int, required=True)
    args = ap.parse_args()
    
    # Log inicial do processo
    print(f"[INICIO] 🚀 Iniciando sistema com PID {args.id}")
    
    try:
        node = Node(pid=args.id)
        node.run()
    except KeyboardInterrupt:
        print(f"[SAÍDA] 🛑 Processo {args.id} interrompido pelo usuário")
    except Exception as e:
        print(f"[ERRO] 💥 Processo {args.id} falhou: {e}")
        import traceback
        traceback.print_exc()
    else:
        print(f"[NORMAL] ✅ Processo {args.id} terminou normalmente (não deveria acontecer)")
    finally:
        print(f"[FIM] 👋 Processo {args.id} terminado")

if __name__ == "__main__":
    main()

