import asyncio
import time
import os
import httpx
from fastapi.testclient import TestClient
from backend.app.main import app

def run_benchmark():
    # Start a server? Better to just use httpx with an ASGI transport, or simply TestClient?
    pass
