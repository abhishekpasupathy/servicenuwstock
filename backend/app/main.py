from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.market import router as market_router
from app.routers.quant import router as quant_router
from app.routers.trading_system import router as trading_system_router
from app.routers.websocket import router as websocket_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)
app.include_router(quant_router)
app.include_router(trading_system_router)
app.include_router(websocket_router)
