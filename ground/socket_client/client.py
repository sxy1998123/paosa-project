# client.py
import socketio
import threading
import time


class WifiSocketClient:
    def __init__(self, server_ip="127.0.0.1", port=8001, on_device_message=None):
        self.server_url = f"ws://{server_ip}:{port}"
        self.sio = socketio.Client()
        self._setup_events()
        self.on_device_message = on_device_message

    def _setup_events(self):
        @self.sio.event
        def connect():
            print(f"✅ 已连接到 无人机端主机: {self.server_url}")

        @self.sio.event
        def disconnect():
            print("❌ 与 无人机端主机断开连接")
            threading.Thread(target=self._auto_reconnect, daemon=True).start()

        @self.sio.on('server_message')
        def on_server_message(data):
            print(f"📡 收到 无人机端主机消息: {data}")

        @self.sio.on('command_ack')
        def on_command_ack(data):
            print(f"✅ 收到 无人机端主机确认: {data}")

        @self.sio.on('device_message')
        def on_device_message(data):
            print(f"📡 收到 无人机端主机转发的设备消息: {data} type: {type(data)}")
            if self.on_device_message:
                self.on_device_message(data)

    def connect(self):
        def _connect():
            while True:
                try:
                    if not self.sio.connected:  # ✅ 防止重复连接
                        self.sio.connect(self.server_url)
                        self.sio.wait()
                except Exception as e:
                    print(f"⚠️ 连接 无人机端主机失败: {e}")
                    time.sleep(5)
        threading.Thread(target=_connect, daemon=True).start()

    def send_command(self, command: dict):
        try:
            self.sio.emit('device_command', command)
            print(f"🚀 向WiFi模块发送: {command}")
        except Exception as e:
            print(f"⚠️ 发送失败: {e}")

    def _auto_reconnect(self):
        time.sleep(3)
        if not self.sio.connected:
            print("🔄 尝试重新连接 无人机端主机...")
            self.connect()


if __name__ == '__main__':
    wifi_socket_client = WifiSocketClient()
    wifi_socket_client.connect()
    wifi_socket_client.sio.wait()
