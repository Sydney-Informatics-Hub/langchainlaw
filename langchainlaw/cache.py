from pathlib import Path


class Cache:
    def __init__(self, root):
        self.root = root

    def write(self, case_id, filename, results):
        cache_dir = Path(self.root) / Path(case_id)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / Path(filename)
        with open(cache_file, "w") as fh:
            fh.write(results)

    def read(self, case_id, filename):
        cache_file = Path(self.root) / Path(case_id) / Path(filename)
        if cache_file.is_file():
            with open(cache_file, "r") as fh:
                results = fh.read()
                return results
        else:
            return None
