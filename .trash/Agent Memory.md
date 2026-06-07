# Agent Memory

> **来源清单**（已提炼）：
> - [x] 01_Agent Memory框架对比
>
> **更新时间**：2026-06-07

---

## 一、五大框架定位总览

| 框架 | 一句话定位 | 核心隐喻 | Stars |
|------|-----------|---------|-------|
| **Text2Mem** | 记忆系统的操作语言（ISA） | CPU指令集 | 较少（学术导向） |
| **Mem0** | 记忆中间件（即插即用） | 数据库中间件 | 52k+ |
| **Letta** | 用OS虚拟内存管理记忆的操作系统 | 操作系统 | 较高 |
| **ReMe** | 文件即记忆，用户可直接编辑 | 文件系统 | 中等 |
| **memU** | 记忆本身是一个24/7后台Agent | 自主生命体 | 12.4k |

📄 [原文01: Agent Memory框架对比](../raw/AI agent/01_Agent Memory框架对比.md)

---

## 二、Text2Mem — 记忆的"指令集架构"

### 核心思想

不做记忆系统，而是为所有记忆系统定义一套**通用操作语言**。

### 关键设计

- **12 个原子操作**，分三个阶段：
  - **ENC 阶段**：`Encode`（记忆的诞生）
  - **RET 阶段**：`Retrieve`（纯数据取回，~50ms）、`Summarize`（LLM 摘要，~50000ms）—— 故意分开，因为延迟差 1000 倍，工程策略完全不同
  - **STO 阶段**：9 个操作覆盖完整生命周期（Update、Delete、Promote 等）

- **五元 JSON 契约**：每条记忆操作 = `{stage, op, target, args, meta}`
- **双层验证**：外层 JSON Schema 验格式，内层 Pydantic 验业务逻辑
- **四种锁模式**：read_only / no_delete / append_only / custom
- **安全兜底**：meta 中的 `dry_run` 和 `confirmation` 二选一，防止 LLM 误删

### 短板

目前只有 SQLite 参考实现，无向量 API，暂以 JSON 文本存储。

### 适用场景

研究者、想自定义记忆操作语言的团队。

📄 [原文01: Agent Memory框架对比](../raw/AI agent/01_Agent Memory框架对比.md)

---

## 三、Mem0 — 工程化全家桶

### 核心思想

成熟的**记忆中间件**，即插即用。

### 关键设计

- **三层架构**：Memory API → 逻辑层（LLM 推理 + 向量检索 + 图谱） → 存储层
- **5 个工厂模式**（插件化精髓）：
  - LLM Factory（17+ 提供商）
  - Embedder Factory（11+ 模型）
  - VectorStore Factory（22+ 种向量存储）
  - GraphStore Factory（4 种图存储）
  - Reranker Factory（5 种）
  - 全部通过 `importlib` 动态加载，未安装的依赖不会报错

- **三种记忆类型**：
  - 语义记忆（抽象事实知识）
  - 情景记忆（具体事件）
  - 程序记忆（Agent 执行步骤，逐字保留用于崩溃恢复）

- **四个值得学的设计**：
  1. **UID 换算处理**：LLM 看到的简单整数 ID ↔ 系统内部真实 UUID 映射
  2. **双存储并行**：向量存储（语义搜索）+ 图存储（关系推理），`ThreadPoolExecutor` 并行执行
  3. **双 Prompt 策略**：User Prompt 只看用户消息、Agent Prompt 只看助手消息，防止 AI 自我表达污染用户记忆
  4. **多层级隔离**：用户隔离 / Agent 隔离 / 运行时隔离

### 成本瓶颈

- 每次 `add()` 调用完整模式需 2-5 次 LLM 调用（事实提取 → 记忆对比 → 实体提取 → 关系建立 → 关系清理）
- Token 成本随记忆数量线性增长
- 更适合中低频写入场景

### 适用场景

快速给产品加记忆能力，追求工程成熟度和生态兼容性（对话助手、客服、健康追踪）。

📄 [原文01: Agent Memory框架对比](../raw/AI agent/01_Agent Memory框架对比.md)

---

## 四、Letta — 记忆的操作系统

### 核心思想

把 OS 虚拟内存机制搬进 Agent，**突破上下文窗口硬性限制**。

### 三层记忆（对应 OS 的 RAM/磁盘/日志）

| 记忆层 | 对应 | 说明 |
|--------|------|------|
| Core Memory（核心内存） | CPU RAM | 直接嵌入 system prompt，每次推理 LLM 都看得到 |
| Archival Memory（归档内存） | 磁盘 | 容量无限，向量索引 |
| Recall Memory（召回内存） | 操作系统日志 | 所有历史对话消息 |

### 关键设计

- **Core Memory Block 三元组**：`label`（路径命名空间）+ `description`（功能描述）+ `value`（实际内容）+ `limit`（字符上限）
  - limit 是强制的信息压缩约束，逼迫 Agent 主动做信息蒸馏

- **虚拟内存机制**：上下文快满 → 触发 Summarizer → 默认驱逐 30% 消息 → 被驱逐消息写入 Recall Memory → 仍可通过 Conversation Search 再检索

