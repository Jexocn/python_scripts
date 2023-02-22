#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2023/2/17 17::41
Desc: 计算A股股票收益情况
"""

def str_to_date(hist_date):
	ret_date = None
	try:
		ret_date = dateutil.parser.parse(str(hist_date)).date()
	except:
		pass
	finally:
		pass
	return ret_date


def date_to_str(date):
	return '%d-%02d-%02d' % (date.year, date.month, date.day)

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
		fee = max(round(buy_cost*fee_rate,2), min_fee)
		remain_cash = cash - price*buy_amount - fee
		if remain_cash >= 0:
			return buy_amount, buy_cost, fee, remain_cash
		buy_amount -= 100

def cal_a_stock_gains(hist_df, dividents_df, rights_issue_df, init_price, begin_date, end_date, init_amount=10000, init_cash=0, roid=0, fee_rate=0, min_fee=0):
	'''
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
		if not ex_date is datetime.date:
			ex_date = str_to_date(ex_date)
		if not received_date is datetime.date:
			received_date = str_to_date(received_date)
		if not ex_date is None:
			dividents_ex_right[ex_date] = row
		if not received_date is None:
			dividents_received[received_date] = row
	rights_issue_record = {}	# 配股股权登记日
	rights_issue_ex_right = {}	# 配股除权日
	for i in range(0, len(rights_issue_df)):
		row = rights_issue_df.iloc[i]
		ex_date = row['除权日']
		record_date = row['股权登记日']
		if not ex_date is datetime.date:
			ex_date = str_to_date(ex_date)
		if not record_date is datetime.date:
			record_date = str_to_date(record_date)
		if not ex_date is None:
			rights_issue_ex_right[ex_date] = row
		if not received_date is None:
			rights_issue_record[record_date] = row
	init_value = init_amount*init_price + init_cash
	columns = ['现金', '未到账派息', '总市值', '总持仓', '总收益率', '交易日期', '买入', '卖出', '转增', '送股', '派息']
	data = []
	amount = init_amount
	remain_cash = init_cash 	# 实际到账现金
	fh_cash = 0
	for i in range(0, len(hist_df)):
		row = hist_df.iloc[i]
		hist_date = str_to_date(row['日期'])
		if hist_date >= begin_date and hist_date <= end_date:
			if hist_date in rights_issue_record:
				sell_amount = amount
				sell_cash = row['收盘']*sell_amount
				fee = max(round(sell_cash*fee_rate, 2), min_fee)
				sell_cash -= fee
				amount = 0
				remain_cash += sell_cash
				rate = round(((remain_cash+fh_cash)/init_value-1)*100, 2)
				remain_cash += sell_cash
				data.append([remain_cash, fh_cash, 0, 0, rate, hist_date, 0, sell_amount, 0, 0, 0])
			elif hist_date in rights_issue_ex_right:
				assert(amount == 0 or i == 0)
				if i == 0:
					amount = 0
					remain_cash = init_value
				if pd.notna(row['开盘']):
					buy_amount, buy_cost, fee, remain_cash = cal_buy_amount(remain_cash, row['开盘'], fee_rate, min_fee)
					amount = buy_amount
					value = row['收盘']*amount
					rate = round(((value+remain_cash+fh_cash)/init_value-1)*100, 2)
					data.append([remain_cash, fh_cash, value, amount, rate, hist_date, buy_amount, 0, 0, 0, 0])
			else:
				buy_amount = 0
				if remain_cash > 0 and pd.notna(row['开盘']):
					# TODO: roid == 1 涨停不买入、跌停不卖出
					buy_amount, buy_cost, fee, remain_cash = cal_buy_amount(remain_cash, row['开盘'], fee_rate, min_fee)
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
					if roid != 2:
						dividents_row = dividents_received[hist_date]
						if pd.notna(dividents_row['派息比例']):
							fh_add_cash = round(amount/10*dividents_row['派息比例'], 2)
							fh_cash -= fh_add_cash
							remain_cash += fh_add_cash
							fh_add_cash = 0
						assert(math.abs(fh_cash) < 0.001)
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
