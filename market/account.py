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

def summaryField(ibc, account, field, usd=None):
    aSum = summary(ibc, account)
    for i in range(0, len(aSum)):
        if aSum[i][1] == field and (not usd or aSum[i][3] == 'USD'):
            return aSum[i][2]
    raise RuntimeError('problem: did not find {} in account summary: {}'.format(field, aSum))

def availableFunds(ibc, account):
    return float( summaryField(ibc, account, 'AvailableFunds', usd=True) )

def buyingPower(ibc, account):
    return float( summaryField(ibc, account, 'BuyingPower', usd=True) )

def maintMargin(ibc, account):
    return summaryField(ibc, account, 'MaintMarginReq')
