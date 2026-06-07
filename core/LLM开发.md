# LLM开发

> **来源清单**（已提炼）：
> - [x] 01_OpenAI_SDK基础与调用
> - [x] 02_流式输出与SSE协议
> - [x] 03_Function_Calling规范与实践
>
> **更新时间**：2026-06-07

## 一、OpenAI SDK基础与调用

### SDK版本与导入

新版SDK (v1.x+) 采用面向对象的客户端模式，通过 `base_url` 可兼容DeepSeek等第三方API。

```python
# 新版 v1.x+（推荐）
from openai import OpenAI
client = OpenAI(api_key="sk-xxx", base_url="https://api.deepseek.com")

# 旧版 v0.x（已废弃）
import openai  # 不再使用
```

| 对比项 | 旧版 v0.x | 新版 v1.x+ |
|--------|-----------|------------|
| 风格 | 面向过程，全局配置 | 面向对象，客户端实例 |
| 密钥管理 | 全局变量，多账户切换困难 | 每个客户端独立配置 |
| 调用方式 | `openai.ChatCompletion.create()` | `client.chat.completions.create()` |
| 多服务支持 | 配置互相覆盖 | 创建多个客户端，互不干扰 |

📄 [原文01: OpenAI SDK基础与调用](../raw/LLM开发/01_OpenAI_SDK基础与调用.md)

### 调用DeepSeek API

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}]
)
print(response.choices[0].message.content)
```

请求流程：`环境变量读取Key` → `创建客户端` → `构建请求` → `POST到API端点` → `解析响应`

📄 [原文01: OpenAI SDK基础与调用](../raw/LLM开发/01_OpenAI_SDK基础与调用.md)

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

```
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

📄 [原文01: OpenAI SDK基础与调用](../raw/LLM开发/01_OpenAI_SDK基础与调用.md)

### 注意事项

- `base_url` 只改变请求地址，SDK逻辑不变；`model` 须使用目标服务的模型名
- 多轮对话需手动维护 `messages` 列表，将历史消息一起传入
- `temperature` 和 `top_p` 不要同时大幅调整，通常只调其中一个

---

## 二、流式输出与SSE协议

### SSE协议基础

SSE (Server-Sent Events) 是一种服务端向客户端推送数据的技术，基于HTTP协议，服务端通过同一个连接持续推送文本片段。

```
传统HTTP：
客户端 → 发请求 → 服务端
客户端 ← 完整响应 ← 服务端
（连接关闭）

SSE：
客户端 → 发请求 → 服务端
客户端 ← 数据片段1 ← 服务端
客户端 ← 数据片段2 ← 服务端
客户端 ← ...       ← 服务端
（连接保持打开，持续推送）
```

#### HTTP响应头

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

- `Content-Type: text/event-stream`：标识SSE流
- 无 `Content-Length`：总长度未知

#### SSE消息格式

```
data: 你

data: 好

data: ！

data: [DONE]
```

每条消息由 `字段名: 值` 组成，消息之间用**两个换行符**分隔。

#### 支持的字段

| 字段 | 说明 | 是否必填 |
|------|------|----------|
| `data` | 消息内容 | 是 |
| `event` | 事件类型（自定义） | 否 |
| `id` | 消息ID（断线重连用） | 否 |
| `retry` | 重连间隔（毫秒） | 否 |

#### 通信方式对比

