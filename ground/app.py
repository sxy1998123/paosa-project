from flask import Flask, send_from_directory, send_file, jsonify, request
from flask_socketio import SocketIO, send, emit
from mqtt.mqtt import MQTTClient
# from socket_client.client import WifiSocketClient
import logging
from datetime import datetime
import json
import threading
import os
# logger
logging.basicConfig(
    level=logging.INFO,  # 修改日志级别输出所有日志
    format='%(asctime)s %(name)s [%(pathname)s:%(lineno)d] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # 日期时间格式
)

logger = logging.getLogger(__name__)

# flask
app = Flask(__name__, static_folder="frontend_dist")
app.config['DOWNLOAD_FOLDER'] = 'download_cache'  # 文件下载路径
app.config['HISTORY_DATA_FOLDER'] = './HistoryData'  # 上传文件大小限制
# socketio server
socketio = SocketIO(app, cors_allowed_origins="*")

# 无人机地址
uavip = "127.0.0.1"
uavport = 8001


# 心跳包消息
heart_beat_messages = ['www.usr.cn']

# 设备列表
device_list = []
device_list_lock = threading.Lock()  # 设备列表更新锁

# 设备高度图表数据
device_alt_chartdata_map_all = {}
device_alt_chartdata_map_mqtt = {}
device_alt_chartdata_map_http = {}
device_alt_chartdata_map_lock = threading.Lock()  # 设备高度图表数据更新锁


# mqtt 消息格式
# {
#     "timestamp": "07:45:29",
#     "device_id": "gnss001",
#     "coordinates": {
#         "lon": 118.07828833333333,
#         "lat": 24.494528333333335,
#         "alt": 48.1
#     }
# }
# 设备高度图表数据格式
# device_alt_chartdata_map_all = {
#     # x轴时间 y轴高度
#     "gnss001": {
#         "xData": [1756278925148, 1756278926148, 1756278927148, 1756278925148],
#         "yData": [100, 102, 103, 104]
#     },

# device_alt_chartdata_map_mqtt = {
#     "gnss001": {
#         "xData": [1756278935148, 1756278936148, 1756278427148, 1756275925148],
#         "yData": [100, 102, 103, 104]
#     },
# }
# device_alt_chartdata_map_http = {
#     "gnss001": {
#         "xData": [1756278935148, 1756278936148, 1756278427148, 1756275925148],
#         "yData": [100, 102, 103, 104]
#     }
# }


def saveGNSS(gnss_data):
    try:
        if not gnss_data:
            return
        time = datetime.now().strftime("%Y-%m-%d")
        filename = "GNSS_" + time + ".txt"
        filepath = os.path.join(app.config['HISTORY_DATA_FOLDER'], filename)
        # logger.info("gnss_data: %s", gnss_data)
        if not os.path.exists(app.config['HISTORY_DATA_FOLDER']):
            os.makedirs(app.config['HISTORY_DATA_FOLDER'])

        # 构造数据文本
        timestamp = gnss_data.get("timestamp")
        device_id = gnss_data.get("device_id")
        coordinates = gnss_data.get("coordinates")
        lon = coordinates.get("lon")
        lat = coordinates.get("lat")
        alt = coordinates.get("alt")
        gnss_data_text = f"设备ID：{device_id} 装置消息发送时间：{timestamp} 经度：{lon} 纬度：{lat} 高度：{alt} \n"
        logger.info("GNSS数据：%s", gnss_data_text)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(gnss_data_text)
        return True
    except Exception as e:
        logger.error("GNSS数据保存失败 %s", e)
        return False


