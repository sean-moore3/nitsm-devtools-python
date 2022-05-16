import ctypes
import socket
import time

HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'


class TestClass:

    def __init__(self):
        self.testVar = None


class Client:

    def __init__(self):
        self.client = None
        self.client_running = True

    def run(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(ADDR)
        while self.client_running:
            time.sleep(1)
            self.send("Test")

    def send(self, msg):
        message = msg.encode(FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        self.client.send(send_length)
        self.client.send(message)
        rec = self.client.recv(2048).decode(FORMAT)
        print(rec)
        test_class: TestClass = ctypes.cast(int(rec), ctypes.py_object).value
        print(test_class.testVar)

    def stop(self):
        self.client_running = False
        print("[STOPPING} client is stopping...")

