"""
WSGI config for Analytics project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import threading
import time
from django.conf import settings
import nacos
from django.core.wsgi import get_wsgi_application
import logging
import json
import traceback
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 设置日志记录器
logging.basicConfig(filename='heartbeat.log', level=logging.INFO, format='%(asctime)s - %(message)s)', encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Analytics.settings')

application = get_wsgi_application()
# 全局配置变量
global_config = {}
# 初始化 Nacos 客户端
client = nacos.NacosClient(
    server_addresses=settings.NACOS_SERVER_ADDRESSES,
    namespace=settings.NACOS_NAMESPACE,
    username=settings.NACOS_USERNAME,
    password=settings.NACOS_PASSWORD
)

# 注册服务到 Nacos
def register_service():
    client.add_naming_instance(
        service_name=settings.NACOS_SERVICE_NAME,
        ip=settings.NACOS_IP,
        port=settings.NACOS_PORT,
        group_name=settings.NACOS_GROUP
    )
    print("服务注册成功")

register_service()

# 心跳机制
def send_heartbeat():
    success = True
    while True:
        try:
            client.send_heartbeat(
                service_name=settings.NACOS_SERVICE_NAME,
                ip=settings.NACOS_IP,
                port=settings.NACOS_PORT,
                group_name=settings.NACOS_GROUP
            )
        except Exception as e:
            print(f"Failed to send heartbeat: {e}")
            success = False
        finally:
            # print(f"心跳：{success}")
            logging.info(f'Heartbeat check(心跳) - {success}')
        time.sleep(5)  # 每 5 秒发送一次心跳

# 启动心跳线程
heartbeat_thread = threading.Thread(target=send_heartbeat)
heartbeat_thread.daemon = True
heartbeat_thread.start()

# 动态配置
def config_callback(args):
    print(f"Config changed: {args}")
    print(json.loads(args['raw_content']))
    print(json.loads(args['content']))
    update_app_config(args)


# 获取并监听配置
def get_and_listen_config():
    try:
        config = client.get_config(
            data_id=settings.NACOS_CONFIG_DATA_ID,
            group=settings.NACOS_CONFIG_GROUP
        )
        print(f"Initial config: {config}")
        client.add_config_watcher(
            data_id=settings.NACOS_CONFIG_DATA_ID,
            group=settings.NACOS_CONFIG_GROUP,
            cb=config_callback
        )
    except Exception as e:
        print(f"Failed to get or listen config: {e}")

get_and_listen_config()

# 热部署部分
class ConfigHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('analytics.json'):
            try:
                with open('analytics.json', 'r') as f:
                    new_config = json.load(f)
                # 更新应用中的配置（这里假设你有一个更新配置的函数）
                update_app_config(new_config)
                logging.info(f"Config updated from file: {new_config}")
            except Exception as e:
                logging.error(f"Error updating config from file: {e}\n{traceback.format_exc()}")

def update_app_config(new_config):
    global global_config
    global_config = new_config
    print(f"Config updated from file: {global_config}")

observer = Observer()
observer.schedule(ConfigHandler(), path='.', recursive=False)
observer.start()
# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     observer.stop()
# observer.join()