def handleDeviceMsgMqtt(deviceMsgStr):
    # 处理设备上报信息逻辑
    try:
        if not deviceMsgStr:
            raise Exception("消息为空")
        if deviceMsgStr.isdecimal():
            raise Exception("消息内容为纯数字")
        deviceMsg = json.loads(deviceMsgStr)
        device_id = deviceMsg.get("device_id")
        if device_id is None:
            raise Exception("设备ID为空")
    except Exception as e:
        logger.error("mqtt消息解析失败 %s", e)
        return

    # 新增或更新设备信息
    global device_list
    with device_list_lock:
        matched_device = next((device for device in device_list if device['device_id'] == device_id), None)
        if matched_device:
            matched_device.update(deviceMsg)
            matched_device["server_time"] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")  # 服务器时间
            matched_device["mqtt_timestamp"] = datetime.now().timestamp() * 1000  # 转换为毫秒时间戳
        else:
            deviceMsg["server_time"] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")  # 服务器时间
            deviceMsg["mqtt_timestamp"] = datetime.now().timestamp() * 1000  # 转换为毫秒时间戳
            device_list.append(deviceMsg)
        # logger.info("device_list update: %s", device_list)

    # 新增或更新设备高度图表数据
    global device_alt_chartdata_map_all, device_alt_chartdata_map_mqtt, device_alt_chartdata_map_lock
    with device_alt_chartdata_map_lock:
        matched_device = device_alt_chartdata_map_all.get(device_id)
        if matched_device:
            matched_device["xData"].append(datetime.now().timestamp() * 1000)
            matched_device["yData"].append(deviceMsg.get("coordinates").get("alt"))
            # logger.info("device_alt_chartdata_map_all update via mqtt: %s", device_alt_chartdata_map_all)
        else:
            device_alt_chartdata_map_all[device_id] = {
                "xData": [datetime.now().timestamp() * 1000],
                "yData": [deviceMsg.get("coordinates").get("alt")]
            }
            # logger.info("device_alt_chartdata_map_all add a new device via mqtt: %s", device_alt_chartdata_map_all)

        matched_device = device_alt_chartdata_map_mqtt.get(device_id)
        if matched_device:
            matched_device["xData"].append(datetime.now().timestamp() * 1000)
            matched_device["yData"].append(deviceMsg.get("coordinates").get("alt"))
            # logger.info("device_alt_chartdata_map_mqtt update via mqtt: %s", device_alt_chartdata_map_mqtt)
        else:
            device_alt_chartdata_map_mqtt[device_id] = {
                "xData": [datetime.now().timestamp() * 1000],
                "yData": [deviceMsg.get("coordinates").get("alt")]
            }
            # logger.info("device_alt_chartdata_map_mqtt add a new device via mqtt: %s", device_alt_chartdata_map_mqtt)

    # 通知前端设备信息更新及更新的设备ID
    socketio.emit("device_list", device_list)
    socketio.emit("updated_device_id", device_id)
    # 保存到文件
    saveGNSS(deviceMsg)


def handleDeviceMsgWebsocket(deviceMsg):
    device_id = deviceMsg.get("device_id")
    device_msg = deviceMsg
    # 新增或更新设备信息
    global device_list
    with device_list_lock:
        matched_device = next((device for device in device_list if device['device_id'] == device_id), None)
        if matched_device:
            matched_device.update(device_msg)
            matched_device["server_time"] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")  # 服务器时间
            matched_device["http_timestamp"] = datetime.now().timestamp() * 1000  # 转换为毫秒时间戳
        else:
            device_msg["server_time"] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")  # 服务器时间
            device_msg["http_timestamp"] = datetime.now().timestamp() * 1000  # 转换为毫秒时间戳
            device_list.append(device_msg)
        logger.info("device_list update via websocket: %s", device_list)

    # 新增或更新设备高度图表数据
    global device_alt_chartdata_map_all, device_alt_chartdata_map_http, device_alt_chartdata_map_lock
    with device_alt_chartdata_map_lock:
        matched_device = device_alt_chartdata_map_all.get(device_id)
        if matched_device:
            matched_device["xData"].append(datetime.now().timestamp() * 1000)
            matched_device["yData"].append(device_msg.get("coordinates").get("alt"))
            logger.info("device_alt_chartdata_map_all update via websocket: %s", device_alt_chartdata_map_all)
        else:
            device_alt_chartdata_map_all[device_id] = {
                "xData": [datetime.now().timestamp() * 1000],
                "yData": [device_msg.get("coordinates").get("alt")]
            }
            logger.info("device_alt_chartdata_map_all add a new device via websocket: %s", device_alt_chartdata_map_all)

        matched_device = device_alt_chartdata_map_http.get(device_id)
        if matched_device:
            matched_device["xData"].append(datetime.now().timestamp() * 1000)
            matched_device["yData"].append(device_msg.get("coordinates").get("alt"))
            logger.info("device_alt_chartdata_map_http update via websocket: %s", device_alt_chartdata_map_http)
        else:
            device_alt_chartdata_map_http[device_id] = {
                "xData": [datetime.now().timestamp() * 1000],
                "yData": [device_msg.get("coordinates").get("alt")]
            }
            logger.info("device_alt_chartdata_map_http add a new device via websocket: %s", device_alt_chartdata_map_http)

    # 通知前端设备信息更新及更新的设备ID
    socketio.emit("device_list", device_list)
    socketio.emit("updated_device_id", device_id)
    # 保存到文件
    saveGNSS(deviceMsg)


def onMqttMessageCallback(client, userdata, message):
    # 解码mqtt消息及调用消息处理
    try:
        message_decoded = message.payload.decode("utf-8")
    except UnicodeDecodeError:
        message_decoded = message.payload.decode("gb18030")
    except Exception as e:
        logger.error("MQTT消息解析失败")
        logger.error(e)
        return
    # logger.info("收到MQTT消息 话题：%s 消息：%s" % (message.topic, message_decoded))
    if message_decoded in heart_beat_messages:
        # 舍弃心跳包
        logger.info("收到MQTT心跳包 话题：%s 消息：%s" % (message.topic, message_decoded))
        return
    handleDeviceMsgMqtt(message_decoded)
    # socketio.emit("device-mqtt-message", message.payload.decode("gb18030"))


