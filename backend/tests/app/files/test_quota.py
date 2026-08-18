from app.files.quota import _parse_storage_limit_string

def test_parse_storage_limit_string_percentage():
    assert _parse_storage_limit_string("50%") == (50.0, "%")
    assert _parse_storage_limit_string(" 100% ") == (100.0, "%")
    assert _parse_storage_limit_string("70.5%") == (70.5, "%")
    assert _parse_storage_limit_string("0%") == (None, None)
    assert _parse_storage_limit_string("101%") == (None, None)

def test_parse_storage_limit_string_bytes():
    assert _parse_storage_limit_string("10M") == (10 * 1024**2, "bytes")
    assert _parse_storage_limit_string("20MB") == (20 * 1024**2, "bytes")
    assert _parse_storage_limit_string("30MiB") == (30 * 1024**2, "bytes")
    assert _parse_storage_limit_string(" 40 G ") == (40 * 1024**3, "bytes")
    assert _parse_storage_limit_string("50GB") == (50 * 1024**3, "bytes")
    assert _parse_storage_limit_string("60GiB") == (60 * 1024**3, "bytes")
    assert _parse_storage_limit_string("70T") == (70 * 1024**4, "bytes")
    assert _parse_storage_limit_string("80TB") == (80 * 1024**4, "bytes")
    assert _parse_storage_limit_string("90TiB") == (90 * 1024**4, "bytes")
    assert _parse_storage_limit_string("0M") == (None, None)
    assert _parse_storage_limit_string("-10G") == (None, None)

def test_parse_storage_limit_string_invalid():
    assert _parse_storage_limit_string("invalid") == (None, None)
    assert _parse_storage_limit_string("10K") == (None, None)
    assert _parse_storage_limit_string("10") == (None, None)
    assert _parse_storage_limit_string("") == (70.0, "%")
    assert _parse_storage_limit_string("  ") == (70.0, "%")
