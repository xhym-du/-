import requests

# 直接测试VVHan天气API
def test_vvhan_api():
    url = "http://api.vvhan.com/api/weather"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124',
        'Content-Type': 'application/json'
    }
    
    # 尝试不同的城市
    cities = ['成都', '北京', '上海', '广州']
    
    for city in cities:
        try:
            print(f"\n=== 测试城市: {city} ===")
            
            # 使用params参数
            response = requests.get(url, params={"city": city}, headers=headers, timeout=10)
            print(f"使用params参数 - 状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}...")
            
            # 直接在URL中拼接参数
            full_url = f"{url}?city={city}"
            response2 = requests.get(full_url, headers=headers, timeout=10)
            print(f"直接拼接URL - 状态码: {response2.status_code}")
            print(f"响应内容: {response2.text[:200]}...")
            
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    test_vvhan_api()