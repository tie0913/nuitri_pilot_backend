import asyncio

async def with_txn(db, fn, *, max_retries=3):
    for i in range(max_retries):
        sess = await db.client.start_session()
        try:
            sess.start_transaction()
            result = await fn()
            await sess.commit_transaction()
            return result
        except Exception as e:
            if "TransientTransactionError" in str(e) and i < max_retries - 1:
                await asyncio.sleep(0.05 * (2**i))
                continue
            if sess.in_transaction:
                await sess.abort_transaction()
            raise
        finally:
            await sess.end_session()
