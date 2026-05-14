from fastapi import APIRouter, HTTPException

from app.database import add_alert, delete_alert, list_alerts

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
async def get_alerts():
    return list_alerts()


@router.post("/alerts")
async def post_alert(payload: dict):
    return add_alert(payload)


@router.delete("/alerts/{alert_id}")
async def remove_alert(alert_id: int):
    if not delete_alert(alert_id):
        raise HTTPException(404, "Alert not found")
    return {"deleted": True}
