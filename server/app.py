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


def saveUnknownMsg(unknown_msg):
    try:
        if not unknown_msg:
            return
        time = datetime.now().strftime("%Y-%m-%d")
        filename = "UnknownMsg_" + time + ".txt"
        filepath = os.path.join(config['HISTORY_DATA_FOLDER'], filename)
        if not os.path.exists(config['HISTORY_DATA_FOLDER']):
            os.makedirs(config['HISTORY_DATA_FOLDER'])
        with open(filepath, "ab") as f:
            f.write(unknown_msg + b"\n") if isinstance(unknown_msg, bytes) else f.write(unknown_msg.encode('latin1') + b"\n")
        return True
    except Exception as e:
        logger.error("未知消息保存失败 %s", e)
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
    try:
        # 尝试UTF-8解码
        message_decoded = message.payload.decode("utf-8")
    except UnicodeDecodeError:
        try:
            # 尝试GB18030解码
            message_decoded = message.payload.decode("gb18030")
        except UnicodeDecodeError:
            saveUnknownMsg(message.payload)
            logger.error("⚠️ 非UTF-8或GB18030编码的MQTT消息，已保存到未知消息文件")
            return
    except Exception as e:
        logger.error("MQTT消息解析异常: %s", e)
        return

    # 打印前可检查是否可能是JSON文本
    if not message_decoded.strip():
        logger.warning("⚠️ MQTT消息为空")
        return

    if message_decoded in heart_beat_messages:
        logger.info("收到MQTT心跳包 话题：%s 消息：%s", message.topic, message_decoded)
        return

    # 若不是纯文本或JSON，可加检查
    if not message_decoded.strip().startswith("{"):
        logger.warning("⚠️ 非JSON格式MQTT消息: %s", message_decoded)
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
        mqtt_client.client.publish(topic='gnss', payload=b'\xf8\xfd\xfe\xffhello')
        time.sleep(5)
