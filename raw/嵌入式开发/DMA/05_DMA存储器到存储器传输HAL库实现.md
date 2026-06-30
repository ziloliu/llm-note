# DMA 存储器到存储器传输 — HAL 库实现 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| 传输方向 | **ROM（Flash）→ RAM（SRAM）** |
| DMA 控制器 | DMA1 通道 1 |
| 模式 | 存储器到存储器（MEM2MEM） |
| 数据宽度 | 8 位（字节） |
| 传输数据 | 4 个字节 |
| 实现方式 | HAL 库（CubeMX） |

---

## 二、CubeMX 配置

### 2.1 基础配置

| 配置项 | 设置 |
|--------|------|
| Debug | Serial Wire |
| RCC | HSE 外部高速晶振 |
| 时钟树 | HSE → PLL ×9 → 72MHz, APB1 /2 → 36MHz |
| Connectivity | USART1 异步模式 |

### 2.2 DMA 配置

```
DMA 在 CubeMX 中的位置：
  System Core → DMA（不是外设，是系统核心模块）

配置步骤：
  ① 点击 DMA Settings 页签
  ② 点击 Add 按钮
  ③ 选择 Memory To Memory
  ④ 保持默认配置
```

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| DMA Request | **Memory To Memory** | 存储器到存储器 |
| DMA Controller | DMA1 | DMA1 控制器 |
| Channel | Channel 1 | 通道 1（任意均可） |
| Direction | Memory To Memory | 固定 |
| Mode | **Normal** | 正常模式 |
| Priority | Low | 低优先级（可改） |
| Src Memory | Byte（8 位） | 源数据宽度 |
| Dst Memory | Byte（8 位） | 目标数据宽度 |
| Src Address Increment | ✅ | 源地址自增 |
| Dst Address Increment | ✅ | 目标地址自增 |

### 2.3 数据宽度选项

| CubeMX 选项 | 位宽 | 字节数 | 寄存器值 |
|-------------|:----:|:------:|:--------:|
| Byte | 8 位 | 1 | 00 |
| Half Word | 16 位 | 2 | 01 |
| Word | 32 位 | 4 | 10 |

### 2.4 NVIC 配置

| 中断 | 勾选 |
|------|:----:|
| **DMA1 Channel1 global interrupt** | ✅ |

---

## 三、CubeMX 生成的代码

### 3.1 自动生成的文件

```
dma.c          → DMA 初始化
dma.h          → DMA 头文件
stm32f1xx_it.c → DMA1_Channel1_IRQHandler（中断服务函数）
```

### 3.2 DMA 初始化代码（dma.c）

```c
DMA_HandleTypeDef hdma_memtomem_dma1_channel1;

void MX_DMA_Init(void)
{
    __HAL_RCC_DMA1_CLK_ENABLE();

    hdma_memtomem_dma1_channel1.Instance = DMA1_Channel1;
    hdma_memtomem_dma1_channel1.Init.Direction = DMA_MEMORY_TO_MEMORY;
    hdma_memtomem_dma1_channel1.Init.PeriphInc = DMA_PINC_ENABLE;
    hdma_memtomem_dma1_channel1.Init.MemInc = DMA_MINC_ENABLE;
    hdma_memtomem_dma1_channel1.Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
    hdma_memtomem_dma1_channel1.Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
    hdma_memtomem_dma1_channel1.Init.Mode = DMA_NORMAL;
    hdma_memtomem_dma1_channel1.Init.Priority = DMA_PRIORITY_LOW;
    HAL_DMA_Init(&hdma_memtomem_dma1_channel1);
}
```

### 3.3 DMA 句柄结构体说明

```
DMA_HandleTypeDef hdma_memtomem_dma1_channel1;

结构体名称含义：
  hdma     = HAL DMA handle
  memtomem = 存储器到存储器模式
  dma1     = DMA1 控制器
  channel1 = 通道 1

结构体内容：
  → Instance：指向 DMA1_Channel1（寄存器基地址）
  → Init：所有配置参数
  → 各种回调函数指针
  → 状态信息
```

---

## 四、HAL 库关键函数

### 4.1 启动 DMA 传输

```c
// 不带中断启动
HAL_DMA_Start(&hdma_memtomem_dma1_channel1,
              (uint32_t)source,          // 源地址
              (uint32_t)dest,            // 目标地址
              4);                        // 数据长度

// 带中断启动（本实验使用）
HAL_DMA_Start_IT(&hdma_memtomem_dma1_channel1,
                 (uint32_t)source,
                 (uint32_t)dest,
                 4);
```

### 4.2 关闭 DMA 通道

```c
// 关闭/中止 DMA 传输
HAL_DMA_Abort(&hdma_memtomem_dma1_channel1);

// 带中断方式关闭
HAL_DMA_Abort_IT(&hdma_memtomem_dma1_channel1);
```

```
⚠️ HAL 库中没有 HAL_DMA_Stop 函数
  → 关闭用 Abort（丢弃/中止）
  → 底层操作：禁用所有中断 + 禁用 DMA 通道 + 清除标志
```

