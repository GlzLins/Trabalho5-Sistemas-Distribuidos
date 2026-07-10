import socket
import threading
import time
import sys
import json

BASE_PORT = 5000
TIMEOUT = 3.0

class Node:
    def __init__(self, node_id, total_nodes):
        self.id = node_id
        self.total_nodes = total_nodes
        self.port = BASE_PORT + node_id
        self.coordinator_id = -1
        self.is_election_in_progress = False
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('localhost', self.port))
        self.sock.settimeout(1.0)
        
        print(f"[Nó {self.id}] Inicializado na porta {self.port}")

    def send_message(self, target_id, msg_type):
        target_port = BASE_PORT + target_id
        msg = json.dumps({'type': msg_type, 'sender': self.id}).encode('utf-8')
        try:
            self.sock.sendto(msg, ('localhost', target_port))
        except Exception:
            # Ignora erros de envio caso a porta de destino já esteja completamente fechada
            pass

    def start_election(self):
        self.is_election_in_progress = True
        self.coordinator_id = -1
        higher_nodes = [i for i in range(self.id + 1, self.total_nodes)]
        
        if not higher_nodes:
            print(f"[Nó {self.id}] Nenhum nó com ID maior. Assumindo a coordenação!")
            self.become_coordinator()
            return

        print(f"[Nó {self.id}] Iniciando eleição. Enviando ELECTION para nós {higher_nodes}")
        for target in higher_nodes:
            self.send_message(target, 'ELECTION')
            
        # Aguarda respostas OK
        time.sleep(TIMEOUT)
        if self.is_election_in_progress:
            print(f"[Nó {self.id}] Timeout sem resposta de nós maiores. Vencendo a eleição.")
            self.become_coordinator()

    def become_coordinator(self):
        self.coordinator_id = self.id
        self.is_election_in_progress = False
        print(f"\n>>> [Nó {self.id}] É O NOVO COORDENADOR! <<<\n")
        
        lower_nodes = [i for i in range(0, self.id)]
        for target in lower_nodes:
            self.send_message(target, 'COORDINATOR')

    def listen(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
                msg = json.loads(data.decode('utf-8'))
                sender = msg['sender']
                msg_type = msg['type']
                
                if msg_type == 'ELECTION':
                    print(f"[Nó {self.id}] Recebeu ELECTION de Nó {sender}. Enviando OK.")
                    self.send_message(sender, 'OK')
                    if not self.is_election_in_progress:
                        threading.Thread(target=self.start_election).start()
                        
                elif msg_type == 'OK':
                    print(f"[Nó {self.id}] Recebeu OK de Nó {sender}. Interrompendo própria eleição e aguardando COORDINATOR.")
                    self.is_election_in_progress = False
                    
                elif msg_type == 'COORDINATOR':
                    self.coordinator_id = sender
                    self.is_election_in_progress = False
                    print(f"[Nó {self.id}] Aceitou Nó {sender} como novo coordenador.")
                    
            except socket.timeout:
                continue
            except ConnectionResetError:
                # Trata o WinError 10054: ignora o erro de conexão resetada pelo Windows ao procurar portas fechadas
                continue
            except KeyboardInterrupt:
                print(f"[Nó {self.id}] Encerrando processo.")
                sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Uso: python bully_election.py <ID_DO_NO> <TOTAL_DE_NOS>")
        sys.exit(1)
        
    node_id = int(sys.argv[1])
    total = int(sys.argv[2])
    
    node = Node(node_id, total)
    listener_thread = threading.Thread(target=node.listen, daemon=True)
    listener_thread.start()
    
    # Se for o nó inicial (ou após um enter no terminal), inicia a checagem
    try:
        input("Pressione ENTER para forçar o início de uma eleição neste nó...\n")
        node.start_election()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)