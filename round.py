import time
import os
import random
import threading

class RoundManager:
    def __init__(self, comm, all_ids, get_leader):
        self.comm = comm
        self.all_ids = all_ids
        self.get_leader = get_leader
        self.alive = set(all_ids)
        self.next_id = self._compute_next()
        self.current_round = 0

        comm.on("ROUND", self._on_round)
        comm.on("ROUND_RESULT", self._on_result)
        comm.on("UPDATE_RING", self._on_update_ring)

    def _compute_next(self):
        idx = self.all_ids.index(self.comm.my_id)
        n = len(self.all_ids)
        for i in range(1, n):
            cand = self.all_ids[(idx + i) % n]
            if cand in self.alive:
                return cand

    def _on_update_ring(self, msg):
        self.alive = set(msg['alive'])
        self.next_id = self._compute_next()

    def start_loop(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            leader = self.get_leader()
            if leader == self.comm.my_id:
                self.current_round += 1
                val = random.random() * os.getpid()
                print(f"[{self.comm.my_id}] 🔁 Round {self.current_round} iniciado")
                msg = {"type": "ROUND", "round": self.current_round, "values": {self.comm.my_id: val}}
                self.next_id = self._compute_next()
                self.comm.send(self.next_id, msg)
            time.sleep(5)

    def _on_round(self, msg):
        rnd = msg['round']
        if self.comm.my_id in msg['values']:
            max_val = max(msg['values'].items(), key=lambda x: x[1])
            print(f"[{self.comm.my_id}] ✅ Round {rnd} vencedor: {max_val}")
            self.comm.multicast({"type": "ROUND_RESULT", "round": rnd, "max": max_val})
        else:
            val = random.random() * os.getpid()
            msg['values'][self.comm.my_id] = val
            self.next_id = self._compute_next()
            self.comm.send(self.next_id, msg)

    def _on_result(self, msg):
        print(f"[{self.comm.my_id}] 🧠 Resultado do round {msg['round']}: {msg['max']}")

