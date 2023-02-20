#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2023/2/17 17::41
Desc: 计算A股股票持有N年的收益情况
"""

import akshare as ak
import pandas as pd
import datetime
import re
import math
import dateutil.parser
import sys
import time
import os
import random

# 注意：
# ak.stock_history_dividend_detail 获取的数据是按时间降序排列的

def hist_date_to_date(hist_date):
	return dateutil.parser.parse(str(hist_date)).date()

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
		for i in range(len(dividend_detail_df)-1, -1, -1):
			row = dividend_detail_df.loc[i]
			cqcx_date = row['除权除息日']
			if pd.notna(cqcx_date):
				if(cqcx_date > end_date):
					break
				if(cqcx_date > init_date):
					init_price = round((init_price - row['派息'])/(1+(row['送股'] + row['转增'])/10), 2)
	return init_price

def gen_year_dividend_detail(dividend_detail_df, begin_year, end_year):
	year_dividend_detail = {}
	for i in range(len(dividend_detail_df)-1, -1, -1):
		row = dividend_detail_df.loc[i]
		cqcx_date = row['除权除息日']
		if(pd.notna(cqcx_date) and cqcx_date.year >= begin_year and cqcx_date.year <= end_year):
			if(cqcx_date.year in year_dividend_detail):
				year_dividend_detail[cqcx_date.year].append(row)
			else:
				year_dividend_detail[cqcx_date.year] = [row]
	return year_dividend_detail

def fetch_stock_dfs(symbol, begin_year, end_year):
	dividend_detail_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="分红")
	start_date = '%d0101' % (begin_year)
	end_date = '%d1231' % (end_year)
	hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
	return dividend_detail_df, hist_df

def cal_stock_gains(symbol, begin_year, end_year, init_amount=10000, dividend_detail_df=None, hist_df=None):
	init_hist = get_init_hist(symbol, begin_year)
	columns = ['10送x', '10派y', '10转z', '不复权收盘价', '送转股数', '红利', '红利累计', '总持股数量', '总持股市值']
	idx_years = [year for year in range(begin_year-1, end_year+1)]
	if dividend_detail_df is None:
		dividend_detail_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="分红")
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
	if hist_df is None:
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
		data[idx][4] = round((data[idx][0] + data[idx][2])/10*amount)
		data[idx][7] = amount + data[idx][4]
		data[idx][5] = round(data[idx][1]/10*amount, 2)
		data[idx][6] = data[idx-1][6] + data[idx][5]
		data[idx][8] = data[idx][7]*data[idx][3]
	df = pd.DataFrame(data, index=idx_years, columns=columns)
	return df

def cal_dividend_inc_amount(dividend_detail_df, hist_df, begin_year, end_year, init_amount, fee_rate=0.0005, min_fee=5):
	dd_idx = -1
	dd_row = None
	cqcx_date = None
	dividend_detail_df.insert(dividend_detail_df.shape[1], 'px', 0)
	dividend_detail_df.insert(dividend_detail_df.shape[1], 'px_inc', 0)
	dividend_detail_df.insert(dividend_detail_df.shape[1], 'px_remain', 0)
	for i in range(len(dividend_detail_df)-1, -1, -1):
		dd_row = dividend_detail_df.loc[i]
		cqcx_date = dd_row['除权除息日']
		if pd.notna(cqcx_date) and cqcx_date.year >= begin_year:
			dd_idx = i
			break
	if dd_idx == -1:
		return
	amount = init_amount
	px_remain = 0
	for i in range(0, len(hist_df)):
		row = hist_df.loc[i]
		hist_date = hist_date_to_date(row['日期'])
		if hist_date >= cqcx_date and (not (row['最高'] - row['最低'] < 0.00001 and row['涨跌幅'] > 4)):	# 是否涨停
			price = row['收盘']
			while pd.isna(cqcx_date) or cqcx_date <= hist_date:
				if pd.notna(cqcx_date):
					px = round(amount*dd_row['派息']/10, 2)
					total_px = px + px_remain
					sz_inc = round(amount*(dd_row['送股'] + dd_row['转增'])/10)
					inc = math.floor(total_px/(price*100))*100
					total_price = inc*price
					fee = max(round(total_price*fee_rate, 2), min_fee)
					px_remain = total_px - inc*price - fee
					while px_remain < 0:
						inc -= 100
						total_price = inc*price
						fee = max(round(total_price*fee_rate, 2), min_fee)
						px_remain = total_px - total_price - fee
					amount += inc + sz_inc
					dividend_detail_df.loc[dd_idx, 'px'] = px
					dividend_detail_df.loc[dd_idx, 'px_inc'] = inc
					dividend_detail_df.loc[dd_idx, 'px_remain'] = px_remain
				dd_idx -= 1
				if dd_idx < 0:
					break
				dd_row = dividend_detail_df.loc[dd_idx]
				cqcx_date = dd_row['除权除息日']
			if dd_idx < 0 or (pd.notna(cqcx_date) and cqcx_date.year > end_year):
				break
		if hist_date.year > end_year:
			break
	while dd_idx > 0 and (pd.isna(cqcx_date) or cqcx_date.year <= end_year):
		px = amount*dd_row['派息']
		px_remain += px
		dividend_detail_df.loc[dd_idx, 'px'] = px
		dividend_detail_df.loc[dd_idx, 'px_remain'] = px_remain
		dd_idx -= 1
		if dd_idx < 0:
			break
		dd_row = dividend_detail_df.loc[dd_idx]
		cqcx_date = dd_row['除权除息日']

def cal_stock_gains_riod(symbol, begin_year, end_year, init_amount=10000, dividend_detail_df=None, hist_df=None, fee_rate=0.0005, min_fee=5):
	init_hist = get_init_hist(symbol, begin_year)
	columns = ['10送x', '10派y', '10转z', '不复权收盘价', '送转股数', '红利', '复投股数', '剩余红利', '总持股数量', '总持股市值']
	idx_years = [year for year in range(begin_year-1, end_year+1)]
	if dividend_detail_df is None:
		dividend_detail_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="分红")
	init_price = cal_init_price(begin_year, init_hist, dividend_detail_df)
	data = [[0, 0, 0, init_price, 0, 0, 0, 0, init_amount, init_amount*init_price]] + [[0 for i in range(0, len(columns))] for k in range(0, len(idx_years)-1)]
	if hist_df is None:
		start_date = '%d0101' % (begin_year)
		end_date = '%d1231' % (end_year)
		hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
	cal_dividend_inc_amount(dividend_detail_df, hist_df, begin_year, end_year, init_amount, fee_rate, min_fee)
	year_dividend_detail = gen_year_dividend_detail(dividend_detail_df, begin_year, end_year)
	# 历年分红
	for year in range(begin_year, end_year+1):
		idx = year - begin_year + 1
		if(year in year_dividend_detail):
			for row in year_dividend_detail[year]:
				data[idx][0] += row['送股']
				data[idx][1] += row['派息']
				data[idx][2] += row['转增']
				data[idx][5] += row['px']
				data[idx][6] += row['px_inc']
				data[idx][7] = row['px_remain']
		else:
			data[idx][7] = data[idx-1][7]
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
		amount = data[idx-1][8]
		data[idx][4] = round((data[idx][0] + data[idx][2])/10*amount)
		data[idx][8] = amount + data[idx][4] + data[idx][6]
		data[idx][9] = data[idx][8]*data[idx][3]
	df = pd.DataFrame(data, index=idx_years, columns=columns)
	return df

def stock_gains_to_xlsx(symbol, begin_year, end_year, init_amount=10000, fee_rate=0.0005, min_fee=5, save_dir='./stock_gains/'):
	info_em_df = ak.stock_individual_info_em(symbol=symbol)
	if len(info_em_df) == 0:
		print('股票代码 {0} 不存在'.format(symbol))
		return
	ss_date = info_em_df.loc[info_em_df['item'] == '上市时间'].iloc[0]['value']
	stock_name = info_em_df.loc[info_em_df['item'] == '股票简称'].iloc[0]['value']
	if not ss_date is datetime.date:
		ss_date = hist_date_to_date(ss_date)
	if ss_date.year >= begin_year:
		print('{0} {1} 上市时间为 {2} 晚于 {3}-12-31，不处理'.format(symbol, stock_name, ss_date, begin_year-1))
		return
	if stock_name.upper().find('ST') != -1:
		print('{0} {1} ST股不处理'.format(symbol, stock_name, ss_date, begin_year-1))
		return
	dividend_detail_df, hist_df = fetch_stock_dfs(symbol, begin_year, end_year)
	gains_df = cal_stock_gains(symbol, begin_year, end_year, init_amount, dividend_detail_df, hist_df)
	gains_roid_df = cal_stock_gains_riod(symbol, begin_year, end_year, init_amount, dividend_detail_df, hist_df, fee_rate, min_fee)
	if not os.path.exists(save_dir):
		os.makedirs(save_dir)
	with pd.ExcelWriter('{0}{1}-{2}.xlsx'.format(save_dir, symbol, stock_name)) as xw:
		gains_df.to_excel(xw, sheet_name='红利不复投')
		gains_roid_df.to_excel(xw, sheet_name='红利复投')
	print('{0} {1} 保存成功'.format(symbol, stock_name))

def all_stocks_gains_to_xlsx(begin_year, end_year, init_amount=10000, fee_rate=0.0005, min_fee=5, save_dir='./stock_gains/'):
	print('获取沪A股票列表...')
	sh_stocks_df = ak.stock_sh_a_spot_em()
	print('获取沪A股票列表 完成')
	print('获取深A股票列表...')
	sz_stocks_df = ak.stock_sz_a_spot_em()
	print('获取深A股票列表 完成')
	stock_count = len(sh_stocks_df) + len(sz_stocks_df)
	print('计算保存沪A股票...')
	p50 = max(len(sh_stocks_df)//50, 2)
	for i in range(0, len(sh_stocks_df)):
		symbol = sh_stocks_df.loc[i]['代码']
		try:
			stock_gains_to_xlsx(symbol, begin_year, end_year, init_amount, fee_rate, min_fee, save_dir)
		except e:
			print('股票代码：{0} 保存失败'.format(symbol))
		finally:
			print("\r", end="")
			print("进度: {0}/{1}: ".format(i+1, len(sh_stocks_df)), "▋" * (i // p50), end="")
			sys.stdout.flush()
		time.sleep(random.random()*10)
	print('计算保存沪A股票 完成')
	print('计算保存深A股票...')
	p50 = max(len(sz_stocks_df)//50, 2)
	for i in range(0, len(sz_stocks_df)):
		symbol = sh_stocks_df.loc[i]['代码']
		try:
			stock_gains_to_xlsx(symbol, begin_year, end_year, init_amount, fee_rate, min_fee, save_dir)			
		except e:
			print('股票代码： {0} 保存失败'.format(symbol))
		finally:
			print("\r", end="")
			print("进度: {0}/{1}: ".format(i+1, len(sh_stocks_df)), "▋" * (i // p50), end="")
			sys.stdout.flush()
		time.sleep(random.random()*10)
	print('计算保存深A股票 完成')

if __name__ == '__main__':
	# dividend_detail_df, hist_df = fetch_stock_dfs('600309', 2011, 2023)
	# print(cal_stock_gains_riod('600309', 2011, 2023, dividend_detail_df=dividend_detail_df, hist_df=hist_df))
	# print(cal_stock_gains('600309', 2011, 2023, dividend_detail_df=dividend_detail_df, hist_df=hist_df))
	# fetch_stocks_and_cal_gains()
	all_stocks_gains_to_xlsx(2011, 2022)
