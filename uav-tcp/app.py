import socket
import threading
import time
from datetime import datetime
import json


class DroneTCPHandler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        # 状态推送地面端服务端配置
        self.ground_status_host = '127.0.0.1'
        self.ground_status_port = 5000
        self.ground_status_hz = 1  # 发送频率
        self.ground_connection_retry_times = 30  # 重连时间

        # 无人机端（本机TCP服务端配置）
        self.drone_host = '0.0.0.0'
        self.drone_port = 5001
        self.drone_tcp_max_connections = 15  # 最大连接数

        # 文件服务配置（暂时不用）
        self.file_host = '0.0.0.0'
        self.file_port = 5002

        # 监测装置连接配置
        self.device_connetion_timeout = 30  # 设备连接超时时间

        # 连接地面端的客户端socket
        self.ground_socket = None
        self.ground_connecting = False

        # 无人机主线程是否运行中
        self.running = False

        self.status_to_send = {
            "type": "device-status",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "device_list": []
        }

        self.message_to_send = {
            "type": "device-message",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "",
            "device_id": "",
            "code": "0"  # 0: 已连接 1: 已断开
        }

        self.registered_devices = []

     # 注册设备
    def handleRegistDevice(self, device_conn, device_id):
        device = {
            "device_id": device_id,
            "device_conn": device_conn,
            "device_status": {}
        }
        self.registered_devices.append(device)
        if (self.ground_connecting):
            self.handleSendMsgToGround(f"监测装置{device_id}已连接", device_id, 0)

    # 注销设备
    def handleUnregistDevice(self, device_id):
        updating_device = next(
            (device for device in self.registered_devices if device["device_id"] == device_id),
            None  # 默认值，可改为其他值如 {}
        )
        if updating_device:
            self.registered_devices.remove(updating_device)
        else:
            print(f"注销时发生异常: 设备未注册: {device_id}")

    # 更新设备状态
    def update_status_to_send(self):
        result = []
        for device in self.registered_devices:
            result.append(
                {
                    "device_id": device["device_id"],
                    "device_status": device["device_status"]
                }
            )
        self.status_to_send["device_list"] = result

    # 发送消息到地面端
    def handleSendMsgToGround(self, message, device_id, code):
        self.message_to_send["message"] = message
        self.message_to_send["device_id"] = device_id
        self.message_to_send["code"] = code
        json_data = json.dumps(self.message_to_send).encode('utf-8')
        length = len(json_data).to_bytes(4, 'big')  # 前4字节表示长度
        self.ground_socket.sendall(length + json_data)  # 发送数据
        self.message_to_send["time"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")  # 更新时间戳
        # print("已发送消息")

    # 发送状态到地面端
    def handleSendStatusToGround(self):
        json_data = json.dumps(self.status_to_send).encode('utf-8')
        length = len(json_data).to_bytes(4, 'big')  # 前4字节表示长度
        # 此时应保证ground_socket可用
        self.ground_socket.sendall(length + json_data)  # 发送数据
        self.update_status_to_send()  # 更新数据
        self.status_to_send["time"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")  # 更新时间戳
        # print("已发送状态")

    # 接收地面端命令线程处理函数（未完成）
    def handleReceiveGroundCmd(self):
        try:
            while self.ground_connecting:
                cmd_length_byte = self.ground_socket.recv(4)
                if not cmd_length_byte:
                    print("接收到地面端无法解析的命令,舍弃")
                    continue
                cmd_length = int.from_bytes(cmd_length_byte, 'big')
                received_data = self.ground_socket.recv(cmd_length)
                while (len(received_data) < cmd_length):
                    chunk = self.ground_socket.recv(cmd_length - len(received_data))
                    if not chunk:
                        break
                    received_data += chunk

                cmd = json.loads(received_data.decode('utf-8'))
                print(f"接收到地面端命令: {cmd}")
                print(f"cmd:{cmd['cmd']} id:{cmd['device_id']}")
        except ConnectionError as e:
            print(f"退出命令接收线程: {e}")

    # 连接地面端的客户端线程处理函数
    def start_drone_client(self):
        while self.running:
            self.ground_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                print("尝试连接地面端服务器")
                self.ground_socket.connect((self.ground_status_host, self.ground_status_port))
                print("连接成功")
                self.ground_connecting = True
                # 启动接收地面端命令线程
                threading.Thread(target=self.handleReceiveGroundCmd, daemon=True).start()
                while (self.ground_connecting):
                    self.handleSendStatusToGround()
                    time.sleep((1 / self.ground_status_hz))  # 发送间隔

            except ConnectionError as e:
                print(f"Connection error: {e}")
                self.ground_socket = None
                self.ground_connecting = False
                time.sleep(self.ground_connection_retry_times)  # 重连
            except Exception as e:
                print(f"Status client error: {e}")
                self.ground_socket = None
                self.ground_connecting = False
                time.sleep(self.ground_connection_retry_times)

    # 接收监测装置数据线程处理函数
    def handle_sensor(self, device_conn):
        # todo 解析消息后在status_to_send["device_list"]中更新装置信息 如果没有则添加
        device_last_active = time.time()
        device_conn.settimeout(self.device_connetion_timeout)  # 设置超时时间
        while self.running:
            try:
                # 接收数据
                data_length_byte = device_conn.recv(4)
                if not data_length_byte:
                    print("从监测装置接收到空数据,判断为断开连接")
                    raise ConnectionError("Connection closed by device")
                    break
                data_length = int.from_bytes(data_length_byte, 'big')
                received_data = device_conn.recv(data_length)
                while (len(received_data) < data_length):
                    chunk = device_conn.recv(data_length - len(received_data))
                    if not chunk:
                        break
                    received_data += chunk
                # 解析数据
                data = json.loads(received_data.decode('utf-8'))

                device_last_active = time.time()
                # 更新或注册设备信息
                device_id = data["device_id"]  # 待更新的设备ID
                updating_device = next(
                    (device for device in self.registered_devices if device["device_id"] == device_id),
                    None  # 默认值，可改为其他值如 {}
                )
                print(f"接收到监测装置数据: {data}  线程ID: {threading.current_thread()}")
                print(f"device_id:{device_id} updating_device:{updating_device}")
                if updating_device:
                    # 更新设备信息
                    updating_device["device_status"] = data
                else:
                    # 注册设备信息
                    self.handleRegistDevice(device_conn, device_id)
            except socket.timeout:
                if time.time() - device_last_active > self.device_connetion_timeout and device_id:
                    self.handleUnregistDevice(device_id)
                    print(f"TCP连接超时: {device_id}, 注销设备")
                break
            except ConnectionError as e:
                print(f"TCP连接断开: {device_id}, 注销设备")
                self.handleSendMsgToGround(f"监测装置{device_id}连接断开", device_id, 1)
                self.handleUnregistDevice(device_id)
                break
            except Exception as e:
                print(f"Sensor data error: {e}")
                break

    # 服务端线程处理函数
    def start_drone_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.drone_host, self.drone_port))
        server.listen(self.drone_tcp_max_connections)  # 最大连接数

        print("无人机等待监测装置连接...")
        while self.running:
            device_conn, addr = server.accept()  # 阻塞式接收监测装置数据
            print(f"监测装置已连接: {addr}")
            threading.Thread(target=self.handle_sensor, args=(device_conn,), daemon=True).start()  # 为每个监测装置创建独立线程

    # 子线程启动函数(实例化时自动调用)
    def run(self):
        self.running = True
        # 启动服务端线程
        drone_server_thread = threading.Thread(target=self.start_drone_server, daemon=True)
        drone_server_thread.start()
        # 启动客户端线程
        drone_client_thread = threading.Thread(target=self.start_drone_client, daemon=True)
        drone_client_thread.start()

        while (drone_server_thread.is_alive() or drone_client_thread.is_alive()):
            time.sleep(5)

    def stop(self):
        self.running = False


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
