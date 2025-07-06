# heartbeat.py
import time
import threading

class Heartbeat:
    def __init__(self, comm, all_ids, on_failure, on_revive):
        self.comm = comm
        self.alive = set(all_ids)
        self.on_failure = on_failure
        self.on_revive = on_revive
        # timestamps dos heartbeats
        self.last_hb = {pid: time.time() for pid in all_ids if pid != comm.my_id}

        comm.on("HEARTBEAT", self._on_hb)
        comm.on("UPDATE_RING", self._on_update_ring)

        threading.Thread(target=self._send_loop, daemon=True).start()
        threading.Thread(target=self._check_loop, daemon=True).start()

    def _on_hb(self, msg):
        sender = msg['from']
        now = time.time()
        prev = sender in self.alive

        # atualiza última vez visto
        self.last_hb[sender] = now

        # se estava morto, revive
        if not prev:
            self.alive.add(sender)
            self.on_revive(sender)

    def _on_update_ring(self, msg):
        # mantém alive consistente quando UPDATE_RING chegar
        self.alive = set(msg['alive'])

    def _send_loop(self):
        while True:
            for pid in list(self.alive):
                if pid != self.comm.my_id:
                    self.comm.send(pid, {"type": "HEARTBEAT"})
            time.sleep(1)

    def _check_loop(self):
        while True:
            now = time.time()
            for pid, ts in list(self.last_hb.items()):
                if pid in self.alive and now - ts > 5:
                    self.alive.remove(pid)
                    self.on_failure(pid)
            time.sleep(1)
