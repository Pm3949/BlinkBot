"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script contains WebSocket connection managers that power all real-time bidirectional
communications in RAGMate.

These managers are refactored to use a Redis Pub/Sub backplane, permitting horizontally 
scaled application servers to share real-time notification feeds and chat streams.
"""

import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect  # Import standard FastAPI WebSocket protocols

# Logging utilities
from utils.logger import get_department_logger
from core.redis_client import get_redis_client

# Set up department logger specifically scoped to "websocket" events
logger = get_department_logger("websocket")

class AgentConnectionManager:
    """
    Manages active WebSocket connections for the interactive agent chat console.
    Maps connection client IDs directly to their corresponding open WebSocket instances
    and manages associated Redis subscription tasks.
    """
    def __init__(self):
        # Dictionary storing connection pairs: {client_id: WebSocket}
        self.active_connections = {}
        # Dictionary storing background listener tasks: {client_id: asyncio.Task}
        self.pubsub_tasks = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Accepts a new client connection, performs handshake validation, and registers it
        along with a background Redis Pub/Sub subscription task.
        """
        logger.info(f"WebSocket client attempting to connect. Client ID: {client_id}")
        await websocket.accept()  # Establish WebSocket protocol handshake
        self.active_connections[client_id] = websocket  # Register connection mapping
        
        # Start a Redis Pub/Sub subscription listener for this specific client
        redis_client = get_redis_client()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"chat:{client_id}:events")
        
        async def redis_listener():
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            # Forward incoming message directly to client
                            data = json.loads(message["data"])
                            await websocket.send_json(data)
                        except Exception as send_err:
                            logger.error(f"Error forwarding Redis msg to client {client_id}: {send_err}")
            except asyncio.CancelledError:
                pass
            finally:
                await pubsub.unsubscribe(f"chat:{client_id}:events")
                await pubsub.close()
                await redis_client.aclose()

        self.pubsub_tasks[client_id] = asyncio.create_task(redis_listener())
        logger.info(f"WebSocket connection accepted and registered for client ID: {client_id}. Redis listener started.")

    def disconnect(self, client_id: str):
        """
        Deregisters a disconnected client ID and cancels its Redis listener.
        """
        logger.info(f"WebSocket client disconnecting. Client ID: {client_id}")
        # Clean up dictionary entries
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        task = self.pubsub_tasks.pop(client_id, None)
        if task:
            task.cancel()
            logger.info(f"WebSocket connection deregistered and Redis listener stopped for client ID: {client_id}")

    async def send_json(self, message: dict, client_id: str):
        """
        Pushes a JSON message to a client channel via Redis Pub/Sub.
        """
        redis_client = get_redis_client()
        try:
            await redis_client.publish(f"chat:{client_id}:events", json.dumps(message))
        finally:
            await redis_client.aclose()

# Instantiate global singleton connection manager
agent_connection_manager = AgentConnectionManager()


class UploadStatusManager:
    """
    Manages WebSocket listeners for real-time document upload progress updates.
    Maps session keys to lists of active WebSocket connections and runs a Redis listener per session.
    """
    def __init__(self):
        # Dictionary storing connection pairs: {session_key: [WebSocket, ...]}
        self.connections = {}
        # Dictionary storing background listener tasks: {session_key: asyncio.Task}
        self.pubsub_tasks = {}

    async def connect(self, websocket: WebSocket, session_key: str):
        """
        Accepts and adds a WebSocket connection to the listeners list for a session.
        Spawns a Redis listener task if it is the first connection for this session key.
        """
        logger.info(f"Upload WebSocket client attempting to connect. Session Key: {session_key}")
        await websocket.accept()  # Accept connection
        if session_key not in self.connections:
            self.connections[session_key] = []
        self.connections[session_key].append(websocket)  # Register connection mapping
        
        # Spawn subscription task if it is the first client listening to this session
        if session_key not in self.pubsub_tasks:
            redis_client = get_redis_client()
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"upload:{session_key}:events")
            
            async def redis_listener():
                try:
                    async for message in pubsub.listen():
                        if message["type"] == "message":
                            data = json.loads(message["data"])
                            sockets = self.connections.get(session_key, [])
                            disconnected_sockets = []
                            for ws in sockets:
                                try:
                                    await ws.send_json(data)
                                except Exception as e:
                                    logger.error(f"Error dispatching status to socket in session {session_key}: {str(e)}")
                                    disconnected_sockets.append(ws)
                            # Remove disconnected sockets
                            for ws in disconnected_sockets:
                                self.disconnect(ws, session_key)
                except asyncio.CancelledError:
                    pass
                finally:
                    await pubsub.unsubscribe(f"upload:{session_key}:events")
                    await pubsub.close()
                    await redis_client.aclose()
                    
            self.pubsub_tasks[session_key] = asyncio.create_task(redis_listener())
            
        logger.info(f"Upload WebSocket connection accepted. Registered for Session: {session_key}.")

    def disconnect(self, websocket: WebSocket, session_key: str):
        """
        Removes a WebSocket connection from a session's listeners list.
        Cancels the Redis listener task if no more local clients are connected to this key.
        """
        logger.info(f"Upload WebSocket disconnecting. Session Key: {session_key}")
        if session_key in self.connections:
            if websocket in self.connections[session_key]:
                self.connections[session_key].remove(websocket)  # Remove socket from list
                logger.debug(f"WebSocket removed from upload list for session {session_key}.")
            # Clean up empty dictionary entries
            if not self.connections[session_key]:
                del self.connections[session_key]
                task = self.pubsub_tasks.pop(session_key, None)
                if task:
                    task.cancel()
                logger.info(f"All connections closed. Purged session key registry and listener: {session_key}")

    async def send_status(self, session_key: str, status: str, filename: str, detail: str = "", progress: float = 0.0):
        """
        Broadcasts status updates to all active listeners monitoring a session key via Redis.
        """
        logger.debug(f"Broadcasting upload status update for session '{session_key}': status={status}, progress={progress}")
        redis_client = get_redis_client()
        try:
            payload = {
                "status": status,
                "filename": filename,
                "detail": detail,
                "progress": progress
            }
            await redis_client.publish(f"upload:{session_key}:events", json.dumps(payload))
        finally:
            await redis_client.aclose()

