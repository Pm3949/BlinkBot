from fastapi import WebSocket

from utils.logger import get_department_logger

logger = get_department_logger("websocket")

class AgentConnectionManager:
    """
    What it does: Manages real-time WebSocket connections for the AI chat interface.
    """
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        logger.info(f"WebSocket client attempting to connect. Client ID: {client_id}")
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connection accepted and registered for client ID: {client_id}. Active connections count: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        logger.info(f"WebSocket client disconnecting. Client ID: {client_id}")
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket connection deregistered for client ID: {client_id}. Remaining active connections count: {len(self.active_connections)}")
        else:
            logger.warning(f"Disconnect requested for unregistered client ID: {client_id}")

    async def send_json(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send JSON message to client {client_id}: {str(e)}", exc_info=True)
                self.disconnect(client_id)
        else:
            logger.warning(f"Failed to send message: Client ID {client_id} is not connected.")

agent_connection_manager = AgentConnectionManager()


class UploadStatusManager:
    """
    What it does: Manages real-time WebSocket connections for sending document upload progress updates.
    """
    def __init__(self):
        self.connections = {}

    async def connect(self, websocket: WebSocket, session_key: str):
        logger.info(f"Upload WebSocket client attempting to connect. Session Key: {session_key}")
        await websocket.accept()
        if session_key not in self.connections:
            self.connections[session_key] = []
        self.connections[session_key].append(websocket)
        logger.info(f"Upload WebSocket connection accepted. Registered for Session: {session_key}. Sockets count: {len(self.connections[session_key])}")

    def disconnect(self, websocket: WebSocket, session_key: str):
        logger.info(f"Upload WebSocket disconnecting. Session Key: {session_key}")
        if session_key in self.connections:
            if websocket in self.connections[session_key]:
                self.connections[session_key].remove(websocket)
                logger.debug(f"WebSocket removed from upload list for session {session_key}.")
            if not self.connections[session_key]:
                del self.connections[session_key]
                logger.info(f"All connections closed. Purged session key registry: {session_key}")
        else:
            logger.warning(f"Disconnect requested for unregistered upload session key: {session_key}")

    async def send_status(self, session_key: str, status: str, filename: str, detail: str = "", progress: float = 0.0):
        logger.debug(f"Broadcasting upload status update for session '{session_key}': status={status}, progress={progress}")
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
                except Exception as e:
                    logger.error(f"Error dispatching status to socket in session {session_key}: {str(e)}")
                    disconnected_sockets.append(ws)
            for ws in disconnected_sockets:
                self.disconnect(ws, session_key)
        else:
            logger.debug(f"No active WebSocket clients listening to status for session: {session_key}")

upload_status_manager = UploadStatusManager()


class NotificationWebSocketManager:
    """
    What it does: Manages real-time WebSocket connections for sending global dashboard notifications.
    """
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, workspace_id: str):
        logger.info(f"Notification WebSocket client attempting to connect. Workspace ID: {workspace_id}")
        await websocket.accept()
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = []
        self.active_connections[workspace_id].append(websocket)
        logger.info(f"Notification WebSocket accepted. Registered for Workspace: {workspace_id}. Sockets count: {len(self.active_connections[workspace_id])}")

    def disconnect(self, websocket: WebSocket, workspace_id: str):
        logger.info(f"Notification WebSocket disconnecting. Workspace ID: {workspace_id}")
        if workspace_id in self.active_connections:
            if websocket in self.active_connections[workspace_id]:
                self.active_connections[workspace_id].remove(websocket)
                logger.debug(f"WebSocket removed from workspace alert list: {workspace_id}")
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]
                logger.info(f"All workspace alerts sockets closed. Purging workspace key registry: {workspace_id}")
        else:
            logger.warning(f"Disconnect requested for unregistered notification workspace ID: {workspace_id}")

    async def broadcast(self, workspace_id: str, notification: dict):
        logger.info(f"Broadcasting workspace notification alert to workspace ID: {workspace_id}. Title: '{notification.get('title')}'")
        if workspace_id in self.active_connections:
            disconnected = []
            for ws in self.active_connections[workspace_id]:
                try:
                    await ws.send_json(notification)
                    logger.debug(f"Workspace alert successfully dispatched to socket.")
                except Exception as e:
                    logger.error(f"Error dispatching workspace alert to socket: {str(e)}")
                    disconnected.append(ws)
            for ws in disconnected:
                self.disconnect(ws, workspace_id)
        else:
            logger.debug(f"No active WebSocket connections registered to receive alerts for workspace: {workspace_id}")

notification_manager = NotificationWebSocketManager()