- **Git Enabled Block Manager**（业界唯一）：
  - 每次记忆变更产生一次 Git Commit（写入 Agent ID + 时间 + 变更原因）
  - 内容寻址防止篡改、完整历史可追溯、多个 Agent 可合并修改

- **MemFS**：记忆组织成真正的目录树（persona / knowledge / skills）

- **Sleeptime Agent**：用户不交互时，每 5 步触发后台 Agent 读取对话、分析更新 Memory Block
  - 主 Agent 只负责推理和回复（低延迟）
  - 后台 Agent 可用更大 token 预算做深度反思

### 代价

认知成本高，数据库依赖强，80+ 个依赖包。

### 适用场景

需要真正有状态的 Agent、长期对话、需要记忆版本控制和审计的场景。

📄 [原文01: Agent Memory框架对比](../raw/AI agent/01_Agent Memory框架对比.md)

---

## 五、ReMe — 记忆的用户主权

### 核心思想

**文件即记忆**，把控制权和透明度还给用户。

### 两套系统

- **ReMe Light**：文件系统，用于短期工作记忆
- **ReMe 本体**：向量记忆，用于长期语义记忆

### 三个技术亮点

1. **DeltaFileWatcher 增量监控**：文件追加模式下只处理新增部分，节省 92% 的 API 调用
2. **when_to_use 与 content 分离**：向量索引建在 `when_to_use` 上（与用户查询天然语义接近），大幅提升召回率
3. **AI 自主记忆管理**：给 AI 提供 read_file/write_file/edit_file 工具，让 AI 自己决定如何组织记忆

### 性能数据

Qwen2.5-38B + ReMe 综合得分超过没有记忆的 Qwen2.5-72B（好的记忆系统可以让小模型打过大模型）。

### 适用场景

注重用户主权和记忆透明度、需要用户直接编辑记忆的场景。

📄 [原文01: Agent Memory框架对比](../raw/AI agent/01_Agent Memory框架对比.md)

---

## 六、memU — 记忆本身是 Agent

### 核心思想

从被动记忆变为主动记忆，记忆系统 **24/7 运行**。

### 关键设计

- **双 Agent 架构**：
  - Main Agent：听用户说话、调工具、生成回复
  - MemU Bot：持续盯着每一次交互，后台提取、整理、分类记忆
  - 通过 `asyncio.create_task` 异步运行，靠共享 `conversation_messages` 列表通信

- **文件系统隐喻**（底层是数据库）：
  - 文件夹 → Category
  - 文件 → MemoryItem
  - 符号链接 → 交叉引用
  - 挂载点 → Resource

- **Reinforcement Count 机制**：每条记忆带计数器，每次被检索计数 +1，排序时按强化次数加权。越常用的记忆越容易被再次召回 = 给记忆加了"肌肉记忆"。

### 性能数据

LOCOMO 基准测试：平均准确率 92.09%（同一基准下 MemGPT 为 71.8%）。

### 适用场景

长期陪伴型 AI 助手、企业级客服、DevOps Agent、研究型助手。

📄 [原文01: Agent Memory框架对比](../raw/AI agent/01_Agent Memory框架对比.md)

---

## 七、选型决策树

```
你的核心需求是什么？
│
├─ 快速集成、开箱即用 ──────────→ Mem0
│   (工程成熟度最高，生态最丰富)
│
├─ 需要真正有状态的Agent ────────→ Letta
│   (虚拟内存+Git版本化+Sleeptime反思)
│
├─ 要记忆透明、用户可编辑 ───────→ ReMe
│   (文件即记忆，用户主权)
│
├─ 要记忆主动学习、预测用户需求 ──→ memU
│   (记忆本身是Agent，24/7运行)
│
└─ 要定义自己的记忆操作标准 ──────→ Text2Mem
    (学术/研究导向，做底层协议)
```

📄 [原文01: Agent Memory框架对比](../raw/AI agent/01_Agent Memory框架对比.md)

---

## 八、趋势判断

目前没有任何一个框架是标准答案，但它们构成一个清晰的范式演进光谱：

> **Agent 有记忆 → Agent 管理记忆 → 记忆本身是 Agent**

| 时间维度 | 推荐 | 理由 |
|----------|------|------|
| 短期 | Mem0 | 工程落地最优选，工厂模式+双存储+多层级隔离解决 80% 实际问题 |
| 中期 | Letta | 操作系统级解法，虚拟内存+Git 版本化+Sleeptime Agent 在复杂系统中越来越重要 |
| 长期 | memU | "记忆即Agent"范式，7x24 持续学习和进化时被动式架构会成为瓶颈 |

**真正的趋势是融合**：底层用 Text2Mem 式标准化操作语言，中间层用 Mem0 式中间件做兼容，上层用 Letta 式虚拟内存做分层，再加 memU 式主动学习能力。未来标准答案很可能是分层的组合架构。

📄 [原文01: Agent Memory框架对比](../raw/AI agent/01_Agent Memory框架对比.md)
