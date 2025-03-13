项目目录说明<br/>
cloud-tcp    #云服务器上的tcp服务端及客户端<br/>
ground       #地面站的http服务端前后端一体 tcp客户端 用于与其他模块通信<br/>
uav-tcp      #无人机的tcp服务端及tcp客户端<br/>
main.py      #启动器<br/>


推荐启动顺序：

地面端最先启动服务

无人机随后启动双重服务

监测装置最后启动并主动连接