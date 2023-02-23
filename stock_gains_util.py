#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2023/2/17 17::41
Desc: 计算A股股票收益情况

akshare 升级：
pip install akshare --upgrade -i https://pypi.org/simple
"""

import pandas as pd
import datetime
import re
import math
import dateutil.parser

def str_to_date(hist_date):
	ret_date = None
	try:
		ret_date = dateutil.parser.parse(str(hist_date)).date()
	except Exception as e:
		pass
	finally:
		pass
	return ret_date

def date_to_str(date, split='-'):
	return split.join([str(date.year), '%02d' % date.month, '%02d' % date.day])

def cell_to_number(cell):
	if pd.isna(cell):
		return 0
	ret_num = 0
	try:
		ret_num = float(cell)
	except:
		pass
	finally:
		pass
	return ret_num

def cal_buy_amount(cash, price, fee_rate, min_fee):
	buy_amount = math.floor(cash/(price*100))*100
	while True:
		buy_cost = price*buy_amount
		fee = max(round(buy_cost*fee_rate,2), min_fee) if buy_cost > 0 else 0
		remain_cash = cash - buy_cost - fee
		if remain_cash >= 0:
			return buy_amount, buy_cost, fee, remain_cash
		buy_amount -= 100

def is_rights_issue_sell_date(hist_date, next_hist_date, rights_issue_df):
	if hist_date is None:
		return False
	for i in range(0, len(rights_issue_df)):
		row = rights_issue_df.iloc[i]
		record_date = row['股权登记日']
		if not isinstance(record_date, datetime.date):
			record_date = str_to_date(record_date)
		if not record_date is None:
			if hist_date == record_date or (hist_date < record_date and not next_hist_date is None and next_hist_date > record_date):
				return True
			elif hist_date > record_date:
				# rights_issue_df 是按日期倒序排列的
				return False
	return False

def stock_dividents_sina_to_cinfo(sina_dividents_df, detail_dfs=None):
	columns = ['送股比例', '转增比例', '派息比例', '股权登记日', '除权日', '派息日']
	data = []
	sina_columns = ['送股', '转增', '派息', '股权登记日', '除权除息日']
	for i in range(0, len(sina_dividents_df)):
		row = sina_dividents_df.iloc[i]
		data_row = [row[column] for column in sina_columns]
		px_date = row['除权除息日']
		if not detail_dfs is None and row['公告日期'] in detail_dfs:
			detail_df = detail_dfs[row['公告日期']]
			for j in range(0, len(detail_df)):
				detail_row = detail_df.iloc[i]
				if detail_row['item'] == '红利/配股起始日（送、转股到账日）':
					px_date = detail_row['value']
					break
		data.append(data_row + [px_date])
	return pd.DataFrame(data, columns=columns)

def cal_a_stock_gains(hist_df, dividents_df, rights_issue_df, init_price, begin_date, end_date, init_amount=10000, init_cash=0, roid=0, fee_rate=0, min_fee=0):
	'''
		计算A股个股收益
		hist_df 历史行情数据 ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20170301", end_date='20210907', adjust="")
		dividents_df 历史分红数据		ak.stock_dividents_cninfo(symbol="600009")
		rights_issue_df 历史配股数据	ak.stock_history_dividend_detail(symbol="000002", indicator="配股")
		init_price 前收盘价
		begin_date 计算起始日期
		end_date 计算截止日期
		init_amount 初始持股数量
		roid 分红复投类型 [0 = 分红不复投, 1 = 分红复投(分红实际到账日复投)]
		fee_rate 交易费率
		min_fee 最小交易费
		note: 
			分红不复投，配股处理？
			分红复投： 
				上市第一天不买入；
				交易日涨停不买入，跌停不卖出，否则按策略买入或卖出；
				账户收到分红后，下一个交易日以开盘价买入；
				如果遇到配股，不参与配股（配股登记日前收盘价卖出，除权日开盘价买入）；
	'''
	dividents_ex_right = {}	# 分红除权日
	dividents_received = {}	# 分红到账日
	for i in range(0, len(dividents_df)):
		row = dividents_df.iloc[i]
		ex_date = row['除权日']
		received_date = row['派息日']
		if not isinstance(ex_date, datetime.date):
			ex_date = str_to_date(ex_date)
		if not isinstance(received_date, datetime.date):
			received_date = str_to_date(received_date)
		if not ex_date is None:
			dividents_ex_right[ex_date] = row
		if not received_date is None:
			dividents_received[received_date] = row
	init_value = init_amount*init_price + init_cash
	columns = ['现金', '未到账派息', '总市值', '总持仓', '总收益率', '交易日期', '买入', '卖出', '转增', '送股', '派息']
	data = []
	amount = init_amount
	remain_cash = init_cash 	# 实际到账现金
	fh_cash = 0
	sell_cash = 0
	last_hist_date = begin_date - datetime.timedelta(days=1)

	# 填充无历史交易的送分红送转信息
	def fill_no_hist_data(hist_date):
		nonlocal remain_cash, fh_cash, amount, last_hist_date
		fill_end_date = hist_date - datetime.timedelta(days=1)
		fill_date = last_hist_date + datetime.timedelta(days=1)
		last_hist_date = hist_date
		while fill_date <= fill_end_date:
			sg_amount = 0
			zz_amount = 0
			fh_add_cash = 0
			has_divident = False
			if fill_date in dividents_ex_right:
				dividents_row = dividents_ex_right[fill_date]
				if pd.notna(dividents_row['送股比例']):
					sg_amount = round(amount/10*dividents_row['送股比例'])
				if pd.notna(dividents_row['转增比例']):
					zz_amount = round(amount/10*dividents_row['转增比例'])
				if pd.notna(dividents_row['派息比例']):
					fh_add_cash = round(amount/10*dividents_row['派息比例'], 2)
				if fill_date in dividents_received:
					remain_cash += fh_add_cash
				else:
					fh_cash += fh_add_cash
				has_divident = True
			elif fill_date in dividents_received:
				dividents_row = dividents_received[fill_date]
				if pd.notna(dividents_row['派息比例']):
					remain_cash += fh_cash
					fh_cash = 0
				has_divident = True
			if has_divident:
				amount += zz_amount + sg_amount
				value = 0
				if amount > 0:
					if pd.notna(row['收盘']):
						value = row['收盘']*amount
					elif i > 0:
						value = round(data[i-1][2]/data[i-1][3]*amount, 2)
					else:
						value = round(init_price*amount, 2)
				rate = round(((value+remain_cash+fh_cash)/init_value-1)*100, 2)
				data.append([remain_cash, fh_cash, value, amount, rate, fill_date, 0, 0, zz_amount, sg_amount, fh_add_cash])
			fill_date = fill_date + datetime.timedelta(days=1)

	for i in range(0, len(hist_df)):
		row = hist_df.iloc[i]
		next_row = hist_df.iloc[i+1] if i+1 < len(hist_df) else None
		hist_date = str_to_date(row['日期'])
		next_hist_date = str_to_date(next_row['日期']) if not next_row is None else None
		if hist_date >= begin_date and hist_date <= end_date:
			fill_no_hist_data(hist_date)
			if is_rights_issue_sell_date(hist_date, next_hist_date, rights_issue_df):
				sell_amount = amount
				sell_cash = row['收盘']*sell_amount
				fee = max(round(sell_cash*fee_rate, 2), min_fee)
				sell_cash -= fee
				amount = 0
				remain_cash += sell_cash
				rate = round(((remain_cash+fh_cash)/init_value-1)*100, 2)
				data.append([remain_cash, fh_cash, 0, 0, rate, hist_date, 0, sell_amount, 0, 0, 0])
				# print('配股股权登记日前卖出', hist_date, sell_amount, sell_cash, fee)
			else:
				buy_amount = 0
				if remain_cash > 0 and pd.notna(row['开盘']) and (sell_cash > 0 or roid > 0):
					# TODO: 涨停不买入、跌停不卖出
					buy_amount, buy_cost, fee, tmp_remain_cash = cal_buy_amount(remain_cash if roid > 0 or sell_cash == 0 else sell_cash,
						row['开盘'], fee_rate, min_fee)
					remain_cash -= buy_cost + fee
					if sell_cash > 0:
						# print('配股除权买入', hist_date, buy_amount, buy_cost, fee, sell_cash, remain_cash)
						sell_cash = 0
				sg_amount = 0
				zz_amount = 0
				fh_add_cash = 0
				if hist_date in dividents_ex_right:
					dividents_row = dividents_ex_right[hist_date]
					if pd.notna(dividents_row['送股比例']):
						sg_amount = round(amount/10*dividents_row['送股比例'])
					if pd.notna(dividents_row['转增比例']):
						zz_amount = round(amount/10*dividents_row['转增比例'])
					if pd.notna(dividents_row['派息比例']):
						fh_add_cash = round(amount/10*dividents_row['派息比例'], 2)
					if hist_date in dividents_received:
						remain_cash += fh_add_cash
					else:
						fh_cash += fh_add_cash
				elif hist_date in dividents_received:
					dividents_row = dividents_received[hist_date]
					if pd.notna(dividents_row['派息比例']):
						remain_cash += fh_cash
						fh_cash = 0
				amount += zz_amount + sg_amount + buy_amount
				value = 0
				if amount > 0:
					if pd.notna(row['收盘']):
						value = row['收盘']*amount
					elif i > 0:
						value = round(data[i-1][2]/data[i-1][3]*amount, 2)
					else:
						value = round(init_price*amount, 2)
				rate = round(((value+remain_cash+fh_cash)/init_value-1)*100, 2)
				data.append([remain_cash, fh_cash, value, amount, rate, hist_date, buy_amount, 0, zz_amount, sg_amount, fh_add_cash])
	return pd.DataFrame(data, columns=columns)

def next_period_begin_gen(period, day=1):
	period_mode, period_n = re.findall('^([dmy])([1-9]\d*)$', period)[0]
	period_n = int(period_n)
	day = max(min(day, 31), 1)

	def next_period_d(date):
		return date + datetime.timedelta(days=period_n)

	def fix_day(ret_date):
		if day > 1:
			tmp_date = ret_date + datetime.timedelta(days=day-1)
			ret_date = tmp_date - datetime.timedelta(days=tmp_date.day) if tmp_date.month > ret_date.month else tmp_date
		return ret_date

	def next_period_m(date):
		year = date.year + period_n//12
		month = date.month + period_n%12
		if month > 12:
			month -= 12
			year += 1
		return fix_day(datetime.date(year, month, 1))

	def next_period_y(date):
		return fix_day(datetime.date(date.year+period_n, 1, 1))

	if period_mode == 'd':
		return next_period_d
	elif period_mode == 'm':
		return next_period_m
	elif period_mode == 'y':
		return next_period_y
	return None


def cal_a_indicator_gains(gains_df, indicator_df, gain_period='m1', begin_date=None, end_date=None):
	'''
		计算A股个股区间收益率
		gains_df 个股收益, cal_a_stock_gains
		indicator_df 个股指标 ak.stock_a_lg_indicator(symbol="000001")
		range: 收益率计算区间 d30=30天 m1=1月 y1=1年
	'''
	if begin_date is None:
		begin_date = indicator_df.iloc[0]['trade_date']
	if end_date is None:
		end_date = indicator_df.iloc[len(indicator_df)-1]['trade_date']
	dot_next_period_f = next_period_begin_gen('m1')
	gain_next_period_f = next_period_begin_gen(gain_period, day=31)
	gains_idx = 0
	period_begin = begin_date
	period_end = dot_next_period_f(period_begin)
	columns = ['trade_date', 'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm', 'dv_ratio', 'dv_ttm', 'total_mv', 'gain_rate']
	data = []
	for i in range(0, len(indicator_df)):
		indicator_row = indicator_df.iloc[i]
		ind_date = indicator_row['trade_date']
		if ind_date > end_date:
			break
		if ind_date < begin_date:
			continue
		indicator_next_row = indicator_df.iloc[i+1] if i < len(indicator_df)-1 else None
		ind_next_date = indicator_next_row['trade_date'] if not indicator_next_row is None else None
		if ind_next_date is None or ind_next_date >= period_end:
			gains_begin_row = None
			gains_end_row = None
			gains_end_date = gain_next_period_f(ind_date)
			while gains_idx < len(gains_df):
				gains_row = gains_df.iloc[gains_idx]
				gains_date = gains_row['交易日期']
				if gains_date > ind_date:
					gains_idx -= 1
					break
				gains_begin_row = gains_row
				gains_idx += 1
			gains_end_idx = gains_idx + 1
			while gains_end_idx < len(gains_df):
				gains_row = gains_df.iloc[gains_end_idx]
				gains_date = gains_row['交易日期']
				if gains_date > gains_end_date:
					gains_end_row = gains_df.iloc[gains_end_idx-1]
					break
				gains_end_idx += 1
			if not gains_end_row is None:
				if not gains_begin_row is None:
					gain_rate = round(((1+gains_end_row['总收益率']/100)/(1+gains_begin_row['总收益率']/100)-1)*100, 2)
				else:
					gain_rate = gains_end_row['总收益率']
				data.append([indicator_row[column] for column in columns[:len(columns)-1]] + [gain_rate])
			if gains_end_row is None:
				break
	return pd.DataFrame(data, columns=columns)
