import asyncio, time, json
import main

if __name__ == '__main__':
    req = main.IngestRequest(game='pick3', force=True)
    try:
        res = asyncio.run(main.ingest_data(req))
        print('ENQUEUE_RESULT', json.dumps(res, ensure_ascii=False))
    except Exception as e:
        print('ENQUEUE_ERROR', str(e))

    game='pick3'
    for i in range(600):
        state = main.manual_ingest_state.get(game, {"status":"idle"})
        print('STATE', json.dumps(state, ensure_ascii=False))
        if state.get('status') in ('completed','error'):
            break
        time.sleep(1)
    print('MONITOR_DONE')
