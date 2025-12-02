import requests
from bs4 import BeautifulSoup

def baidu_spider(keyword):
    """
    百度搜索爬虫函数
    :param keyword: 搜索关键字
    :return: 搜索结果列表，每个结果包含标题、概要、URL和封面URL
    """
    try:
        # 构建搜索URL
        url = f"https://www.baidu.com/s?wd={keyword}"
        
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,en-GB;q=0.6'
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取搜索结果
        results = []
        search_items = soup.find_all('div', class_='result')
        
        for item in search_items:
            # 提取标题
            title_tag = item.find('h3')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            
            # 提取URL
            url_tag = title_tag.find('a')
            if not url_tag:
                continue
            url = url_tag.get('href', '')
            
            # 提取概要
            summary_tag = item.find('div', class_='c-abstract')
            summary = summary_tag.get_text(strip=True) if summary_tag else ''
            
            # 提取封面URL（如果有）
            cover_url = ''
            cover_tag = item.find('img', class_='c-img')
            if cover_tag:
                cover_url = cover_tag.get('src', '')
            
            # 添加到结果列表
            if title and url:
                results.append({
                    'title': title,
                    'summary': summary,
                    'url': url,
                    'cover_url': cover_url
                })
        
        return results
    
    except Exception as e:
        print(f"爬虫出错: {str(e)}")
        return []

# Dify兼容的函数接口
def main(keyword: str):
    """
    Dify兼容的主函数接口
    :param keyword: 搜索关键字
    :return: 结构化的搜索结果
    """
    results = baidu_spider(keyword)
    return {
        "result": results
    }