from node import Node

if __name__ == "__main__":
    import sys
    import time

    peers = {
        1: ('127.0.0.1', 10001),
        2: ('127.0.0.1', 10002),
        3: ('127.0.0.1', 10003),
    }
    pid = int(sys.argv[1])
    port = int(sys.argv[2])
    Node(pid, peers, port)
    while True:
        time.sleep(1)
