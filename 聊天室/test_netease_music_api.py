import requests
import json

def test_netease_music_api(song_name):
    """测试网易云音乐API"""
    print(f"测试歌曲: {song_name}")
    
    # 1. 搜索歌曲获取歌曲ID
    search_url = f"https://music.163.com/api/search/get?type=1&s={song_name}&offset=0&limit=1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        search_response = requests.get(search_url, headers=headers, timeout=10)
        print(f"搜索API状态码: {search_response.status_code}")
        search_data = search_response.json()
        print(f"搜索API响应: {json.dumps(search_data, ensure_ascii=False, indent=2)}")
        
        # 2. 解析搜索结果
        if search_data.get('code') == 200:
            songs = search_data.get('result', {}).get('songs', [])
            if songs:
                song = songs[0]
                song_id = song.get('id')
                song_name = song.get('name')
                artist = '/'.join([artist.get('name') for artist in song.get('artists', [])])
                album = song.get('album', {}).get('name')
                album_pic_url = song.get('album', {}).get('picUrl')
                
                print(f"\n搜索结果:")
                print(f"歌曲ID: {song_id}")
                print(f"歌曲名: {song_name}")
                print(f"歌手: {artist}")
                print(f"专辑: {album}")
                print(f"专辑封面: {album_pic_url}")
                
                # 3. 获取歌曲播放链接
                play_url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
                print(f"\n播放链接: {play_url}")
                
                # 4. 测试播放链接是否有效
                play_response = requests.head(play_url, headers=headers, allow_redirects=True, timeout=10)
                print(f"播放链接状态码: {play_response.status_code}")
                print(f"播放链接最终URL: {play_response.url}")
                
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
        test_netease_music_api(song)
        print("=" * 50)
        print()