| | 传统请求 | SSE | WebSocket |
|---|---|---|---|
| 方向 | 双向（请求-响应） | 服务端→客户端单向 | 双向 |
| 协议 | HTTP | HTTP | 独立协议 (ws://) |
| 连接 | 每次新建 | 持续复用 | 持续复用 |
| 典型场景 | 普通API | 大模型输出、实时通知 | 聊天室、游戏 |

📄 [原文02: 流式输出与SSE协议](../raw/LLM开发/02_流式输出与SSE协议.md)

### SDK流式调用

```python
from openai import OpenAI

client = OpenAI(api_key="sk-xxx", base_url="https://api.deepseek.com")

stream = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}],
    stream=True
)

for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)
```

#### chunk数据结构

```python
chunk = ChatCompletionChunk(
    id="chatcmpl-abc123",
    choices=[ChunkChoice(
        index=0,
        delta=Delta(role="assistant", content="你"),
        finish_reason=None
    )]
)
```

#### delta vs message（关键区别）

```
非流式 → response.choices[0].message.content    ← 完整回复
流式   → chunk.choices[0].delta.content          ← 增量片段
```

#### print参数

| 参数 | 作用 |
|------|------|
| `end=""` | 不换行，文本连续拼接 |
| `flush=True` | 立即刷新缓冲区，实现实时显示 |

📄 [原文02: 流式输出与SSE协议](../raw/LLM开发/02_流式输出与SSE协议.md)

### httpx手动实现SSE请求

```python
import httpx
import json

with httpx.stream(
    "POST",
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization": "Bearer sk-xxx"},
    json={
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": True
    }
) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            chunk = json.loads(data)
            content = chunk["choices"][0]["delta"].get("content")
            if content:
                print(content, end="", flush=True)
```

📄 [原文02: 流式输出与SSE协议](../raw/LLM开发/02_流式输出与SSE协议.md)

### 注意事项

- `if content:` 必不可少，某些chunk的 `delta.content` 为 `None`
- 手动实现时用 `.get("content")` 而非 `["content"]`，因为某些chunk无此字段
- `flush=True` 必不可少，否则看不到逐字输出
- `[DONE]` 是SSE约定的结束信号，不是JSON
- SSE是单向的（服务端→客户端），需要反向通信用WebSocket

---

## 三、Function Calling规范与实践

### 核心概念

Function Calling 是大模型结构化调用外部函数/API的机制：模型根据对话内容判断是否需要调用函数，返回结构化的函数名和JSON参数，开发者执行后将结果回传，模型再生成最终回复。

```
用户消息 → 模型判断是否需要调用函数
              │
              ├─ 不需要 → 正常文本回复
              │
              └─ 需要 → 返回 tool_calls（函数名 + JSON参数）
                            │
                            开发者执行函数，拿到结果
                            │
                            将结果作为 tool 消息回传
                            │
                            模型基于结果生成最终回复
```

📄 [原文03: Function Calling规范与实践](../raw/LLM开发/03_Function_Calling规范与实践.md)

### 定义工具（tools）

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的当前天气",  # 最关键字段，模型据此决定是否调用
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市名称"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"]
                }
            },
            "required": ["location"],
            "additionalProperties": false
        }
    }
}]
```

#### parameters支持的JSON Schema特性

| 特性 | 示例 | 说明 |
|------|------|------|
| 基本类型 | `string`, `number`, `integer`, `boolean`, `object`, `array` | |
| `enum` | `["celsius", "fahrenheit"]` | 枚举约束 |
| `description` | `"城市名称"` | **强烈建议填写** |
| `minimum`/`maximum` | `"minimum": 0` | 数值范围 |
| `minLength`/`maxLength` | `"minLength": 1` | 字符串长度 |
| `pattern` | `"pattern": "^[A-Z]{2}$"` | 正则约束 |
| `items` | `"items": {"type": "string"}` | 数组元素类型 |
| 嵌套对象 | `type: "object"` 内嵌 `properties` | 支持 |

📄 [原文03: Function Calling规范与实践](../raw/LLM开发/03_Function_Calling规范与实践.md)

### 发起请求

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京天气？"}],
    tools=tools,
    tool_choice="auto",
    temperature=0
)
```

#### tool_choice控制策略

| 值 | 行为 |
|---|---|
| `"auto"`（默认） | 模型自行决定是否调用、调用哪个 |
| `"none"` | 禁止调用，强制文本回复 |
| `"required"` | 强制至少调用一个工具 |
| `{"type":"function","function":{"name":"xxx"}}` | 强制调用指定函数 |

#### 其他相关参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `parallel_tool_calls` | `true` | 设为 `false` 则每次最多一个tool_call |
| `response_format` | - | 可设 `{"type":"json_object"}` 保证最终文本也是JSON |

