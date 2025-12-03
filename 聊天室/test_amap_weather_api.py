import requests

# 测试高德地图天气API
def test_amap_weather_api(city):
    try:
        # 使用提供的API Key
        key = "047f39952d09b77c2253f27b36a257a8"
        url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={city}&output=JSON&key={key}"
        print(f"测试URL: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"响应内容: {data}")
                return data
            except Exception as e:
                print(f"JSON解析错误: {str(e)}")
                print(f"原始响应内容: {response.text}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"请求异常: {str(e)}")
    
    return None

# 测试几个城市
if __name__ == "__main__":
    print("测试高德地图天气API...")
    cities = ["成都", "北京", "上海"]
    
    for city in cities:
        print(f"\n=== 测试城市: {city} ===")
        data = test_amap_weather_api(city)
        if data:
            print(f"API调用成功！")
        else:
            print(f"API调用失败！")