## 笔记 1：OpenAI SDK 基础与调用

> 合并来源：`from openai import OpenAI与import openai区别` + `OpenAI SDK调用DeepSeek API` + `chat.completions.create方法详解`

### 一句话定义

OpenAI Python SDK (v1.x+) 通过面向对象的客户端模式调用大语言模型，通过 `base_url` 可兼容 DeepSeek 等第三方 API，核心方法 `chat.completions.create()` 控制模型选择、对话内容和生成行为。

### SDK 版本与导入

```python
# ✅ 新版 v1.x+（当前推荐）
from openai import OpenAI
client = OpenAI(api_key="sk-xxx", base_url="https://api.deepseek.com")

# ❌ 旧版 v0.x（已废弃）
import openai
openai.api_key = "sk-xxx"
openai.ChatCompletion.create(...)  # 已不可用
```

| 对比项 | 旧版 v0.x | 新版 v1.x+ |
|--------|-----------|------------|
| 风格 | 面向过程，全局配置 | 面向对象，客户端实例 |
| 密钥管理 | 全局变量，多账户切换困难 | 每个客户端独立配置 |
| 调用方式 | `openai.ChatCompletion.create()` | `client.chat.completions.create()` |
| 多服务支持 | 配置互相覆盖 | 创建多个客户端，互不干扰 |

```python
# 新版多服务独立调用示例
from openai import OpenAI

openai_client = OpenAI(api_key="key-for-openai")
deepseek_client = OpenAI(
    api_key="key-for-deepseek",
    base_url="https://api.deepseek.com"
)

openai_client.chat.completions.create(...)     # → OpenAI
deepseek_client.chat.completions.create(...)   # → DeepSeek
```

### 调用 DeepSeek API

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"          # 关键：指向 DeepSeek
)

response = client.chat.completions.create(
    model="deepseek-chat",                        # DeepSeek 模型名
    messages=[{"role": "user", "content": "你好"}]
)
print(response.choices[0].message.content)
```

请求流程：`环境变量读取 Key` → `创建客户端（指向 DeepSeek）` → `构建请求` → `POST 到 https://api.deepseek.com/chat/completions` → `解析响应`

### chat.completions.create() 方法

#### 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `model` | `str` | 模型名称，如 `"deepseek-chat"`、`"gpt-4o"` |
| `messages` | `list[dict]` | 对话消息列表，按时间顺序 |

#### 消息格式

```python
{"role": "system",    "content": "你是一个有帮助的助手"}   # 系统提示
{"role": "user",      "content": "你好"}                  # 用户输入
{"role": "assistant", "content": "你好！有什么可以帮你？"}  # 模型回复
```

#### 常用可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `temperature` | `float` | `1.0` | 随机性控制。`0` = 确定性输出 |
| `max_tokens` | `int` | 模型默认 | 最大生成 token 数 |
| `top_p` | `float` | `1.0` | 核采样，与 temperature 二选一 |
| `n` | `int` | `1` | 候选回复数 |
| `stream` | `bool` | `False` | 是否流式输出 |
| `stop` | `str/list` | `None` | 停止生成的字符串 |

#### 返回值结构

```python
response
├── id                 # 请求唯一标识
├── model              # 实际使用的模型
├── choices[]          # 候选回复列表
│   ├── index          # 候选索引
│   ├── message
│   │   ├── role       # "assistant"
│   │   └── content    # 回复文本
│   └── finish_reason  # "stop" / "length"
├── usage              # token 用量
│   ├── prompt_tokens
│   ├── completion_tokens
│   └── total_tokens
└── created
```

```python
print(response.choices[0].message.content)
print(response.usage.total_tokens)
print(response.choices[0].finish_reason)
```

### 注意事项

- `import openai` 对应旧版 v0.x 已废弃，当前应使用 `from openai import OpenAI`
- `base_url` 只改变请求地址，SDK 逻辑不变；`model` 须使用目标服务的模型名
- 多轮对话需手动维护 `messages` 列表，将历史消息一起传入
- `temperature` 和 `top_p` 不要同时大幅调整，通常只调其中一个

### 相关笔记

- [[流式输出与SSE协议]]
- [[Function Calling 规范与实践]]

