from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, send, emit
import requests
from datetime import datetime

app = Flask(__name__, static_folder="frontend")
app.config['DOWNLOAD_FOLDER'] = 'download_cache'  # 文件下载路径

# device_list = [{"device_id": "1", "device_online": True, "altitude": 0, "battery": 0, "counter": 0}]
device_list = []

ground_station_ip = "http://localhost:8000"
socketio = SocketIO(app, cors_allowed_origins="*")
connected_clients = set()


@app.route('/')
def index():
    return "uav模块 服务器端程序运行中"


# 设备端调用此接口上报信息
@app.route('/update_device_info', methods=['POST'])
def update_device_info():
    # 检查请求是否为 JSON 格式
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.json
    required_keys = ['device_id']

    # 检查必需字段
    for key in required_keys:
        if key not in data:
            return jsonify({"error": f"Missing key: {key}"}), 400

    socketio.emit('device_message', data)

    response = {
        "status": 200,
        "message": "更新设备信息成功",
    }
    return jsonify(response)

# 地面端调用此接口控制无人机
# @app.route('/cmd_uav', methods=['POST'])
# def cmd_uav():
#     # 检查请求是否为 JSON 格式
#     if not request.is_json:
#         return jsonify({"error": "Request must be JSON"}), 400

#     data = request.json
#     required_keys = ['cmd']

#     # 检查必需字段
#     for key in required_keys:
#         if key not in data:
#             return jsonify({"error": f"Missing key: {key}"}), 400


@socketio.on('connect')
def handle_connect():
    connected_clients.add(request.sid)
    client_ip = request.remote_addr
    print(f"✅ 地面站已连接，IP地址: {client_ip}")
    emit('server_message', {'msg': '你好，地面站！已连接到WiFi模块'})


@socketio.on('disconnect')
def handle_disconnect():
    print("❌ 地面站已断开")
    connected_clients.discard(request.sid)


@socketio.on('device_command')
def handle_device_command(data):
    print(f"📩 收到地面站指令: {data}")
    # 可以在此执行具体动作，例如转发到串口或控制设备
    emit('command_ack', {'msg': '指令已收到'}, broadcast=False)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8001, debug=False)
