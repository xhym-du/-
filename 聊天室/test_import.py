#!/usr/bin/env python3
# 测试app模块是否能正常导入

print("开始测试app模块导入...")

try:
    import sys
    import os
    
    # 添加当前目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 尝试导入app模块
    import app
    print("✅ app模块导入成功!")
    
    # 检查关键组件是否存在
    if hasattr(app, 'app'):
        print("✅ Flask app对象存在")
    if hasattr(app, 'socketio'):
        print("✅ SocketIO对象存在")
    if hasattr(app, 'handle_message'):
        print("✅ handle_message函数存在")
        
    print("\n测试完成，所有关键组件都存在!")
    
except Exception as e:
    print(f"❌ 导入错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()