### 4.3 地址类型转换

```c
// 数组名是 uint8_t* 指针类型
// HAL_DMA_Start_IT 需要 uint32_t 参数
// 必须强转

HAL_DMA_Start_IT(&handle,
                 (uint32_t)source,       // 指针 → uint32_t
                 (uint32_t)dest,
                 4);
```

```
⚠️ printf 的 %p 格式接受指针类型，不需要强转
   HAL_DMA_Start_IT 需要 uint32_t，必须强转
   不转编译器会报错
```

---

## 五、中断处理方式

### 5.1 方式一：直接在中断服务函数中处理

```c
// stm32f1xx_it.c

extern volatile uint8_t is_finished;

void DMA1_Channel1_IRQHandler(void)
{
    HAL_DMA_Abort_IT(&hdma_memtomem_dma1_channel1);
    is_finished = 1;
}
```

### 5.2 方式二：注册回调函数（推荐扩展）

```c
// 注册回调函数
HAL_DMA_RegisterCallback(&hdma_memtomem_dma1_channel1,
                         HAL_DMA_XFER_CPLT_CB_ID,       // 传输完成回调 ID
                         FinishedCallback);              // 回调函数名

// 回调函数实现
void FinishedCallback(DMA_HandleTypeDef *hdma)
{
    printf("Callback called!\n");
    HAL_DMA_Abort_IT(hdma);
    is_finished = 1;
}
```

### 5.3 回调 ID 类型

| 枚举值 | 含义 |
|--------|------|
| `HAL_DMA_XFER_CPLT_CB_ID` | 传输完成 |
| `HAL_DMA_XFER_HALFCPLT_CB_ID` | 传输过半 |
| `HAL_DMA_XFER_ERROR_CB_ID` | 传输错误 |
| `HAL_DMA_XFER_ABORT_CB_ID` | 传输中止 |
| `HAL_DMA_XFER_ALL_CB_ID` | 所有事件 |

### 5.4 回调函数注册原理

```
HAL_DMA_RegisterCallback 函数：
  参数 1：DMA 句柄地址
  参数 2：回调 ID（枚举类型）
  参数 3：函数指针（回调函数名，不带括号）

底层操作：
  将函数指针存入 DMA_HandleTypeDef 结构体的对应成员

HAL_DMA_IRQHandler 被调用时：
  → 根据中断类型判断
  → 调用对应结构体成员中的函数指针
  → 执行我们注册的回调函数
```

### 5.5 回调函数格式

```c
// 函数签名必须是：
void CallbackName(DMA_HandleTypeDef *hdma);

// 返回值：void
// 参数：DMA_HandleTypeDef 指针
// 名称：自定义
```

### 5.6 两种中断处理方式对比

| 对比项 | 方式一（直接处理） | 方式二（回调函数） |
|--------|:------------------:|:-----------------:|
| 代码位置 | `it.c` 中 IRQHandler | `main.c` 中自定义函数 |
| 可读性 | 一般 | **更好**（语义明确） |
| 区分事件 | 需要手动判断 | **自动区分**（不同回调 ID） |
| 复杂度 | 简单 | 稍复杂（注册机制） |
| 适用场景 | 简单项目 | 复杂项目、多通道管理 |

---

## 六、HAL 库底层回调机制

### 6.1 HAL_DMA_IRQHandler 内部流程

```c
void HAL_DMA_IRQHandler(DMA_HandleTypeDef *hdma)
{
    // 传输过半
    if (半传输完成标志 && 半传输中断使能)
    {
        禁用 HT 中断;
        清除 HT 标志;
        hdma->XferHalfCpltCallback(hdma);  // 调用半完成回调
    }

    // 传输完成
    if (传输完成标志 && 传输完成中断使能)
    {
        禁用 TC 中断;
        清除 TC 标志;
        hdma->XferCpltCallback(hdma);      // 调用完成回调
    }

    // 传输错误
    if (错误标志 && 错误中断使能)
    {
        禁用所有中断;
        清除所有标志;
        hdma->XferErrorCallback(hdma);     // 调用错误回调
    }
}
```

### 6.2 函数指针概念

```c
// DMA_HandleTypeDef 中的回调成员定义
void (* XferCpltCallback)(struct __DMA_HandleTypeDef *hdma);
//  ↑ 函数指针          ↑ 参数类型

// 调用方式：
hdma->XferCpltCallback(hdma);

// 注册方式：
// 将自定义函数名赋给这个函数指针成员
```

---

## 七、主函数实现

### 7.1 完整代码

