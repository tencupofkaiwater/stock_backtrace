import akshare as ak
import json
import os
import warnings
warnings.filterwarnings('ignore')

# 缓存文件路径（避免重复拉取数据）
CACHE_FILE = "stock_list_cache.json"
# 过滤规则：排除创业板(300)、科创板(688)
FILTER_PREFIX = ["300", "688"]

def get_stock_list_from_akshare():
    return get_backup_stock_list()
    """从akshare拉取全量A股列表（剔除创业板、科创板）"""
    try:
        stock_info_df = ak.stock_info_a_code_name()
        # 新增：去重（按代码去重）
        stock_info_df = stock_info_df.drop_duplicates(subset=['代码'], keep='last')
        stock_info_df = stock_info_df[
            ~stock_info_df['代码'].str.startswith(tuple(FILTER_PREFIX))
        ]
        stock_dict = dict(zip(stock_info_df['代码'], stock_info_df['名称']))
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