# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import ctypes
import sys
import threading
import time

from server import Server
from client import Client


class ServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.server = Server()

    def run(self):
        self.server.run()

    def stop(self):
        self.server.stop()


class ClientThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.client = Client()

    def run(self):
        self.client.run()

    def stop(self):
        self.client.stop()


serverThread = ServerThread()
clientThread = ClientThread()


def run_server_client():
    serverThread.start()
    clientThread.start()


def stop_server_client():
    clientThread.stop()
    serverThread.stop()


run_server_client()
time.sleep(1)
stop_server_client()
