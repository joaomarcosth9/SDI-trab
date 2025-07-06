# election.py
class RingElection:
    def __init__(self, comm, all_ids, on_leader_elected):
        self.comm = comm
        self.all_ids = all_ids
        self.alive = set(all_ids)
        self.next_id = self._compute_next()
        self.leader = None
        self.on_leader_elected = on_leader_elected

        comm.on("ELECTION", self._on_election)
        comm.on("LEADER", self._on_leader)
        comm.on("UPDATE_RING", self._on_update_ring)

    def _compute_next(self):
        idx = self.all_ids.index(self.comm.my_id)
        n = len(self.all_ids)
        for i in range(1, n):
            cand = self.all_ids[(idx + i) % n]
            if cand in self.alive:
                return cand

    def start(self):
        # refresh successor
        self.next_id = self._compute_next()
        msg = {"type": "ELECTION", "ids": [self.comm.my_id]}
        self.comm.send(self.next_id, msg)

    def _on_election(self, msg):
        eid = msg['ids']
        if self.comm.my_id in eid:
            leader = max(eid)
            self.leader = leader
            self.on_leader_elected(leader)
            self._broadcast_update()
            self.comm.send(self._compute_next(), {"type": "LEADER", "leader": leader})
        else:
            eid.append(self.comm.my_id)
            self.next_id = self._compute_next()
            self.comm.send(self.next_id, msg)

    def _on_leader(self, msg):
        self.leader = msg['leader']
        self.on_leader_elected(self.leader)
        if self.leader != self.comm.my_id:
            self.next_id = self._compute_next()
            self.comm.send(self.next_id, msg)

    def _on_update_ring(self, msg):
        self.alive = set(msg['alive'])
        self.next_id = self._compute_next()

    def mark_dead(self, pid):
        if pid in self.alive:
            self.alive.remove(pid)
            self._broadcast_update()
            self.next_id = self._compute_next()

    def _broadcast_update(self):
        self.comm.multicast({"type": "UPDATE_RING", "alive": list(self.alive)})
