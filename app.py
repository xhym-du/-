import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import emoji
import requests
import os
import re
import sqlite3
from urllib.parse import quote_plus
try:
    import bcrypt as _bcrypt
    def pw_hash(p):
        return _bcrypt.hashpw(p.encode('utf-8'), _bcrypt.gensalt()).decode('utf-8')
    def pw_check(p, h):
        return _bcrypt.checkpw(p.encode('utf-8'), h.encode('utf-8'))
    BCRYPT_OK = True
except Exception:
    import hashlib
    def pw_hash(p):
        return hashlib.sha256(p.encode('utf-8')).hexdigest()
    def pw_check(p, h):
        return pw_hash(p) == h
    BCRYPT_OK = False
from datetime import datetime
from config import (
    SERVER_HOST, SERVER_PORT, MESSAGE_TYPE, SERVERS, SPECIAL_COMMANDS,
    AI_CONFIG, AI_END_SESSION_COMMANDS, SQLITE_PATH, COOKIE_SECRET
)

# 全局用户存储
class User:
    def __init__(self, nickname, ws):
        self.nickname = nickname
        self.ws = ws
        self.join_time = datetime.now()
        # AI会话状态管理
        self.ai_chat_session = False  # 是否处于AI聊天会话中
        self.ai_chat_history = []  # 聊天历史记录

# 在线用户字典 {nickname: User对象}
online_users = {}

DB_AVAILABLE = True
CURRENT_DB_PATH = SQLITE_PATH
CURRENT_PORT = SERVER_PORT
try:
    db = sqlite3.connect(SQLITE_PATH, check_same_thread=False, timeout=5)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))" )
    cur.execute("CREATE TABLE IF NOT EXISTS raw_data (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, dtype TEXT, content TEXT, created_at TEXT DEFAULT (datetime('now')))" )
    db.commit()
    print('SQLite connected:', SQLITE_PATH)
except Exception:
    db = None
    DB_AVAILABLE = False

def ensure_db():
    global db, DB_AVAILABLE
    if db is not None and DB_AVAILABLE:
        return True
    try:
        db = sqlite3.connect(SQLITE_PATH, check_same_thread=False, timeout=5)
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))" )
        cur.execute("CREATE TABLE IF NOT EXISTS raw_data (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, dtype TEXT, content TEXT, created_at TEXT DEFAULT (datetime('now')))" )
        db.commit()
        DB_AVAILABLE = True
        CURRENT_DB_PATH = SQLITE_PATH
        print('SQLite connected:', CURRENT_DB_PATH)
        return True
    except Exception as e:
        # 尝试使用本地应用目录作为回退路径
        try:
            import os
            base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
            fallback_dir = os.path.join(base, 'DaiPChat')
            os.makedirs(fallback_dir, exist_ok=True)
            fallback_path = os.path.join(fallback_dir, 'chat.db')
            db = sqlite3.connect(fallback_path, check_same_thread=False, timeout=5)
            db.row_factory = sqlite3.Row
            cur = db.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))" )
            cur.execute("CREATE TABLE IF NOT EXISTS raw_data (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, dtype TEXT, content TEXT, created_at TEXT DEFAULT (datetime('now')))" )
            db.commit()
            DB_AVAILABLE = True
            CURRENT_DB_PATH = fallback_path
            print('SQLite fallback path used:', fallback_path)
            return True
        except Exception as e2:
            DB_AVAILABLE = False
            print('SQLite init failed:', e, 'fallback:', e2)
            return False

