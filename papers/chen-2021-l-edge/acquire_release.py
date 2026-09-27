#!/usr/bin/env python3
"""Download the exact public release and safely extract its single data member."""
import argparse
import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path
from prepare_assets import EXPECTED_SHA256, sha

def main(output):
    output.mkdir(parents=True, exist_ok=True)
    meta_path = output / 'figshare.json'
    metadata = urllib.request.urlopen('https://api.figshare.com/v2/articles/12824513/versions/1', timeout=120).read()
    meta_path.write_bytes(metadata)
    entry = json.loads(metadata)['files'][0]
    assert entry['id'] == 24332060 and entry['name'] == 'L-XAS.json.tgz'
    archive = output / entry['name']
    if not archive.exists():
        urllib.request.urlretrieve(entry['download_url'], archive)
    assert archive.stat().st_size == entry['size'] and sha(archive) == EXPECTED_SHA256
    raw = output / 'raw'
    raw.mkdir(exist_ok=True)
    with tarfile.open(archive) as tf:
        members = tf.getmembers()
        assert len(members) == 1 and members[0].name == 'L_XAS.json' and members[0].isfile()
        tf.extractall(raw, filter='data')
    print(json.dumps({'archive':str(archive),'raw':str(raw/'L_XAS.json'),'metadata':str(meta_path),'sha256':EXPECTED_SHA256}))
if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    main(p.parse_args().output)