```c
#include "main.h"
#include "dma.h"
#include "usart.h"
#include <stdio.h>

/* 数据定义 */
const uint8_t source[4] = {12, 13, 14, 10};   // ROM（Flash）
uint8_t dest[4] = {0, 0, 0, 0};               // RAM（SRAM）
volatile uint8_t is_finished = 0;               // 传输完成标志

/* 回调函数声明 */
void FinishedCallback(DMA_HandleTypeDef *hdma);

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_USART1_UART_Init();

    printf("Hello World!\n");

    // 打印地址验证
    printf("source addr: %p\n", source);
    printf("dest addr:   %p\n", dest);

    /* 方式一：带中断启动，回调在 it.c 中处理 */
    // HAL_DMA_Start_IT(&hdma_memtomem_dma1_channel1,
    //                  (uint32_t)source, (uint32_t)dest, 4);

    /* 方式二：注册回调函数 */
    HAL_DMA_RegisterCallback(&hdma_memtomem_dma1_channel1,
                             HAL_DMA_XFER_CPLT_CB_ID,
                             FinishedCallback);

    HAL_DMA_Start_IT(&hdma_memtomem_dma1_channel1,
                     (uint32_t)source, (uint32_t)dest, 4);

    while (1)
    {
        if (is_finished)
        {
            is_finished = 0;
            for (uint8_t i = 0; i < 4; i++)
            {
                printf("%d\t", dest[i]);
            }
            printf("\n");
        }
    }
}

void FinishedCallback(DMA_HandleTypeDef *hdma)
{
    printf("Callback called!\n");
    HAL_DMA_Abort_IT(hdma);
    is_finished = 1;
}
```

---

## 八、运行结果

```
Hello World!
source addr: 0x080008B0
dest addr:   0x20000001
Callback called!
12    13    14    10
```

```
地址验证：
  source（const）→ 0x0800xxxx → ROM/Flash
  dest（变量）    → 0x2000xxxx → RAM/SRAM

传输结果：
  dest[0]=12, dest[1]=13, dest[2]=14, dest[3]=10 ✅
```

---

## 九、CubeMX 配置与寄存器对照

| CubeMX 配置 | 寄存器 | 值 |
|-------------|--------|:--:|
| DMA Request = Memory To Memory | CCR.MEM2MEM | 1 |
| Direction = Memory To Memory | CCR.DIR | 0 |
| Src Memory = Byte | CCR.PSIZE | 00 |
| Dst Memory = Byte | CCR.MSIZE | 00 |
| Src Address Increment = ✅ | CCR.PINC | 1 |
| Dst Address Increment = ✅ | CCR.MINC | 1 |
| Mode = Normal | CCR.CIRC | 0 |
| Priority = Low | CCR.PL | 00 |

---

## 十、HAL 库 DMA 函数汇总

| 函数 | 功能 |
|------|------|
| `HAL_DMA_Init()` | 初始化 DMA（CubeMX 生成） |
| `HAL_DMA_Start()` | 启动 DMA 传输（无中断） |
| `HAL_DMA_Start_IT()` | 启动 DMA 传输（带中断） |
| `HAL_DMA_Abort()` | 中止 DMA 传输 |
| `HAL_DMA_Abort_IT()` | 中止 DMA 传输（带中断回调） |
| `HAL_DMA_RegisterCallback()` | 注册回调函数 |
| `HAL_DMA_IRQHandler()` | 中断处理分发函数 |

---

## 十一、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 时钟开启 | `RCC->AHBENR \|= DMA1EN` | CubeMX 自动生成 |
| CCR 配置 | 手动逐位配置 | CubeMX 图形化 |
| CPAR/CMAR | 手动赋值 | `HAL_DMA_Start_IT` 参数传入 |
| CNDTR | 手动赋值 | `HAL_DMA_Start_IT` 参数传入 |
| 通道使能 | `CCR \|= EN` | `HAL_DMA_Start_IT` 自动 |
| 中断处理 | 手动判断 ISR/IFCR | `HAL_DMA_IRQHandler` 自动分发 |
| 关闭通道 | `CCR &= ~EN` | `HAL_DMA_Abort_IT` |
| 回调机制 | 无 | `HAL_DMA_RegisterCallback` |

---

## 十二、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 编译报类型错误 | 指针类型未转 uint32_t | `(uint32_t)source` |
| 传输无结果 | CubeMX 未配 DMA | System Core → DMA 中添加 |
| 中断不进 | NVIC 未勾选 | 勾选 DMA1 Channel1 中断 |
| 回调不执行 | 未注册或 ID 错误 | 检查 `RegisterCallback` 参数 |
| 数据不正确 | 源/目标地址写反 | CPAR=源，CMAR=目标 |
| printf 地址输出正常 | %p 接受指针类型 | 不需要强转 |

---

## 十三、HAL 库中 Start vs Abort 对应关系

| 启动函数 | 关闭函数 | 说明 |
|----------|----------|------|
| `HAL_DMA_Start()` | `HAL_DMA_Abort()` | 无中断 |
| `HAL_DMA_Start_IT()` | `HAL_DMA_Abort_IT()` | 带中断 |

```
⚠️ 没有 HAL_DMA_Stop 函数
   HAL 库用 Abort（中止）代替 Stop（停止）
   Abort 底层操作：
     → 禁用所有中断
     → 禁用 DMA 通道
     → 清除所有标志位
```