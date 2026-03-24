#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
sys.path.append('backtrader/backend')

import app
from werkzeug.test import Client
from werkzeug.wrappers import Response

# 创建测试客户端
client = Client(app.app, Response)

print("=== Flask App Route Test ===")
print("=" * 40)

print("\n1. 检查所有注册的路由:")
for rule in app.app.url_map.iter_rules():
    print(f"- {rule}")

print("\n" + "=" * 40)
print("2. 测试访问根路径 '/'")

try:
    # 发送 GET 请求到根路径
    response = client.get('/', follow_redirects=True)
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Length: {len(response.data)} bytes")
    print(f"  Response Type: {type(response.data)}")

    if response.status_code == 200:
        print(f"\n  Response Content:")
        print(response.data.decode('utf-8')[:500] + "..." if len(response.data) > 500 else response.data.decode('utf-8'))
    else:
        print(f"\n  Error: {response.data.decode('utf-8')}")

except Exception as e:
    print(f"\n  Exception: {type(e).__name__}: {str(e)}")
    import traceback
    print(f"  Stack Trace: {traceback.format_exc()}")

print("\n" + "=" * 40)
print("3. 测试访问股票列表接口")
try:
    response = client.get('/api/get_stock_list')
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Content: {response.data.decode('utf-8')}")
except Exception as e:
    print(f"\n  Exception: {type(e).__name__}: {str(e)}")

print("\n" + "=" * 40)
print("4. 测试访问静态资源")
try:
    response = client.get('/index.html')
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Length: {len(response.data)} bytes")
    if response.status_code == 200:
        print("  Success: index.html")
    else:
        print(f"  Error: {response.data.decode('utf-8')}")
except Exception as e:
    print(f"  Exception: {type(e).__name__}: {str(e)}")
