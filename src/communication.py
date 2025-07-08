import socket, struct
import time
from .config import MULTICAST_GRP, MULTICAST_PORT

def create_socket() -> socket.socket:
    """
    Cria e configura um socket UDP para comunicação multicast.
    
    Configura o socket para:
    - Reutilizar endereço (SO_REUSEADDR)
    - Fazer bind na porta multicast
    - Juntar-se ao grupo multicast
    
    Returns:
        socket.socket: Socket UDP configurado para multicast
        
    Raises:
        socket.error: Se houver erro na criação ou configuração do socket
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", MULTICAST_PORT))
    mreq = struct.pack("=4sl", socket.inet_aton(MULTICAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return sock

def safe_create_socket() -> socket.socket:
    """
    Cria socket de forma segura com retry automático.
    Tenta até conseguir criar o socket.
    """
    while True:
        try:
            return create_socket()
        except Exception as e:
            time.sleep(2)

def send(sock: socket.socket, data: bytes) -> bool:
    """
    Envia dados via multicast para o grupo configurado.
    
    Args:
        sock (socket.socket): Socket UDP configurado para multicast
        data (bytes): Dados a serem enviados (mensagem serializada)
        
    Returns:
        bool: True se enviou com sucesso, False se houve erro
    """
    try:
        sock.sendto(data, (MULTICAST_GRP, MULTICAST_PORT))
        return True
    except Exception as e:
        return False

def receive(sock: socket.socket, buffer_size: int = 1024) -> tuple[bytes, tuple] | None:
    """
    Recebe dados do socket multicast.
    
    Args:
        sock (socket.socket): Socket UDP configurado para multicast
        buffer_size (int): Tamanho do buffer para recepção
        
    Returns:
        tuple[bytes, tuple] | None: (dados, endereço) se sucesso, None se erro
    """
    try:
        return sock.recvfrom(buffer_size)
    except Exception as e:
        return None

class NetworkManager:
    """
    Gerenciador de rede que reconecta automaticamente quando a conexão cai.
    """
    
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
            print("✓ Conectado à rede")
        except Exception as e:
            self.connected = False
            print(f"✗ Falha na conexão: {e}")
    
    def send(self, data: bytes) -> bool:
        """
        Envia dados com reconexão automática se necessário.
        
        Args:
            data (bytes): Dados a serem enviados
            
        Returns:
            bool: True se enviou com sucesso
        """
        if not self.connected:
            self._reconnect()
            
        if not self.connected:
            return False
            
        success = send(self.sock, data)
        
        if not success:
            print("Conexão perdida. Tentando reconectar...")
            self.connected = False
            self._reconnect()
            
            # Tenta enviar novamente após reconectar
            if self.connected:
                return send(self.sock, data)
        
        return success
    
    def receive(self, buffer_size: int = 1024) -> tuple[bytes, tuple] | None:
        """
        Recebe dados com reconexão automática se necessário.
        
        Args:
            buffer_size (int): Tamanho do buffer
            
        Returns:
            tuple[bytes, tuple] | None: (dados, endereço) se sucesso
        """
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

