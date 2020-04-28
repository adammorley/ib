class Quote:
    symbol: str
    current: float
    high: float
    low: float
    open_: float
    previousClose: float
    timestamp: int

    def __init__(self, s, c, h, l , o, pc, t):
        self.symbol = s
        self.current = c
        self.high = h
        self.low = l
        self.open = o
        self.previousClose = pc
        self.timestamp = t

    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ', '.join(pieces)
