import asyncio
import time
import os
import tempfile
import aiofiles

def sync_write(data, temp_path):
    start = time.time()
    # writing 1GB of data piece by piece to exaggerate the effect
    with open(temp_path, "wb") as f:
        for i in range(0, len(data), 64*1024):
            chunk = data[i:i+64*1024]
            # fake more CPU/IO time
            f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
    end = time.time()
    return end - start

async def block_event_loop(data, temp_path):
    return sync_write(data, temp_path)

async def async_write(data, temp_path):
    start = time.time()
    async with aiofiles.open(temp_path, "wb") as f:
        for i in range(0, len(data), 64*1024):
            chunk = data[i:i+64*1024]
            await f.write(chunk)
            await f.flush()
            os.fsync(f.fileno()) # Note: aiofiles doesn't have an async fsync natively, but flush works for our benchmark
    end = time.time()
    return end - start

async def ping_loop(duration):
    delays = []
    start_total = time.time()
    while time.time() - start_total < duration:
        start = time.time()
        await asyncio.sleep(0.01)
        delays.append(time.time() - start - 0.01)
    if delays:
        return max(delays)
    return 0

async def main():
    # 50 MB data
    data = b"x" * (50 * 1024 * 1024)

    with tempfile.TemporaryDirectory() as d:
        sync_file = os.path.join(d, "sync.txt")
        async_file = os.path.join(d, "async.txt")

        # Test Sync
        print("Testing sync write (blocking the event loop)...")
        ping_task = asyncio.create_task(ping_loop(5.0)) # run ping task concurrently

        await asyncio.sleep(0.1)

        sync_time = await block_event_loop(data, sync_file)

        max_delay_sync = await ping_task
        print(f"Sync write took {sync_time:.2f}s. Max event loop delay: {max_delay_sync:.4f}s")

        # Test Async
        print("Testing async write (aiofiles)...")
        ping_task = asyncio.create_task(ping_loop(5.0))

        await asyncio.sleep(0.1)

        async_time = await async_write(data, async_file)
        max_delay_async = await ping_task
        print(f"Async write took {async_time:.2f}s. Max event loop delay: {max_delay_async:.4f}s")

if __name__ == "__main__":
    asyncio.run(main())