# Instantiate global singleton upload manager
upload_status_manager = UploadStatusManager()


class NotificationWebSocketManager:
    """
    Manages active WebSocket connections for global alert feeds.
    Groups connections by workspace ID to broadcast alerts via Redis Pub/Sub.
    """
    def __init__(self):
        # Dictionary storing connection pairs: {workspace_id: [WebSocket, ...]}
        self.active_connections = {}
        # Dictionary storing background listener tasks: {workspace_id: asyncio.Task}
        self.pubsub_tasks = {}

    async def connect(self, websocket: WebSocket, workspace_id: str):
        """
        Accepts and adds a WebSocket connection to the alert listeners list for a workspace.
        Spawns a Redis subscription task if it is the first listener connection.
        """
        logger.info(f"Notification WebSocket client attempting to connect. Workspace ID: {workspace_id}")
        await websocket.accept()  # Accept connection
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = []
        self.active_connections[workspace_id].append(websocket)  # Register connection mapping
        
        # Spawn subscription task if it is the first client listening to this workspace
        if workspace_id not in self.pubsub_tasks:
            redis_client = get_redis_client()
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"workspace:{workspace_id}:events")
            
            async def redis_listener():
                try:
                    async for message in pubsub.listen():
                        if message["type"] == "message":
                            data = json.loads(message["data"])
                            sockets = self.active_connections.get(workspace_id, [])
                            disconnected = []
                            for ws in sockets:
                                try:
                                    await ws.send_json(data)
                                    logger.debug(f"Workspace alert successfully dispatched to socket.")
                                except Exception as e:
                                    logger.error(f"Error dispatching workspace alert to socket: {str(e)}")
                                    disconnected.append(ws)
                            # Remove disconnected sockets
                            for ws in disconnected:
                                self.disconnect(ws, workspace_id)
                except asyncio.CancelledError:
                    pass
                finally:
                    await pubsub.unsubscribe(f"workspace:{workspace_id}:events")
                    await pubsub.close()
                    await redis_client.aclose()
                    
            self.pubsub_tasks[workspace_id] = asyncio.create_task(redis_listener())
            
        logger.info(f"Notification WebSocket accepted. Registered for Workspace: {workspace_id}.")

    def disconnect(self, websocket: WebSocket, workspace_id: str):
        """
        Removes a WebSocket connection from a workspace's listeners list.
        Cancels the Redis task when the last connection for a workspace drops.
        """
        logger.info(f"Notification WebSocket disconnecting. Workspace ID: {workspace_id}")
        if workspace_id in self.active_connections:
            if websocket in self.active_connections[workspace_id]:
                self.active_connections[workspace_id].remove(websocket)  # Remove socket from list
                logger.debug(f"WebSocket removed from workspace alert list: {workspace_id}")
            # Clean up empty dictionary entries
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]
                task = self.pubsub_tasks.pop(workspace_id, None)
                if task:
                    task.cancel()
                logger.info(f"All workspace alerts sockets closed. Purging workspace key registry and listener: {workspace_id}")

    async def broadcast(self, workspace_id: str, notification: dict):
        """
        Broadcasts a workspace notification alert to all active listeners in a workspace via Redis.
        """
        logger.info(f"Broadcasting workspace notification alert to workspace ID: {workspace_id}. Title: '{notification.get('title')}'")
        redis_client = get_redis_client()
        try:
            await redis_client.publish(f"workspace:{workspace_id}:events", json.dumps(notification))
        finally:
            await redis_client.aclose()

# Instantiate global singleton notification manager
notification_manager = NotificationWebSocketManager()
