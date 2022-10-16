import json
import os

import requests
import tornado.httpserver
import tornado.ioloop
import tornado.web
from natsort import natsort
from tornado.options import define, options, parse_command_line

define("port", default=8888, help="运行端口", type=int)
define("root_path", default="E:/pdata", help="运行端口", type=str)


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self) -> None:
        self.set_header('Access-Control-Allow-Origin', '*')


class InitDataHandler(BaseHandler):
    def get(self):
        file_list = []

        for dir_ in os.listdir(options.root_path):
            for file in os.listdir(f"{options.root_path}/{dir_}/"):
                if file.split(".")[-1] == "jpg":
                    file_list.append(f"{dir_}/{file.split('.')[0]}")
        self.write(json.dumps({'message': 'ok', "data": list(natsort.natsorted(file_list))}))


class UpDataPathAndText(BaseHandler):
    def post(self):
        path = self.get_body_argument("path", "")
        text = self.get_body_argument("text", "")
        with open(f"{options.root_path}/{path}.txt", "w", encoding="utf-8", newline="") as f:
            f.write(text.replace("\n", "") + "\n")
        f.close()
        self.write(json.dumps({'message': 'ok', }))


class SynchronizationDataToServer(BaseHandler):
    def post(self):
        randomUsername = self.get_argument("randomUsername", "")
        data = self.getFileTxtDict()
        with open(f"result/{randomUsername}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.close()

        if randomUsername == "":
            self.write(json.dumps({'message': 'error', "result": "Your pc have not cookie"}))
        else:
            id_files = [f"{i}".split("."[0]) for i in os.listdir("result")]
            if randomUsername in id_files or len(id_files) == 0:
                result = requests.post("http://localhost:8889/upload", json=data,
                                       params={"randomUsername": randomUsername}).json()
                self.write(json.dumps(result))
            elif len(id_files) == 1:
                randomUsername = id_files[0]
                result = requests.post("http://localhost:8889/upload", json=data,
                                       params={"randomUsername": randomUsername}).json()
                self.write(json.dumps(result))
            else:
                self.write(json.dumps({'message': 'error', "result": "只能使用一个浏览器提交"}))

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


class MyStaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        # Disable cache
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')


if __name__ == "__main__":
    parse_command_line()
    print("http://localhost:{}/index.html".format(options.port))
    app = tornado.web.Application(
        handlers=[
            (r"/init", InitDataHandler),
            (r"/upload", UpDataPathAndText),
            (r"/synchronization", SynchronizationDataToServer),
            (r"/data/(.*)", MyStaticFileHandler, {"path": options.root_path}),
            (r"/(.*)", MyStaticFileHandler, {"path": "static/"})

        ],
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
