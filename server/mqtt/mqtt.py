import time
import paho.mqtt.client as mqtt
import json
from threading import Lock
from datetime import datetime, timezone
import logging

logging.basicConfig(
    level=logging.INFO,  # 修改日志级别输出所有日志
    format='%(asctime)s %(name)s [%(pathname)s:%(lineno)d] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # 日期时间格式
)

logger = logging.getLogger(__name__)


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

    def __init__(self, broker, port=1883, username=None, password=None, client_id=None, onConnectCallback=None, onDisconnectCallback=None, onPublishCallback=None, onMessageCallback=None, tls=False, ca_certs=None):
        if self._initialized:
            return
        self._initialized = True

        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        

        self.onConnectCallback = onConnectCallback or self._on_connect
        self.onDisconnectCallback = onDisconnectCallback or self._on_disconnect
        self.onPublishCallback = onPublishCallback or self._on_publish
        self.onMessageCallback = onMessageCallback or self._on_message

        self.client = mqtt.Client(self.client_id)
        
        self._setup_callbacks()
        if tls and ca_certs in [None, ""]:
            logger.info("MQTTClient initialized with TLS but no ca_certs provided.skipping ca_certs")
            self.client.tls_set()
            self.client.tls_insecure_set(True)
        elif tls and ca_certs not in [None, ""]:
            logger.info(f"MQTTClient initialized with TLS and ca_certs provided.ca_certs: {ca_certs}")
            self.client.tls_set(ca_certs=ca_certs)
        else:
            logger.info("MQTTClient initialized without TLS")
        self.connect()

    def _setup_callbacks(self):
        """设置MQTT事件回调"""
        self.client.on_connect = self.onConnectCallback
        self.client.on_disconnect = self.onDisconnectCallback
        self.client.on_publish = self.onPublishCallback
        self.client.on_message = self.onMessageCallback

    def connect(self):
        """连接MQTT Broker"""
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        # 设置自动重连延迟（指数退避）
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        self.client.connect_async(self.broker, self.port)
        self.client.loop_start()  # 启动后台线程处理网络流量
        logger.info("Connecting to MQTT Broker...")

    def _on_connect(self, client, userdata, flags, rc):
        """连接成功回调"""
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            self.subscribe("gnss")
        else:
            logger.info(f"Failed to connect, return code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """连接断开回调"""
        logger.info(f"Disconnected with code {rc}, attempting reconnect...")


    def _on_publish(self, client, userdata, mid):
        """消息发布成功回调（可选）"""
        logger.info(f"Message {mid} published.")

    def _on_message(self, client, userdata, message):
        """消息接收成功回调"""
        logger.info(f"Received `{message.payload.decode()}` from `{message.topic}` topic")

    def publish(self, topic="gnss", payload={}, qos=1, retain=False):
        """发布消息（线程安全）"""
        utc_string = generate_utc_timestamp()

        payload_predata = {
            "time": utc_string,
            "data": payload
        }
        msg_str = json.dumps(payload_predata, indent=4)
        logger.info(f"Publishing `{msg_str}` to `{topic}` topic")
        self.client.publish(topic, msg_str, qos=qos, retain=retain)

    def subscribe(self, topic):
        """订阅主题"""
        self.client.subscribe(topic)
        logger.info(f"Subscribed to `{topic}` topic")

    def shutdown(self):
        """关闭连接"""
        self.client.loop_stop()
        self.client.disconnect()


# test
if __name__ == "__main__":
    # 有人云
    # MQTT_BROKER = 'mqtt.usr.cn'
    # MQTT_PORT = 1883
    # MQTT_USER = 'usr.cn'
    # MQTT_PASSWORD = 'usr.cn'
    # MQTT_CLIENT_ID = 'GZDKYSWCXZZ'
   
    # emqx
    # MQTT_BROKER = 'le6e110a.ala.cn-hangzhou.emqxsl.cn'
    # MQTT_PORT = 8883
    # MQTT_USER = 'test'
    # MQTT_PASSWORD = '123'
    # MQTT_CLIENT_ID = 'paosa-python-client'
    
    # vultr
    # MQTT_BROKER = '155.138.210.11'
    # MQTT_PORT = 1883
    # MQTT_USER = 'test'
    # MQTT_PASSWORD = '123'
    # MQTT_CLIENT_ID = 'paosa-python-client'

    # 阿里云
    MQTT_BROKER = '8.140.205.252'
    MQTT_PORT = 1883
    MQTT_USER = 'test'
    MQTT_PASSWORD = '123'
    MQTT_CLIENT_ID = 'paosa-python-client'

    def on_message_callback(client, userdata, message):
        """消息接收成功回调"""
        logger.info(f"Received `{message.payload.decode()}` from `{message.topic}` topic")

    # 使用证书
    # mqtt_client = MQTTClient(broker=MQTT_BROKER, port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASSWORD,
    #                          client_id=MQTT_CLIENT_ID, onMessageCallback=on_message_callback, tls=True, ca_certs='D:\\Project2025\\paosa-project\\ground\\mqtt\\emqxsl-ca.crt')
    # 不使用证书
    mqtt_client = MQTTClient(broker=MQTT_BROKER, port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASSWORD,
                             client_id=MQTT_CLIENT_ID, onMessageCallback=on_message_callback, tls=False)
    # mqtt_client.subscribe("gnss")
    logger.info("MQTTClient started")
    time.sleep(5)
    while True:
        # mqtt_client.publish()
        time.sleep(10)
