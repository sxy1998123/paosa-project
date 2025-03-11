import threading
import socket
import time
# 共享状态变量 主线程只读不写
status = {
    "sensor_temp": 25.0,
    "last_update": time.time(),
    "connection_status": False
}

# TCP通信线程相关


class DroneConnector(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.host = '127.0.0.1'  
        self.port = 5000  # 无人机端tcp服务端所用ip及端口
        self.running = True  # 为True且有本类实例时则会保持TCP连接

    def run(self):
        while self.running:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.host, self.port))
                    status['connection_status'] = True
                    while True:
                        # 接收实时状态数据（格式：JSON字符串）
                        data = s.recv(1024).decode()
                        print(f"{data}")
                        if data.startswith('STATUS:'):
                            status.update(eval(data[7:]))
                            status['last_update'] = time.time()

            except Exception as e:
                status['connection_status'] = False
                print(f"Connection error: {e}")
                time.sleep(5)

    def restart(self):
        self.running = True

    def stop(self):
        self.running = False


