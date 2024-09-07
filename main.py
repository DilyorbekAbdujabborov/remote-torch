from faker import Faker
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.templating import Jinja2Templates
from fastapi.requests import Request
from typing import List, Dict


app = FastAPI()

templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str: WebSocket] = {}
        self.admin_ids: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, name: str, is_admin: bool = False) -> None:
        await websocket.accept()
        if is_admin:
            self.admin_ids.append(websocket)
        else:
            self.active_connections[name] = websocket

        await self.send_user_list()

    async def disconnect(self, websocket: WebSocket, name: str, is_admin: bool = False) -> None:

        if is_admin:
            self.admin_ids.remove(websocket)
        else:
            del self.active_connections[name]
            await self.send_user_list()

    async def send_message(self, websocket: WebSocket, message: str):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def toggle(self, name: str, status: str):
        websocket = self.active_connections[name]
        await websocket.send_json({"name": name, "status": status})


    async def send_user_list(self):
        for admin in self.admin_ids:
            try:
                await admin.send_json(list(self.active_connections.keys()))
                print("Sending")
            except Exception as err:
                self.admin_ids.remove(admin)
                print(err)


manager = ConnectionManager()


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/admin")
async def get_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, admin: bool = False):
    fake = Faker()
    name = fake.name()
    await manager.connect(websocket, name=name, is_admin=admin)

    # if not admin:
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "command":
                await manager.toggle(name=data.get("name"), status=data.get("status"))
            else:
                await manager.send_user_list()

    except WebSocketDisconnect:
        await manager.disconnect(websocket, name=name, is_admin=admin)

# @app.get("/admin/stream")
# async def admin_stream():
#     async def event_generator():
#         while True:
#             await asyncio.sleep(1)
#             yield f"data: {json.dumps(list(manager.client_ids.values()))}\n\n"
#
#     return StreamingResponse(event_generator(), media_type="text/event-stream")
