import socket
import threading
import time

class DroneTCPServer:
    def __init__(self):
        # 状态服务配置
        self.status_host = '0.0.0.0'
        self.status_port = 5000
        
        # 文件服务配置
        self.file_host = '0.0.0.0'
        self.file_port = 5001
        
    def start_status_service(self):
        """ 状态推送服务 """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.status_host, self.status_port))
            s.listen(5)
            
            while True:
                conn, addr = s.accept()
                print(f"Status client connected: {addr}")
                threading.Thread(target=self.handle_status_client, args=(conn,)).start()
                
    def handle_status_client(self, conn):
        """ 处理状态客户端 """
        try:
            while True:
                # 使用TCP从监测装置读取最新数据

                
        except ConnectionResetError:
            conn.sendall(f"串口连接失败")
            print("Status client disconnected")
            
    def start_file_service(self):
        """ 文件传输服务 """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.file_host, self.file_port))
            s.listen(5)
            
            while True:
                conn, addr = s.accept()
                print(f"File client connected: {addr}")
                threading.Thread(target=self.handle_file_client, args=(conn,)).start()
                
    def handle_file_client(self, conn):
        """ 处理文件请求 """
        try:
            # 接收下载指令
            request = conn.recv(1024).decode()
            if request.startswith("DOWNLOAD:"):
                filename = request[9:]
                filepath = f"data_storage/{filename}"
                
                # todo从单片机读取文件
                # if self.sensor_reader.file_exists(filename):
                #     with open(filepath, 'rb') as f:
                #         while chunk := f.read(4096):
                #             conn.sendall(chunk)
                #     print(f"File {filename} sent")
                # else:
                #     conn.sendall(b'FILE_NOT_FOUND')
                    
        except Exception as e:
            print(f"File transfer error: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    server = DroneTCPServer()
    
    # 启动两个服务线程
    status_thread = threading.Thread(target=server.start_status_service)
    file_thread = threading.Thread(target=server.start_file_service)
    
    status_thread.start()
    file_thread.start()
    
    status_thread.join()
    file_thread.join()