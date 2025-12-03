import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import ssl

# 打印SSL版本信息
print(f"SSL版本: {ssl.OPENSSL_VERSION}")

# 禁用SSL警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

try:
    # 使用正确的HTTPS地址
    api_url = "https://api.vvhan.com/api/60s?type=json"
    print(f"测试API (HTTPS): {api_url}")
    
    # 添加完整的请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive'
    }
    
    # 尝试不同的请求方式
    print("正在发送请求...")
    response = requests.get(api_url, timeout=15, headers=headers, verify=False, allow_redirects=True)
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 尝试解析JSON
    news_data = response.json()
    print(f"解析后的JSON: {news_data}")
    print(f"success字段: {news_data.get('success')}")
    print(f"time字段: {news_data.get('time')}")
    print(f"data字段: {news_data.get('data')}")
    
except Exception as e:
    print(f"API调用错误: {str(e)}")