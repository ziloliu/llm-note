# 知识库工作流总纲

## 定位
本文件是 AI 助手的**工作流总调度指南**，只描述：
- 什么场景下应该执行什么操作
- 去哪里查找具体操作规范

**不包含**具体操作细节，所有细节在 `rules/` 下。

---

## 一、目录结构

```
knowledge-base/
├── raw/        # 原始笔记
├── core/       # 核心提炼
├── index/      # 索引目录
├── log/        # 操作日志
├── scripts/    # 自动化脚本
├── rules/      # 操作规范
└── AGENTS.md   # 本文件
```

---

## 二、行为调度表

| 场景 | 操作 | 规范文件 |
|------|------|----------|
| 收到新笔记 | 筛查 → 命名 → 归类 → 放入raw/ | `rules/raw_processing.md` |
| 提炼笔记 | 读raw → 提取知识 → 写入core/ | `rules/extraction_standard.md` |
| 更新索引 | 运行 `python scripts/generate_index.py` | `rules/index_generation.md` |
| 任何修改 | 记录日志 | `rules/log_standard.md` |
| 编写脚本 | 存入scripts/，更新README | `rules/script_standard.md` |
| 查询内容 | 先读index/，再按需打开文件 | `rules/index_generation.md` |

---

## 三、核心原则

1. **总纲与细则分离**：本文件是地图，rules是法律
2. **冲突时以rules为准**：发现冲突以rules执行，日志中备注
3. **日志必须记录**：每次操作后记录到 `log/YYYY-MM.md`

---

## 四、快速参考

### 日志格式
```
[时间] [操作类型] [状态] [目标路径]
```

### 操作类型
`RAW_IN` `RAW_ORG` `EXTRACT` `INDEX` `CORE_EDIT` `SCRIPT` `RULE_EDIT` `GIT`

### 状态标记
`OK` `FAIL` `REVIEW` `SKIP`

详细规范见 `rules/log_standard.md`

---

## 五、自动版本控制

每次完成重要操作后，AI 自动执行：
```bash
git add . && git commit -m "描述" && git push
```

**重要操作定义**：
- 入库新笔记（RAW_IN）
- 重命名/移动/删除raw文件（RAW_ORG）
- 提炼笔记到core（EXTRACT）
- 更新索引（INDEX）
- 编辑core文件（CORE_EDIT）
- 修改规则文件（RULE_EDIT）
- 新增/修改脚本（SCRIPT）

**不触发推送的操作**：
- 读取文件、查看目录
- 仅查询索引
- 日志记录本身

**commit 格式**：`[操作类型] 简要描述`

详见 `rules/log_standard.md`