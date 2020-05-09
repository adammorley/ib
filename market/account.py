def validate(aSum, account):
    for i in range(0, len(aSum)):
        if aSum[i][0] != account:
            raise RuntimeError('problem: did not get back expected {} from account summary {}'.format(aSum[i], aSum))

def summary(ibc, account):
    ibc.sleep(0)
    aSum = ibc.accountSummary(account=account)
    ibc.sleep(0)
    validate(aSum, account)
    return aSum

def values(ibc, account):
    ibc.sleep(0)
    aVal = ibc.accountValues(account=account)
    ibc.sleep(0)
    validate(aVal, account)
    return aVal

# summmary field doesn't seem to work: https://groups.io/g/insync/topic/74075536#4662
def summaryField(ibc, account, field, usd=None):
    aSum = summary(ibc, account)
    for i in range(0, len(aSum)):
        if aSum[i][1] == field and (not usd or aSum[i][3] == 'USD'):
            return aSum[i][2]
    raise RuntimeError('problem: did not find {} in account summary: {}'.format(field, aSum))

def valuesField(ibc, account, field, usd=None):
    aVal = values(ibc, account)
    for i in range(0, len(aVal)):
        if aVal[i][1] == field and (not usd or aVal[i][3] == 'USD'):
            return aVal[i][2]
    raise RuntimeError('problem: did not find {} in account values: {}'.format(field, aVal))

def availableFunds(ibc, account):
    return float( valuesField(ibc, account, 'AvailableFunds', usd=True) )

def buyingPower(ibc, account):
    return float( valuesField(ibc, account, 'BuyingPower', usd=True) )
