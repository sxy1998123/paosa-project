import socket
import time
import json
HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 5001
mock_status = {"device_id": "1"}
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        json_data = json.dumpsjson_data = json.dumps(
            mock_status).encode('utf-8')  # 序列化为json
        length = len(json_data).to_bytes(4, 'big')  # 前4字节表示长度
        data = s.sendall(length + json_data)
        print(f"Sent {length + json_data} bytes")
        time.sleep(3)
