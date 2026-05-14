from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/quote/{ticker}")
async def quote_ws(websocket: WebSocket, ticker: str):

    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Received: {data}")
