import socket, struct
import time
from .config import MULTICAST_GRP, MULTICAST_PORT, NETWORK_RETRY_DELAY

def create_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", MULTICAST_PORT))
    mreq = struct.pack("=4sl", socket.inet_aton(MULTICAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return sock

def safe_create_socket() -> socket.socket:
    while True:
        try:
            return create_socket()
        except Exception as e:
            time.sleep(NETWORK_RETRY_DELAY)

def send(sock: socket.socket, data: bytes) -> bool:
    try:
        sock.sendto(data, (MULTICAST_GRP, MULTICAST_PORT))
        return True
    except Exception as e:
        return False

def receive(sock: socket.socket, buffer_size: int = 1024) -> tuple[bytes, tuple] | None:
    try:
        return sock.recvfrom(buffer_size)
    except Exception as e:
        return None

    def __init__(self):
        self.sock = None
        self.connected = False
        self._reconnect()
    
    def _reconnect(self):
        """Tenta reconectar e atualiza o status."""
        try:
            if self.sock:
                self.sock.close()
            self.sock = safe_create_socket()
            self.connected = True
            print("[REDE] Conectado à rede")
        except Exception as e:
            self.connected = False
            print(f"[REDE] Falha na conexão: {e}")
    
    def send(self, data: bytes) -> bool:
        if not self.connected:
            self._reconnect()
            
        if not self.connected:
            return False
            
        success = send(self.sock, data)
        
        if not success:
            print("Conexão perdida. Tentando reconectar...")
            self.connected = False
            self._reconnect()
            
            if self.connected:
                return send(self.sock, data)
        
        return success
    
    def receive(self, buffer_size: int = 1024) -> tuple[bytes, tuple] | None:
        if not self.connected:
            self._reconnect()
            
        if not self.connected:
            return None
            
        result = receive(self.sock, buffer_size)
        
        if result is None:
            print("Conexão perdida. Tentando reconectar...")
            self.connected = False
            self._reconnect()
        
        return result
    
    def close(self):
        """Fecha o socket."""
        if self.sock:
            self.sock.close()
            self.sock = None
        self.connected = False

