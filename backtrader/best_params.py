import akshare as ak
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import warnings
import itertools
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams['axes.unicode_minus'] = False

# 定义基础MACD策略类（用于参数优化）
class MACDStrategy(bt.Strategy):
    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
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
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        
        # 记录交易数据（用于计算胜率）
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
            # 记录单笔交易盈亏
            trade_profit = (self.data.close[0] - self.position.price) * self.position.size
            self.trades.append(trade_profit)
            if trade_profit > 0:
                self.win_trades += 1
            else:
                self.lose_trades += 1
            self.sell(size=self.position.size)

    def stop(self):
        # 策略结束时计算关键指标
        total_profit = self.broker.get_value() - 100000  # 初始资金10万
        profit_rate = (total_profit / 100000) * 100
        win_rate = (self.win_trades / (self.win_trades + self.lose_trades)) * 100 if (self.win_trades + self.lose_trades) > 0 else 0
        
        # 保存参数和对应指标（供优化器读取）
        self.params_result = {
            'macd1': self.params.macd1,
            'macd2': self.params.macd2,
            'macdsig': self.params.macdsig,
            'total_profit': total_profit,
            'profit_rate': profit_rate,
            'win_rate': win_rate,
            'total_trades': self.win_trades + self.lose_trades
        }

# 获取A股数据（复用之前的函数）
def get_stock_data(stock_code="600519", start_date="20240101", end_date="20250301"):
    stock_df = ak.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )
    stock_df.rename(
        columns={
            "日期": "datetime", "开盘": "open", "最高": "high", 
            "最低": "low", "收盘": "close", "成交量": "volume", "成交额": "openinterest"
        },
        inplace=True
    )
    stock_df["datetime"] = pd.to_datetime(stock_df["datetime"])
    stock_df.set_index("datetime", inplace=True)
    return bt.feeds.PandasData(dataname=stock_df)

# 参数优化主函数
def optimize_macd_params(stock_code="600519", start_date="20240101", end_date="20250301"):
    # 1. 定义参数搜索范围（根据经验设置合理区间）
    macd1_range = range(6, 18, 2)    # DIF周期：6,8,...,16,18
    macd2_range = range(20, 32, 2)   # DEA周期：20,22,...,30,32
    macdsig_range = range(6, 12, 1)  # 信号线周期：6,7,...,11
    
    # 2. 存储所有参数组合的结果
    results = []
    
    # 3. 遍历所有参数组合（网格搜索）
    for macd1, macd2, macdsig in itertools.product(macd1_range, macd2_range, macdsig_range):
        # 跳过无效组合（macd1必须小于macd2）
        if macd1 >= macd2:
            continue
        
        # 创建回测引擎
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.00025)
        
        # 添加策略（传入当前参数）
        cerebro.addstrategy(MACDStrategy, macd1=macd1, macd2=macd2, macdsig=macdsig)
        
        # 添加数据
        stock_data = get_stock_data(stock_code, start_date, end_date)
        cerebro.adddata(stock_data)
        
        # 运行回测
        strategies = cerebro.run()
        strat = strategies[0]
        
        # 保存当前参数组合的结果
        results.append(strat.params_result)
        print(f"参数组合：({macd1},{macd2},{macdsig}) | 收益率：{strat.params_result['profit_rate']:.2f}% | 胜率：{strat.params_result['win_rate']:.2f}%")
    
    # 4. 转换为DataFrame，方便分析
    results_df = pd.DataFrame(results)
    
    # 5. 找到最优参数（按收益率排序，兼顾胜率）
    # 优先选收益率最高，且胜率>50%的组合
    valid_results = results_df[results_df['win_rate'] > 50]
    if not valid_results.empty:
        best_params = valid_results.loc[valid_results['profit_rate'].idxmax()]
    else:
        # 若无胜率>50%的组合，选收益率最高的
        best_params = results_df.loc[results_df['profit_rate'].idxmax()]
    
    # 6. 输出优化结果
    print("\n=== 参数优化结果 ===")
    print(f"最优MACD参数：DIF={best_params['macd1']}, DEA={best_params['macd2']}, 信号线={best_params['macdsig']}")
    print(f"对应收益率：{best_params['profit_rate']:.2f}%")
    print(f"对应胜率：{best_params['win_rate']:.2f}%")
    print(f"总交易次数：{best_params['total_trades']}")
    
    # 7. 可视化参数敏感度（收益率 vs 参数）
    plt.figure(figsize=(12, 8))
    
    # 子图1：macd1 vs 收益率
    plt.subplot(2,2,1)
    plt.scatter(results_df['macd1'], results_df['profit_rate'], c='red', alpha=0.6)
    plt.xlabel('MACD1 (DIF周期)')
    plt.ylabel('收益率 (%)')
    plt.title('DIF周期 vs 收益率')
    
    # 子图2：macd2 vs 收益率
    plt.subplot(2,2,2)
    plt.scatter(results_df['macd2'], results_df['profit_rate'], c='blue', alpha=0.6)
    plt.xlabel('MACD2 (DEA周期)')
    plt.ylabel('收益率 (%)')
    plt.title('DEA周期 vs 收益率')
    
    # 子图3：macdsig vs 收益率
    plt.subplot(2,2,3)
    plt.scatter(results_df['macdsig'], results_df['profit_rate'], c='green', alpha=0.6)
    plt.xlabel('MACDSIG (信号线周期)')
    plt.ylabel('收益率 (%)')
    plt.title('信号线周期 vs 收益率')
    
    # 子图4：胜率 vs 收益率
    plt.subplot(2,2,4)
    plt.scatter(results_df['win_rate'], results_df['profit_rate'], c='purple', alpha=0.6)
    plt.xlabel('胜率 (%)')
    plt.ylabel('收益率 (%)')
    plt.title('胜率 vs 收益率')
    
    plt.tight_layout()
    plt.show()
    
    return best_params, results_df

# 运行参数优化
if __name__ == "__main__":
    # 优化贵州茅台（600519）的MACD参数
    best_params, results_df = optimize_macd_params(
        stock_code="600519",
        start_date="20240101",
        end_date="20250301"
    )
