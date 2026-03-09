import requests
from concurrent.futures import ThreadPoolExecutor

games = ['pick3','quickdraw','take5','powerball','nylotto','pick10','cash4life','megamillions']

URL = 'http://localhost:5000/api/ingest'

def post_game(g):
    try:
        r = requests.post(URL, json={'game': g, 'force': True}, timeout=10)
        return g, r.status_code, r.text
    except Exception as e:
        return g, 'ERR', str(e)

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(post_game, g) for g in games]
        for fut in futures:
            print(fut.result())
