import sys, requests
from time import sleep

if len(sys.argv) > 1:
    game = sys.argv[1]
else:
    game = 'pick3'

url = f'http://localhost:5000/api/ingest_stream?game={game}'
print('CONNECTING_TO', url, flush=True)
try:
    with requests.get(url, stream=True, timeout=300) as r:
        for line in r.iter_lines():
            if line:
                try:
                    print('LINE', line.decode('utf-8'), flush=True)
                except Exception:
                    print('LINE', line, flush=True)
            sleep(0.01)
except Exception as e:
    print('STREAM_ERROR', e, flush=True)
