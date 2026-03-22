import akshare as ak
import backtrader as bt
import pandas as pd  # 补充缺失的导入
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体，避免图表中文乱码
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 定义带买卖信号的MACD策略类
class MACDStrategy(bt.Strategy):
    params = (
        # MACD参数
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        # 仓位参数：每次买入总资产的百分比
        ('order_percent', 0.9),
    )

    def __init__(self):
        # 计算MACD指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd1,
            period_me2=self.params.macd2,
            period_signal=self.params.macdsig
        )
        # 计算MACD金叉/死叉信号（DIF上穿/下穿DEA）
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        
        # 记录持仓状态（避免重复买卖）
        self.position_flag = False

    def next(self):
        # 获取当前账户现金和总资产
        cash = self.broker.get_cash()
        value = self.broker.get_value()
        
        # 1. 金叉信号（DIF上穿DEA）：买入
        if self.crossover > 0 and not self.position:
            # 计算买入数量（按总资产的90%买入，避免全仓）
            size = int((cash * self.params.order_percent) / self.data.close[0])
            if size > 0:
                # 发出买入订单
                self.buy(size=size)
                self.position_flag = True
                print(f"买入信号 | 日期：{self.data.datetime.date(0)} | 价格：{self.data.close[0]:.2f} | 数量：{size}")
        
        # 2. 死叉信号（DIF下穿DEA）：卖出
        elif self.crossover < 0 and self.position:
            # 卖出全部持仓
            self.sell(size=self.position.size)
            self.position_flag = False
            print(f"卖出信号 | 日期：{self.data.datetime.date(0)} | 价格：{self.data.close[0]:.2f} | 数量：{self.position.size}")

# 获取A股日线数据（以贵州茅台 600519 为例）
def get_stock_data(stock_code="600519", start_date="20240101", end_date="20250301"):
    """
    获取A股日线数据
    :param stock_code: 股票代码（如600519）
    :param start_date: 开始日期（格式YYYYMMDD）
    :param end_date: 结束日期（格式YYYYMMDD）
    :return: 符合backtrader格式的数据源
    """
    # 通过akshare获取A股日线数据
    stock_df = ak.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"  # 前复权
    )
    
    # 数据格式转换（适配backtrader）
    stock_df.rename(
        columns={
            "日期": "datetime",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "openinterest"
        },
        inplace=True
    )
    stock_df["datetime"] = pd.to_datetime(stock_df["datetime"])
    stock_df.set_index("datetime", inplace=True)
    
    # 转换为backtrader数据源
    data = bt.feeds.PandasData(dataname=stock_df)
    return data

# 主函数：运行策略并绘制MACD图表
if __name__ == "__main__":
    # 1. 创建回测引擎
    cerebro = bt.Cerebro()
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    # 设置交易佣金（A股默认万分之2.5）
    cerebro.broker.setcommission(commission=0.00025)
    
    # 2. 添加策略
    cerebro.addstrategy(MACDStrategy)
    
    # 3. 获取并添加股票数据
    stock_data = get_stock_data(stock_code="600519", start_date="20240101", end_date="20250301")
    cerebro.adddata(stock_data)
    
    # 打印初始资金
    print(f"初始资金：{cerebro.broker.getcash():.2f} 元")
    
    # 4. 运行回测
    cerebro.run()
    
    # 打印最终资金和收益
    final_value = cerebro.broker.getvalue()
    profit = final_value - 100000
    profit_rate = (profit / 100000) * 100
    print(f"最终资金：{final_value:.2f} 元")
    print(f"总收益：{profit:.2f} 元 | 收益率：{profit_rate:.2f}%")
    
    # 5. 绘制图表（包含K线、MACD、买卖信号标记）
    cerebro.plot(style='candlestick', iplot=False, barup='red', bardown='green')
    plt.show()
