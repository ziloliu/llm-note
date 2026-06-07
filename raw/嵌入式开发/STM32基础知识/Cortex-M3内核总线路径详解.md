---
title: "Cortex-M3内核总线路径详解"
category: "STM32/基础知识"
tags: ["总线", "系统架构", "Cortex-M3", "Harvard架构", "存储器"]
abstract: "详解Cortex-M3内核四条关键总线路径：I-Code、D-Code、System、FSMC"
source: "资料摘抄"
update_time: 2026-05-25
status: 完成
type: 原理
---

## 一句话定义
Cortex-M3内核采用多总线（哈佛架构）设计，通过I-Code、D-Code、System三条独立总线和FSMC外部存储控制器，实现指令获取、数据加载、外设访问的并行处理，打破性能瓶颈。

## 核心内容
![Cortex-M3内核总线架构](assets/02_system-bus-architecture.png)

### 1. I-Code 指令总线（Instruction Code）
- **路径**：`Cortex-M3` → `I-Code` → `Flash接口` → `Flash`
- **功能**：CPU**专门用于取指令**（读取程序代码）的通道
- **特点**：只连接Flash，避免数据访问干扰，保证指令获取的实时性和效率

### 2. D-Code 数据总线（Data Code）
- **路径**：`Cortex-M3` → `D-Code` → 分两路：
    - 一路直达 `Flash接口` → 访问 `Flash`
    - 一路进入 `总线矩阵`
- **功能**：主要用于**加载常量**（如`const`修饰变量、字符串字面量、数字常量等）
- **补充**：DCode最终也接入总线矩阵，也能访问SRAM中的数据，但核心设计是为了快速加载Flash中的常量

### 3. System 系统总线（System Bus）
- **路径**：`Cortex-M3` → `System` → `总线矩阵`
- **功能**：CPU**访问SRAM（静态随机存取存储器）和片内外设**的主要通道
- **特点**：程序运行时的**变量**（栈、堆、全局变量）都在SRAM里，通过总线矩阵可访问SRAM，也可经过AHB系统总线和桥接器读取或配置APB1/APB2上的外设

### 4. FSMC（Flexible Static Memory Controller）
- **位置**：连接在`总线矩阵`下方
- **功能**：**外部存储控制器**（不是一条总线）
- **作用**：让CPU像访问内部SRAM一样**驱动外部存储器**，如外扩NOR Flash、NAND Flash、PSRAM，或连接8080/6800接口的LCD屏幕

### 设计原理
这种**分离总线（哈佛结构）**设计的核心目的是**打破性能瓶颈**：
- 假设只有一条共享总线：当CPU从Flash读取常量时（D-Code功能），会阻塞下一条指令的读取（I-Code功能）
- 通过拆分实现并行：
    - **I-Code**：专心把指令灌给CPU
    - **D-Code**：快速抓取常量
    - **System**：负责跑软件变量和外设
- 三者并行工作，大大提高了嵌入式MCU的运行效率

## 注意事项 & 踩坑
1. 不同总线的访问速度和优先级不同，设计程序时需考虑数据存放位置
2. FSMC配置复杂，需要根据外部存储器特性设置时序参数
3. 总线矩阵会仲裁多主机访问冲突，DMA和CPU同时访问同一资源时需注意优先级

## 相关笔记

- [[系统架构与总线分类]]

## 参考来源
- 原始笔记：未命名.md（Cortex-M3架构图解析）
