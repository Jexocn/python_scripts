balance = 139000
rate = 2.6/10000
# 2018-07-21, 2018-09-14, 2020-07-21
m = ['2018-%02d-14'% k for k in xrange(9, 13)] + ['2019-%02d-14'%k for k in xrange(1, 13)] + ['2020-%02d-14'%k for k in xrange(1,8)] + ['2020-07-21']
days = [55]+[30 for k in xrange(0, 22)]+[7]
mounts = [7276.66] + [6373.16 for k in xrange(0, 22)] + [6335.45]

for k in xrange(0, len(days)):
	r = round(balance*rate*days[k], 2)
	b = mounts[k] - r
	balance = balance - b
	print m[k], '%7.2f'%r, '%7.2f'%b, '%9.2f'%round(balance, 2), '%9.2f'%(139000-round(balance, 2))
