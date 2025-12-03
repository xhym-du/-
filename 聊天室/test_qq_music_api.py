import requests
import json

def test_qq_music_api(song_name):
    """测试QQ音乐API"""
    print(f"测试歌曲: {song_name}")
    
    # 1. 搜索歌曲
    search_url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    search_params = {
        'ct': '24',
        'qqmusic_ver': '1298',
        'new_json': '1',
        'remoteplace': 'txt.yqq.center',
        'searchid': '57113331384710553',
        't': '0',
        'aggr': '1',
        'cr': '1',
        'catZhida': '1',
        'lossless': '0',
        'flag_qc': '0',
        'p': '1',
        'n': '20',
        'w': song_name,
        'g_tk_new_20200303': '5381',
        'g_tk': '5381',
        'loginUin': '0',
        'hostUin': '0',
        'format': 'json',
        'inCharset': 'utf8',
        'outCharset': 'utf-8',
        'notice': '0',
        'platform': 'yqq.json',
        'needNewCode': '0'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://y.qq.com/portal/search.html'
    }
    
    try:
        search_response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        print(f"搜索API状态码: {search_response.status_code}")
        search_data = search_response.json()
        print(f"搜索API响应: {json.dumps(search_data, ensure_ascii=False, indent=2)}")
        
        # 2. 解析搜索结果
        if search_data.get('code') == 0:
            songs = search_data.get('data', {}).get('song', {}).get('list', [])
            if songs:
                song = songs[0]
                song_id = song.get('mid')
                song_name = song.get('name')
                artists = song.get('singer', [])
                artist_names = ', '.join([artist.get('name') for artist in artists])
                album_pic = f"https://y.qq.com/music/photo_new/T002R300x300M000{song.get('album', {}).get('mid')}.jpg"
                play_url = f"https://y.qq.com/n/ryqq/songDetail/{song_id}"
                
                print(f"\n搜索结果:")
                print(f"歌曲ID: {song_id}")
                print(f"歌曲名: {song_name}")
                print(f"歌手: {artist_names}")
                print(f"专辑封面: {album_pic}")
                print(f"播放链接: {play_url}")
                
                # 3. 测试专辑封面链接是否有效
                cover_response = requests.head(album_pic, headers=headers, allow_redirects=True, timeout=10)
                print(f"专辑封面状态码: {cover_response.status_code}")
                
                return True
            else:
                print("未找到歌曲")
                return False
        else:
            print(f"搜索API调用失败: {search_data.get('msg')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return False

if __name__ == "__main__":
    # 测试歌曲列表
    test_songs = ["小幸运", "成都"]
    
    for song in test_songs:
        print("=" * 50)
        test_qq_music_api(song)
        print("=" * 50)
        print()