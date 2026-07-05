"""
WebSocket Handlers

What it does: This file centralizes all the WebSocket connection managers used across the backend (Chat, Notifications, Document Uploads).
It allows different parts of the application to keep track of active connections and send real-time data to connected clients.
"""
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class AgentConnectionManager:
    """
    What it does: Manages real-time WebSocket connections for the AI chat interface.
    """
    def __init__(self):
        """
        What it does: Initializes an empty dictionary to store active connections.
        Args: None.
        Returns: None.
        """
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """
        What it does: Accepts a new WebSocket connection and adds it to the active list for a specific client.
        Args:
            websocket (WebSocket): The connection object.
            client_id (str): The unique identifier for the user/client.
        Returns: None.
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        """
        What it does: Removes a client's WebSocket connection from the active list when they disconnect.
        Args:
            client_id (str): The unique identifier for the user/client.
        Returns: None.
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_json(self, message: dict, client_id: str):
        """
        What it does: Sends a JSON message to a specific connected client.
        Args:
            message (dict): The data payload to send.
            client_id (str): The unique identifier for the user/client.
        Returns: None.
        """
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

agent_connection_manager = AgentConnectionManager()


class UploadStatusManager:
    """
    What it does: Manages real-time WebSocket connections for sending document upload progress updates.
    """
    def __init__(self):
        """
        What it does: Initializes a dictionary mapping session keys to lists of active WebSockets.
        Args: None.
        Returns: None.
        """
        # session_key (e.g. agent_id) -> list of WebSockets
        self.connections = {}

    async def connect(self, websocket: WebSocket, session_key: str):
        """
        What it does: Accepts a new connection for tracking upload status.
        Args:
            websocket (WebSocket): The connection object.
            session_key (str): The session or agent ID tracking the upload.
        Returns: None.
        """
        await websocket.accept()
        if session_key not in self.connections:
            self.connections[session_key] = []
        self.connections[session_key].append(websocket)

    def disconnect(self, websocket: WebSocket, session_key: str):
        """
        What it does: Removes a disconnected WebSocket from the tracking list.
        Args:
            websocket (WebSocket): The connection object.
            session_key (str): The session or agent ID.
        Returns: None.
        """
        if session_key in self.connections:
            if websocket in self.connections[session_key]:
                self.connections[session_key].remove(websocket)
            if not self.connections[session_key]:
                del self.connections[session_key]

    async def send_status(self, session_key: str, status: str, filename: str, detail: str = "", progress: float = 0.0):
        """
        What it does: Broadcasts the current upload status (like 'processing', 'completed') to all clients listening to a specific session.
        Args:
            session_key (str): The session or agent ID.
            status (str): Current status code.
            filename (str): Name of the file being processed.
            detail (str): Extra text info (e.g. error messages).
            progress (float): Percentage of completion from 0.0 to 1.0.
        Returns: None.
        """
        if session_key in self.connections:
            disconnected_sockets = []
            for ws in self.connections[session_key]:
                try:
                    await ws.send_json({
                        "status": status,
                        "filename": filename,
                        "detail": detail,
                        "progress": progress
                    })
                except Exception:
                    disconnected_sockets.append(ws)
            for ws in disconnected_sockets:
                self.disconnect(ws, session_key)

upload_status_manager = UploadStatusManager()


class NotificationWebSocketManager:
    """
    What it does: Manages real-time WebSocket connections for sending global dashboard notifications.
    """
    def __init__(self):
        """
        What it does: Initializes a dictionary mapping workspace IDs to lists of active WebSockets.
        Args: None.
        Returns: None.
        """
        # workspace_id -> list of WebSockets
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, workspace_id: str):
        """
        What it does: Accepts a connection for listening to workspace notifications.
        Args:
            websocket (WebSocket): The connection object.
            workspace_id (str): The ID of the workspace the user belongs to.
        Returns: None.
        """
        await websocket.accept()
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = []
        self.active_connections[workspace_id].append(websocket)

    def disconnect(self, websocket: WebSocket, workspace_id: str):
        """
        What it does: Removes a disconnected WebSocket from the notification tracking list.
        Args:
            websocket (WebSocket): The connection object.
            workspace_id (str): The ID of the workspace.
        Returns: None.
        """
        if workspace_id in self.active_connections:
            if websocket in self.active_connections[workspace_id]:
                self.active_connections[workspace_id].remove(websocket)
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]

    async def broadcast(self, workspace_id: str, notification: dict):
        """
        What it does: Sends a notification message to all connected clients in a specific workspace.
        Args:
            workspace_id (str): The workspace to broadcast to.
            notification (dict): The notification details (title, message, type, etc.).
        Returns: None.
        """
        if workspace_id in self.active_connections:
            disconnected = []
            for ws in self.active_connections[workspace_id]:
                try:
                    await ws.send_json(notification)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self.disconnect(ws, workspace_id)

notification_manager = NotificationWebSocketManager()
