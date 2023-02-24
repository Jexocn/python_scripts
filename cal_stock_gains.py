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
import stock_gains_util as util

# 注意：
# ak.stock_history_dividend_detail 获取的数据是按时间降序排列的

str_to_date = util.str_to_date
date_to_str = util.date_to_str
cell_to_number = util.cell_to_number

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
	init_date = str_to_date(init_hist['日期'])	
	end_date = datetime.date(begin_year-1, 12, 31)
	init_price = init_hist['收盘']
	if(init_date >= end_date):
		return init_price
	if(init_date < end_date):
		for i in range(len(dividend_detail_df)-1, -1, -1):
			row = dividend_detail_df.loc[i]
			cqcx_date = row['除权日']
			if pd.notna(cqcx_date):
				if(cqcx_date > end_date):
					break
				if(cqcx_date > init_date):
					init_price = round((init_price - row['派息'])/(1+(row['送股'] + row['转增'])/10), 2)
	return init_price

def fetch_stock_sina_dividents_detail_dfs(symbol, dividend_detail_df):
	ret_dfs = {}
	for i in range(0, len(dividend_detail_df)):
		row = dividend_detail_df.iloc[i]
		date = row['公告日期']
		detail_df = None
		try:
			detail_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="分红", date=date_to_str(date))
		except Exception as e:
			break
		finally:
			pass
		if not detail_df is None:
			ret_dfs[date] = detail_df
			# 不能太快获取，会被封禁
			time.sleep(2+random.random()*3)
	return ret_dfs

def fetch_stock_dfs(symbol, begin_year, end_year):
	dividend_detail_df = None
	try:
		dividend_detail_df = ak.stock_dividents_cninfo(symbol=symbol)
	except Exception as e:
		print('fetch_stock_dfs ak.stock_dividents_cninfo fail', symbol, e)
		dividend_detail_df = None
		pass
	finally:
		pass
	if dividend_detail_df is None:
		try:
			dividend_detail_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="分红")
			detail_dfs = fetch_stock_sina_dividents_detail_dfs(symbol, dividend_detail_df)
			time.sleep(2+random.random()*3)
			dividend_detail_df = util.stock_dividents_sina_to_cinfo(dividend_detail_df, detail_dfs)
		except Exception as e:
			print('fetch_stock_dfs ak.stock_history_dividend_detail fail', symbol, e)
			dividend_detail_df = None
			pass
		finally:
			pass
	rights_issue_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="配股")
	start_date = date_to_str(begin_year, '') if isinstance(begin_year, datetime.date) else '%d0101' % (begin_year)
	end_date = date_to_str(end_year, '') if isinstance(end_year, datetime.date) else '%d1231' % (end_year)
	hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
	return dividend_detail_df, hist_df, rights_issue_df

def fill_data_dividents(data, dividend_detail_df, begin_year, end_year):
	for i in range(0, len(dividend_detail_df)):
		row = dividend_detail_df.iloc[i]
		ex_date = row['除权日']
		if not isinstance(ex_date, datetime.date):
			ex_date = str_to_date(ex_date)
		if not ex_date is None and ex_date.year >= begin_year and ex_date.year <= end_year:
			idx = ex_date.year - begin_year + 1
			if pd.notna(row['送股比例']):
				data[idx][0] += row['送股比例']
			if pd.notna(row['派息比例']):
				data[idx][1] += row['派息比例']
			if pd.notna(row['转增比例']):
				data[idx][2] += row['转增比例']

