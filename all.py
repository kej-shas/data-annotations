import os
import json
from abc import ABC

import yaml
import asyncio
import pystray
import requests
import threading
import webbrowser
import tornado.web
from PIL import Image
import tornado.ioloop
import tornado.httpserver
from natsort import natsort
from pystray import MenuItem as item
from tornado.options import define, options, parse_command_line

server_state = False
define("port", default=8888, help="运行端口", type=int)
config_path = yaml.load(open("config.yaml", "r", encoding="utf-8"), Loader=yaml.FullLoader)
define("root_path",
       default=f"{config_path['root_path']}/{config_path['DatasetPath']['times']}/",
       help="运行路径", type=str)
define("times",
       default=config_path['DatasetPath']['times'],
       help="运行路径", type=int)


def get_groups_file():
    groups = {}
    for i in range(1, 11):
        path_group = os.listdir(f"{options.root_path}/{i}/alstonia_scholaris_diseased/")[0].split(".")[0]
        groups[f"alstonia_scholaris_diseased/{path_group}"] = i

    json_dicts = []
    sids = []
    for jsonfile in os.listdir("result"):
        with open(f"result/{jsonfile}", "r", encoding="utf-8") as f:
            fd = json.load(f)
        sid = jsonfile.split(".")[0]
        fd["sid"] = sid
        sids.append(sid)
        json_dicts.append(fd)

    groups_file = {}

    for j in json_dicts:
        for group, v in groups.items():
            j: dict
            if group in j.keys():
                sid = j["sid"]
                del j["sid"]
                groups_file[sid] = {"group": v, "data": j}

    return groups_file, sids


groups_file, sids = get_groups_file()


class MainHandler(tornado.web.RequestHandler, ABC):
    def get(self):
        self.write("Hello, world!\n")


class BaseHandler(tornado.web.RequestHandler, ABC):
    def set_default_headers(self) -> None:
        self.set_header('Access-Control-Allow-Origin', '*')


class InitDataHandler(BaseHandler, ABC):
    def get(self):
        file_list = []

        # for dir_ in os.listdir(options.root_path):
        #     for file in os.listdir(f"{options.root_path}/{dir_}/"):
        #         if file.split(".")[-1] == "jpg":
        #             file_list.append(f"{dir_}/{file.split('.')[0]}")
        self.write(json.dumps({'message': 'ok', "data": {"sids": sids, "groups_file": groups_file}}))


class UpDataPathAndText(BaseHandler, ABC):
    def post(self):
        sid=self.get_body_argument("sid", "")
        path = self.get_body_argument("path", "")
        text = self.get_body_argument("text", "")
        # with open(f"{options.root_path}/{path}.txt", "w", encoding="utf-8", newline="") as f:
        #     f.write(text.replace("\n", "") + "\n")
        # f.close()
        groups_file[sid]["data"][path]=text
        with open(f"result/{sid}.json", "w", encoding="utf-8") as f:
            json.dump(groups_file[sid]["data"], f, ensure_ascii=False)
            f.close()

        self.write(json.dumps({'message': 'ok', }))


# class SynchronizationDataToServer(BaseHandler, ABC):
#     def post(self):
#         randomUsername = self.get_argument("randomUsername", "")
#         data = self.getFileTxtDict()
#
#         if randomUsername == "":
#             self.write(json.dumps({'message': 'error', "result": "Your pc have not cookie"}))
#         else:
#             id_files = [f"{i}".split(".")[0] for i in os.listdir("result")]
#             print(id_files)
#             if randomUsername in id_files or len(id_files) == 0:
#                 result = requests.post("http://124.221.156.245:8889/upload", json=data,
#                                        params={"randomUsername": randomUsername}).json()
#                 self.write(json.dumps(result))
#
#             else:
#                 self.write(json.dumps({'message': 'error', "result": "只能使用一个浏览器提交"}))
#         with open(f"result/{randomUsername}.json", "w", encoding="utf-8") as f:
#             json.dump(data, f, ensure_ascii=False)
#             f.close()

    def getFileTxtDict(self):
        root_path = options.root_path
        file_list = {}
        for dir_ in os.listdir(root_path):
            for file in os.listdir(f"{root_path}/{dir_}/"):
                if file.split(".")[-1] == "txt":
                    with open(f"{root_path}/{dir_}/{file}", "r", encoding="utf-8") as f:
                        all_str = ""
                        for line in f.readlines():
                            all_str += line
                        file_list[f"{dir_}/{file.split('.')[0]}"] = all_str
                    f.close()
        return file_list


class MyStaticFileHandler(tornado.web.StaticFileHandler, ABC):
    def set_extra_headers(self, path):
        # Disable cache
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')


parse_command_line()
print("http://localhost:{}/index.html".format(options.port))
application = tornado.web.Application(
    handlers=[
        (r"/", MainHandler),
        (r"/init", InitDataHandler),
        (r"/upload", UpDataPathAndText),
        # (r"/synchronization", SynchronizationDataToServer),
        (r"/data/(.*)", MyStaticFileHandler, {"path": options.root_path}),
        (r"/(.*)", MyStaticFileHandler, {"path": "static/"})

    ],
)

http_server = tornado.httpserver.HTTPServer(application)


def stop_tornado():
    global server_state
    server_state = False
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.add_callback(ioloop.stop)


def start_tornado():
    global server_state
    if server_state:
        return
    server_state = True
    print("server_state", server_state)

    http_server.listen(8888)
    ws = tornado.ioloop.IOLoop.instance()
    loop = asyncio.new_event_loop()
    p = threading.Thread(target=worker, args=(ws, loop,))
    p.start()


def quit_window(icon, item):
    global server_state
    if server_state:
        stop_tornado()
        icon.stop()
    else:
        icon.stop()


def show_browser(icon, item: item):
    webbrowser.open('http://localhost:8888/w.html')


def worker(ws, loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws.start())


if __name__ == "__main__":
    start_tornado()
    webbrowser.open('http://localhost:8888/w.html')
    menu = (item('浏览器打开', show_browser), item('退出', quit_window))
    image = Image.open("ico.png")
    icon = pystray.Icon("数据标注", image, "植物数据集", menu)
    icon.run()