def onWebsocketMessageCallback(device_msg):
    try:
        if type(device_msg) is not dict:
            raise Exception("消息格式错误")
    except Exception as e:
        logger.error("ws消息解析失败 %s", e)
        return
    handleDeviceMsgWebsocket(device_msg)


# mqtt
MQTT_BROKER = '8.140.205.252'
MQTT_PORT = 1883
MQTT_USER = 'test'
MQTT_PASSWORD = '123'
MQTT_CLIENT_ID = 'paosa-python-client'

mqtt_client = MQTTClient(
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    username=MQTT_USER,
    password=MQTT_PASSWORD,
    client_id=MQTT_CLIENT_ID,
    onMessageCallback=onMqttMessageCallback,
)

# socketio client
# wifi_socket_client = WifiSocketClient(server_ip=uavip, on_device_message=onWebsocketMessageCallback)
# wifi_socket_client.connect()


@app.route('/<path:filename>')
def static_files(filename):
    file_path = os.path.join(app.static_folder, filename)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, filename)
    else:
        # 文件不存在，交给前端路由处理
        return send_from_directory(app.static_folder, 'index.html')


@app.errorhandler(404)
def page_not_found(error):
    # 返回index.html页面
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/')
def index():
    global uavIp
    arg_uavIp = request.args.get('uavIp')
    logger.info(f"接收到的uavIp:{arg_uavIp}")
    if arg_uavIp:
        uavIp = arg_uavIp
        logger.info(f"设置uavIp:{uavIp}")
    return send_from_directory(app.static_folder, 'index.html')


# 无人机相关接口
@app.route('/api/set_uavip', methods=['POST'])
def set_uavip():
    # 设置无人机IP
    global uavip
    # 检查请求是否为 JSON 格式
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    uavip = request.json.get("uavip")
    logger.info("设置无人机IP %s", uavip)
    response = {
        "status": 200,
        "message": "OK"
    }
    return jsonify(response)


@app.route('/api/uav_command', methods=['POST'])
def uav_command():
    # 无人机控制命令
    # 检查请求是否为 JSON 格式
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    command = request.json.get("command")
    logger.info("收到无人机控制命令 %s", command)
    wifi_socket_client.send_command(command)
    logger.info("发送控制命令到无人机 %s", command)
    response = {
        "status": 200,
        "message": "OK"
    }
    return jsonify(response)

# 设备信息接口


# @app.route('/api/update_device_info', methods=['POST'])
# def update_device_info():
#     # 检查请求是否为 JSON 格式
#     if not request.is_json:
#         return jsonify({"error": "Request must be JSON"}), 400
#     device_msg = request.json

#     # 接收到设备上报信息
#     handleDeviceMsgWebsocket(device_msg)
#     response = {
#         "status": 200,
#         "message": "OK"
#     }
#     return jsonify(response)


# @app.route('/update_device_list', methods=['POST'])
# def update_device_list():
#     # 接收到设备列表
#     global device_list
#     # 检查请求是否为 JSON 格式
#     if not request.is_json:
#         return jsonify({"error": "Request must be JSON"}), 400
#     device_list = request.json
#     device_list = device_list

#     logger.info("更新设备列表接口调用 全量更新设备列表")

#     socketio.emit("device_list", device_list)
#     response = {
#         "status": 200,
#         "message": "OK"
#     }
#     return jsonify(response)
@app.route('/api/get_device_chartdata')
def get_device_chartdata():
    # 获取设备图表数据
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400
    response = {}
    global device_alt_chartdata_map_all, device_alt_chartdata_map_mqtt, device_alt_chartdata_map_http, device_alt_chartdata_map_lock
    with device_alt_chartdata_map_lock:
        chartdata_all = device_alt_chartdata_map_all.get(device_id)
        chartdata_mqtt = device_alt_chartdata_map_mqtt.get(device_id)
        chartdata_http = device_alt_chartdata_map_http.get(device_id)
        if not chartdata_all:
            response = {
                "success": False,
                "message": "设备不存在"
            }
            return jsonify(response)
        if not chartdata_mqtt:
            chartdata_mqtt = []
        if not chartdata_http:
            chartdata_http = []

        response = {
            "success": True,
            "chartdata": {
                "all": chartdata_all,
                "mqtt": chartdata_mqtt,
                "http": chartdata_http
            }
        }
    return jsonify(response)

# socket服务端相关


@socketio.on('message')
def handleMessage(msg):
    logger.info('Message: ' + msg)
    send(msg)


@socketio.on('device_list')
def handleDeviceList(msg):
    global device_list
    if msg == "refresh":
        emit("device_list", device_list)
        logger.info('Device list from http emitted')


@socketio.on('connect')
def handleConnect():
    global device_list
    logger.info('Connected')
    emit("device_list", device_list)


@socketio.on('disconnect')
def handleDisconnect():
    logger.info('Disconnected')


if __name__ == '__main__':
    # 主线程启动Flask
    socketio.run(app, host='0.0.0.0', port=8000, debug=False)  # debug务必为False 防止代码执行两次 导致mqtt连接失败
