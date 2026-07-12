import asyncio
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import logging

logging.basicConfig(level=logging.INFO)

async def fix_floating_agents():
    async with get_db_cursor_async(commit=True) as cursor:
        # Get all Network Managers
        await run_in_threadpool(
            cursor.execute,
            "SELECT project_id, id FROM agents WHERE name = 'Network Manager' AND project_id IS NOT NULL"
        )
        managers = await run_in_threadpool(cursor.fetchall)
        
        for project_id, manager_id in managers:
            # Update all agents in this project that have no parent and are NOT the Network Manager
            await run_in_threadpool(
                cursor.execute,
                """
                UPDATE agents 
                SET parent_agent_id = %s 
                WHERE project_id = %s 
                  AND parent_agent_id IS NULL 
                  AND id != %s
                """,
                (manager_id, project_id, manager_id)
            )
            updated_count = cursor.rowcount
            if updated_count > 0:
                print(f"Project {project_id}: Connected {updated_count} floating agents to Network Manager.")

if __name__ == "__main__":
    asyncio.run(fix_floating_agents())
