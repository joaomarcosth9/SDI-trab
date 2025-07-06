import socket
import threading
import json
import struct

MULTICAST_GRP = '224.1.1.1'
MULTICAST_PORT = 10000
TTL_DEFAULT = 1

class Comm:
    def __init__(self, my_id, peer_table, unicast_port):
        self.my_id = my_id
        self.peer_table = peer_table  # {pid: (host, port)}
        self.handlers = {}

        # Unicast socket (cada processo escuta numa porta única)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        self.sock.bind(('', unicast_port))
        threading.Thread(target=self._unicast_recv_loop, daemon=True).start()

        # Multicast socket (compartilhado por todos)
        self.msock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.msock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.msock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        self.msock.bind(('', MULTICAST_PORT))
        self.msock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL_DEFAULT)
        self.msock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

        mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GRP), socket.INADDR_ANY)
        self.msock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        threading.Thread(target=self._multicast_recv_loop, daemon=True).start()

    def on(self, msg_type, callback):
        self.handlers[msg_type] = callback

    def send(self, to_id, msg):
        msg['from'] = self.my_id
        data = json.dumps(msg).encode()
        host, port = self.peer_table[to_id]
        self.sock.sendto(data, (host, port))

    def multicast(self, msg):
        msg['from'] = self.my_id
        data = json.dumps(msg).encode()
        self.msock.sendto(data, (MULTICAST_GRP, MULTICAST_PORT))

    def handle_heartbeat(self, msg):
        sender = msg['from']
        self.last_seen[sender] = time.time()

        if not self.alive.get(sender, True):
            print(f"✅ Nó {sender} voltou a vida")
            self.alive[sender] = True

    def _unicast_recv_loop(self):
        while True:
            data, _ = self.sock.recvfrom(65536)
            msg = json.loads(data.decode())
            handler = self.handlers.get(msg.get("type"))
            if handler:
                handler(msg)

    def _multicast_recv_loop(self):
        while True:
            data, _ = self.msock.recvfrom(65536)
            msg = json.loads(data.decode())
            handler = self.handlers.get(msg.get("type"))
            if handler:
                handler(msg)
