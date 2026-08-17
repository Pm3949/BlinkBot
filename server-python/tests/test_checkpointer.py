import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta

# Ensure server-python root is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from utils.postgres_saver import PostgresCheckpointSaver
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata

async def run_tests():
    print("🧪 Running Checkpointer & Pruning Integration Tests...")
    
    # 1. Initialize custom checkpointer
    saver = PostgresCheckpointSaver()
    thread_id = f"test_thread_{uuid.uuid4()}"
    
    # Mock configs and checkpoints
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "test_ns",
        }
    }
    
    checkpoint_1 = {
        "v": 1,
        "id": f"chk_{uuid.uuid4()}",
        "ts": datetime.utcnow().isoformat(),
        "channel_values": {"messages": ["hello"]},
        "channel_versions": {},
        "versions_seen": {},
        "pending_sends": []
    }
    
    metadata_1 = {
        "source": "input",
        "step": 0
    }
    
    print("\n[Test 1] Saving and retrieving checkpoint...")
    # Put checkpoint
    updated_config = await saver.aput(config, checkpoint_1, metadata_1, {})
    assert updated_config["configurable"]["checkpoint_id"] == checkpoint_1["id"], "Aput should return updated config with checkpoint ID"
    
    # Retrieve checkpoint
    tup = await saver.aget_tuple(updated_config)
    assert tup is not None, "Aget_tuple should retrieve the saved checkpoint"
    assert tup.checkpoint["id"] == checkpoint_1["id"], "Retrieved checkpoint ID should match"
    assert tup.checkpoint["channel_values"]["messages"] == ["hello"], "Retrieved state should match"
    print("✅ Checkpoint save and retrieve passed!")
    
    # 2. Test saving and retrieving writes
    print("\n[Test 2] Saving and retrieving pending writes...")
    writes = [("output", "how can I help you?")]
    task_id = "task_1"
    
    await saver.aput_writes(updated_config, writes, task_id)
    
    # Re-retrieve to verify writes are populated
    tup_with_writes = await saver.aget_tuple(updated_config)
    assert len(tup_with_writes.pending_writes) == 1, "Should have 1 pending write"
    assert tup_with_writes.pending_writes[0][0] == task_id, "Task ID should match"
    assert tup_with_writes.pending_writes[0][1] == "output", "Channel name should match"
    assert tup_with_writes.pending_writes[0][2] == "how can I help you?", "Written value should match"
    print("✅ Pending writes serialization passed!")
    
    # 3. Test Thread depth cap pruning (Keep Latest 5)
    print("\n[Test 3] Verifying thread-level depth cap pruning...")
    # Let's save 7 more checkpoints (total 8) on the same thread
    checkpoint_ids = [checkpoint_1["id"]]
    
    for i in range(1, 8):
        chk = {
            "v": 1,
            "id": f"chk_step_{i}_{uuid.uuid4()}",
            "ts": datetime.utcnow().isoformat(),
            "channel_values": {"messages": [f"msg_{i}"]},
            "channel_versions": {},
            "versions_seen": {},
            "pending_sends": []
        }
        await saver.aput(config, chk, {"step": i}, {})
        checkpoint_ids.append(chk["id"])
        
    # Verify we have 8 checkpoints in database for this thread
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT count(*) FROM langgraph_checkpoints WHERE thread_id = %s",
            (thread_id,)
        )
        count = (await run_in_threadpool(cursor.fetchone))[0]
        assert count == 8, f"Should have exactly 8 checkpoints, found {count}"

    # Run the Depth Cap pruning queries
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            DELETE FROM langgraph_writes
            WHERE thread_id = %s AND checkpoint_id NOT IN (
                SELECT checkpoint_id
                FROM langgraph_checkpoints
                WHERE thread_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            );
            """,
            (thread_id, thread_id)
        )
        await run_in_threadpool(
            cursor.execute,
            """
            DELETE FROM langgraph_checkpoints
            WHERE thread_id = %s AND checkpoint_id NOT IN (
                SELECT checkpoint_id
                FROM langgraph_checkpoints
                WHERE thread_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            );
            """,
            (thread_id, thread_id)
        )
        
    # Verify that exactly 5 checkpoints are left
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT count(*) FROM langgraph_checkpoints WHERE thread_id = %s",
            (thread_id,)
        )
        count_after = (await run_in_threadpool(cursor.fetchone))[0]
        assert count_after == 5, f"Should have pruned to 5 checkpoints, found {count_after}"
        
        # Verify they are the latest 5 (i.e. steps 3, 4, 5, 6, 7)
        await run_in_threadpool(
            cursor.execute,
            "SELECT checkpoint_id FROM langgraph_checkpoints WHERE thread_id = %s ORDER BY created_at DESC",
            (thread_id,)
        )
        remaining_ids = [r[0] for r in (await run_in_threadpool(cursor.fetchall))]
        expected_ids = list(reversed(checkpoint_ids[-5:]))
        assert remaining_ids == expected_ids, "Pruned checkpoints should be the most recent 5 ones"
        
    print("✅ Depth cap pruning logic successfully verified!")
    
    # 4. Test Global TTL Cleanup
    print("\n[Test 4] Verifying global time-to-live cleanups...")
    old_thread_id = f"old_thread_{uuid.uuid4()}"
    old_checkpoint_id = f"chk_old_{uuid.uuid4()}"
    
    # Create an old checkpoint and write by modifying its created_at timestamp
    async with get_db_cursor_async(commit=True) as cursor:
        checkpoint_bytes = saver._serialize(checkpoint_1)
        metadata_bytes = saver._serialize(metadata_1)
        
        # Insert checkpoint backdated by 4 days
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO langgraph_checkpoints (thread_id, checkpoint_id, checkpoint, metadata, created_at)
            VALUES (%s, %s, %s, %s, NOW() - INTERVAL '4 days')
            """,
            (old_thread_id, old_checkpoint_id, checkpoint_bytes, metadata_bytes)
        )
        
        # Insert write backdated by 4 days
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO langgraph_writes (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, value, created_at)
            VALUES (%s, 'test_ns', %s, 'task_old', 0, 'output', %s, NOW() - INTERVAL '4 days')
            """,
            (old_thread_id, old_checkpoint_id, checkpoint_bytes)
        )
        
    # Verify the backdated data exists
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT count(*) FROM langgraph_checkpoints WHERE thread_id = %s",
            (old_thread_id,)
        )
        old_count = (await run_in_threadpool(cursor.fetchone))[0]
        assert old_count == 1, "Old checkpoint should be present before cleanup"
        
    # Execute global cleanup queries (same as main.py daily cron)
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM langgraph_writes WHERE created_at < NOW() - INTERVAL '3 days'"
        )
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM langgraph_checkpoints WHERE created_at < NOW() - INTERVAL '3 days'"
        )
        
    # Verify the backdated data is gone
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT count(*) FROM langgraph_checkpoints WHERE thread_id = %s",
            (old_thread_id,)
        )
        old_count_after = (await run_in_threadpool(cursor.fetchone))[0]
        assert old_count_after == 0, "Old checkpoint should be deleted after global TTL cleanup"
        
        await run_in_threadpool(
            cursor.execute,
            "SELECT count(*) FROM langgraph_writes WHERE thread_id = %s",
            (old_thread_id,)
        )
        old_writes_after = (await run_in_threadpool(cursor.fetchone))[0]
        assert old_writes_after == 0, "Old writes should be deleted after global TTL cleanup"
        
    print("✅ Global TTL cleanup logic successfully verified!")
    
    print("\n🎉 All integration tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())
