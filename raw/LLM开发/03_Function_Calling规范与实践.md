## 笔记 3：Function Calling 规范与实践

> 合并来源：`Function Calling 规范` + `Function Calling 请求参数详解` + `Function Calling content为null场景`

### 一句话定义

Function Calling 是大模型结构化调用外部函数/API 的机制：模型根据对话内容判断是否需要调用函数，返回结构化的函数名和 JSON 参数，开发者执行后将结果回传，模型再生成最终回复。

### 核心流程

```
用户消息 → 模型判断是否需要调用函数
              │
              ├─ 不需要 → 正常文本回复
              │
              └─ 需要 → 返回 tool_calls（函数名 + JSON 参数）
                            │
                            开发者执行函数，拿到结果
                            │
                            将结果作为 tool 消息回传
                            │
                            模型基于结果生成最终回复
```

### 定义工具（tools）

```python
tools = [{
    "type": "function",                       # 目前仅支持 "function"
    "function": {
        "name": "get_weather",                # 唯一标识，snake_case/camelCase，≤64字符
        "description": "获取指定城市的当前天气",  # ⚠️ 最关键字段，模型据此决定是否调用
        "parameters": {                        # JSON Schema 格式
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市名称"    # 强烈建议填写，影响准确性
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"]
                }
            },
            "required": ["location"],
            "additionalProperties": false       # strict 模式下必须为 false
        }
    }
}]
```

#### parameters 支持的 JSON Schema 特性

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

### 发起请求

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京天气？"}],
    tools=tools,
    tool_choice="auto",       # 见下方控制策略
    temperature=0              # Function Calling 建议低值
)
```

#### tool_choice 控制策略

| 值 | 行为 |
|---|---|
| `"auto"`（默认） | 模型自行决定是否调用、调用哪个 |
| `"none"` | 禁止调用，强制文本回复 |
| `"required"` | 强制至少调用一个工具 |
| `{"type":"function","function":{"name":"xxx"}}` | 强制调用指定函数 |

#### 其他相关参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `parallel_tool_calls` | `true` | 设为 `false` 则每次最多一个 tool_call |
| `response_format` | - | 可设 `{"type":"json_object"}` 保证最终文本也是 JSON |

### 模型响应（三种场景）

#### 场景 1：纯文本回复（不调用函数）

```json
{
  "role": "assistant",
  "content": "北京今天晴朗，22°C。",
  "tool_calls": null
}
```

#### 场景 2：纯函数调用（无伴随文本）

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

#### 场景 3：文本 + 函数调用同时存在

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

模型可能一次返回**多个 tool_calls**，需分别执行并回传：

```json
{
  "tool_calls": [
    { "id": "call_001", "function": { "name": "get_weather", "arguments": "{\"location\":\"Beijing\"}" } },
    { "id": "call_002", "function": { "name": "get_weather", "arguments": "{\"location\":\"Shanghai\"}" } }
  ]
}
```

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

### content 为 null 的处理

当模型请求调用函数时，`assistant` 消息的 `content` 通常为 `null`。回传时**必须保留 null，不能改成空字符串**：

```python
# ✅ 正确
messages.append({
    "role": "assistant",
    "content": None,                 # Python 中用 None
    "tool_calls": response.tool_calls
})

# ❌ 错误 —— null 改成空字符串会影响上下文理解
messages.append({
    "role": "assistant",
    "content": "",
    "tool_calls": response.tool_calls
})
```

各语言 `null` 表示：Python → `None`，JavaScript → `null`，Go → `nil`，Java → `null`

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

strict 模式要求：`additionalProperties: false`（必须）、所有字段必须在 `required` 中、不支持 `oneOf`/`anyOf` 等复杂组合。

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
        args = json.loads(tc.function.arguments)     # arguments 是字符串化 JSON
        result = get_weather(**args)                   # 执行实际函数
        messages.append(msg)                           # 保留 content: None
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,                     # 与 call_xxx 对应
            "content": json.dumps(result, ensure_ascii=False)
        })

    # Step 3: 模型基于结果生成最终回复
    final = client.chat.completions.create(
        model="gpt-4o", messages=messages, tools=tools
    )
    print(final.choices[0].message.content)
```

### 最佳实践

| 实践 | 说明 |
|---|---|
| 写好 `description` | 模型决定是否调用的关键依据 |
| 参数设计简洁 | 避免过深嵌套，语义明确 |
| 校验 `arguments` | 模型可能返回不完美的参数，做类型/范围校验 |
| 处理执行异常 | 函数失败时将错误信息回传，让模型自行调整 |
| 限制工具数量 | 过多会增加延迟和 token，按场景动态注入 |
| 使用 strict 模式 | 结构化要求高的场景开启 |
| 回传保留 `content: null` | 不要改成 `""` |

### 相关笔记

- [[OpenAI SDK 基础与调用]]
- [[流式输出与SSE协议]]