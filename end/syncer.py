

import asyncio
import copy
import json
import queue
import threading
from random import randint
from time import sleep
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, WebSocket

SET = 0
DEL = 1
SYNC = 2
LOAD = 3


class SyncDict():
    def __init__(self, actionQueue: queue.Queue, initData: dict = {}):
        '''
        KV数据结构
        用于远程一对多单向同步数据
        '''
        self.version = 0  # 数据版本 传递给远端 用于指示下一次应该收到的version
        self.storage = initData  # kv存储
        self.actionQueue = actionQueue  # 通知队列
        self.running = True  # 是否运行
        self.lock = threading.Lock()  # 锁

    def load(self, data: dict):
        with self.lock:
            self.storage = data
            _next = (self.version + 1) & 0xffff
            self.actionQueue.put(
                {
                    "action": LOAD,
                    "current": self.version,
                    "next": _next,
                    "data": copy.deepcopy(self.storage)
                }
            )
            self.version = _next

    def set(self, key, value):
        with self.lock:
            self.storage[key] = value
            _next = (self.version + 1) & 0xffff
            self.actionQueue.put(
                {
                    "action": SET,
                    "current": self.version,
                    "next": _next,
                    "key": key,
                    "value": value
                }
            )
            self.version = _next

    def get(self, key):
        return self.storage[key] if key in self.storage else None

    def delete(self, key):
        with self.lock:
            del self.storage[key]
            _next = (self.version + 1) & 0xffff
            self.actionQueue.put(
                {
                    "action": DEL,
                    "current": self.version,
                    "next": _next,
                    "key": key
                }
            )
            self.version = _next

    def has(self, key):
        return key in self.storage

    def json(self) -> str:
        return json.dumps(self.storage)

    def sync(self, flag):
        self.actionQueue.put(
            {
                "action": SYNC,
                "next": self.version,  # sync不更新version 因为sync是单客户端同步，而其他的则是广播
                "flag": flag,
                "data": copy.deepcopy(self.storage)
            }
        )

    def __str__(self) -> str:
        return f"ver:{self.version} -- " + str(self.storage)


class wsBindDict():
    def __init__(self, initDict: Dict = {}):
        self.__actionQueue = queue.Queue()
        self.__syncDict = SyncDict(self.__actionQueue, initDict)
        self.__active_connections: List[WebSocket] = []

        async def __run():
            while True:
                action = self.__actionQueue.get()
                try:
                    if action["action"] == SET or action["action"] == DEL or action["action"] == LOAD:
                        await self.__broadcast(action)
                    elif action["action"] == SYNC:
                        ws = action["flag"]
                        action["flag"] = f"{ws.client.host}:{ws.client.port}"
                        await ws.send_json(action)

                except Exception as e:
                    continue

        threading.Thread(target=asyncio.get_event_loop(
        ).run_until_complete, args=(__run(),)).start()

    def getSyncDict(self) -> SyncDict:
        return self.__syncDict

    async def handel_connect(self, ws: WebSocket):
        await ws.accept()
        self.__active_connections.append(ws)
        print(f"{ws.client.host}:{ws.client.port} connected")
        try:
            while True:
                msg = await ws.receive_text()
                self.__handel_message(msg, ws)
        except Exception as e:
            print(e, ws, "ws disconnect")
            self.__active_connections.remove(ws)

    async def __broadcast(self, msg):
        for ws in self.__active_connections:
            await ws.send_json(msg)

    def __handel_message(self, msg, ws):
        if msg == "sync":
            self.__syncDict.sync(ws)


app = FastAPI(async_request_limit=1000)
wsBinder = wsBindDict({
    "b": 999,
    "c": 1,
})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await wsBinder.handel_connect(websocket)


if __name__ == "__main__":
    threading.Thread(target=uvicorn.run, args=(app,), kwargs={
        "host": "0.0.0.0",
        "port": 9999,
        "log_level": "debug",
    }).start()

    def writeSimulation():
        count = 0
        sd = wsBinder.getSyncDict()
        while True:
            # sd.set("a", randint(0, 100)*100)
            # sd.set("a", randint(0, 100)*10000)
            sd.set("a", sd.version)
            sd.load({
                "sd": {},
                "version": sd.version
            })
            count += 1
            print(sd)
            sleep(1)
            # sleep(0.001)

    threading.Thread(target=writeSimulation).start()
