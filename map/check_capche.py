import os
import gzip
import pickle

cache_dir = "map_cache"
for file in os.listdir(cache_dir):
    if file.endswith('.gz'):
        path = os.path.join(cache_dir, file)
        try:
            with gzip.open(path, 'rb') as f:
                data = pickle.load(f)
            print(f"✓ {file}: OK - {len(data) if hasattr(data, '__len__') else '?'} records")
        except:
            print(f"✗ {file}: CORRUPTED")