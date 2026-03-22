# 日志配置（核心修复）
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import akshare as ak
import backtrader as bt
import pandas as pd
import warnings
import os
from stock_config import get_stock_options  # 核心导入

# 在app.py中添加tushare配置（替换akshare逻辑）
import tushare as ts

# 替换为你的tushare token（注册地址：https://tushare.pro/register?reg=786730）
# API说明：https://tushare.pro/document/2
TS_TOKEN = "dd5399c8a323be44ef4f3188a474237cf7a0a137705e109c8b3750b5"  # 18180674927
# TS_TOKEN = "b0bf212b10b0dc751bd6b3db841841f33a8fb94f030627078809b3fd"  # 18180674925

ts.set_token(TS_TOKEN)
pro = ts.pro_api()

# 新增：配置请求头，模拟浏览器访问
ak.headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

warnings.filterwarnings('ignore')

# 初始化app（保持不变）
app = Flask(
    __name__,
    static_folder=os.path.abspath('../frontend'),
    template_folder=os.path.abspath('../frontend')
)
CORS(app)

# 股票列表接口（保持不变）
@app.route('/api/get_stock_list', methods=['GET'])
def get_stock_list():
    try:
        stock_options = get_stock_options()
        return jsonify({
            "code": 0,
            "msg": "success",
            "data": stock_options
        })
    except Exception as e:
        return jsonify({
            "code": -1,
            "msg": f"获取股票列表失败：{str(e)}",
            "data": []
        })

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# 全局配置
INITIAL_CAPITAL = 100000.0
COMMISSION_RATE = 0.00025
ORDER_PERCENT = 0.9

# MACD策略类
class MACDStrategy(bt.Strategy):
    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        ('order_percent', ORDER_PERCENT),
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
        if self.crossover > 0 and not self.position:
            size = int((cash * self.params.order_percent) / self.data.close[0])
            if size > 0:
                self.buy(size=size)
        elif self.crossover < 0 and self.position:
            trade_profit = (self.data.close[0] - self.position.price) * self.position.size
            self.trades.append(trade_profit)
            self.win_trades += 1 if trade_profit > 0 else 0
            self.lose_trades += 1 if trade_profit <= 0 else 0
            self.sell(size=self.position.size)

    def stop(self):
        self.total_profit = self.broker.get_value() - INITIAL_CAPITAL
        self.profit_rate = (self.total_profit / INITIAL_CAPITAL) * 100
        total_trades = self.win_trades + self.lose_trades
        self.win_rate = (self.win_trades / total_trades) * 100 if total_trades > 0 else 0
        self.total_trades = total_trades

