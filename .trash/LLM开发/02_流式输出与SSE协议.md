## 笔记 2：流式输出与 SSE 协议

> 合并来源：`流式输出详解` + `Server-Sent Events SSE详解` + `httpx手动实现SSE请求`

### 一句话定义

流式输出基于 SSE (Server-Sent Events) 协议，服务端通过同一个 HTTP 连接持续推送文本片段，客户端实时接收处理，用户无需等待完整响应即可看到逐字输出。

### SSE 协议基础

#### 与传统 HTTP 对比

```
传统 HTTP：
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

#### HTTP 响应头

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

- `Content-Type: text/event-stream`：标识 SSE 流
- 无 `Content-Length`：总长度未知

#### SSE 消息格式

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
| `id` | 消息 ID（断线重连用） | 否 |
| `retry` | 重连间隔（毫秒） | 否 |

#### 通信方式对比

| | 传统请求 | SSE | WebSocket |
|---|---|---|---|
| 方向 | 双向（请求-响应） | 服务端→客户端单向 | 双向 |
| 协议 | HTTP | HTTP | 独立协议 (ws://) |
| 连接 | 每次新建 | 持续复用 | 持续复用 |
| 典型场景 | 普通 API | 大模型输出、实时通知 | 聊天室、游戏 |

### SDK 流式调用

```python
from openai import OpenAI

client = OpenAI(api_key="sk-xxx", base_url="https://api.deepseek.com")

stream = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}],
    stream=True                                          # 开启流式
)

for chunk in stream:
    content = chunk.choices[0].delta.content             # 增量片段
    if content:
        print(content, end="", flush=True)
```

#### chunk 数据结构

```python
chunk = ChatCompletionChunk(
    id="chatcmpl-abc123",
    choices=[ChunkChoice(
        index=0,
        delta=Delta(role="assistant", content="你"),     # 增量内容
        finish_reason=None
    )]
)
```

#### delta vs message（关键区别）

```
非流式 → response.choices[0].message.content    ← 完整回复
流式   → chunk.choices[0].delta.content          ← 增量片段
```

#### 逐字输出过程

```
第1次迭代 → delta.content = "你"
第2次迭代 → delta.content = "好"
第3次迭代 → delta.content = "！"
...
最后一次 → delta.content = None  (结束信号)
```

#### print 参数

| 参数 | 作用 |
|------|------|
| `end=""` | 不换行，文本连续拼接 |
| `flush=True` | 立即刷新缓冲区，实现实时显示 |

### httpx 手动实现 SSE 请求

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
            data = line[6:]                     # 去掉 "data: " 前缀（6字符）
            if data.strip() == "[DONE]":
                break
            chunk = json.loads(data)
            content = chunk["choices"][0]["delta"].get("content")
            if content:
                print(content, end="", flush=True)
```

#### 解析流程

```
httpx 发送 POST（stream=True）
    ↓
服务端返回 200 OK，Content-Type: text/event-stream
    ↓
服务端持续推送：
  data: {"choices":[{"delta":{"content":"你"}}]}
  data: {"choices":[{"delta":{"content":"好"}}]}
  data: [DONE]
    ↓
for 循环逐行读取 → json.loads → 提取 delta.content
    ↓
with 块结束，连接自动关闭
```

### 注意事项

- `if content:` 必不可少——某些 chunk 的 `delta.content` 为 `None`（首帧可能只有 `role`，末帧为结束信号）
- 流式结束后可能单独返回 `usage` 统计
- 手动实现时用 `.get("content")` 而非 `["content"]`，因为某些 chunk 无此字段
- `flush=True` 必不可少，否则看不到逐字输出
- `[DONE]` 是 SSE 约定的结束信号，不是 JSON
- SSE 是单向的（服务端→客户端），需要反向通信用 WebSocket

### 相关笔记

- [[OpenAI SDK 基础与调用]]
- [[Function Calling 规范与实践]]