def cal_stock_gains(symbol, begin_year, end_year, init_amount=10000, dividend_detail_df=None, hist_df=None, rights_issue_df=None):
	init_hist = get_init_hist(symbol, begin_year)
	columns = ['10送x', '10派y', '10转z', '不复权收盘价', '送转股数', '红利', '红利累计', '剩余现金', '总持股数量', '总持股市值', '收益率', '年化收益率']
	idx_years = [year for year in range(begin_year-1, end_year+1)]
	if dividend_detail_df is None:
		dividend_detail_df = ak.stock_dividents_cninfo(symbol=symbol)
	init_price = cal_init_price(begin_year, init_hist, dividend_detail_df)
	data = [[0, 0, 0, init_price, 0, 0, 0, 0, init_amount, init_amount*init_price, 0, 0]] + [[0 for i in range(0, len(columns))] for k in range(0, len(idx_years)-1)]
	if hist_df is None:
		start_date = '%d0101' % (begin_year)
		end_date = '%d1231' % (end_year)
		hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
	if rights_issue_df is None:
		rights_issue_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="配股")
	gains_df = util.cal_a_stock_gains(hist_df, dividend_detail_df, rights_issue_df, init_price, datetime.date(begin_year, 1, 1), datetime.date(end_year, 12, 31),
		init_amount, 0, 0)
	fill_data_dividents(data, dividend_detail_df, begin_year, end_year)
	year = begin_year
	latest_price = init_price

	def fill_data(fill_end_year):
		nonlocal year
		idx = year - begin_year + 1
		data[idx][3] = latest_price
		data[idx][6] = data[idx-1][6] + data[idx][5]
		if data[idx][7] == 0:
			data[idx][7] = data[idx-1][7]
		data[idx][11] = round(((1+data[idx][10]/100)**(1/idx)-1)*100, 2)
		year += 1
		while year < fill_end_year:
			idx = year - begin_year + 1
			data[idx][3] = data[idx-1][3]
			data[idx][6] = data[idx-1][6]
			data[idx][7] = data[idx-1][7]
			data[idx][8] = data[idx-1][8]
			data[idx][9] = data[idx-1][9]
			data[idx][10] = data[idx-1][10]
			data[idx][11] = round(((1+data[idx][10]/100)**(1/idx)-1)*100, 2)
			year += 1

	for i in range(0, len(gains_df)):
		row = gains_df.iloc[i]
		if year < row['交易日期'].year:
			fill_data(row['交易日期'].year)
		idx = year - begin_year + 1
		if row['总持仓'] > 0:
			latest_price = round(row['总市值']/row['总持仓'], 2)
		data[idx][4] += row['送股'] + row['转增']
		data[idx][5] += row['派息']
		data[idx][7] = row['现金'] + row['未到账派息']
		data[idx][8] = row['总持仓']
		data[idx][9] = row['总市值']
		data[idx][10] = row['总收益率']
	if year <= end_year:
		fill_data(end_year+1)
	df = pd.DataFrame(data, index=idx_years, columns=columns)
	return df

def cal_stock_gains_riod(symbol, begin_year, end_year, init_amount=10000, dividend_detail_df=None, hist_df=None, rights_issue_df=None, fee_rate=0.0005, min_fee=5):
	init_hist = get_init_hist(symbol, begin_year)
	columns = ['10送x', '10派y', '10转z', '不复权收盘价', '送转股数', '红利', '复投股数', '剩余现金', '总持股数量', '总持股市值', '收益率', '年化收益率']
	idx_years = [year for year in range(begin_year-1, end_year+1)]
	if dividend_detail_df is None:
		dividend_detail_df = ak.stock_dividents_cninfo(symbol=symbol)
	init_price = cal_init_price(begin_year, init_hist, dividend_detail_df)
	data = [[0, 0, 0, init_price, 0, 0, 0, 0, init_amount, init_amount*init_price, 0, 0]] + [[0 for i in range(0, len(columns))] for k in range(0, len(idx_years)-1)]
	if hist_df is None:
		start_date = '%d0101' % (begin_year)
		end_date = '%d1231' % (end_year)
		hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
	if rights_issue_df is None:
		rights_issue_df = ak.stock_history_dividend_detail(symbol=symbol, indicator="配股")
	gains_df = util.cal_a_stock_gains(hist_df, dividend_detail_df, rights_issue_df, init_price, datetime.date(begin_year, 1, 1), datetime.date(end_year, 12, 31),
		init_amount, 0, 1, fee_rate, min_fee)
	fill_data_dividents(data, dividend_detail_df, begin_year, end_year)
	year = begin_year
	latest_price = init_price

	def fill_data(fill_end_year):
		nonlocal year
		idx = year - begin_year + 1
		data[idx][3] = latest_price
		if data[idx][7] == 0:
			data[idx][7] = data[idx-1][7]
		data[idx][11] = round(((1+data[idx][10]/100)**(1/idx)-1)*100, 2)
		year += 1
		while year < fill_end_year:
			idx = year - begin_year + 1
			data[idx][3] = data[idx-1][3]
			data[idx][7] = data[idx-1][7]
			data[idx][8] = data[idx-1][8]
			data[idx][9] = data[idx-1][9]
			data[idx][10] = data[idx-1][10]
			data[idx][11] = round(((1+data[idx][10]/100)**(1/idx)-1)*100, 2)
			year += 1

	for i in range(0, len(gains_df)):
		row = gains_df.iloc[i]
		if year < row['交易日期'].year:
			fill_data(row['交易日期'].year)
		idx = year - begin_year + 1
		if row['总持仓'] > 0:
			latest_price = round(row['总市值']/row['总持仓'], 2)
			data[idx][6] += row['买入']
		data[idx][4] += row['送股'] + row['转增']
		data[idx][5] += row['派息']
		data[idx][7] = row['现金'] + row['未到账派息']
		data[idx][8] = row['总持仓']
		data[idx][9] = row['总市值']
		data[idx][10] = row['总收益率']
	if year <= end_year:
		fill_data(end_year+1)
	df = pd.DataFrame(data, index=idx_years, columns=columns)
	return df

