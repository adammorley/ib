#!/usr/bin/python3
import websocket

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-s','--symbol', action='append', type=str, default=None)
args = parser.parse_args()

def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    for s in args.symbol:
        r = '{"type":"subscribe","symbol":"' + s + '"}'
        ws.send(r)

websocket.enableTrace(True)
ws = websocket.WebSocketApp("wss://ws.finnhub.io?token=bqj5mj7rh5r89luqscug",
        on_message = on_message,
        on_error = on_error,
        on_close = on_close)
ws.on_open = on_open
ws.run_forever()

