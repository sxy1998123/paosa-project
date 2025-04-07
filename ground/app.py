from flask import Flask, send_from_directory, send_file, jsonify
from flask_socketio import SocketIO, send
from DroneConnector import DroneConnector
import threading

app = Flask(__name__, static_folder="frontend")
app.config['DOWNLOAD_FOLDER'] = 'download_cache'  # 文件下载路径
socketio = SocketIO(app, cors_allowed_origins="*")
droneConnector = DroneConnector(socketio)


@app.errorhandler(404)
def page_not_found(error):
    # 返回index.html页面
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/download')
def download_file():
    print("发送下载指令")
    droneConnector.drone_conn.sendall(
        droneConnector.pack_data({"cmd": "download", "device_id": 1})
    )
    return "OK"
    # try:
    #     # 建立专用下载连接
    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dl_sock:
    #         dl_sock.connect((droneConnector.host, 5001))  # 无人机下载专用端口
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


@app.route('/test')
def test():
    return jsonify({
        "drone_connecting": droneConnector.drone_connecting
    })


@socketio.on('message')
def handleMessage(msg):
    print('Message: ' + msg)
    send(msg)


@socketio.on('connect')
def handleConnect():
    print('Connected')


@socketio.on('disconnect')
def handleDisconnect():
    print('Disconnected')


if __name__ == '__main__':
    # 子线程启动TCP服务器
    droneConnector.start()
    # 主线程启动Flask
    socketio.run(app, host='0.0.0.0', port=8000)