@app.route('/api/analyze_macd', methods=['POST'])
def analyze_macd():
    logger.info("收到MACD分析请求，参数：%s", request.json)
    try:
        params = request.json or {}
        # 必选参数校验
        required = ['stockCode', 'startDate', 'endDate']
        for key in required:
            if not params.get(key):
                return jsonify({'code': -1, 'msg': f'缺少参数：{key}'})
        
        # 解析参数
        stock_code = params.get('stockCode')
        start_date = params.get('startDate')
        end_date = params.get('endDate')
        macd1 = int(params.get('macd1', 12))
        macd2 = int(params.get('macd2', 26))
        macdsig = int(params.get('macdsig', 9))

        # 在analyze_macd接口中替换「获取股票数据」部分
        try:
            # 转换日期格式（tushare要求YYYY-MM-DD）
            start_dt = pd.to_datetime(start_date).strftime('%Y-%m-%d')
            end_dt = pd.to_datetime(end_date).strftime('%Y-%m-%d')
            
            # 通过tushare获取日线数据
            df = pro.daily(
                ts_code=f"{stock_code}.SZ" if stock_code.startswith('00') else f"{stock_code}.SH",
                start_date=start_date,
                end_date=end_date
                # adj='qfq'  # 前复权
            )

            # 缓存数据
            df.to_csv(f"{stock_code}_data.csv", index=False, encoding='utf-8')

            # 转换为akshare兼容的格式
            if not df.empty:
                df = df.sort_values('trade_date')
                stock_df = pd.DataFrame({
                    '日期': pd.to_datetime(df['trade_date']),
                    '开盘': df['open'],
                    '最高': df['high'],
                    '最低': df['low'],
                    '收盘': df['close'],
                    '成交量': df['vol'] * 100  # tushare成交量单位是手，转换为股
                })
            else:
                return jsonify({'code': -1, 'msg': 'tushare获取数据为空'})
        except Exception as e:
            return jsonify({'code': -1, 'msg': f'tushare接口异常：{str(e)}'})

        # # 获取股票数据
        # stock_df = ak.stock_zh_a_hist(
        #     symbol=stock_code,
        #     period="daily",
        #     start_date=start_date,
        #     end_date=end_date,
        #     adjust="qfq"
        # )
        if stock_df.empty:
            logger.error("处理请求失败：%s", jsonify({'code': -1, 'msg': '股票数据获取失败，请检查代码或日期'}), exc_info=True)
            # 2. 在接口中读取本地缓存
            try:
                stock_df = pd.read_csv(f"{stock_code}_data.csv")
                stock_df['日期'] = pd.to_datetime(stock_df['日期'])
                # 过滤指定日期范围
                stock_df = stock_df[
                    (stock_df['日期'] >= pd.to_datetime(start_date)) & 
                    (stock_df['日期'] <= pd.to_datetime(end_date))
                ]
            except FileNotFoundError:
                return jsonify({'code': -1, 'msg': '本地缓存数据不存在，请先缓存'})

        # ========== 核心修复：数据清洗 ==========
        # 1. 按日期去重（保留最后一条）
        stock_df = stock_df.drop_duplicates(subset=['日期'], keep='last')
        # 2. 重置索引（避免索引重复）
        stock_df = stock_df.reset_index(drop=True)
        # 3. 确保日期列格式正确
        stock_df['日期'] = pd.to_datetime(stock_df['日期'])

        # 计算MACD
        # （删除原有的 stock_df['datetime'] = pd.to_datetime(stock_df['日期'])，避免列重复）
        stock_df['ema12'] = stock_df['收盘'].ewm(span=macd1, adjust=False).mean()
        stock_df['ema26'] = stock_df['收盘'].ewm(span=macd2, adjust=False).mean()
        stock_df['dif'] = stock_df['ema12'] - stock_df['ema26']
        stock_df['dea'] = stock_df['dif'].ewm(span=macdsig, adjust=False).mean()
        stock_df['bar'] = 2 * (stock_df['dif'] - stock_df['dea'])

        # 格式化图表数据（使用已转换的「日期」列，而非重复的datetime列）
        kline_data = []
        macd_data = []
        for _, row in stock_df.iterrows():
            timestamp = int(row['日期'].timestamp() * 1000)  # 直接用已转换的日期列
            kline_data.append([
                timestamp, round(row['开盘'], 2), round(row['最高'], 2),
                round(row['最低'], 2), round(row['收盘'], 2), int(row['成交量'])
            ])
            macd_data.append([
                timestamp, round(row['dif'], 4), round(row['dea'], 4), round(row['bar'], 4)
            ])

        # 回测数据处理（核心修复：避免重复赋值datetime列）
        bt_df = stock_df.rename(columns={
            "日期": "datetime", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume"
        })
        # 移除重复的 datetime 列赋值（原代码中 bt_df['datetime'] = pd.to_datetime(bt_df['datetime']) 会导致重复）
        bt_df.set_index('datetime', inplace=True)
        # 再次去重（确保索引无重复）
        bt_df = bt_df[~bt_df.index.duplicated(keep='last')]
        data = bt.feeds.PandasData(dataname=bt_df)

        # 运行回测（原有逻辑不变）
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(INITIAL_CAPITAL)
        cerebro.broker.setcommission(commission=COMMISSION_RATE)
        cerebro.addstrategy(MACDStrategy, macd1=macd1, macd2=macd2, macdsig=macdsig)
        cerebro.adddata(data)
        strategies = cerebro.run()
        strat = strategies[0]

        # 返回结果（原有逻辑不变）
        result = {
            'code': 0,
            'msg': 'success',
            'data': {
                'klineData': kline_data,
                'macdData': macd_data,
                'backtest': {
                    'initialCapital': INITIAL_CAPITAL,
                    'finalCapital': round(cerebro.broker.get_value(), 2),
                    'totalProfit': round(strat.total_profit, 2),
                    'profitRate': round(strat.profit_rate, 2),
                    'winRate': round(strat.win_rate, 2),
                    'totalTrades': strat.total_trades
                }
            }
        }
        logger.info("请求处理成功，返回结果：%s", result)
        return jsonify(result)

    except Exception as e:
        logger.error("处理请求失败：%s", str(e), exc_info=True)
        return jsonify({'code': -1, 'msg': f'服务器错误：{str(e)}'})

# 测试接口（用于验证服务是否启动）
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'code': 0, 'msg': '服务正常运行', 'data': {'port': 5000}})

# 1. 提前缓存数据（单独运行一次）
def cache_stock_data(stock_code, start_date, end_date):
    df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
    df.to_csv(f"{stock_code}_data.csv", index=False, encoding='utf-8')

if __name__ == '__main__':
    # 强制指定IP和端口，避免自动分配导致的不匹配
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False  # 关闭自动重载，避免端口占用
    )