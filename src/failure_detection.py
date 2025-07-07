from time import monotonic, sleep
from threading import Thread
from .communication import send
from .message import pack
from .config import HEARTBEAT_INT, FAIL_TIMEOUT

def start_heartbeat(node):

    def pulse():
        while True:
            send(node.sock, pack("HB", pid=node.pid))
            sleep(HEARTBEAT_INT)

    Thread(target=pulse, daemon=True).start()

def start_monitor(node):

    def monitor():
        while True:
            now = monotonic()
            dead = [pid for pid, ts in node.alive.items()
                    if now - ts > FAIL_TIMEOUT]
            for pid in dead:
                node.alive.pop(pid, None)
                node.log(f"Processo {pid} considerado MORTO")
                if pid == node.leader:
                    node.log("Líder caiu ➜ iniciando eleição")
                    node.start_election()
            sleep(1)

    Thread(target=monitor, daemon=True).start()

