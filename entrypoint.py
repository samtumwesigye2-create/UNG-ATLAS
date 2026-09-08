from app import app
from operations_feed import router as operations_router

app.include_router(operations_router)
