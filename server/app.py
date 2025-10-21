from mqtt.mqtt import MQTTClient
import logging
from datetime import datetime
import json
import os
import time
# logger
logging.basicConfig(
    level=logging.INFO,  # 修改日志级别输出所有日志
    format='%(asctime)s %(name)s [%(pathname)s:%(lineno)d] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # 日期时间格式
)

logger = logging.getLogger(__name__)
config = {
    "HISTORY_DATA_FOLDER": "./HistoryData"
}
# 心跳包消息
heart_beat_messages = ['www.usr.cn']


def saveGNSS(gnss_data):
    try:
        if not gnss_data:
            return
        time = datetime.now().strftime("%Y-%m-%d")
        filename = "GNSS_" + time + ".txt"
        filepath = os.path.join(config['HISTORY_DATA_FOLDER'], filename)
        # logger.info("gnss_data: %s", gnss_data)
        if not os.path.exists(config['HISTORY_DATA_FOLDER']):
            os.makedirs(config['HISTORY_DATA_FOLDER'])

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


if __name__ == '__main__':
    # mqtt
    MQTT_BROKER = '8.140.205.252'
    MQTT_PORT = 1883
    MQTT_USER = 'test123'
    MQTT_PASSWORD = '123'
    MQTT_CLIENT_ID = 'paosa-python-client2'

    mqtt_client = MQTTClient(
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASSWORD,
        client_id=MQTT_CLIENT_ID,
        onMessageCallback=onMqttMessageCallback,
    )
    while True:
        time.sleep(5)
