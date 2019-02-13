balance = 139000
rate = 2.6/10000
# 2018-07-21, 2018-09-14, 2020-07-21
days = [55]+[30 for k in xrange(0, 22)]+[7]
mounts = [7276.66] + [6373.16 for k in xrange(0, 22)] + [6335.45]

for k in xrange(0, len(days)):
	r = round(balance*rate*days[k], 2)
	b = mounts[k] - r
	balance = balance - b
	print k+1, r, b, round(balance, 2)

