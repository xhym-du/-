from openai import OpenAI
import traceback

# 配置 DeepSeek 客户端
client = OpenAI(
    api_key="sk-gzxavqqlvlxdtlxdnvvisgruvsktvdfwlqmdqfstmsbbsxuj",
    base_url="https://api.deepseek.com"
)

# 测试对话
messages = [
    {"role": "system", "content": "你是四川农业大学的AI小助手小美，使用友好的语气回答问题。"},
    {"role": "user", "content": "你好"}
]

try:
    print("开始调用DeepSeek API...")
    completion = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        max_tokens=500,
        temperature=0.7
    )
    print("API调用成功!")
    print(f"响应: {completion}")
    print(f"AI回复: {completion.choices[0].message.content}")
except Exception as e:
    print("API调用失败!")
    print(f"错误类型: {type(e)}")
    print(f"错误信息: {e}")
    traceback.print_exc()