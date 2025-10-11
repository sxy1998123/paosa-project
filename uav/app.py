from flask import Flask, send_from_directory, jsonify, request
import requests
from datetime import datetime

app = Flask(__name__, static_folder="frontend")
app.config['DOWNLOAD_FOLDER'] = 'download_cache'  # 文件下载路径

# device_list = [{"device_id": "1", "device_online": True, "altitude": 0, "battery": 0, "counter": 0}]
device_list = []

ground_station_ip = "http://localhost:8000"


@app.route('/')
def index():
    return "hello world"


@app.route('/update_device_info', methods=['POST'])
def update_device_info():
    global device_list
    # 检查请求是否为 JSON 格式
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.json
    print(data)
    required_keys = ['device_id']

    # 检查必需字段
    for key in required_keys:
        if key not in data:
            return jsonify({"error": f"Missing key: {key}"}), 400

    matched_device = next((device for device in device_list if device['device_id'] == data['device_id']), None)
    print(matched_device)
    
    now = datetime.now()
    device_update_time = now.strftime("%Y-%m-%d %H:%M:%S %Z")  # 输出时间但不含时区名称
    if matched_device is None:
        print("新增设备")
        data['device_update_time'] = device_update_time
        device_list.append(data)
    else:
        data['device_update_time'] = device_update_time
        matched_device = data

    requests.post(f"{ground_station_ip}/update_device_info", json=device_list)

    response = {
        "status": 200,
        "message": "更新设备信息成功",
    }
    return jsonify(response)


@app.route('/cmd_uav', methods=['POST'])
def cmd_uav():
    # 检查请求是否为 JSON 格式
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.json
    print(data)
    required_keys = ['cmd']

    # 检查必需字段
    for key in required_keys:
        if key not in data:
            return jsonify({"error": f"Missing key: {key}"}), 400


if __name__ == '__main__':
    # 主线程启动Flask
    app.run(host='0.0.0.0', port=8001, debug=True)
