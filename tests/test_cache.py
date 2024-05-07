from pathlib import Path
from langchainlaw.cache import Cache


def test_cache(tmp_path):
    """Very basic test that caches work as expected"""
    cache_dir = Path(tmp_path) / "cache"
    cache = Cache(cache_dir)
    cache.write("testA", "testB", "contents")
    contents = cache.read("testA", "testB")
    assert contents == "contents"