📄 [原文03: Function Calling规范与实践](../raw/LLM开发/03_Function_Calling规范与实践.md)

### 模型响应（三种场景）

#### 场景1：纯文本回复（不调用函数）

```json
{
  "role": "assistant",
  "content": "北京今天晴朗，22°C。",
  "tool_calls": null
}
```

#### 场景2：纯函数调用（无伴随文本）

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"location\": \"Beijing\"}"
      }
    }
  ]
}
```

#### 场景3：文本 + 函数调用同时存在

```json
{
  "role": "assistant",
  "content": "我来帮你查一下。",
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"location\": \"Beijing\"}"
      }
    }
  ]
}
```

#### 并行调用

模型可能一次返回**多个tool_calls**，需分别执行并回传：

```json
{
  "tool_calls": [
    { "id": "call_001", "function": { "name": "get_weather", "arguments": "{\"location\":\"Beijing\"}" } },
    { "id": "call_002", "function": { "name": "get_weather", "arguments": "{\"location\":\"Shanghai\"}" } }
  ]
}
```

📄 [原文03: Function Calling规范与实践](../raw/LLM开发/03_Function_Calling规范与实践.md)

### 回传函数结果

```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"temperature\": 22, \"condition\": \"晴\", \"humidity\": 45}"
}
```

| 字段 | 说明 |
|---|---|
| `role` | 固定 `"tool"` |
| `tool_call_id` | **必须**与模型返回的 `call_xxx` 一一对应 |
| `content` | 函数执行结果（字符串形式） |

### content为null的处理

当模型请求调用函数时，`assistant` 消息的 `content` 通常为 `null`。回传时**必须保留null，不能改成空字符串**：

```python
# 正确
messages.append({
    "role": "assistant",
    "content": None,
    "tool_calls": response.tool_calls
})

# 错误 - null改成空字符串会影响上下文理解
messages.append({
    "role": "assistant",
    "content": "",
    "tool_calls": response.tool_calls
})
```

各语言null表示：Python → `None`，JavaScript → `null`，Go → `nil`，Java → `null`

📄 [原文03: Function Calling规范与实践](../raw/LLM开发/03_Function_Calling规范与实践.md)

### 严格模式（strict mode）

```json
{
  "function": {
    "name": "get_weather",
    "strict": true,
    "parameters": {
      "type": "object",
      "properties": {
        "location": { "type": "string" },
        "unit": { "type": "string", "enum": ["celsius", "fahrenheit"] }
      },
      "required": ["location", "unit"],
      "additionalProperties": false
    }
  }
}
```

strict模式要求：`additionalProperties: false`（必须）、所有字段必须在 `required` 中、不支持 `oneOf`/`anyOf` 等复杂组合。

### 完整调用示例

```python
import openai, json

client = openai.OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取天气",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "城市名"}
            },
            "required": ["location"]
        }
    }
}]

messages = [{"role": "user", "content": "北京天气？"}]

# Step 1: 发送请求
response = client.chat.completions.create(
    model="gpt-4o", messages=messages, tools=tools, tool_choice="auto"
)
msg = response.choices[0].message

# Step 2: 检查是否有函数调用
if msg.tool_calls:
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        result = get_weather(**args)
        messages.append(msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False)
        })

    # Step 3: 模型基于结果生成最终回复
    final = client.chat.completions.create(
        model="gpt-4o", messages=messages, tools=tools
    )
    print(final.choices[0].message.content)
```

📄 [原文03: Function Calling规范与实践](../raw/LLM开发/03_Function_Calling规范与实践.md)

### 最佳实践

| 实践 | 说明 |
|---|---|
| 写好 `description` | 模型决定是否调用的关键依据 |
| 参数设计简洁 | 避免过深嵌套，语义明确 |
| 校验 `arguments` | 模型可能返回不完美的参数，做类型/范围校验 |
| 处理执行异常 | 函数失败时将错误信息回传，让模型自行调整 |
| 限制工具数量 | 过多会增加延迟和token，按场景动态注入 |
| 使用strict模式 | 结构化要求高的场景开启 |
| 回传保留 `content: null` | 不要改成 `""` |
