import json
import logging

from fastapi import WebSocket

logger = logging.getLogger("websocket")


def log_connection(websocket: WebSocket, endpoint: str, user_id: str = None, action: str = "connected"):
    """
    Log details about WebSocket connections.

    Args:
    websocket (WebSocket): The WebSocket connection.
    endpoint (str): 'auth' or 'messages' to indicate the WebSocket type.
    user_id (str): Optional user ID for authenticated connections.
    action (str): 'connected' or 'disconnected'.
    """
    log_data = {
        "client_ip": websocket.client.host,
        "client_port": websocket.client.port,
        "endpoint": endpoint,
        "user_id": user_id,
        "action": action
    }
    logger.info(json.dumps(log_data))
