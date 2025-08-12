import socket
import threading
import time
from datetime import datetime
import json

# 对于云服务器上的TCP服务端程序，我们需要实现以下功能：
# 1. 监听来自地面端的连接请求
# 2. 监听来自监测装置的连接请求，维护设备连接状态
# 3. 若有来自地面端的连接socket，则启动一个线程持续向地面端发送设备状态信息
# 4. 当有接收到监测装置的状态消息时 更新设备状态信息
# 5. 接收到地面端的下载命令 向监测装置发送下载文件消息 同时接收文件保存到本地后提供下载给地面端（待定）


class ServerTCPHandler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        # 连接地面端服务端配置
        self.ground_status_server_host = '0.0.0.0'
        self.ground_status_server_port = 5002
        self.ground_status_hz = 0.4  # 发送频率
        self.ground_connection_retry_times = 30  # 重连时间

        # 连接监测装置服务端配置
        self.device_server_host = '0.0.0.0'
        self.device_server_port = 5003
        self.device_tcp_max_connections = 15  # 最大连接数(目前最多支持15个设备)
        self.device_connetion_timeout = 30  # 连接超时时间
        # 文件服务配置（暂时不用）
        self.file_host = '0.0.0.0'
        self.file_port = 5004

        # 连接地面端服务端socket
        self.ground_socket = None
        self.ground_connecting = False

        # 连接监测装置的客户端socket
        self.registered_devices = []

        # 程序运行标志
        self.running = False

        self.status_to_send = {
            "type": "device-status",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "device_list": [],
            "from": "server"
        }

        self.message_to_send = {
            "type": "device-message",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "",
            "device_id": "",
            "from": "server"
        }

     # 注册设备

    def handleRegistDevice(self, device_conn, device_id):
        device = {
            "device_id": device_id,
            "device_conn": device_conn,
            "device_status": {},
            "device_online":  True
        }
        self.registered_devices.append(device)
        self.handleSendMsgToGround(f"监测装置{device_id}已新建连接", device_id)

    # 注销设备
    def handleUnregistDevice(self, device_id):
        updating_device = next(
            (device for device in self.registered_devices if device["device_id"] == device_id),
            None  # 默认值，可改为其他值如 {}
        )
        if updating_device:
            updating_device["device_online"] = False
        else:
            print(f"注销时发生异常: 未找到设备: {device_id}")

    # 更新设备状态
    def update_status_to_send(self):
        result = []
        for device in self.registered_devices:
            result.append(
                {
                    "device_id": device["device_id"],
                    "device_status": device["device_status"],
                    "device_online": device["device_online"]
                }
            )
        self.status_to_send["device_list"] = result

    # 发送消息到地面端
    def handleSendMsgToGround(self, message, device_id):
        if not self.ground_connecting:
            print("地面端未连接，无法发送消息")
            print("未发送的消息: " + message)
            return
        self.message_to_send["message"] = message
        self.message_to_send["device_id"] = device_id
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
        if not self.ground_socket:
            print("地面端未连接，无法发送状态")
            return -1
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
            print(f"因网络连接断开而退出命令接收线程: {e}")

    # 连接地面端的客户端线程处理函数
    def start_ground_server(self):
        while self.running:
            self.ground_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.ground_socket.bind((self.ground_status_server_host, self.ground_status_server_port))
                self.ground_socket.listen(self.device_tcp_max_connections)  # 最大连接数
                print("等待地面端连接...")
                device_conn, addr = self.ground_socket.accept()  # 阻塞式等待地面端连接
                print(f"地面端已连接: {addr}")
                self.ground_socket = device_conn
                self.ground_connecting = True
                # 启动接收命令线程
                receive_cmd_thread = threading.Thread(target=self.handleReceiveGroundCmd, daemon=True)
                receive_cmd_thread.start()

                while self.ground_connecting:
                    # 发送状态信息
                    self.handleSendStatusToGround()
                    time.sleep(1 / self.ground_status_hz)
            except ConnectionError as e:
                print(f"Connection error: {e}")
                self.ground_socket = None
                self.ground_connecting = False
            except Exception as e:
                print(f"与地面端连接异常: {e}")
                # self.ground_socket = None
                # self.ground_connecting = False

    # 接收监测装置数据线程处理函数
    def handle_device(self, device_conn):
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
                print(f"接收到监测装置前4字节数据: {received_data}")
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
                print(f"接收到监测装置json数据: {data} ")
                # print(f"线程ID: {threading.current_thread()}")
                # print(f"device_id:{device_id} updating_device:{updating_device}")
                if updating_device and updating_device["device_online"] == False:
                    # 断线设备重连
                    updating_device["device_online"] = True
                    updating_device["device_status"] = data
                    self.handleSendMsgToGround(f"监测装置{device_id}已重新连接", device_id)
                elif updating_device:
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
                self.handleSendMsgToGround(f"监测装置{device_id}连接断开", device_id)
                self.handleUnregistDevice(device_id)
                break
            except Exception as e:
                print(f"Device data error: {e}")
                break

    # 监测装置服务端线程处理函数
    def start_device_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.device_server_host, self.device_server_port))
        server.listen(self.device_tcp_max_connections)  # 最大连接数

        print("等待监测装置连接...")
        while self.running:
            device_conn, addr = server.accept()  # 阻塞式接收监测装置数据
            print(f"监测装置已连接: {addr}")
            # 启动接收数据线程
            threading.Thread(target=self.handle_device, args=(device_conn,), daemon=True).start()  # 为每个监测装置创建独立线程

    # 子线程启动函数(实例化时自动调用)
    def run(self):
        self.running = True
        # 启动监测装置服务端线程
        device_server_thread = threading.Thread(target=self.start_device_server, daemon=True)
        device_server_thread.start()
        # 启动地面端服务端线程
        ground_server_thread = threading.Thread(target=self.start_ground_server, daemon=True)
        ground_server_thread.start()

        while (device_server_thread.is_alive() or ground_server_thread.is_alive()):
            time.sleep(5)

    def stop(self):
        self.running = False


if __name__ == '__main__':
    try:
        serverTCPHandler = ServerTCPHandler()
        serverTCPHandler.start()
        # 主线程等待子线程结束
        while serverTCPHandler.is_alive():
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n接收到Ctrl+C，正在停止服务...")
        serverTCPHandler.stop()
        print("服务已停止")
