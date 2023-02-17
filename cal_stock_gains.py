import akshare as ak
import pandas as pd
import datetime
import re
import math

def cal_stock_gains(symbol, begin_year, end_year, init_amount=10000):
	start_date = '%d1231' % (begin_year-1)
	end_date = '%d1231' % (end_year)
	dividend_detail_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="分红")
	idx_dates = [datetime.date(begin_year-1, 12, 31)]	
	song10 = [0]
	zhuan10 = [0]
	pai10 = [0]
	last_date = idx_dates[0]
	for row in dividend_detail_df.sort_values(by='除权除息日', ascending=True).itertuples():
		cqcx_date = getattr(row, '除权除息日')
		if(cqcx_date.year >= begin_year and cqcx_date.year <= end_year):
			while(cqcx_date.year > last_date.year):
				if(idx_dates[len(idx_dates)-1] < last_date):
					idx_dates.append(last_date)
					song10.append(0)
					zhuan10.append(0)
					pai10.append(0)
				last_date = datetime.date(last_date.year+1, 12, 31)
			idx_dates.append(cqcx_date)
			song10.append(getattr(row, '送股'))
			zhuan10.append(getattr(row, '转增'))
			pai10.append(getattr(row, '派息'))
	if(datetime.date(end_year, 12, 31) not in idx_dates):
		idx_dates.append(datetime.date(end_year, 12, 31))
		song10.append(0)
		zhuan10.append(0)
		pai10.append(0)
	hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
	sp_prices = [-1 for year in idx_dates]
	idx = 1
	last_row = None
	for row in hist_df.itertuples():
		hist_date = datetime.date(*[int(i) for i in re.findall('\d+', getattr(row, '日期'))])
		if(sp_prices[0] < 0):
			idx_dates[0] = hist_date
			sp_prices[0] = getattr(row, '收盘')
		elif(hist_date >= idx_dates[idx]):
			sp_prices[idx] = getattr(row if hist_date == idx_dates[idx] else last_row, '收盘')
			if(idx == len(idx_dates) - 1):
				break
			idx += 1
		last_row = row
	while(idx < len(idx_dates) and sp_prices[idx] < 0):
		sp_prices[idx] = getattr(last_row, '收盘')
		idx += 1
	# print(sp_prices)
	amounts = []
	sz_amounts = []
	pai_amounts = []
	total_pai_amounts = []
	stock_values = []
	last_amount = init_amount
	total_pai = 0
	for idx in range(0, len(idx_dates)):
		sz_amount = 0
		pai_amount = 0
		if(song10[idx] > 0):
			sz_amount += math.floor(init_amount/10*song10[idx])
		if(zhuan10[idx] > 0):
			sz_amount += math.floor(init_amount/10*zhuan10[idx])
		if(pai10[idx] > 0):
			pai_amount = round(init_amount/10*pai10[idx], 2)
		total_pai += pai_amount
		last_amount += sz_amount
		amounts.append(last_amount)
		sz_amounts.append(sz_amount)
		pai_amounts.append(pai_amount)
		total_pai_amounts.append(total_pai)
		stock_values.append(last_amount*sp_prices[idx])
	init_value = init_amount*sp_prices[0]
	pai_rate = round(total_pai/init_value, 2)
	total_value = total_pai + last_amount*sp_prices[len(sp_prices)-1]
	value_rate = round(total_value/init_value, 2)
	data = pd.DataFrame({'10送x':song10, '10派y':pai10, '10转z':zhuan10, '不复权收盘价':sp_prices, '送转股数':sz_amounts,
		'红利':pai_amounts, '红利累计':total_pai_amounts, '总持股数量':amounts, '总持股市值':stock_values}, index=idx_dates)
	print(data)
	print(pai_rate, value_rate)


def cal_stock_gains_riod(symbol, begin_year, end_year, init_amount=10000):
	pass

if __name__ == '__main__':
	cal_stock_gains('600900', 2011, 2021)
	# cal_stock_gains('600603', 2011, 2021)
