#!/usr/bin/env python3
# 调试脚本来运行app.py并捕获异常

print("开始调试app.py...")

try:
    import sys
    import os
    import traceback
    
    # 添加当前目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 导入app模块
    import app
    print("✅ app模块导入成功")
    
    # 尝试运行服务器
    print("尝试运行服务器...")
    
    # 覆盖socketio.run以打印调试信息
    original_run = app.socketio.run
    def debug_run(*args, **kwargs):
        print(f"调用socketio.run，参数: {args}, {kwargs}")
        try:
            original_run(*args, **kwargs)
        except Exception as e:
            print(f"❌ socketio.run抛出异常: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise
    
    app.socketio.run = debug_run
    
    # 执行app.py的主程序
    if __name__ == "__main__":
        # 直接运行app.py的主逻辑
        import subprocess
        subprocess.run(['python', 'app.py'], timeout=5)
        
except Exception as e:
    print(f"❌ 发生异常: {type(e).__name__}: {e}")
    traceback.print_exc()