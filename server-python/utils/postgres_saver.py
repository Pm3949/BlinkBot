import json
from typing import Any, AsyncIterator, Iterator, Optional, Sequence, Union, List, Tuple
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
)
from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

class PostgresCheckpointSaver(BaseCheckpointSaver):
    def __init__(self, *, serde = None):
        super().__init__(serde=serde)

    def _serialize(self, obj: Any) -> bytes:
        if obj is None:
            return b""
        fmt, data = self.serde.dumps_typed(obj)
        return fmt.encode("utf-8") + b":" + data

    def _deserialize(self, blob: bytes) -> Any:
        if not blob:
            return None
        parts = bytes(blob).split(b":", 1)
        if len(parts) == 2:
            fmt = parts[0].decode("utf-8")
            data = parts[1]
            return self.serde.loads_typed((fmt, data))
        # Fallback if no colon prefix exists (for backward compatibility)
        return self.serde.loads_typed(("json", blob))

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        raise NotImplementedError("Use async aput instead.")

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        raise NotImplementedError("Use async aget_tuple instead.")

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[CheckpointMetadata] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        raise NotImplementedError("Use async alist instead.")

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        
        # Serialize checkpoint and metadata using typed wrappers
        checkpoint_bytes = self._serialize(checkpoint)
        metadata_bytes = self._serialize(metadata)
        
        parent_config = config.get("configurable", {}).get("parent_config")
        parent_checkpoint_id = parent_config.get("checkpoint_id") if parent_config else None

        async with get_db_cursor_async(commit=True) as cursor:
            await run_in_threadpool(
                cursor.execute,
                """
                INSERT INTO langgraph_checkpoints (thread_id, checkpoint_id, checkpoint, metadata, parent_checkpoint_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (thread_id, checkpoint_id)
                DO UPDATE SET checkpoint = EXCLUDED.checkpoint, metadata = EXCLUDED.metadata;
                """,
                (thread_id, checkpoint_id, checkpoint_bytes, metadata_bytes, parent_checkpoint_id)
            )
            
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        
        async with get_db_cursor_async(commit=False) as cursor:
            if checkpoint_id:
                await run_in_threadpool(
                    cursor.execute,
                    """
                    SELECT checkpoint_id, checkpoint, metadata, parent_checkpoint_id
                    FROM langgraph_checkpoints
                    WHERE thread_id = %s AND checkpoint_id = %s
                    """,
                    (thread_id, checkpoint_id)
                )
            else:
                await run_in_threadpool(
                    cursor.execute,
                    """
                    SELECT checkpoint_id, checkpoint, metadata, parent_checkpoint_id
                    FROM langgraph_checkpoints
                    WHERE thread_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (thread_id,)
                )
            row = await run_in_threadpool(cursor.fetchone)
            if not row:
                return None
                
            res_checkpoint_id, checkpoint_bytes, metadata_bytes, parent_checkpoint_id = row
            checkpoint = self._deserialize(bytes(checkpoint_bytes))
            metadata = self._deserialize(bytes(metadata_bytes)) if metadata_bytes else {}
            
            # Fetch pending writes
            await run_in_threadpool(
                cursor.execute,
                """
                SELECT task_id, channel, value
                FROM langgraph_writes
                WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                """,
                (thread_id, checkpoint_ns, res_checkpoint_id)
            )
            write_rows = await run_in_threadpool(cursor.fetchall)
            pending_writes = [
                (task_id, channel, self._deserialize(bytes(val_bytes)))
                for task_id, channel, val_bytes in write_rows
            ]

            parent_config = None
            if parent_checkpoint_id:
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=pending_writes
            )

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[CheckpointMetadata] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"] if config else None
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "") if config else ""
        
        query = "SELECT checkpoint_id, checkpoint, metadata, parent_checkpoint_id FROM langgraph_checkpoints"
        params = []
        where_clauses = []
        
        if thread_id:
            where_clauses.append("thread_id = %s")
            params.append(thread_id)
            
        if before:
            before_checkpoint_id = before["configurable"].get("checkpoint_id")
            if before_checkpoint_id:
                where_clauses.append("created_at < (SELECT created_at FROM langgraph_checkpoints WHERE thread_id = %s AND checkpoint_id = %s)")
                params.extend([thread_id, before_checkpoint_id])
                
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT %s"
            params.append(limit)
            
        async with get_db_cursor_async(commit=False) as cursor:
            await run_in_threadpool(cursor.execute, query, tuple(params))
            rows = await run_in_threadpool(cursor.fetchall)
            
            for row in rows:
                res_checkpoint_id, checkpoint_bytes, metadata_bytes, parent_checkpoint_id = row
                checkpoint = self._deserialize(bytes(checkpoint_bytes))
                metadata = self._deserialize(bytes(metadata_bytes)) if metadata_bytes else {}
                
                # Fetch pending writes
                await run_in_threadpool(
                    cursor.execute,
                    """
                    SELECT task_id, channel, value
                    FROM langgraph_writes
                    WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                    """,
                    (thread_id, checkpoint_ns, res_checkpoint_id)
                )
                write_rows = await run_in_threadpool(cursor.fetchall)
                pending_writes = [
                    (task_id, channel, self._deserialize(bytes(val_bytes)))
                    for task_id, channel, val_bytes in write_rows
                ]

                parent_config = None
                if parent_checkpoint_id:
                    parent_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_checkpoint_id,
                        }
                    }
                    
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": res_checkpoint_id,
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config,
                    pending_writes=pending_writes
                )

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")
        if not checkpoint_id:
            async with get_db_cursor_async(commit=False) as cursor:
                await run_in_threadpool(
                    cursor.execute,
                    "SELECT checkpoint_id FROM langgraph_checkpoints WHERE thread_id = %s ORDER BY created_at DESC LIMIT 1",
                    (thread_id,)
                )
                row = await run_in_threadpool(cursor.fetchone)
                if row:
                    checkpoint_id = row[0]

        async with get_db_cursor_async(commit=True) as cursor:
            for idx, (channel, value) in enumerate(writes):
                value_bytes = self._serialize(value)
                await run_in_threadpool(
                    cursor.execute,
                    """
                    INSERT INTO langgraph_writes (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, value, task_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                    DO UPDATE SET value = EXCLUDED.value;
                    """,
                    (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, value_bytes, task_path)
                )
