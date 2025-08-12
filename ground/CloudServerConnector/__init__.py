import threading
import socket
import time
import json
from flask_socketio import SocketIO, send


class CloudServerConnector(threading.Thread):
    def __init__(self, socketio):
        super().__init__(daemon=True)
        self.cloudHost = '127.0.0.1'  # 云端服务器ip
        self.cloudPort = 5002  # 云端服务器端口
        self.cloudReconnectionTime = 5  # 云端服务器重连时间
        self.running = True  # 本线程alive时为True

        self.cloud_conn = None
        self.cloud_connecting = False

        self.socketio = socketio  # 主线程的socketio对象

    def run(self):
        while self.running:
            try:
                if not self.cloud_connecting:
                    self.cloud_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.cloud_conn.connect((self.cloudHost, self.cloudPort))
                    self.cloud_connecting = True
                    print("已与云端服务器建立连接")
                while True:
                    # 接收实时状态数据（格式：JSON字符串）
                    data_length_byte = self.cloud_conn.recv(4)
                    if not data_length_byte:
                        print("接收到无法识别的报文, 舍弃")
                        continue
                    # 开始接收完整数据
                    data_length = int.from_bytes(data_length_byte[:4], 'big')
                    received_data = self.cloud_conn.recv(data_length)
                    print(data_length_byte, data_length)
                    while (len(received_data) < data_length):
                        chunk = self.cloud_conn.recv(
                            data_length - len(received_data))
                        if not chunk:
                            break
                        received_data += chunk
                    my_dict = json.loads(received_data.decode('utf-8'))
                    print(f"已接收到云端服务器数据包：{my_dict}")
                    self.socketio.emit(my_dict['type'], my_dict)
            except ConnectionError as e:
                print(f"Connection error: {e}")
                self.cloud_connecting = False
                time.sleep(self.cloudReconnectionTime)

            except socket.timeout:
                print("tcp连接超时")
                self.cloud_connecting = False
                time.sleep(self.cloudReconnectionTime)

        self.running = False

    def pack_data(self, data):
        data_json = json.dumps(data).encode('utf-8')
        data_length = len(data_json).to_bytes(4, 'big')
        return data_length + data_json

    def restart(self):
        self.running = True

    def stop(self):
        self.running = False