def stock_gains_to_xlsx(symbol, begin_year, end_year, init_amount=10000, fee_rate=0.0005, min_fee=5, save_dir='./stock_gains/', rank_df=None):
	info_em_df = ak.stock_individual_info_em(symbol=symbol)
	if len(info_em_df) == 0:
		print('股票代码 {0} 不存在'.format(symbol))
		return False
	ss_date = info_em_df.loc[info_em_df['item'] == '上市时间'].iloc[0]['value']
	stock_name = info_em_df.loc[info_em_df['item'] == '股票简称'].iloc[0]['value']
	total_value = info_em_df.loc[info_em_df['item'] == '总市值'].iloc[0]['value']
	if not isinstance(ss_date, datetime.date):
		ss_date = str_to_date(ss_date)
	if ss_date is None:
		print('{0} {1} 未上市，不处理'.format(symbol, stock_name, ss_date, begin_year-1))
		return False
	if ss_date.year >= begin_year:
		print('{0} {1} 上市时间为 {2} 晚于 {3}-12-31，不处理'.format(symbol, stock_name, ss_date, begin_year-1))
		return False
	if stock_name.upper().find('ST') != -1 or stock_name.find('退市') != -1 or re.search('^\d+(.\d+)?$', str(total_value)) is None:
		print('{0} {1} ST股、退市股不处理'.format(symbol, stock_name))
		return False
	save_fname = '{0}{1}-{2}.xlsx'.format(save_dir, symbol, stock_name)
	if os.path.exists(save_fname):
		print('{0} {1} 已处理过'.format(symbol, stock_name))
		if not rank_df is None:
			saved_dfs = pd.read_excel(save_fname, sheet_name=['红利不复投', '红利复投'])
			gains_df, gains_roid_df = saved_dfs['红利不复投'], saved_dfs['红利复投']
			rank_df.loc[len(rank_df)] = [symbol, stock_name, gains_df.iloc[len(gains_df)-1]['年化收益率'], gains_roid_df.iloc[len(gains_df)-1]['年化收益率']]
		return False
	dividend_detail_df, hist_df, rights_issue_df = fetch_stock_dfs(symbol, begin_year, end_year)
	gains_df = cal_stock_gains(symbol, begin_year, end_year, init_amount, dividend_detail_df, hist_df, rights_issue_df)
	gains_roid_df = cal_stock_gains_riod(symbol, begin_year, end_year, init_amount, dividend_detail_df, hist_df, rights_issue_df, fee_rate, min_fee)
	if not os.path.exists(save_dir):
		os.makedirs(save_dir)
	with pd.ExcelWriter('{0}{1}-{2}.xlsx'.format(save_dir, symbol, stock_name)) as xw:
		gains_df.to_excel(xw, sheet_name='红利不复投')
		gains_roid_df.to_excel(xw, sheet_name='红利复投')
	print('{0} {1} 保存成功'.format(symbol, stock_name))
	if not rank_df is None:
		rank_df.loc[len(rank_df)] = [symbol, stock_name, gains_df.iloc[len(gains_df)-1]['年化收益率'], gains_roid_df.iloc[len(gains_df)-1]['年化收益率']]
	return True

