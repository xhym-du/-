import socketio
import time

# 创建Socket.IO客户端
# sio = socketio.Client()

# 连接到服务器
# sio.connect('http://localhost:5000')

# 定义事件处理函数
# @sio.on('connect')
def on_connect():
    print('已连接到服务器')
    
    # 发送加入房间请求
    # sio.emit('join', {'username': '测试用户'})
    
    # 发送新闻指令
    time.sleep(1)
    # sio.emit('send_message', {'username': '测试用户', 'message': '@新闻'})
    print('已发送新闻指令')

# @sio.on('assistant_response')
def on_assistant_response(data):
    print('收到助手回复:')
    print(f'用户名: {data["username"]}')
    print(f'消息: {data["message"]}')
    
    # 断开连接
    # sio.disconnect()

# 测试模拟新闻数据生成
from datetime import datetime

def test_mock_news():
    print("\n=== 测试模拟新闻数据生成 ===")
    mock_news_data = {
        'success': True,
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'data': [
            '1. 教育部发布最新教育改革方案，强调素质教育的重要性',
            '2. 科技巨头发布全新人工智能模型，性能提升30%',
            '3. 国内多地迎来降温天气，专家提醒注意保暖',
            '4. 体育赛事：国家队在国际比赛中获得优异成绩',
            '5. 新能源汽车销量持续增长，市场份额突破30%',
            '6. 文化节活动在各地举办，促进文化交流与传承',
            '7. 医疗领域取得新突破，新型药物进入临床试验',
            '8. 环保组织呼吁减少塑料使用，保护生态环境',
            '9. 数字经济发展迅速，创造大量就业机会',
            '10. 国际合作项目启动，推动全球可持续发展'
        ]
    }
    
    print(f"时间: {mock_news_data['time']}")
    print("新闻列表:")
    for news in mock_news_data['data']:
        print(news)
    
    # 构建HTML内容
    news_html = f"📅 {mock_news_data['time']} 每天60秒读懂世界<br><br>"
    for i, news in enumerate(mock_news_data['data'], 1):
        news_html += f"{i}. {news}<br>"
    news_html += "<br>💡 哪怕微小的光也能照亮黑夜"
    
    print("\n生成的HTML内容:")
    print(news_html)

# 运行测试
if __name__ == '__main__':
    # 测试模拟新闻数据
    test_mock_news()
    
    # 启动Socket.IO客户端
    # print("\n=== 测试Socket.IO连接 ===")
    # sio.wait()