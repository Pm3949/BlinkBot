"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script contains WebSocket connection managers that power all real-time bidirectional
communications in RAGMate.

From top to bottom, the file defines three distinct connection manager classes and
instantiates global singleton instances for each:
1. `AgentConnectionManager` (Instantiated as `agent_connection_manager`):
   - Manages real-time WebSocket connections for the main chat interface.
   - Maps unique `client_id` parameters directly to their open socket connections.
2. `UploadStatusManager` (Instantiated as `upload_status_manager`):
   - Manages connections for document upload and vectorization progress updates.
   - Groups lists of open listener socket channels under shared `session_key` parameters.
3. `NotificationWebSocketManager` (Instantiated as `notification_manager`):
   - Manages dashboard alert feeds.
   - Groups lists of listener socket channels under shared `workspace_id` parameters
     to broadcast real-time event updates to all logged-in teammates.
"""

from fastapi import WebSocket  # Import standard FastAPI WebSocket protocols

# Logging utilities
from utils.logger import get_department_logger

# Set up department logger specifically scoped to "websocket" events
logger = get_department_logger("websocket")

class AgentConnectionManager:
    """
    Manages active WebSocket connections for the interactive agent chat console.
    Maps connection client IDs directly to their corresponding open WebSocket instances.
    """
    def __init__(self):
        # Dictionary storing connection pairs: {client_id: WebSocket}
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Accepts a new client connection, handshake validation, and registers it.

        Parameters:
            websocket (WebSocket): The raw FastAPI WebSocket connection context.
            client_id (str): The unique tracking ID associated with the client.

        Returns:
            None: Modifies active connections dictionary in-place.
        """
        logger.info(f"WebSocket client attempting to connect. Client ID: {client_id}")
        await websocket.accept()  # Establish WebSocket protocol handshake
        self.active_connections[client_id] = websocket  # Register connection mapping
        logger.info(f"WebSocket connection accepted and registered for client ID: {client_id}. Active connections count: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        """
        Deregisters a disconnected client ID.

        Parameters:
            client_id (str): The unique client ID to remove.

        Returns:
            None: Modifies active connections dictionary in-place.
        """
        logger.info(f"WebSocket client disconnecting. Client ID: {client_id}")
        # Clean up dictionary entries
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket connection deregistered for client ID: {client_id}. Remaining active connections count: {len(self.active_connections)}")
        else:
            logger.warning(f"Disconnect requested for unregistered client ID: {client_id}")

    async def send_json(self, message: dict, client_id: str):
        """
        Pushes a JSON message to a connected client ID.
        If transmission fails, automatically disconnects the client.

        Parameters:
            message (dict): JSON-serializable message payload dictionary.
            client_id (str): The target client ID.

        Returns:
            None: Pushes socket payload.
        """
        if client_id in self.active_connections:
            try:
                # Transmit payload async
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                # Catch communication failures, log details, and clean up connection entries
                logger.error(f"Failed to send JSON message to client {client_id}: {str(e)}", exc_info=True)
                self.disconnect(client_id)
        else:
            logger.warning(f"Failed to send message: Client ID {client_id} is not connected.")

# Instantiate global singleton connection manager
agent_connection_manager = AgentConnectionManager()


class UploadStatusManager:
    """
    Manages WebSocket listeners for real-time document upload progress updates.
    Maps session keys to lists of active WebSocket connections.
    """
    def __init__(self):
        # Dictionary storing connection pairs: {session_key: [WebSocket, ...]}
        self.connections = {}

    async def connect(self, websocket: WebSocket, session_key: str):
        """
        Accepts and adds a WebSocket connection to the listeners list for a session.

        Parameters:
            websocket (WebSocket): The incoming socket context.
            session_key (str): The document/agent session key to monitor.

        Returns:
            None: Modifies connections dictionary in-place.
        """
        logger.info(f"Upload WebSocket client attempting to connect. Session Key: {session_key}")
        await websocket.accept()  # Accept connection
        if session_key not in self.connections:
            self.connections[session_key] = []
        self.connections[session_key].append(websocket)  # Register connection mapping
        logger.info(f"Upload WebSocket connection accepted. Registered for Session: {session_key}. Sockets count: {len(self.connections[session_key])}")

    def disconnect(self, websocket: WebSocket, session_key: str):
        """
        Removes a WebSocket connection from a session's listeners list.

        Parameters:
            websocket (WebSocket): The socket context to remove.
            session_key (str): The session key mapped to the connection.

        Returns:
            None: Modifies connections dictionary in-place.
        """
        logger.info(f"Upload WebSocket disconnecting. Session Key: {session_key}")
        if session_key in self.connections:
            if websocket in self.connections[session_key]:
                self.connections[session_key].remove(websocket)  # Remove socket from list
                logger.debug(f"WebSocket removed from upload list for session {session_key}.")
            # Clean up empty dictionary entries
            if not self.connections[session_key]:
                del self.connections[session_key]
                logger.info(f"All connections closed. Purged session key registry: {session_key}")
        else:
            logger.warning(f"Disconnect requested for unregistered upload session key: {session_key}")

    async def send_status(self, session_key: str, status: str, filename: str, detail: str = "", progress: float = 0.0):
        """
        Broadcasts status updates to all active listeners monitoring a session key.

        Parameters:
            session_key (str): The target session identifier.
            status (str): Current execution state (e.g., 'processing', 'completed', 'failed').
            filename (str): Name of the file being processed.
            detail (str, optional): Explanatory status text detail details.
            progress (float, optional): Ingestion progress percentage (0.0 to 1.0).

        Returns:
            None: Sends socket payloads.
        """
        logger.debug(f"Broadcasting upload status update for session '{session_key}': status={status}, progress={progress}")
        if session_key in self.connections:
            disconnected_sockets = []
            # Broadcast updates to all listeners
            for ws in self.connections[session_key]:
                try:
                    await ws.send_json({
                        "status": status,
                        "filename": filename,
                        "detail": detail,
                        "progress": progress
                    })
                except Exception as e:
                    # Catch failures and add to clean up list
                    logger.error(f"Error dispatching status to socket in session {session_key}: {str(e)}")
                    disconnected_sockets.append(ws)
            # Remove disconnected sockets
            for ws in disconnected_sockets:
                self.disconnect(ws, session_key)
        else:
            logger.debug(f"No active WebSocket clients listening to status for session: {session_key}")

# Instantiate global singleton upload manager
upload_status_manager = UploadStatusManager()


class NotificationWebSocketManager:
    """
    Manages active WebSocket connections for global alert feeds.
    Groups connections by workspace ID to broadcast alerts to all workspace members.
    """
    def __init__(self):
        # Dictionary storing connection pairs: {workspace_id: [WebSocket, ...]}
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, workspace_id: str):
        """
        Accepts and adds a WebSocket connection to the alert listeners list for a workspace.

        Parameters:
            websocket (WebSocket): The incoming socket context.
            workspace_id (str): The unique target workspace ID.

        Returns:
            None: Modifies active connections dictionary in-place.
        """
        logger.info(f"Notification WebSocket client attempting to connect. Workspace ID: {workspace_id}")
        await websocket.accept()  # Accept connection
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = []
        self.active_connections[workspace_id].append(websocket)  # Register connection mapping
        logger.info(f"Notification WebSocket accepted. Registered for Workspace: {workspace_id}. Sockets count: {len(self.active_connections[workspace_id])}")

    def disconnect(self, websocket: WebSocket, workspace_id: str):
        """
        Removes a WebSocket connection from a workspace's listeners list.

        Parameters:
            websocket (WebSocket): The socket context to remove.
            workspace_id (str): The workspace ID mapped to the connection.

        Returns:
            None: Modifies active connections dictionary in-place.
        """
        logger.info(f"Notification WebSocket disconnecting. Workspace ID: {workspace_id}")
        if workspace_id in self.active_connections:
            if websocket in self.active_connections[workspace_id]:
                self.active_connections[workspace_id].remove(websocket)  # Remove socket from list
                logger.debug(f"WebSocket removed from workspace alert list: {workspace_id}")
            # Clean up empty dictionary entries
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]
                logger.info(f"All workspace alerts sockets closed. Purging workspace key registry: {workspace_id}")
        else:
            logger.warning(f"Disconnect requested for unregistered notification workspace ID: {workspace_id}")

    async def broadcast(self, workspace_id: str, notification: dict):
        """
        Broadcasts a workspace notification alert to all active listeners in a workspace.

        Parameters:
            workspace_id (str): The target workspace ID.
            notification (dict): JSON-serializable alert details.

        Returns:
            None: Broadcasts socket payloads.
        """
        logger.info(f"Broadcasting workspace notification alert to workspace ID: {workspace_id}. Title: '{notification.get('title')}'")
        if workspace_id in self.active_connections:
            disconnected = []
            # Broadcast updates to all listeners
            for ws in self.active_connections[workspace_id]:
                try:
                    await ws.send_json(notification)
                    logger.debug(f"Workspace alert successfully dispatched to socket.")
                except Exception as e:
                    # Catch failures and add to clean up list
                    logger.error(f"Error dispatching workspace alert to socket: {str(e)}")
                    disconnected.append(ws)
            # Remove disconnected sockets
            for ws in disconnected:
                self.disconnect(ws, workspace_id)
        else:
            logger.debug(f"No active WebSocket connections registered to receive alerts for workspace: {workspace_id}")

# Instantiate global singleton notification manager
notification_manager = NotificationWebSocketManager()
