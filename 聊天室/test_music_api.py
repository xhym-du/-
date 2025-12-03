import requests

# 测试音乐API
def test_music_api(song_name):
    try:
        print(f"\n=== 测试歌曲: {song_name} ===")
        
        # 第一步：搜索歌曲
        search_url = "http://mobilecdn.kugou.com/api/v3/search/song"
        search_params = {
            'format': 'json',
            'keyword': song_name,
            'page': 1,
            'pagesize': 1
        }
        
        print(f"第一步：搜索歌曲")
        print(f"URL: {search_url}")
        print(f"参数: {search_params}")
        
        search_response = requests.get(search_url, params=search_params, timeout=10)
        print(f"响应状态码: {search_response.status_code}")
        
        search_response.raise_for_status()
        search_data = search_response.json()
        print(f"响应内容: {search_data}")
        
        # 检查搜索结果
        if search_data.get('errcode') == 0 and search_data.get('data'):
            song_list = search_data.get('data', {}).get('info', [])
            if song_list:
                first_song = song_list[0]
                hash_value = first_song.get('hash')
                album_id = first_song.get('album_id')
                
                print(f"\n搜索成功，提取信息：")
                print(f"歌曲: {first_song.get('songname')}")
                print(f"歌手: {first_song.get('singername')}")
                print(f"Hash: {hash_value}")
                print(f"Album ID: {album_id}")
                
                if hash_value:
                    # 第二步：获取播放链接
                    play_url = "http://www.kugou.com/yy/index.php"
                    play_params = {
                        'r': 'play/getdata',
                        'hash': hash_value
                    }
                    
                    # 设置Cookie和请求头
                    cookies = {
                        'kg_mid': 't=1234567890',
                        'kg_dfid': '1234567890'
                    }
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Referer': 'http://www.kugou.com/'
                    }
                    
                    print(f"\n第二步：获取播放链接")
                    print(f"URL: {play_url}")
                    print(f"参数: {play_params}")
                    print(f"Cookie: {cookies}")
                    print(f"Headers: {headers}")
                    
                    play_response = requests.get(play_url, params=play_params, cookies=cookies, headers=headers, timeout=10)
                    print(f"响应状态码: {play_response.status_code}")
                    
                    play_response.raise_for_status()
                    play_data = play_response.json()
                    print(f"响应内容: {play_data}")
                    
                    # 检查播放链接获取结果
                    if play_data.get('status') == 1 and play_data.get('data'):
                        data = play_data.get('data')
                        play_link = data.get('play_url')
                        img = data.get('img')
                        author_name = data.get('author_name')
                        audio_name = data.get('audio_name')
                        
                        print(f"\n播放信息提取成功：")
                        print(f"播放链接: {play_link}")
                        print(f"封面图片: {img}")
                        print(f"歌手: {author_name}")
                        print(f"歌名: {audio_name}")
                        
                        return True
                    else:
                        print(f"无法获取歌曲播放信息")
                        return False
                else:
                    print(f"无法找到该歌曲的Hash值")
                    return False
            else:
                print(f"未找到歌曲 '{song_name}'")
                return False
        else:
            print(f"搜索歌曲 '{song_name}' 失败")
            return False
            
    except Exception as e:
        print(f"请求异常: {str(e)}")
        return False

# 测试几首歌曲
if __name__ == "__main__":
    print("测试音乐API...")
    songs = ["小幸运", "成都"]
    
    for song in songs:
        success = test_music_api(song)
        if success:
            print(f"✅ 歌曲 '{song}' API调用成功！")
        else:
            print(f"❌ 歌曲 '{song}' API调用失败！")
            
        print("="*50)