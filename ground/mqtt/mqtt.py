import time
import paho.mqtt.client as mqtt
import json
from threading import Lock
from datetime import datetime, timezone


def generate_utc_timestamp() -> str:
    """生成YYYYMMDDTHHMMSSZ格式的UTC时间字符串"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # 直接包含Z字符


class MQTTClient:
    _instance = None
    _lock = Lock()  # 线程安全单例

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, broker, port=1883, username=None, password=None, client_id=None):
        if self._initialized:
            return
        self._initialized = True

        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id

        self.client = mqtt.Client(self.client_id)
        self._setup_callbacks()
        self._connect()
        print("MQTTClient initialized")

    def _setup_callbacks(self):
        """设置MQTT事件回调"""
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        self.client.on_message = self._on_message

    def _connect(self):
        """连接MQTT Broker"""
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        self.client.connect_async(self.broker, self.port)
        self.client.loop_start()  # 启动后台线程处理网络流量

    def _on_connect(self, client, userdata, flags, rc):
        """连接成功回调"""
        if rc == 0:
            print("Connected to MQTT Broker!")

            # test
            self.client.subscribe("/v1/devices/GZDKYSWCXZZ_002/datas")
            # for i in range(1,3):
            #     self.publish(payload=i)
        else:
            print(f"Failed to connect, return code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """连接断开回调"""
        print(f"Disconnected with code {rc}, attempting reconnect...")
        self.client.reconnect()

    def _on_publish(self, client, userdata, mid):
        """消息发布成功回调（可选）"""
        print(f"Message {mid} published.")

    def _on_message(self, client, userdata, message):
        """消息接收成功回调"""
        print(f"Received `{message.payload.decode()}` from `{message.topic}` topic")
        obj = json.loads(message.payload.decode())
        print(obj["devices"])

    def publish(self, topic="/v1/devices/GZDKYSWCXZZ_002/datas", payload={"state": "work"}, qos=1, retain=False):
        """发布消息（线程安全）"""
        # 示例用法
        utc_string = generate_utc_timestamp()

        payload_predata = {
            "msg": "hello"
        }
        msg_str = json.dumps(payload_predata, indent=4)
        # print("utc_string:", utc_string)
        # print(msg_str)
        self.client.publish(topic, msg_str, qos=qos, retain=retain)

    def shutdown(self):
        """关闭连接"""
        self.client.loop_stop()
        self.client.disconnect()


MQTT_BROKER = 'mqtt.usr.cn'
MQTT_PORT = 1883
MQTT_USER = 'usr.cn'
MQTT_PASSWORD = 'usr.cn'
MQTT_CLIENT_ID = 'GZDKYSWCXZZ'

brokerConnected = False

mqtt_client = MQTTClient(
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    username=MQTT_USER,
    password=MQTT_PASSWORD,
    client_id=MQTT_CLIENT_ID
)


if __name__ == "__main__":
    while True:
        mqtt_client.publish(payload={"state": "work"})
        time.sleep(30)
