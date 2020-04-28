#!/usr/bin/python3
import websocket

def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    ws.send('{"type":"subscribe","symbol":"TQQQ"}')

websocket.enableTrace(True)
ws = websocket.WebSocketApp("wss://ws.finnhub.io?token=bqj5mj7rh5r89luqscug",
        on_message = on_message,
        on_error = on_error,
        on_close = on_close)
ws.on_open = on_open
ws.run_forever()

