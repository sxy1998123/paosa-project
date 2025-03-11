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

        # 远程监测装置状态socket
        self.stm32_status_host = '192.168.1.100'  
        self.stm32_status_port = 5000

        # 远程监测装置文件socket
        self.stm32_file_host = '192.168.1.100'  
        self.stm32_file_port = 5001

        # 控制线程运行的标志
        self.running = False
        self.status_socket = None
        self.file_socket = None

    def start_status_service(self):
        """ 状态推送服务 """
        self.status_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.status_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.status_socket.bind((self.status_host, self.status_port))
        self.status_socket.listen(5)
        self.status_socket.settimeout(1)  # 设置超时以定期检查运行状态
        print("TCP状态推送服务已启动")
        self.running = True
        while self.running:
            try:
                conn, addr = self.status_socket.accept()
                print(f"Status client connected: {addr}")
                threading.Thread(target=self.handle_status_client, args=(conn,)).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Status service error: {e}")
                break
        self.status_socket.close()

    def handle_status_client(self, conn):
        """ 状态处理客户端 """
        try:
            while self.running:
                conn.send(b"test")
                time.sleep(1)
        except Exception as e:
            print(f"Status client error: {e}")
        finally:
            conn.close()

    def start_file_service(self):
        """ 文件传输服务 """
        self.file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.file_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.file_socket.bind((self.file_host, self.file_port))
        self.file_socket.listen(5)
        self.file_socket.settimeout(1)
        print("TCP文件传输服务已启动")
        self.running = True
        while self.running:
            try:
                conn, addr = self.file_socket.accept()
                print(f"File client connected: {addr}")
                threading.Thread(target=self.handle_file_client, args=(conn,)).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"File service error: {e}")
                break
        self.file_socket.close()

    def handle_file_client(self, conn):
        """ 处理文件请求 """
        try:
            request = conn.recv(1024).decode()
            if request.startswith("DOWNLOAD:"):
                filename = request[9:]
                # 示例处理，实际应读取文件
                conn.sendall(b"FILE_NOT_FOUND")
        except Exception as e:
            print(f"File transfer error: {e}")
        finally:
            conn.close()

    def stop(self):
        """ 停止服务 """
        self.running = False
        if self.status_socket:
            self.status_socket.close()
        if self.file_socket:
            self.file_socket.close()

if __name__ == '__main__':
    server = DroneTCPServer()
    status_thread = threading.Thread(target=server.start_status_service)
    file_thread = threading.Thread(target=server.start_file_service)
    
    try:
        status_thread.start()
        file_thread.start()
        # 主线程等待子线程结束
        while status_thread.is_alive() or file_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n接收到Ctrl+C，正在停止服务...")
        server.stop()
        status_thread.join()
        file_thread.join()
        print("服务已停止")