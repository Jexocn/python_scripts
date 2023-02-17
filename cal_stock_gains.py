import akshare as ak
import pandas as pd
import datetime
import re
import math
import dateutil.parser

def hist_date_to_date(hist_date):
	return dateutil.parser.parse(hist_date).date()

def date_to_hist_date(date):
	return '%d-%02d-%02d' % (date.year, date.month, date.day)

def get_init_hist(symbol, begin_year):
	# 获取起始年份前一交易日收盘价
	year = begin_year - 1
	while True:
		start_date = '%d0101' % (year)
		end_date = '%d1231' % (year)
		hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
		if(len(hist_df) > 0):
			return hist_df.loc[len(hist_df)-1]
		year -= 1
		if(year < 1984):
			break
	return None

def cal_init_price(begin_year, init_hist, dividend_detail_df):
	# 前一交易日与起始年份之间分红除权
	init_date = hist_date_to_date(init_hist['日期'])	
	end_date = datetime.date(begin_year-1, 12, 31)
	init_price = init_hist['收盘']
	if(init_date >= end_date):
		return init_price
	if(init_date < end_date):
		for i in range(0, len(dividend_detail_df)):
			row = dividend_detail_df.loc[row]
			cqcx_date = row['除权除息日']
			if(cqcx_date > end_date):
				break
			if(cqcx_date > init_date):
				init_price = round((init_price - row['派息'])/(1+(row['送股'] + row['转增'])/10), 2)
	return init_price

def gen_year_dividend_detail(dividend_detail_df, begin_year, end_year):
	year_dividend_detail = {}
	for i in range(0, len(dividend_detail_df)):
		row = dividend_detail_df.loc[i]
		cqcx_date = row['除权除息日']
		if(cqcx_date.year >= begin_year and cqcx_date.year <= end_year):
			if(cqcx_date.year in year_dividend_detail):
				year_dividend_detail[cqcx_date.year].append(row)
			else:
				year_dividend_detail[cqcx_date.year] = [row]
	return year_dividend_detail

def cal_stock_gains_(symbol, begin_year, end_year, init_amount=10000):
	init_hist = get_init_hist(symbol, begin_year)
	columns = ['10送x', '10派y', '10转z', '不复权收盘价', '送转股数', '红利', '红利累计', '总持股数量', '总持股市值']
	idx_years = [year for year in range(begin_year-1, end_year+1)]
	dividend_detail_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="分红").sort_values(by='除权除息日', ascending=True)
	init_price = cal_init_price(begin_year, init_hist, dividend_detail_df)
	data = [[0, 0, 0, init_price, 0, 0, 0, init_amount, init_amount*init_price]] + [[0 for i in range(0, len(columns))] for k in range(0, len(idx_years)-1)]
	year_dividend_detail = gen_year_dividend_detail(dividend_detail_df, begin_year, end_year)
	# 历年分红
	for year in range(begin_year, end_year+1):
		if(year in year_dividend_detail):
			idx = year - begin_year + 1
			for row in year_dividend_detail[year]:
				data[idx][0] += row['送股']
				data[idx][1] += row['派息']
				data[idx][2] += row['转增']
	start_date = '%d0101' % (begin_year)
	end_date = '%d1231' % (end_year)
	hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
	last_year_row = None
	year = begin_year
	for i in range(0, len(hist_df)):
		row = hist_df.loc[i]
		hist_date = hist_date_to_date(row['日期'])
		if(hist_date.year > year):
			idx = year-begin_year + 1
			price = 0
			price_date = None
			if last_year_row is None:
				price = data[idx-1][3]
				price_date = hist_date_to_date(last_year_row['日期'])
			else:
				price = last_year_row['收盘']
				price_date = datetime.date(year-1, 12, 31)
			# 最后一个交易日到下一年之间之间分红除权除息 TODO
			data[idx][3] = price
			year += 1
		last_year_row = row
	data[year-begin_year+1][3] = last_year_row['收盘']
	for idx in range(1, len(idx_years)):
		amount = data[idx-1][7]
		data[idx][4] = math.floor((data[idx][0] + data[idx][2])/10*amount)
		data[idx][7] = amount + data[idx][4]
		data[idx][5] = round(data[idx][1]/10*amount, 2)
		data[idx][6] = data[idx-1][6] + data[idx][5]
		data[idx][8] = data[idx][7]*data[idx][3]
	df = pd.DataFrame(data, index=idx_years, columns=columns)
	return df

def cal_stock_gains_riod(symbol, begin_year, end_year, init_amount=10000):
	pass

if __name__ == '__main__':
	print(cal_stock_gains_('600900', 2011, 2021))