def batch_stocks_gains_to_xlsx(stocks_df, begin_year, end_year, init_amount=10000, fee_rate=0.0005, min_fee=5, save_dir='./stock_gains/', rank_df=None):
	stock_count = len(stocks_df)
	p50 = max(stock_count//50, 2)
	for i in range(0, len(stocks_df)):
		symbol = stocks_df.loc[i]['代码']
		need_sleep = 0.05
		retry = 0
		while retry < 3:
			if retry > 0:
				print('{0}秒后重试：{1}'.format(round(need_sleep, 1), retry))
				time.sleep(need_sleep)
			try:
				need_sleep = 2+random.random()*3 if stock_gains_to_xlsx(symbol, begin_year, end_year, init_amount, fee_rate, min_fee, save_dir, rank_df) else 0.05
				break
			except Exception as e:
				print('股票代码：{0} 保存失败'.format(symbol))
				print(e)
				# 出现失败要停止
				need_sleep = 5+5*random.random()
			finally:
				retry += 1
		if not rank_df is None:
			print(rank_df.sort_values(by='复投年化', ascending=False).head(10))
		print("\r", end="")
		print("进度: {0}/{1}: ".format(i+1, stock_count), "▋" * (i // p50), end="")
		sys.stdout.flush()
		time.sleep(need_sleep)

def all_stocks_gains_to_xlsx(begin_year, end_year, init_amount=10000, fee_rate=0.0005, min_fee=5, save_dir='./stock_gains/'):
	print('获取沪A股票列表...')
	sh_stocks_df = ak.stock_sh_a_spot_em()
	print('获取沪A股票列表 完成')
	print('获取深A股票列表...')
	sz_stocks_df = ak.stock_sz_a_spot_em()
	print('获取深A股票列表 完成')
	rank_df = pd.DataFrame(columns=['代码', '股票简称', '不复投年化', '复投年化'])
	print('计算保存沪A股票...')
	batch_stocks_gains_to_xlsx(sh_stocks_df, begin_year, end_year, init_amount, fee_rate, min_fee, save_dir, rank_df)
	print('计算保存沪A股票 完成')
	print('计算保存深A股票...')
	batch_stocks_gains_to_xlsx(sz_stocks_df, begin_year, end_year, init_amount, fee_rate, min_fee, save_dir, rank_df)
	print('计算保存深A股票 完成')
	with pd.ExcelWriter('{0}/收益排行.xlsx'.format(save_dir)) as xw:
		rank_df.sort_values(by='不复投年化', ascending=False).to_excel(xw, sheet_name='红利不复投')
		rank_df.sort_values(by='复投年化', ascending=False).to_excel(xw, sheet_name='红利复投')

def cal_stock_indicator_gains(symbol, begin_date=None, end_date=None):
	if not (begin_date is None or isinstance(begin_date, datetime.date)):
		begin_date = str_to_date(begin_date)
	if not (end_date is None or isinstance(end_date, datetime.date)):
		end_date = str_to_date(end_date)
	indicator_df = ak.stock_a_lg_indicator(symbol=symbol)	
	hist_begin_date = indicator_df.iloc[0]['trade_date']
	hist_end_date = indicator_df.iloc[len(indicator_df)-1]['trade_date']	
	dividend_detail_df, hist_df, rights_issue_df = fetch_stock_dfs(symbol, hist_begin_date+datetime.timedelta(days=1), hist_end_date)
	gains_df = util.cal_a_stock_gains(hist_df, dividend_detail_df, rights_issue_df, 0, hist_begin_date, hist_end_date, 0, 100000, 1)
	return util.cal_a_indicator_gains(gains_df, indicator_df, 'm1', begin_date, end_date)

def stock_indicator_gains_to_xlsx(symbol, save_dir='./stock_indicator_gains/'):
	info_em_df = ak.stock_individual_info_em(symbol=symbol)
	if len(info_em_df) == 0:
		print('股票代码 {0} 不存在'.format(symbol))
		return False
	ss_date = info_em_df.loc[info_em_df['item'] == '上市时间'].iloc[0]['value']
	stock_name = info_em_df.loc[info_em_df['item'] == '股票简称'].iloc[0]['value']
	total_value = info_em_df.loc[info_em_df['item'] == '总市值'].iloc[0]['value']
	if not isinstance(ss_date, datetime.date):
		ss_date = str_to_date(ss_date)
	if ss_date is None:
		print('{0} {1} 未上市，不处理'.format(symbol, stock_name, ss_date, begin_year-1))
		return False
	if stock_name.upper().find('ST') != -1 or stock_name.find('退市') != -1 or re.search('^\d+(.\d+)?$', str(total_value)) is None:
		print('{0} {1} ST股、退市股不处理'.format(symbol, stock_name))
		return False
	save_fname = '{0}{1}-{2}.xlsx'.format(save_dir, symbol, stock_name)
	if os.path.exists(save_fname):
		print('{0} {1} 已处理过'.format(symbol, stock_name))
		return False
	gains_df = cal_stock_indicator_gains(symbol)
	if not os.path.exists(save_dir):
		os.makedirs(save_dir)
	with pd.ExcelWriter('{0}{1}-{2}.xlsx'.format(save_dir, symbol, stock_name)) as xw:
		gains_df.to_excel(xw, sheet_name='指标收益率')
	print('{0} {1} 保存成功'.format(symbol, stock_name))
	return True

def batch_stocks_indicator_gains_to_xlsx(stocks_df, save_dir='./stock_indicator_gains/'):
	stock_count = len(stocks_df)
	p50 = max(stock_count//50, 2)
	for i in range(0, len(stocks_df)):
		symbol = stocks_df.loc[i]['代码']
		need_sleep = 0.05
		retry = 0
		while retry < 3:
			if retry > 0:
				print('{0}秒后重试：{1}'.format(round(need_sleep, 1), retry))
				time.sleep(need_sleep)
			try:
				need_sleep = 2+random.random()*3 if stock_indicator_gains_to_xlsx(symbol, save_dir) else 0.05
				break
			except Exception as e:
				print('股票代码：{0} 保存失败'.format(symbol))
				print(e)
				# 出现失败要停止
				need_sleep = 5+5*random.random()
			finally:
				retry += 1
		print("\r", end="")
		print("进度: {0}/{1}: ".format(i+1, stock_count), "▋" * (i // p50), end="")
		sys.stdout.flush()
		time.sleep(need_sleep)

def all_stocks_indicator_gains_to_xlsx(save_dir='./stock_indicator_gains/'):
	print('获取沪A股票列表...')
	sh_stocks_df = ak.stock_sh_a_spot_em()
	print('获取沪A股票列表 完成')
	print('获取深A股票列表...')
	sz_stocks_df = ak.stock_sz_a_spot_em()
	print('获取深A股票列表 完成')
	print('计算保存沪A股票...')
	batch_stocks_indicator_gains_to_xlsx(sh_stocks_df, save_dir)
	print('计算保存沪A股票 完成')
	print('计算保存深A股票...')
	batch_stocks_indicator_gains_to_xlsx(sz_stocks_df, save_dir)
	print('计算保存深A股票 完成')

if __name__ == '__main__':
	# dividend_detail_df, hist_df, rights_issue_df = fetch_stock_dfs('600309', 2011, 2023)
	# print(cal_stock_gains_riod('600309', 2011, 2023, dividend_detail_df=dividend_detail_df, hist_df=hist_df, rights_issue_df=rights_issue_df))
	# print(cal_stock_gains('600309', 2011, 2023, dividend_detail_df=dividend_detail_df, hist_df=hist_df, rights_issue_df=rights_issue_df))
	# all_stocks_gains_to_xlsx(2011, 2022)
	# print(cal_stock_indicator_gains('600309'))
	all_stocks_indicator_gains_to_xlsx()

