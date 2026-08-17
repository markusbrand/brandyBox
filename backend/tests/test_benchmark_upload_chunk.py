import pytest
import tempfile
import os
from fastapi import Request
from unittest.mock import AsyncMock, MagicMock
from app.users.models import User

@pytest.fixture
def mock_request():
    request = AsyncMock(spec=Request)
    return request

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.email = "test@example.com"
    return user

def test_upload_chunk_benchmark(benchmark, mock_request, mock_user, monkeypatch):
    from app.files import routes

    # Mock user_base_path to return a temp directory
    temp_dir = tempfile.mkdtemp()
    upload_id = "test_upload_id"
    upload_dir = os.path.join(temp_dir, ".uploads", upload_id)
    os.makedirs(upload_dir, exist_ok=True)

    import pathlib
    monkeypatch.setattr(routes, "user_base_path", lambda email: pathlib.Path(temp_dir))

    import asyncio

    def run_upload_chunk():
        # Reset the stream generator for each run
        async def stream_generator():
            chunk_data = b"a" * 65536
            for _ in range(10):
                yield chunk_data
        mock_request.stream.return_value = stream_generator()

        return asyncio.run(routes.upload_chunk(
            request=mock_request,
            current_user=mock_user,
            upload_id=upload_id,
            index=0
        ))

    result = benchmark.pedantic(run_upload_chunk, iterations=50, rounds=10)

    assert result["index"] == 0
    assert result["size"] == 655360

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
