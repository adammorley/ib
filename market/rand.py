import random
import string

def Int():
        return random.randint(1,100)

def String(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))
