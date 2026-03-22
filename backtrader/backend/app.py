from flask import Flask, request, jsonify
from flask_cors import CORS
import akshare as ak
import backtrader as bt
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)  # 解决跨域问题

# MACD策略类（用于回测）
class MACDStrategy(bt.Strategy):
    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        ('order_percent', 0.9),
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd1,
            period_me2=self.params.macd2,
            period_signal=self.params.macdsig
        )
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        self.trades = []
        self.win_trades = 0
        self.lose_trades = 0

    def next(self):
        cash = self.broker.get_cash()
        # 金叉买入
        if self.crossover > 0 and not self.position:
            size = int((cash * self.params.order_percent) / self.data.close[0])
            if size > 0:
                self.buy(size=size)
        # 死叉卖出
        elif self.crossover < 0 and self.position:
            trade_profit = (self.data.close[0] - self.position.price) * self.position.size
            self.trades.append(trade_profit)
            if trade_profit > 0:
                self.win_trades += 1
            else:
                self.lose_trades += 1
            self.sell(size=self.position.size)

    def stop(self):
        self.total_profit = self.broker.get_value() - 100000
        self.profit_rate = (self.total_profit / 100000) * 100
        self.win_rate = (self.win_trades / (self.win_trades + self.lose_trades)) * 100 if (self.win_trades + self.lose_trades) > 0 else 0
        self.total_trades = self.win_trades + self.lose_trades

# 获取股票数据+计算MACD+回测
@app.route('/api/analyze_macd', methods=['POST'])
def analyze_macd():
    try:
        # 获取前端参数
        params = request.json
        stock_code = params.get('stockCode')
        start_date = params.get('startDate')
        end_date = params.get('endDate')
        macd1 = int(params.get('macd1', 12))
        macd2 = int(params.get('macd2', 26))
        macdsig = int(params.get('macdsig', 9))

        # 1. 获取A股日线数据
        stock_df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )

        if stock_df.empty:
            return jsonify({'code': -1, 'msg': '股票数据获取失败，请检查代码或日期'})

        # 2. 计算MACD指标（供前端绘图）
        stock_df['datetime'] = pd.to_datetime(stock_df['日期'])
        stock_df['ema12'] = stock_df['收盘'].ewm(span=macd1, adjust=False).mean()
        stock_df['ema26'] = stock_df['收盘'].ewm(span=macd2, adjust=False).mean()
        stock_df['dif'] = stock_df['ema12'] - stock_df['ema26']
        stock_df['dea'] = stock_df['dif'].ewm(span=macdsig, adjust=False).mean()
        stock_df['bar'] = 2 * (stock_df['dif'] - stock_df['dea'])

        # 3. 格式转换（适配Highcharts）
        kline_data = []
        macd_data = []
        for _, row in stock_df.iterrows():
            # K线数据：[时间戳, 开盘, 最高, 最低, 收盘, 成交量]
            timestamp = int(row['datetime'].timestamp() * 1000)
            kline_data.append([
                timestamp,
                round(row['开盘'], 2),
                round(row['最高'], 2),
                round(row['最低'], 2),
                round(row['收盘'], 2),
                int(row['成交量'])
            ])
            # MACD数据：[时间戳, DIF, DEA, BAR]
            macd_data.append([
                timestamp,
                round(row['dif'], 4),
                round(row['dea'], 4),
                round(row['bar'], 4)
            ])

        # 4. 回测策略
        # 数据格式适配backtrader
        bt_df = stock_df.rename(columns={
            "日期": "datetime", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume"
        })
        bt_df['datetime'] = pd.to_datetime(bt_df['datetime'])
        bt_df.set_index('datetime', inplace=True)
        data = bt.feeds.PandasData(dataname=bt_df)

        # 运行回测
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.00025)
        cerebro.addstrategy(MACDStrategy, macd1=macd1, macd2=macd2, macdsig=macdsig)
        cerebro.adddata(data)
        strategies = cerebro.run()
        strat = strategies[0]

        # 5. 构造返回结果
        result = {
            'code': 0,
            'msg': 'success',
            'data': {
                # K线+MACD数据
                'klineData': kline_data,
                'macdData': macd_data,
                # 回测结果
                'backtest': {
                    'initialCapital': 100000.0,
                    'finalCapital': round(cerebro.broker.get_value(), 2),
                    'totalProfit': round(strat.total_profit, 2),
                    'profitRate': round(strat.profit_rate, 2),
                    'winRate': round(strat.win_rate, 2),
                    'totalTrades': strat.total_trades
                }
            }
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({'code': -1, 'msg': f'服务器错误：{str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)