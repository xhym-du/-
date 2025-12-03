import requests

# 测试wttr.in天气API
def test_wttr_weather_api(city):
    try:
        # 使用wttr.in API（无需API Key）
        url = f"http://wttr.in/{city}?format=j1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        print(f"测试URL: {url}")
        
        response = requests.get(url, timeout=10, headers=headers)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"响应内容: {data}")
                
                # 检查天气信息
                current_condition = data.get('current_condition', [])
                if current_condition:
                    weather_data = current_condition[0]
                    temp = weather_data.get('temp_C', '未知')
                    weather = weather_data.get('weatherDesc', [{}])[0].get('value', '未知')
                    winddirection = weather_data.get('winddir16Point', '未知')
                    humidity = weather_data.get('humidity', '未知')
                    
                    print(f"\n天气信息摘要：")
                    print(f"城市: {city}")
                    print(f"当前温度: {temp}°C")
                    print(f"天气状况: {weather}")
                    print(f"风向: {winddirection}")
                    print(f"湿度: {humidity}%")
                    
                    return True
                else:
                    print(f"未找到天气信息")
                    return False
                    
            except Exception as e:
                print(f"JSON解析错误: {str(e)}")
                print(f"原始响应内容: {response.text}")
                return False
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"请求异常: {str(e)}")
        return False

# 测试几个城市
if __name__ == "__main__":
    print("测试wttr.in天气API...")
    cities = ["成都", "北京", "上海"]
    
    for city in cities:
        print(f"\n=== 测试城市: {city} ===")
        success = test_wttr_weather_api(city)
        if success:
            print("✅ API调用成功！")
        else:
            print("❌ API调用失败！")