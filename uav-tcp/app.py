import socket
import threading
import time
import json
import struct


class DroneTCPHandler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        # 状态推送地面端服务端配置
        self.ground_status_host = '127.0.0.1'
        self.ground_status_port = 5000

        # 无人机端（本机TCP服务端配置）
        self.drone_host = '0.0.0.0'
        self.drone_port = 5001

        # 文件服务配置（暂时不用）
        self.file_host = '0.0.0.0'
        self.file_port = 5002

        # 远程监测装置文件socket（暂时不用）
        self.stm32_file_host = '192.168.1.100'
        self.stm32_file_port = 5001

        # 连接地面端的客户端socket
        self.ground_socket = None
        self.ground_connecting = False

        # 线程是否运行中
        self.running = False

        self.data_to_send = {
            "heart_beat": 1,
            "device_list": []
        }

    def handleSendToGroung(self):
        # 客户端线程用 发送数据
        # 此时应保证ground_socket可用
        json_data = json.dumps(self.data_to_send).encode('utf-8')
        # 发送消息头 数据长度
        length = len(json_data).to_bytes(4, 'big')  # 4字节表示长度
        self.ground_socket.sendall(length + json_data)
        # 发送数据
        print("已发送")
        self.data_to_send["heart_beat"] += 1
        time.sleep(5)

    def start_drone_client(self):
        while self.running:
            self.ground_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            try:
                print("尝试连接地面端服务器")
                self.ground_socket.connect(
                    (self.ground_status_host, self.ground_status_port))

                print("连接成功")
                self.ground_connecting = True
                # self.handleSendToGroung()
                while (self.ground_connecting):
                    self.handleSendToGroung()
                    time.sleep(1)

            except ConnectionError as e:
                print(f"Connection error: {e}")
                self.ground_socket = None
                self.ground_connecting = False
                time.sleep(3)  # 重连
            except Exception as e:
                print(f"Status client error: {e}")
                self.ground_connecting = False
                self.ground_socket = None
                time.sleep(3)

    def handle_sensor(self, device_conn):
        # 转发处理函数
        # todo 解析消息后在data_to_send["device_list"]中更新装置信息 如果没有则添加
        while True:
            time.sleep(10)
        #     data = device_conn.recv(1024)
        #     self.ground_socket.sendall(data)
        #     print(f"已转发数据到地面端: {data.decode()}")

    def start_drone_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.drone_host, self.drone_port))
        server.listen(5)

        print("无人机等待监测装置连接...")
        while self.running:
            device_conn, addr = server.accept()  # 阻塞式接收客户端数据
            print(f"监测装置已连接: {addr}")
            # 为每个监测装置创建独立线程
            threading.Thread(target=self.handle_sensor,
                             args=(device_conn,), daemon=True).start()

    def run(self):
        self.running = True
        # 启动服务端线程
        drone_server_thread = threading.Thread(
            target=self.start_drone_server, daemon=True)
        drone_server_thread.start()
        # 启动客户端线程
        drone_client_thread = threading.Thread(
            target=self.start_drone_client, daemon=True)
        drone_client_thread.start()

        while (drone_server_thread.is_alive() or drone_client_thread.is_alive()):
            time.sleep(5)

    def stop(self):
        self.running = False
        self.status_socket = None


if __name__ == '__main__':
    try:
        droneTCPHandle = DroneTCPHandler()
        droneTCPHandle.start()
        # 主线程等待子线程结束
        while droneTCPHandle.is_alive():
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n接收到Ctrl+C，正在停止服务...")
        droneTCPHandle.stop()
        print("服务已停止")
