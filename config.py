# 配置文件

# 服务器配置
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8888

# 可用服务器地址列表（用于登录页面下拉选择）
SERVERS = [
    {'name': '本地服务器', 'url': 'ws://127.0.0.1:8888/ws'}
]

# 消息类型定义
MESSAGE_TYPE = {
    'SYSTEM': 'system',      # 系统消息
    'USER_JOIN': 'user_join', # 用户加入
    'USER_LEAVE': 'user_leave', # 用户离开
    'TEXT': 'text',         # 文本消息
    'USER_LIST': 'user_list' # 用户列表更新
}

# 特殊指令前缀
SPECIAL_COMMANDS = {
    'MOVIE': '@电影',
    'AI_CHAT': '@川小农'
}

# AI大模型配置
AI_CONFIG = {
    'API_TYPE': 'siliconflow',
    'API_URL': 'https://api.siliconflow.cn/v1/chat/completions',
    'API_KEY': 'sk-gzxavqqlvlxdtlxdnvvisgruvsktvdfwlqmdqfstmsbbsxuj',
    'MODEL': 'Qwen/Qwen2.5-7B-Instruct',
    'MAX_TOKENS': 512,
    'TEMPERATURE': 0.2,
}

# 结束会话指令
AI_END_SESSION_COMMANDS = ['结束会话', '结束对话', '退出', '再见']

import os
SQLITE_PATH = os.environ.get('SQLITE_PATH', os.path.join(os.path.dirname(__file__), 'chat.db'))

COOKIE_SECRET = os.environ.get('COOKIE_SECRET', 'change-me')
