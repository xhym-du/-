import os
import re

print("搜索项目中所有文件的天气相关错误信息:")
for root, dirs, files in os.walk('.'):
    for f in files:
        # 跳过一些不需要搜索的文件和目录
        if f.endswith('.pyc') or f.startswith('.') or root.startswith('./__pycache__'):
            continue
            
        file_path = os.path.join(root, f)
        
        # 跳过自身文件
        if os.path.basename(file_path) == 'search_error.py':
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # 特别关注app.py文件
                if os.path.basename(file_path) == 'app.py':
                    # 搜索所有天气相关的错误信息
                    # 使用更精确的正则表达式，查找实际的错误处理代码
                    error_pattern = re.compile(r'天气.*?(繁忙|错误|失败|不可用|超时)')
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines):
                        if error_pattern.search(line):
                            # 检查是否是错误处理代码（包含返回信息或错误处理）
                            if any(keyword in line for keyword in ['return', 'message', '错误', '繁忙', '失败', 'except']):
                                print(f"{file_path} 第{i+1}行: {line.strip()}")
        except:
            # 只处理文本文件
                pass

print("搜索完成!")