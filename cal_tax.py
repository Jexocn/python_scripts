#!/usr/bin/python

max_tax_rate = 0.45
max_tax_rate_ded = 181920
tax_rate_conf = [
	[36000,0.03,0],
	[144000,0.1,2520],
	[300000,0.2,16920],
	[420000,0.25,31920],
	[660000,0.3,52920],
	[960000,0.35,85920],
]

def cal_tax(month_earns, month_deductions):
	nMonth = len(month_earns)
	rate_earn = sum(month_earns) - sum(month_deductions) - 5000*nMonth
	if rate_earn <= 0:
		return 0
	for k in xrange(0, len(tax_rate_conf)):
		conf = tax_rate_conf[k]
		if conf[0] >= rate_earn:
			return round(rate_earn*conf[1] - conf[2], 2)
	return round(rate_earn*max_tax_rate - max_tax_rate_ded, 2)

def cal_tax_month(month_earns, month_deductions):
	if len(month_earns) < 1:
		return 0
	elif len(month_earns) == 1:
		return round(cal_tax(month_earns, month_deductions), 2)
	return round(cal_tax(month_earns, month_deductions) - cal_tax(month_earns[:-1], month_deductions[:-1]), 2)

month_earns = []
month_deductions = []

taxes = [cal_tax_month(month_earns[:k+1], month_deductions[:k+1]) for k in xrange(0, len(month_earns))]
real_earns = [month_earns[k]-taxes[k] for k in xrange(0, len(month_earns))]

print taxes, sum(taxes)
print real_earns, sum(real_earns)
