import asyncio
import sys
import os

# Add server-python to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import billing_repository
from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def test_wallet_and_billing_operations():
    # Setup test user UUID
    test_user_id = "00000000-0000-0000-0000-000000000000"
    
    # 1. Clean existing test data if any
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "DELETE FROM credit_transactions WHERE user_id = %s", (test_user_id,))
        await run_in_threadpool(cursor.execute, "DELETE FROM user_wallets WHERE user_id = %s", (test_user_id,))
        await run_in_threadpool(cursor.execute, "DELETE FROM public.users WHERE id = %s", (test_user_id,))
        # Insert a dummy user in public.users to satisfy foreign keys
        await run_in_threadpool(cursor.execute, "INSERT INTO public.users (id, email, password_hash) VALUES (%s, 'test_billing@blinkbot.in', 'dummy_hash') ON CONFLICT DO NOTHING", (test_user_id,))

    # 2. Get wallet details (should create/initialize the wallet with 0.0 balance)
    wallet = await billing_repository.get_wallet_details(test_user_id)
    assert wallet["credit_balance"] == 0.0
    assert wallet["auto_recharge_enabled"] is False

    # 3. Top-up wallet credits
    await billing_repository.topup_wallet_credits(test_user_id, 50.0)
    balance = await billing_repository.get_wallet_balance(test_user_id)
    assert balance == 50.0

    # 4. Deduct wallet balance atomically
    await billing_repository.deduct_wallet_balance_atomic(test_user_id, 15.5)
    balance = await billing_repository.get_wallet_balance(test_user_id)
    assert balance == 34.5

    # 5. Create credit transaction log
    await billing_repository.create_credit_transaction(
        user_id=test_user_id,
        agent_id=None,
        amount_credits=-15.5,
        transaction_type="usage_deduction",
        model_used="gemini-2.0-flash-exp",
        prompt_tokens=1000,
        completion_tokens=500
    )
    
    txs = await billing_repository.get_credit_transactions(test_user_id)
    assert len(txs) > 0
    assert txs[0]["amount_credits"] == -15.5
    assert txs[0]["model_used"] == "gemini-2.0-flash-exp"
    assert txs[0]["prompt_tokens"] == 1000
    assert txs[0]["completion_tokens"] == 500

    # Clean up test user
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "DELETE FROM credit_transactions WHERE user_id = %s", (test_user_id,))
        await run_in_threadpool(cursor.execute, "DELETE FROM user_wallets WHERE user_id = %s", (test_user_id,))
        await run_in_threadpool(cursor.execute, "DELETE FROM public.users WHERE id = %s", (test_user_id,))

if __name__ == "__main__":
    print("Running decoupled billing test suite...")
    asyncio.run(test_wallet_and_billing_operations())
    print("All decoupled billing tests passed successfully!")
