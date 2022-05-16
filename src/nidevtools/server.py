import socket
import threading
from typing import List, Any

HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(ADDR)
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"


class TestClass:

    def __init__(self):
        self.testVar = 5


testObj = TestClass()


class ClientHandlerThread(threading.Thread):
    def __init__(self, conn, addr):
        threading.Thread.__init__(self)
        self.connected = False
        self.conn = conn
        self.addr = addr

    def run(self):
        self.handle_client(self.conn, self.addr)

    def stop(self):
        self.connected = False

    def handle_client(self, conn, addr):
        print(f"[NEW CONNECTION] {addr} connected")
        self.connected = True
        while self.connected:
            msg_length = conn.recv(HEADER).decode(FORMAT)
            if msg_length:
                msg_length = int(msg_length)
                msg = conn.recv(msg_length).decode(FORMAT)
                if msg == DISCONNECT_MESSAGE:
                    self.connected = False
                print(f"[{addr}] {msg}")
                conn.send(str(id(testObj)).encode(FORMAT))

        conn.close()





class Server:

    def __init__(self):
        self.server_running = False
        self.all_clients: List[Any] = []

    def run(self):
        print("[STARTING} server is starting...")
        server.listen()
        print(f"[listening] Server is listening on {SERVER}")
        self.server_running = True
        while self.server_running:
            try:
                conn, addr = server.accept()
                thread = ClientHandlerThread(conn, addr)
                thread.start()
                self.all_clients.append(thread)
                print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 2}")
            except:
                pass

    def stop(self):
        for client in self.all_clients:
            client.stop()

        self.server_running = False
        server.close()
        print("[STOPPING} server is stopping...")
