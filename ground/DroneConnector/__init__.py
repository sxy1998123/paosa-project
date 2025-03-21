import threading
import socket
import time
import json
# 共享状态变量 主线程只读不写
status = {

}

# TCP通信线程相关


class DroneConnector(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.host = '127.0.0.1'
        self.port = 5000  # 本机tcp服务端所用ip及端口
        self.running = True  # 本线程alive时为True

        self.server_socket = None
        self.drone_conn = None
        self.drone_connecting = False

    def run(self):
        self.server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print("地面端TCP服务器已启动,等待无人机连接...")
        while self.running:
            try:
                # 等待无人机连接
                self.drone_conn, addr = self.server_socket.accept()
                print("无人机已连接")
                self.drone_connecting = True
                while True:
                    # 接收实时状态数据（格式：JSON字符串）
                    data_length_byte = self.drone_conn.recv(4)
                    if not data_length_byte:
                        print("接收到无法识别的报文, 舍弃")
                        continue
                    # 开始接收完整数据
                    data_length = int.from_bytes(data_length_byte[:4], 'big')
                    received_data = self.drone_conn.recv(data_length)
                    # print(data_length_byte, data_length)
                    while (len(received_data) < data_length):
                        chunk = self.drone_conn.recv(
                            data_length - len(received_data))
                        if not chunk:
                            break
                        received_data += chunk
                    my_dict = json.loads(received_data.decode('utf-8'))
                    print(f"已接收到{addr}无人机端开发板设备tcp端数据包：{my_dict}")

            except ConnectionError as e:
                print(f"Connection error: {e}")
                self.drone_connecting = False

            except socket.timeout:
                self.drone_connecting = False
                print("tcp连接超时")

        self.running = False

    def pack_data(self, data):
        data_json = json.dumps(data).encode('utf-8')
        data_length = len(data_json).to_bytes(4, 'big')
        return data_length + data_json

    def restart(self):
        self.running = True

    def stop(self):
        self.running = False