# WebSocket 处理器
class ChatWebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
    
    def check_origin(self, origin):
        # 允许跨域请求
        return True
    
    def open(self):
        u = self.get_secure_cookie('user')
        if u:
            nickname = u.decode('utf-8')
            if nickname in online_users:
                self.user = online_users[nickname]
            else:
                self.user = User(nickname, self)
                online_users[nickname] = self.user
                self.broadcast_message({
                    'type': MESSAGE_TYPE['USER_JOIN'],
                    'nickname': nickname,
                    'message': f'{nickname} 加入了聊天室',
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                }, exclude=self.user)
                self.update_user_list()
            self.write_message(json.dumps({'type': 'login_success', 'nickname': nickname}))
    
    def on_message(self, message):
        try:
            data = json.loads(message)
            
            if data.get('type') == 'login':
                nickname = data.get('nickname')
                if nickname in online_users:
                    self.write_message(json.dumps({'type': 'login_failed','message': '昵称已被使用，请更换昵称'}))
                    return
                self.user = User(nickname, self)
                online_users[nickname] = self.user
                self.write_message(json.dumps({'type': 'login_success','nickname': nickname,'message': f'欢迎 {nickname} 加入聊天室！'}))
                self.broadcast_message({'type': MESSAGE_TYPE['USER_JOIN'],'nickname': nickname,'message': f'{nickname} 加入了聊天室','timestamp': datetime.now().strftime('%H:%M:%S')}, exclude=self.user)
                self.update_user_list()
                
            # 处理聊天消息
            elif data.get('type') == 'chat' and self.user:
                content = data.get('content', '')
                
                # 处理特殊指令
                if content.startswith('@查天气'):
                    city_input = content[len('@查天气'):].strip()
                    fuzzy_map = {
                        '北上广': ['北京', '上海', '广州'],
                        '深杭': ['深圳', '杭州'],
                        '成渝': ['成都', '重庆']
                    }
                    candidates = fuzzy_map.get(city_input) if city_input else None
                    if candidates:
                        self.write_message(json.dumps({
                            'type': 'weather_candidates',
                            'candidates': candidates,
                            'origin': city_input
                        }))
                    elif city_input:
                        try:
                            api_key = os.environ.get('WEATHER_API_KEY') or '76c5dc52fcd1e3a8'
                            if api_key:
                                url = 'https://v2.xxapi.cn/api/weatherDetails'
                                params = {'city': city_input, 'key': api_key}
                                headers = {'User-Agent': 'xiaoxiaoapi/1.0.0'}
                                resp = requests.get(url, params=params, headers=headers, timeout=2)
                                data = resp.json()
                                if data.get('code') == 200 and isinstance(data.get('data'), dict):
                                    payload = data['data']
                                    city = payload.get('city', city_input)
                                    days = payload.get('data') or []
                                    rt = None
                                    if days:
                                        day0 = days[0]
                                        rt_list = day0.get('real_time_weather') or []
                                        if rt_list:
                                            rt = rt_list[-1]
                                    condition = (rt or {}).get('weather') or (day0.get('weather_from') if days else None)
                                    temp = (rt or {}).get('temperature')
                                    humidity_raw = (rt or {}).get('humidity')
                                    if isinstance(humidity_raw, str):
                                        try:
                                            humidity = float(humidity_raw.replace('%', ''))
                                        except:
                                            humidity = humidity_raw
                                    else:
                                        humidity = humidity_raw
                                    wind_speed = (rt or {}).get('wind_speed')
                                    icon_url = None
                                    icon_map = {
                                        '晴': '☀️', '多云': '⛅', '阴': '☁️', '小雨': '🌧️', '中雨': '🌧️', '大雨': '🌧️', '雷阵雨': '⛈️', '雪': '❄️', '小雪': '❄️', '大雪': '❄️', '雾': '🌫️'
                                    }
                                    icon = icon_map.get(str(condition or '').strip(), '')
                                    if temp is None or humidity is None or condition is None:
                                        self.write_message(json.dumps({
                                            'type': 'weather_error',
                                            'message': f'未查询到【{city_input}】的天气数据，请检查城市名称是否正确~'
                                        }))
                                    else:
                                        try:
                                            temp_val = float(str(temp))
                                        except:
                                            temp_val = temp
                                        card = {
                                            'city': city,
                                            'temp': round(temp_val, 1) if isinstance(temp_val, float) else temp_val,
                                            'humidity': humidity,
                                            'desc': condition,
                                            'wind': wind_speed or '',
                                            'iconUrl': icon_url,
                                            'icon': icon,
                                            'forecast': []
                                        }
                                        self.write_message(json.dumps({
                                            'type': 'weather_card',
                                            'card': card
                                        }))
                                else:
                                    self.write_message(json.dumps({
                                        'type': 'weather_error',
                                        'message': '天气查询暂时出错啦，稍后再试试吧！'
                                    }))
                            else:
                                self.write_message(json.dumps({
                                    'type': 'weather_error',
                                    'message': '天气查询暂时出错啦，稍后再试试吧！'
                                }))
                        except Exception:
                            self.write_message(json.dumps({
                                'type': 'weather_error',
                                'message': '天气查询暂时出错啦，稍后再试试吧！'
                            }))
                    else:
                        self.write_message(json.dumps({
                            'type': 'weather_error',
                            'message': '请输入城市名，如：@查天气北京'
                        }))
                elif content.startswith(SPECIAL_COMMANDS['MOVIE']):
                    # 电影播放功能，使用解析接口并返回iframe
                    movie_url = content[len(SPECIAL_COMMANDS['MOVIE']):].strip()
                    if movie_url:
                        try:
                            # 检查URL格式是否有效
                            import re
                            if not re.match(r'^https?://', movie_url):
                                self.write_message(json.dumps({
                                    'type': MESSAGE_TYPE['SYSTEM'],
                                    'message': '请提供有效的电影链接，格式：@电影 https://...',
                                    'timestamp': datetime.now().strftime('%H:%M:%S')
                                }))
                                return
                                
                            # 创建更可靠的iframe HTML结构
                            iframe_html = f'''<div class="movie-container">
                                <iframe src="https://jx.m3u8.tv/jiexi/?url={movie_url}" width="100%" height="450" frameborder="0" allowfullscreen></iframe>
                                <div class="movie-tips">
                                    <p>如果无法播放，可能是解析接口失效，请尝试其他链接或稍后再试</p>
                                </div>
                            </div>'''
                            
                            # 广播消息给所有用户，包含iframe
                            self.broadcast_message({
                                'type': MESSAGE_TYPE['TEXT'],
                                'sender': self.user.nickname,
                                'message': iframe_html,
                                'timestamp': datetime.now().strftime('%H:%M:%S')
                            })
                        except Exception as e:
                            print(f'处理电影链接时出错: {e}')
                            self.write_message(json.dumps({
                                'type': MESSAGE_TYPE['SYSTEM'],
                                'message': '处理电影链接时出错，请稍后重试或检查链接是否有效',
                                'timestamp': datetime.now().strftime('%H:%M:%S')
                            }))
                    else:
                        # 如果没有提供URL，提示用户
                        response = {
                            'type': MESSAGE_TYPE['SYSTEM'],
                            'message': '请提供电影链接，格式：@电影 https://视频链接地址',
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        }
                        self.write_message(json.dumps(response))
                elif content.startswith('@查新闻'):
                    today = datetime.now().strftime('%Y-%m-%d')
                    def cut(s, n):
                        return (str(s)[:n]).strip()
                    items = []
                    try:
                        url = 'https://v2.xxapi.cn/api/douyinhot'
                        headers = { 'Authorization': 'Bearer 76c5dc52fcd1e3a8' }
                        r = requests.get(url, headers=headers, timeout=6)
                        j = r.json()
                        if j and int(j.get('code', 500)) == 200:
                            ds = j.get('data') or []
                            for d in ds[:15]:
                                title = d.get('word') or ''
                                cover = (d.get('word_cover') or {}).get('uri') or ''
                                hot = d.get('hot_value')
                                vt = d.get('video_count')
                                ts = d.get('event_time')
                                tm = today
                                try:
                                    if ts:
                                        tm = datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d')
                                except Exception:
                                    tm = today
                                img = cover and ("https://p3-sign.toutiaoimg.com/" + cover)
                                items.append({
                                    'title': cut(title, 60),
                                    'summary': f"热度指数：{hot}，相关视频：{vt}",
                                    'image_url': img or f"https://source.unsplash.com/featured/400x240?{quote_plus(cut(title,24))}",
                                    'source': '抖音热点',
                                    'time': tm,
                                    'url': f"https://www.bing.com/news/search?q={quote_plus(cut(title,60))}"
                                })
                        else:
                            raise Exception('bad code')
                    except Exception:
                        base = [
                            {"title": "气候大会闭幕", "summary": "多国就减排路线达成一致，明确阶段性目标与资金支持。", "image_keyword": "climate summit", "time": today},
                            {"title": "消费市场回暖", "summary": "餐饮文旅人气提升，社零额稳步增长。", "image_keyword": "shopping", "time": today},
                            {"title": "科技公司发布会", "summary": "新品聚焦AI应用与隐私保护。", "image_keyword": "technology", "time": today},
                            {"title": "国际油价震荡", "summary": "供需分化导致价格窄幅波动。", "image_keyword": "oil price", "time": today},
                            {"title": "公共卫生提示", "summary": "倡导疫苗接种与常态化防护。", "image_keyword": "health", "time": today},
                        ]
                        items = [{
                            'title': cut(it['title'], 60),
                            'summary': cut(it['summary'], 180),
                            'image_url': f"https://source.unsplash.com/featured/400x240?{quote_plus(cut(it['image_keyword'],24))}",
                            'source': '综合',
                            'time': today,
                            'url': f"https://www.bing.com/news/search?q={quote_plus(cut(it['title'],60))}"
                        } for it in (base * 3)][:15]
                    self.write_message(json.dumps({ 'type': 'news_list', 'items': items }))
                    
                elif content.startswith(SPECIAL_COMMANDS['AI_CHAT']):
                    # 开始AI对话会话
                    self.user.ai_chat_session = True
                    ai_query = content[len(SPECIAL_COMMANDS['AI_CHAT']):].strip()
                    self.write_message(json.dumps({
                        'type': MESSAGE_TYPE['TEXT'],
                        'sender': self.user.nickname,
                        'message': ai_query,
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    }))
                    
                    # 检查是否是结束会话指令
                    if self._is_end_session_command(ai_query):
                        self.user.ai_chat_session = False
                        self.user.ai_chat_history = []
                        response = {
                            'type': MESSAGE_TYPE['SYSTEM'],
                            'sender': '川小农',
                            'message': '会话已结束，期待下次与您交流！',
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        }
                    else:
                        # 调用AI模型获取回复
                        ai_response = self.get_ai_response(ai_query)
                        
                        # 保存对话历史
                        self.user.ai_chat_history.append({
                            'role': 'user',
                            'content': ai_query
                        })
                        self.user.ai_chat_history.append({
                            'role': 'assistant',
                            'content': ai_response
                        })
                        
                        response = {
                            'type': MESSAGE_TYPE['SYSTEM'],
                            'sender': '川小农',
                            'message': ai_response,
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        }
                    
                    self.write_message(json.dumps(response))
                elif content.startswith('@听音乐'):
                    query_kw = content[len('@听音乐'):].strip()
                    api_key = (os.environ.get('XXAPI_KEY', '').strip() or '76c5dc52fcd1e3a8')
                    track_list = []
                    if api_key:
                        try:
                            url = 'https://v2.xxapi.cn/api/kugousearch'
                            params = {'key': api_key}
                            if query_kw:
                                kw = str(query_kw).replace('“','').replace('”','').strip()
                                if kw:
                                    params['music'] = kw
                            headers = {'User-Agent': 'DaiPChat/1.0'}
                            resp = requests.get(url, params=params, headers=headers, timeout=6)
                            result = resp.json()
                            data = result.get('data')
                            if isinstance(data, list):
                                for it in data:
                                    src = it.get('url') or it.get('play_url') or it.get('audio') or it.get('src')
                                    title = it.get('song') or it.get('title') or it.get('name') or it.get('songName') or '未知曲目'
                                    cover = it.get('cover') or it.get('pic') or it.get('image') or it.get('album_pic') or ''
                                    singer = it.get('singer') or it.get('artist') or it.get('singerName') or ''
                                    if src:
                                        track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                            elif isinstance(data, dict):
                                lst = data.get('list') or data.get('items')
                                if isinstance(lst, list):
                                    for it in lst:
                                        src = it.get('url') or it.get('play_url') or it.get('audio') or it.get('src')
                                        title = it.get('song') or it.get('title') or it.get('name') or it.get('songName') or '未知曲目'
                                        cover = it.get('cover') or it.get('pic') or it.get('image') or it.get('album_pic') or ''
                                        singer = it.get('singer') or it.get('artist') or it.get('singerName') or ''
                                        if src:
                                            track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                                else:
                                    src = data.get('url') or data.get('play_url') or data.get('audio') or data.get('src')
                                    title = data.get('song') or data.get('title') or data.get('name') or data.get('songName') or '未知曲目'
                                    cover = data.get('cover') or data.get('pic') or data.get('image') or data.get('album_pic') or ''
                                    singer = data.get('singer') or data.get('artist') or data.get('singerName') or ''
                                    if src:
                                        track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                        except Exception:
                            pass
                    if not track_list:
                        self.broadcast_message({
                            'type': MESSAGE_TYPE['SYSTEM'],
                            'sender': '音乐助手',
                            'message': '未找到对应的音乐资源~',
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                    else:
                        track = {
                            'title': query_kw or (track_list[0].get('title') or '音乐搜索'),
                            'src': track_list[0]['src'],
                            'status': 'stopped',
                            'track_list': track_list,
                            'current_index': 0
                        }
                        self.broadcast_message({
                            'type': 'music_card',
                            'track': track,
                            'sender': self.user.nickname,
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        self.broadcast_message({
                            'type': 'music_item',
                            'item': {
                                'title': track_list[0].get('title') or '未知曲目',
                                'singer': track_list[0].get('singer') or '',
                                'cover': track_list[0].get('cover') or '',
                                'lrc_url': '',
                                'detail_link': '',
                                'music_url': track_list[0].get('src')
                            },
                            'sender': self.user.nickname,
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        self.broadcast_message({
                            'type': 'music_state',
                            'status': 'play',
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                
                elif self.user.ai_chat_session:
                    # 如果用户正在AI会话中，直接将消息发送给AI
                    ai_query = content.strip()
                    self.write_message(json.dumps({
                        'type': MESSAGE_TYPE['TEXT'],
                        'sender': self.user.nickname,
                        'message': ai_query,
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    }))
                    
                    # 检查是否是结束会话指令
                    if self._is_end_session_command(ai_query):
                        self.user.ai_chat_session = False
                        self.user.ai_chat_history = []
                        response = {
                            'type': MESSAGE_TYPE['SYSTEM'],
                            'sender': '川小农',
                            'message': '会话已结束，期待下次与您交流！',
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        }
                    else:
                        # 调用AI模型获取回复
                        ai_response = self.get_ai_response(ai_query)
                        
                        # 保存对话历史
                        self.user.ai_chat_history.append({
                            'role': 'user',
                            'content': ai_query
                        })
                        self.user.ai_chat_history.append({
                            'role': 'assistant',
                            'content': ai_response
                        })
                        
                        response = {
                            'type': MESSAGE_TYPE['SYSTEM'],
                            'sender': '川小农',
                            'message': ai_response,
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        }
                    
                    self.write_message(json.dumps(response))
                # 音乐状态控制：来自前端的控制消息
                elif data.get('type') == 'music_control':
                    action = (data.get('action') or '').lower()
                    payload = { 'type': 'music_state', 'status': action, 'timestamp': datetime.now().strftime('%H:%M:%S') }
                    if action in ('play','pause','stop','close'):
                        pass
                    elif action == 'seek':
                        payload['position'] = float(data.get('position') or 0)
                    elif action == 'volume':
                        payload['volume'] = float(data.get('volume') or 1)
                    elif action == 'select_track':
                        payload['index'] = int(data.get('index') or 0)
                    elif action == 'search':
                        keyword = str(data.get('keyword') or '').strip()
                        url = 'https://v2.xxapi.cn/api/kugousearch'
                        api_key = (os.environ.get('XXAPI_KEY', '').strip() or '76c5dc52fcd1e3a8')
                        track_list = []
                        if api_key:
                            try:
                                params = {'key': api_key}
                                if keyword:
                                    kw = str(keyword).replace('“','').replace('”','').strip()
                                    if kw:
                                        params['music'] = kw
                                headers = {'User-Agent': 'DaiPChat/1.0'}
                                resp = requests.get(url, params=params, headers=headers, timeout=6)
                                result = resp.json()
                                data2 = result.get('data')
                                if isinstance(data2, list):
                                    for it in data2:
                                        src = it.get('url') or it.get('play_url') or it.get('audio') or it.get('src')
                                        title = it.get('song') or it.get('title') or it.get('name') or it.get('songName') or '未知曲目'
                                        cover = it.get('image') or it.get('cover') or it.get('pic') or it.get('album_pic') or ''
                                        singer = it.get('singer') or it.get('artist') or it.get('singerName') or ''
                                        if src:
                                            track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                                elif isinstance(data2, dict):
                                    lst = data2.get('list') or data2.get('items')
                                    if isinstance(lst, list):
                                        for it in lst:
                                            src = it.get('url') or it.get('play_url') or it.get('audio') or it.get('src')
                                            title = it.get('song') or it.get('title') or it.get('name') or it.get('songName') or '未知曲目'
                                            cover = it.get('image') or it.get('cover') or it.get('pic') or it.get('album_pic') or ''
                                            singer = it.get('singer') or it.get('artist') or it.get('singerName') or ''
                                            if src:
                                                track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                                    else:
                                        src = data2.get('url') or data2.get('play_url') or data2.get('audio') or data2.get('src')
                                        title = data2.get('song') or data2.get('title') or data2.get('name') or data2.get('songName') or '未知曲目'
                                        cover = data2.get('image') or data2.get('cover') or data2.get('pic') or data2.get('album_pic') or ''
                                        singer = data2.get('singer') or data2.get('artist') or data2.get('singerName') or ''
                                        if src:
                                            track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                            except Exception:
                                pass
                        if not track_list:
                            self.broadcast_message({
                                'type': MESSAGE_TYPE['SYSTEM'],
                                'sender': '音乐助手',
                                'message': '未找到对应的音乐资源~',
                                'timestamp': datetime.now().strftime('%H:%M:%S')
                            })
                            return
                        self.broadcast_message({
                            'type': 'music_card',
                            'track': {
                                'title': keyword or (track_list[0].get('title') or '搜索结果'),
                                'src': track_list[0]['src'],
                                'status': 'stopped',
                                'track_list': track_list,
                                'current_index': 0
                            },
                            'sender': self.user.nickname,
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        self.broadcast_message({
                            'type': 'music_item',
                            'item': {
                                'title': track_list[0].get('title') or '未知曲目',
                                'singer': track_list[0].get('singer') or '',
                                'cover': track_list[0].get('cover') or '',
                                'lrc_url': '',
                                'detail_link': '',
                                'music_url': track_list[0].get('src')
                            },
                            'sender': self.user.nickname,
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        self.broadcast_message({
                            'type': 'music_state',
                            'status': 'play',
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        return
                    elif action == 'search_item':
                        keyword = str(data.get('keyword') or '').strip()
                        n = int(data.get('n') or 1)
                        url = 'https://v2.xxapi.cn/api/kugousearch'
                        api_key = (os.environ.get('XXAPI_KEY', '').strip() or '76c5dc52fcd1e3a8')
                        try:
                            params = {'key': api_key}
                            if keyword:
                                kw = keyword.replace('“','').replace('”','').strip()
                                if kw:
                                    params['music'] = kw
                            headers = {'User-Agent': 'DaiPChat/1.0'}
                            resp = requests.get(url, params=params, headers=headers, timeout=6)
                            result = resp.json()
                            data2 = result.get('data')
                            track_list = []
                            if isinstance(data2, list):
                                for it in data2:
                                    src = it.get('url') or it.get('play_url') or it.get('audio') or it.get('src')
                                    title = it.get('song') or it.get('title') or it.get('name') or it.get('songName') or '未知曲目'
                                    cover = it.get('image') or it.get('cover') or it.get('pic') or it.get('album_pic') or ''
                                    singer = it.get('singer') or it.get('artist') or it.get('singerName') or ''
                                    if src:
                                        track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                            elif isinstance(data2, dict):
                                lst = data2.get('list') or data2.get('items')
                                if isinstance(lst, list):
                                    for it in lst:
                                        src = it.get('url') or it.get('play_url') or it.get('audio') or it.get('src')
                                        title = it.get('song') or it.get('title') or it.get('name') or it.get('songName') or '未知曲目'
                                        cover = it.get('image') or it.get('cover') or it.get('pic') or it.get('album_pic') or ''
                                        singer = it.get('singer') or it.get('artist') or it.get('singerName') or ''
                                        if src:
                                            track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                                else:
                                    src = data2.get('url') or data2.get('play_url') or data2.get('audio') or data2.get('src')
                                    title = data2.get('song') or data2.get('title') or data2.get('name') or data2.get('songName') or '未知曲目'
                                    cover = data2.get('image') or data2.get('cover') or data2.get('pic') or data2.get('album_pic') or ''
                                    singer = data2.get('singer') or data2.get('artist') or data2.get('singerName') or ''
                                    if src:
                                        track_list.append({'title': title, 'src': src, 'cover': cover, 'singer': singer})
                            idx = max(0, min((n or 1) - 1, len(track_list) - 1))
                            if track_list:
                                chosen = track_list[idx]
                                self.broadcast_message({
                                    'type': 'music_item',
                                    'item': {
                                        'title': chosen.get('title') or '未知曲目',
                                        'singer': chosen.get('singer') or '',
                                        'cover': chosen.get('cover') or '',
                                        'lrc_url': '',
                                        'detail_link': '',
                                        'music_url': chosen.get('src')
                                    },
                                    'sender': self.user.nickname,
                                    'timestamp': datetime.now().strftime('%H:%M:%S')
                                })
                                self.broadcast_message({
                                    'type': 'music_state',
                                    'status': 'play',
                                    'timestamp': datetime.now().strftime('%H:%M:%S')
                                })
                                return
                            else:
                                self.broadcast_message({
                                    'type': MESSAGE_TYPE['SYSTEM'],
                                    'sender': '音乐助手',
                                    'message': '未找到对应的音乐资源~',
                                    'timestamp': datetime.now().strftime('%H:%M:%S')
                                })
                                return
                        except Exception:
                            pass
                    else:
                        pass
                    self.broadcast_message(payload)
                    
                else:
                    # 处理emoji表情
                    content = emoji.emojize(content, variant='emoji_type')
                    
                    # 广播聊天消息
                    self.broadcast_message({
                        'type': MESSAGE_TYPE['TEXT'],
                        'sender': self.user.nickname,
                        'message': content,
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    })
                    
            # 处理用户退出
            elif data.get('type') == 'logout' and self.user:
                self.handle_user_leave()
                
        except Exception as e:
            print(f'处理消息时出错: {e}')
    
    def on_close(self):
        # 连接关闭时处理用户离开
        if self.user:
            self.handle_user_leave()
    
    def handle_user_leave(self):
        nickname = self.user.nickname
        if nickname in online_users:
            # 清除AI会话状态
            if hasattr(self.user, 'ai_chat_session'):
                self.user.ai_chat_session = False
                self.user.ai_chat_history = []
            
            del online_users[nickname]
            
            # 广播用户离开消息
            self.broadcast_message({
                'type': MESSAGE_TYPE['USER_LEAVE'],
                'nickname': nickname,
                'message': f'{nickname} 离开了聊天室',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            
            # 更新所有用户的在线列表
            self.update_user_list()
    
    def broadcast_message(self, message, exclude=None):
        for user in online_users.values():
            if exclude and user == exclude:
                continue
            try:
                user.ws.write_message(json.dumps(message))
            except:
                pass
        try:
            if DB_AVAILABLE:
                cur = db.cursor()
                cur.execute('INSERT INTO raw_data(username,dtype,content) VALUES(?,?,?)', (getattr(self, 'user', None).nickname if getattr(self, 'user', None) else '', str(message.get('type')), json.dumps(message, ensure_ascii=False)))
                db.commit()
        except Exception:
            pass
    
    def update_user_list(self):
        # 获取在线用户列表
        user_list = list(online_users.keys())
        
        # 发送给所有在线用户
        for user in online_users.values():
            try:
                user.ws.write_message(json.dumps({
                    'type': MESSAGE_TYPE['USER_LIST'],
                    'users': user_list
                }))
            except:
                pass
    
    def _is_end_session_command(self, command):
        """检查是否是结束会话的指令"""
        command = command.strip()
        for end_cmd in AI_END_SESSION_COMMANDS:
            if end_cmd in command:
                return True
        return False
    
    def get_ai_response(self, query):
        """调用AI大模型获取回复"""
        try:
            if AI_CONFIG['API_TYPE'] == 'huggingface':
                # 使用Hugging Face API
                url = AI_CONFIG['API_URL']
                headers = {
                    'Content-Type': 'application/json'
                }
                
                system_prompt = '你是川小农，一个友好的AI助手。请用自然、友好的语言回答用户的问题。'
                history_text = ''
                if hasattr(self.user, 'ai_chat_history'):
                    for msg in self.user.ai_chat_history:
                        if msg.get('role') == 'user':
                            history_text += f"用户：{msg.get('content','')}\n"
                        elif msg.get('role') == 'assistant':
                            history_text += f"助手：{msg.get('content','')}\n"
                prompt = f"<s>[INST] {system_prompt}\n{history_text}用户：{query}\n请直接回答。 [/INST]"
                data = {
                    'inputs': prompt,
                    'parameters': {
                        'max_new_tokens': AI_CONFIG['MAX_TOKENS'],
                        'temperature': AI_CONFIG['TEMPERATURE'],
                        'return_full_text': False
                    }
                }
                
                # 发送请求
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                if isinstance(result, list) and len(result) > 0 and 'generated_text' in result[0]:
                    return result[0]['generated_text'].strip()
                elif 'error' in result:
                    print(f"Hugging Face API错误: {result['error']}")
                    return "很抱歉，AI服务暂时不可用，请稍后再试。"
                
            elif AI_CONFIG['API_TYPE'] == 'doubao':
                url = AI_CONFIG['API_URL']
                api_key = AI_CONFIG.get('API_KEY') or os.environ.get('DOUBAO_API_KEY', '')
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {api_key}"
                }
                system_prompt = (
                    '你是川小农，一个友好的中文助理。'
                    '请只围绕用户的当次问题作答，避免跑题。'
                    '如果问题不明确，先提出澄清问题；不要臆测。'
                )
                messages = [{'role': 'system', 'content': system_prompt}]
                history = []
                if hasattr(self.user, 'ai_chat_history'):
                    history = self.user.ai_chat_history[-8:]
                messages.extend(history)
                messages.append({'role': 'user', 'content': query})
                data = {
                    'model': AI_CONFIG.get('MODEL', ''),
                    'messages': messages,
                    'max_tokens': AI_CONFIG['MAX_TOKENS'],
                    'temperature': AI_CONFIG['TEMPERATURE'],
                    'top_p': 0.9
                }
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()
                
            elif AI_CONFIG['API_TYPE'] == 'siliconflow':
                url = AI_CONFIG['API_URL']
                api_key = AI_CONFIG.get('API_KEY') or os.environ.get('SILICONFLOW_API_KEY', '')
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {api_key}"
                }
                system_prompt = (
                    '你叫川小农，是一个友好的中文助理。'
                    '严格围绕用户当次问题作答，避免跑题。'
                    '当用户说“结束会话”、“结束对话”、“退出”或“再见”时，结束会话并礼貌告别。'
                )
                messages = [{'role': 'system', 'content': system_prompt}]
                if hasattr(self.user, 'ai_chat_history'):
                    messages.extend(self.user.ai_chat_history[-8:])
                messages.append({'role': 'user', 'content': query})
                data = {
                    'model': AI_CONFIG.get('MODEL', ''),
                    'messages': messages,
                    'max_tokens': AI_CONFIG['MAX_TOKENS'],
                    'temperature': AI_CONFIG['TEMPERATURE']
                }
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()

            elif AI_CONFIG['API_TYPE'] == 'local':
                url = AI_CONFIG['API_URL']
                headers = {
                    'Content-Type': 'application/json'
                }
                system_prompt = (
                    '你叫川小农，是一个友好的中文助理。'
                    '严格围绕用户当次问题作答，避免跑题。'
                    '当用户说“结束会话”、“结束对话”、“退出”或“再见”时，结束会话并礼貌告别。'
                )
                messages = [{'role': 'system', 'content': system_prompt}]
                if hasattr(self.user, 'ai_chat_history'):
                    messages.extend(self.user.ai_chat_history[-8:])
                messages.append({'role': 'user', 'content': query})
                data = {
                    'model': AI_CONFIG.get('MODEL', ''),
                    'messages': messages,
                    'max_tokens': AI_CONFIG['MAX_TOKENS'],
                    'temperature': AI_CONFIG['TEMPERATURE']
                }
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()

            elif AI_CONFIG['API_TYPE'] == 'openai':
                url = AI_CONFIG['API_URL']
                api_key = AI_CONFIG.get('API_KEY') or os.environ.get('OPENAI_API_KEY', '')
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {api_key}"
                }
                system_prompt = (
                    '你叫川小农，是一个友好的中文助理。'
                    '严格围绕用户当次问题作答，避免跑题。'
                    '当用户说“结束会话”、“结束对话”、“退出”或“再见”时，结束会话并礼貌告别。'
                )
                messages = [{'role': 'system', 'content': system_prompt}]
                if hasattr(self.user, 'ai_chat_history'):
                    messages.extend(self.user.ai_chat_history[-8:])
                messages.append({'role': 'user', 'content': query})
                data = {
                    'model': AI_CONFIG.get('MODEL', 'gpt-3.5-turbo'),
                    'messages': messages,
                    'max_tokens': AI_CONFIG['MAX_TOKENS'],
                    'temperature': AI_CONFIG['TEMPERATURE']
                }
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()
        
        except requests.exceptions.RequestException as e:
            print(f"AI API请求异常: {e}")
        except Exception as e:
            print(f"AI回复生成异常: {e}")
        
        # 异常情况下返回模拟回复
        responses = [
            '你好！我是川小农，很高兴为你服务。',
            '这个问题很有趣，让我思考一下...',
            '谢谢你的提问，我会尽力帮助你。',
            '建议你尝试一下不同的角度来看待这个问题。',
            '我认为这是一个很好的想法！'
        ]
        return responses[hash(query) % len(responses)]

# 登录页面处理器
class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            host = self.request.host
            servers = [
                {'name': '本地服务器', 'url': f'ws://127.0.0.1:{SERVER_PORT}/ws'},
                {'name': '局域网服务器', 'url': f'ws://{host}/ws'}
            ]
            self.render('login.html', servers=servers)
        except Exception as e:
            import traceback
            print(f"LoginHandler.get error: {e}")
            print(traceback.format_exc())
            self.set_status(500)
            self.finish(f"Internal Server Error: {e}")

# 聊天页面处理器
class ChatHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            # 先尝试从cookie获取用户信息
            u = self.get_secure_cookie('user')
            if u:
                nickname = u.decode('utf-8')
            else:
                # 如果没有cookie，尝试从URL参数获取
                nickname = self.get_argument('nickname', '').strip()
                if not nickname:
                    self.redirect('/')
                    return
                # 设置cookie以便后续使用
                self.set_secure_cookie('user', nickname, httponly=True, samesite='Lax', expires_days=7, path='/')
            self.render('chat.html', nickname=nickname)
        except Exception as e:
            import traceback
            print(f"ChatHandler.get error: {e}")
            print(traceback.format_exc())
            self.set_status(500)
            self.finish(f"Internal Server Error: {e}")

class RegisterHandler(tornado.web.RequestHandler):
    def post(self):
        if not ensure_db():
            self.set_status(503); self.finish({'error':'数据库不可用，请联系管理员或设置SQLITE_PATH环境变量'}); return
        try:
            data = json.loads(self.request.body.decode('utf-8'))
        except Exception:
            self.set_status(400); self.finish({'error':'请求格式错误'}); return
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        if not re.fullmatch(r'^[A-Za-z0-9_]{3,16}$', username):
            self.set_status(400); self.finish({'error':'用户名格式不合法'}); return
        if len(password) < 8 or len(password) > 20:
            self.set_status(400); self.finish({'error':'密码长度不合法'}); return
        cur = db.cursor()
        cur.execute('SELECT id FROM users WHERE username=?', (username,))
        if cur.fetchone():
            self.set_status(409); self.finish({'error':'用户名已存在'}); return
        h = pw_hash(password)
        cur.execute('INSERT INTO users(username,password_hash) VALUES(?,?)', (username, h))
        db.commit()
        self.finish({'ok':True})

class LoginApiHandler(tornado.web.RequestHandler):
    def post(self):
        if not ensure_db():
            self.set_status(503); self.finish({'error':'数据库不可用，请联系管理员或设置SQLITE_PATH环境变量'}); return
        try:
            data = json.loads(self.request.body.decode('utf-8'))
        except Exception:
            self.set_status(400); self.finish({'error':'请求格式错误'}); return
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        cur = db.cursor()
        cur.execute('SELECT id,password_hash FROM users WHERE username=?', (username,))
        row = cur.fetchone()
        if not row:
            self.set_status(401); self.finish({'error':'账号或密码错误'}); return
        try:
            stored = row['password_hash'] if isinstance(row, sqlite3.Row) or isinstance(row, dict) else row[1]
        except Exception:
            stored = row[1] if isinstance(row, (list, tuple)) else row['password_hash']
        if not pw_check(password, stored):
            self.set_status(401); self.finish({'error':'账号或密码错误'}); return
        self.set_secure_cookie('user', username, httponly=True, samesite='Lax', expires_days=7, path='/')
        self.finish({'ok':True, 'redirect':'/chat'})

class WhoAmIHandler(tornado.web.RequestHandler):
    def get(self):
        u = self.get_secure_cookie('user')
        self.finish({'user': u.decode('utf-8') if u else None})

class ConfigHandler(tornado.web.RequestHandler):
    def get(self):
        port = CURRENT_PORT or SERVER_PORT
        self.finish({
            'http_port': port,
            'ws_url_local': f'ws://127.0.0.1:{port}/ws',
            'ws_url_lan': f'ws://{self.request.host.split(":")[0]}:{port}/ws'
        })

class DbHealthHandler(tornado.web.RequestHandler):
    def get(self):
        import os
        ok = ensure_db()
        path = CURRENT_DB_PATH
        exists = os.path.exists(path)
        size = 0
        err = None
        can_read = False
        can_write = False
        try:
            if exists:
                size = os.path.getsize(path)
            if ok:
                cur = db.cursor()
                cur.execute('SELECT COUNT(*) as c FROM users')
                _ = cur.fetchone()
                can_read = True
                cur.execute('INSERT INTO raw_data(username,dtype,content) VALUES(?,?,?)', ('system','health_check','ok'))
                db.commit()
                can_write = True
                cur.execute("DELETE FROM raw_data WHERE dtype='health_check'")
                db.commit()
        except Exception as e:
            err = str(e)
        self.finish({'ok': ok, 'path': path, 'exists': exists, 'size': size, 'can_read': can_read, 'can_write': can_write, 'error': err})

class DataListHandler(tornado.web.RequestHandler):
    def get(self):
        if not DB_AVAILABLE:
            self.set_status(503); self.finish({'error':'数据库不可用'}); return
        date = (self.get_argument('date','') or '').strip()
        keyword = (self.get_argument('q','') or '').strip()
        sql = 'SELECT id, username, dtype, content, created_at FROM raw_data WHERE 1=1'
        params = []
        if date:
            sql += " AND date(created_at)=date(?)"; params.append(date)
        if keyword:
            sql += " AND content LIKE ?"; params.append(f"%{keyword}%")
        sql += ' ORDER BY created_at DESC LIMIT 200'
        cur = db.cursor()
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        self.finish({'items': rows})

class AudioProxyHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument('url', None)
        if not url or not (url.startswith('http://') or url.startswith('https://')):
            self.set_status(400)
            self.finish('invalid')
            return
        try:
            # 透传常见头，提升外部源的兼容性（部分站点需要 UA/Referer/Range）
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
                'Accept': 'audio/*;q=0.9,*/*;q=0.8'
            }
            req_range = self.request.headers.get('Range')
            if req_range:
                headers['Range'] = req_range
            # 尝试设置 Referer 为资源域名
            try:
                from urllib.parse import urlparse
                p = urlparse(url)
                headers['Referer'] = f'{p.scheme}://{p.hostname or ""}'
            except Exception:
                pass

            r = requests.get(url, headers=headers, stream=True, timeout=12)
            status = r.status_code
            if status not in (200, 206):
                self.set_status(502)
                self.finish('error')
                return

            # 透传关键响应头
            ct = r.headers.get('Content-Type') or 'audio/mpeg'
            cr = r.headers.get('Content-Range')
            cl = r.headers.get('Content-Length')
            ar = r.headers.get('Accept-Ranges') or ('bytes' if req_range else None)
            self.set_header('Content-Type', ct)
            self.set_header('Cache-Control', 'no-cache')
            self.set_header('Access-Control-Allow-Origin', '*')
            if cr:
                self.set_header('Content-Range', cr)
            if cl:
                self.set_header('Content-Length', cl)
            if ar:
                self.set_header('Accept-Ranges', ar)
            if status == 206:
                self.set_status(206)

            for chunk in r.iter_content(65536):
                if chunk:
                    self.write(chunk)
                    self.flush()
            self.finish()
        except Exception:
            self.set_status(502)
            self.finish('error')

# 主应用
def make_app():
    return tornado.web.Application([
        (r'/', LoginHandler),
        (r'/api/register', RegisterHandler),
        (r'/api/login', LoginApiHandler),
        (r'/api/whoami', WhoAmIHandler),
        (r'/api/config', ConfigHandler),
        (r'/api/health/db', DbHealthHandler),
        (r'/api/data/list', DataListHandler),
        (r'/chat', ChatHandler),
        (r'/ws', ChatWebSocketHandler),
        (r'/proxy/audio', AudioProxyHandler),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static'}),
    ], template_path='templates', cookie_secret=COOKIE_SECRET)

if __name__ == '__main__':
    app = make_app()
    try:
        app.listen(SERVER_PORT)
        CURRENT_PORT = SERVER_PORT
    except Exception as e:
        import socket
        bound = False
        for p in range(SERVER_PORT + 1, SERVER_PORT + 11):
            try:
                app.listen(p)
                CURRENT_PORT = p
                bound = True
                break
            except Exception:
                continue
        if not bound:
            raise e
    print(f'服务器启动在 http://127.0.0.1:{CURRENT_PORT}')
    tornado.ioloop.IOLoop.current().start()
