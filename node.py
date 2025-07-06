# node.py
import time
from comm import Comm
from election import RingElection
from heartbeat import Heartbeat
from round import RoundManager
import threading

class Node:
    def __init__(self, me, peers, port):
        self.me = me
        self.peers = peers
        self.all_ids = list(peers.keys())

        # Comunicação
        self.comm = Comm(me, peers, port)

        # Eleição
        self.election = RingElection(
            self.comm,
            self.all_ids,
            self._on_leader_elected
        )

        # Heartbeat (falhas e revives)
        self.hb = Heartbeat(
            self.comm,
            self.all_ids,
            self._on_node_failure,
            self._on_node_revive     # novo callback!
        )

        # Rounds
        self.round_mgr = RoundManager(
            self.comm,
            self.all_ids,
            lambda: self.election.leader
        )

        # Garante captura de UPDATE_RING antes de começar
        self.comm.on("UPDATE_RING", lambda msg: None)
        threading.Thread(target=self.comm._unicast_recv_loop, daemon=True).start()
        time.sleep(2)
        self.election.start()

    def _on_leader_elected(self, lid):
        print(f"[{self.me}] 👑 Novo líder: {lid}")
        if lid == self.me:
            self.round_mgr.start_loop()

    def _on_node_failure(self, pid):
        print(f"[{self.me}] ⚠️ Nó {pid} morreu")
        # atualiza estado na eleição e rounds
        self.election.mark_dead(pid)
        # se morreu o líder, reinicia eleição
        if pid == self.election.leader:
            self.election.leader = None
            self.election.start()

    def _on_node_revive(self, pid):
        print(f"[{self.me}] ✅ Nó {pid} voltou à vida")
        # reintegra no anel e informa todos
        self.election.alive.add(pid)
        self.election._broadcast_update()
