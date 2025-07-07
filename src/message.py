import json
from typing import Any

def pack(op: str, **kwargs: Any) -> bytes:
    """
    Empacota uma mensagem em formato JSON para envio via rede.
    
    Cria um payload JSON com o campo 'op' (operação) e campos adicionais
    conforme especificado nos argumentos nomeados.
    
    Args:
        op (str): Tipo da operação/mensagem (ex: 'HELLO', 'ELECTION', 'HB')
        **kwargs: Campos adicionais da mensagem (ex: pid, round, value)
        
    Returns:
        bytes: Mensagem serializada em JSON e codificada em UTF-8
        
    Example:
        >>> pack("HELLO", pid=1, round=0)
        b'{"op": "HELLO", "pid": 1, "round": 0}'
    """
    payload = {"op": op, **kwargs}
    return json.dumps(payload).encode()

def unpack(data: bytes) -> dict[str, Any]:
    """
    Desempacota uma mensagem recebida da rede.
    
    Decodifica bytes UTF-8 e deserializa JSON para dicionário Python.
    
    Args:
        data (bytes): Dados recebidos da rede (JSON codificado em UTF-8)
        
    Returns:
        dict[str, Any]: Dicionário com os campos da mensagem
        
    Raises:
        json.JSONDecodeError: Se os dados não forem JSON válido
        UnicodeDecodeError: Se os dados não forem UTF-8 válido
        
    Example:
        >>> unpack(b'{"op": "HELLO", "pid": 1}')
        {'op': 'HELLO', 'pid': 1}
    """
    return json.loads(data.decode())

