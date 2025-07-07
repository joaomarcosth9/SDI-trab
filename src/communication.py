import socket, struct
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

def send(sock: socket.socket, data: bytes) -> None:
    """
    Envia dados via multicast para o grupo configurado.
    
    Args:
        sock (socket.socket): Socket UDP configurado para multicast
        data (bytes): Dados a serem enviados (mensagem serializada)
        
    Raises:
        socket.error: Se houver erro no envio da mensagem
    """
    sock.sendto(data, (MULTICAST_GRP, MULTICAST_PORT))

