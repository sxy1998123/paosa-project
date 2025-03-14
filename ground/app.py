from flask import Flask, send_from_directory, send_file
from flask_socketio import SocketIO, send
from DroneConnector import status, DroneConnector
import threading
app = Flask(__name__, static_folder="frontend")
app.config['DOWNLOAD_FOLDER'] = 'download_cache'  # 文件下载路径
socketio = SocketIO(app)
connector = DroneConnector()


@app.errorhandler(404)
def page_not_found(error):
    # 返回index.html页面
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@socketio.on('message')
def handleMessage(msg):
    print('Message: ' + msg)
    send(msg, broadcast=True)


@app.route('/download')
def download_file():
    print("发送下载指令")
    connector.drone_conn.sendall(b"test")
    return "OK"
    # try:
    #     # 建立专用下载连接
    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dl_sock:
    #         dl_sock.connect((connector.host, 5001))  # 无人机下载专用端口
    #         dl_sock.sendall(f"DOWNLOAD:{filename}".encode())

    #         # 接收文件数据
    #         filepath = f"{app.config['DOWNLOAD_FOLDER']}/{filename}"
    #         with open(filepath, 'wb') as f:
    #             while True:
    #                 data = dl_sock.recv(4096)
    #                 if not data:
    #                     break
    #                 f.write(data)

    #     return send_file(filepath, as_attachment=True)
    # except Exception as e:
    #     return f"Download failed: {e}", 500


if __name__ == '__main__':
    # 子线程启动TCP服务器
    connector.start()
    # connector.join() # 线程等待直到手动终止
    # 主线程启动Flask
    app.run(host='0.0.0.0', port=8000)
