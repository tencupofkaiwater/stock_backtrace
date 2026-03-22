import akshare as ak
import json
import os
import warnings
warnings.filterwarnings('ignore')

# 在app.py中添加tushare配置（替换akshare逻辑）
import tushare as ts

# 替换为你的tushare token（注册地址：https://tushare.pro/register?reg=786730）
# API说明：https://tushare.pro/document/2
TS_TOKEN = "dd5399c8a323be44ef4f3188a474237cf7a0a137705e109c8b3750b5"  # 18180674927
# TS_TOKEN = "b0bf212b10b0dc751bd6b3db841841f33a8fb94f030627078809b3fd"  # 18180674925

ts.set_token(TS_TOKEN)
pro = ts.pro_api()

# 缓存文件路径（避免重复拉取数据）
CACHE_FILE = "stock_list_cache.json"
# 过滤规则：排除创业板(300)、科创板(688)
FILTER_PREFIX = ["300", "688"]

import json
import os
from datetime import datetime

def get_stock_options():
    # 缓存文件路径
    cache_file = "stock_list_cache.json"
    # 缓存有效期1天
    cache_expire = 86400
    
    # 检查缓存是否存在且未过期
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            cache_time = cache_data.get("update_time", 0)
            # 未过期则返回缓存数据
            if datetime.now().timestamp() - cache_time < cache_expire:
                return cache_data["data"]
    
    # 缓存失效，重新获取
    stock_basic = pro.stock_basic(...)  # 原有逻辑
    stock_options = [...]  # 原有逻辑
    
    # 保存到缓存
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump({
            "update_time": datetime.now().timestamp(),
            "data": stock_options
        }, f, ensure_ascii=False)
    
    return stock_options
    
def get_stock_list_from_akshare():
    """从akshare拉取全量A股列表（剔除创业板、科创板）"""
    try:
        stock_info_df = pro.stock_basic(
            exchange="",        # 交易所代码，空=全部，可选：SH/SZ/BJ
            list_status="L",    # 上市状态：L=上市 D=退市 P=暂停上市
            fields="ts_code,symbol,name,market,is_st,industry"
        )

        print(f"原始上市股票数量：{len(stock_info_df)}")

        # 2. 核心过滤逻辑
        # 2.1 过滤掉创业板、科创板（只保留主板/中小板）
        # market字段取值：主板/创业板/科创板/北交所/中小板
        allowed_markets = ["主板", "中小板"]  # 只保留这两类
        stock_info_df = stock_info_df[stock_info_df['market'].isin(allowed_markets)]
        
        # 2.2 过滤ST股票（is_st=1 表示ST）
        # 兼容旧版接口：如果is_st字段不存在，通过股票名称包含*ST/ST判断
        if 'is_st' in stock_info_df.columns:
            stock_info_df = stock_info_df[stock_info_df['is_st'] == 0]  # 非ST股
        else:
            # 备用方案：过滤名称含ST/*ST的股票
            stock_info_df = stock_info_df[~stock_info_df['name'].str.contains('ST|*ST', na=False)]
        
        # 2.3 可选：过滤北交所（如果有）
        stock_info_df = stock_info_df[stock_info_df['market'] != "北交所"]
        
        print(f"过滤后股票数量：{len(stock_info_df)}")

        # 新增：去重（按代码去重）
        stock_info_df = stock_info_df.drop_duplicates(subset=['ts_code'], keep='last')
        stock_info_df = stock_info_df[
            ~stock_info_df['ts_code'].str.startswith(tuple(FILTER_PREFIX))
        ]
        stock_dict = dict(zip(stock_info_df['ts_code'], stock_info_df['name']))
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(stock_dict, f, ensure_ascii=False, indent=2)
        return stock_dict
    except Exception as e:
        print(f"拉取实时股票列表失败：{e}，使用备用静态列表")
        return get_backup_stock_list()

def get_backup_stock_list():
    """备用静态股票列表（主流蓝筹/白马股，剔除创业板、科创板）"""
    return {
        # 金融
        "601318": "中国平安", "600036": "招商银行", "601988": "中国银行", "601288": "农业银行",
        "601939": "建设银行", "601818": "光大银行", "601658": "邮储银行", "600016": "民生银行",
        # 消费
        "600519": "贵州茅台", "000858": "五粮液", "600887": "伊利股份", "000333": "美的集团",
        "000651": "格力电器", "601899": "紫金矿业", "600276": "恒瑞医药", "601607": "上海医药",
        # 周期
        "601668": "中国建筑", "601006": "大秦铁路", "600019": "宝钢股份", "601186": "中国铁建",
        "601390": "中国中铁", "600028": "中国石化", "601857": "中国石油", "600000": "浦发银行",
        # 科技（非双创）
        "000001": "平安银行", "002594": "比亚迪", "601689": "拓普集团", "600104": "上汽集团",
        "600703": "三安光电", "000100": "TCL科技", "600895": "张江高科", "002475": "立讯精密",
        # 能源
        "601088": "中国神华", "600900": "长江电力", "600027": "华电国际", "600011": "华能国际",
        # 基建
        "601618": "中国中冶", "600068": "葛洲坝", "601117": "中国化学", "600320": "振华重工",
        # 地产
        "600048": "保利发展", "601155": "新城控股", "000002": "万科A", "001979": "招商蛇口",
        # 交通运输
        "601111": "中国国航", "600029": "南方航空", "601880": "大连港", "600018": "上港集团",
        # 军工
        "601890": "亚星锚链", "600150": "中国船舶", "600391": "航发科技", "600893": "航发动力",
        # 其余主流个股（可按需扩展）
        "600050": "中国联通", "601398": "工商银行", "600585": "海螺水泥", "600010": "包钢股份",
        "000063": "中兴通讯", "601766": "中国中车", "600958": "东方证券", "601788": "光大证券",
        "002027": "分众传媒", "601898": "中煤能源", "600183": "生益科技", "002230": "科大讯飞"
    }

def get_stock_list():
    """获取最终股票列表（优先用缓存，无缓存则拉取实时）"""
    # 优先读取本地缓存
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取缓存文件失败：{e}，拉取实时数据")
            return get_stock_list_from_akshare()
    else:
        # 无缓存则拉取实时数据
        return get_stock_list_from_akshare()

def get_stock_options():
    """转换为前端需要的格式：[{value: 代码, label: 代码 - 名称}]"""
    stock_dict = get_stock_list()
    # 按代码排序，便于前端查找
    sorted_stock = sorted(stock_dict.items(), key=lambda x: x[0])
    return [{"value": code, "label": f"{code} - {name}"} for code, name in sorted_stock]

# 测试代码（运行该文件时验证）
if __name__ == "__main__":
    stock_options = get_stock_options()
    print(f"股票列表总数：{len(stock_options)}")
    print("前10只股票：")
    for item in stock_options[:10]:
        print(item)