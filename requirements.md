# 1. 系统架构
实现一个自动炒股的软件系统，支持多种策略的数据回测。

- Web前端UI：vue + highchars
- Web后端：Python flask
- 股票历史数据接口：backtrader
- 券商股票买卖交易接口：AI推荐一个

# 2. 后端API接口
## 2.1. 

# 3. 前端UI

# 4. 需求变更
## 4.1 变更1
```
在前端添加策略类型下拉选择框（MACD / 均线 / RSI / 网格）

在后端实现不同策略类（MACD策略、均线策略、RSI策略、网格策略）

为所有策略添加ATR止损风险控制机制

优化策略组合逻辑（MACD金叉+量比>1.5）

在K线图上标记买卖点

修改横轴时间格式为2024/1/1格式

更新后端API接口以支持策略参数传递

测试所有功能并修复可能的BUG
```
功能实现总结:
```
1. 策略类型选择
前端：添加了策略类型下拉选择框，支持 MACD、均线、RSI、网格四种策略
后端：根据选择加载对应的策略类
2. ATR止损风险控制
为所有策略添加了ATR止损功能
止损倍数可配置（默认2倍ATR）
在策略类继承的基础策略中实现
止损时自动记录信号
3. 策略组合优化
MACD策略：优化为 MACD金叉 + 量比>1.5 的买入信号
量比指标简化计算（5日均线/20日均线）
提高了策略的胜率和信号可靠性
4. K线图买卖点标记
使用 Highcharts Stock 的 flags 系列标记买卖信号
买入信号（蓝色圆形标记）
卖出信号（红色圆形标记）
鼠标悬停显示价格信息
5. 时间轴格式优化
x轴时间格式统一为：2024/1/1格式
时间标签自动适配不同刻度级别
提示框中时间格式也做了相应调整
技术实现细节
前端修改（backtrader/frontend/index.html）
添加策略类型选择下拉框
优化表单布局
实现策略参数验证逻辑
添加获取策略名称方法
实现买卖信号获取和渲染
优化图表配置（x轴格式、提示框等）
后端修改（backtrader/backend/app.py）
创建基础策略类 BaseStrategy，包含ATR止损逻辑
实现四种策略类继承基础策略：
MACDStrategy：MACD策略，支持金叉+量比条件
MAStrategy：均线策略，支持自定义短期/长期均线
RSIStrategy：RSI策略，支持超买超卖条件配置
GridStrategy：网格策略，支持网格间距和层数配置
优化API接口，支持策略类型和参数传递
在返回结果中添加信号数据
完善回测结果统计
使用说明
启动服务器：


cd c:\Users\王老师\Desktop\stock_backtrace
.venv\Scripts\activate
python backtrader/backend/app.py
访问应用：

打开浏览器访问 http://localhost:5000
或在项目根目录运行：start http://localhost:5000
使用功能：

选择策略类型（MACD/均线/RSI/网格）
选择股票代码
设置分析时间范围
调整策略参数（可保留默认值）
点击"开始分析"按钮
查看回测结果和图表
策略参数说明
策略类型	参数名称	默认值	说明
MACD	macd1 (DIF)	12	DIF周期
macd2 (DEA)	26	DEA周期
macdsig	9	信号周期
均线	maShort	5	短期均线
maLong	20	长期均线
RSI	rsiPeriod	14	RSI周期
rsiOversold	30	超卖阈值
rsiOverbought	70	超买阈值
网格	gridInterval	2	网格间距（百分比）
gridLevels	10	网格层数
所有策略默认使用2倍ATR止损，最大亏损控制在合理范围内。
```

## 4.2 变更2
```
添加新的策略类型（布林带策略）
```