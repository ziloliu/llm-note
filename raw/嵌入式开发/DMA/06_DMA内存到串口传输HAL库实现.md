# DMA 内存到串口传输 — HAL 库实现 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| 传输方向 | **RAM（存储器）→ USART1_TX（外设）** |
| DMA 控制器 | DMA1 通道 4（硬件固定） |
| 模式 | 存储器到外设（Memory to Peripheral） |
| 数据宽度 | 8 位（字节） |
| 实现方式 | HAL 库（CubeMX） |

---

## 二、CubeMX 配置

### 2.1 基础配置

| 配置项 | 设置 |
|--------|------|
| Debug | Serial Wire |
| RCC | HSE 外部高速晶振 |
| 时钟树 | HSE → PLL ×9 → 72MHz, APB1 /2 → 36MHz |
| Connectivity | **USART1** 异步模式，波特率 115200 |

### 2.2 DMA 配置

```
两种配置入口（效果完全相同）：
  ① System Core → DMA → Add → USART1_TX
  ② Connectivity → USART1 → DMA Settings → Add → USART1_TX

推荐：在 USART1 的 DMA Settings 中直接配置
```

### 2.3 DMA 通道配置

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| DMA Request | **USART1_TX** | 串口发送 |
| DMA Controller | DMA1 | DMA1 控制器 |
| Channel | **Channel 4** | **硬件固定，不可更改** |
| Direction | **Memory To Peripheral** | 存储器到外设（固定） |
| Mode | **Normal** / Circular | 正常/循环 |
| Priority | Low | 低优先级 |
| Src Memory (PINC) | **Disable** | 外设地址**不自增** |
| Dst Memory (MINC) | **Enable** | 存储器地址**自增** |
| Src Data Width | Byte | 8 位 |
| Dst Data Width | Byte | 8 位 |

### 2.4 传输方向分析

```
USART1_TX → 方向固定为 Memory To Peripheral

原因：
  → TX 是发送功能
  → 数据来源：存储器（RAM 中的数组）
  → 数据去向：外设（USART 发送缓冲区）
  → 方向：存储器 → 外设（不可更改）

如果是 USART1_RX：
  → 方向自动变为 Peripheral To Memory
  → 数据来源：外设（USART 接收缓冲区）
  → 数据去向：存储器（RAM 中的数组）
```

### 2.5 地址自增分析

```
外设（USART）地址自增 = Disable ✅
  → 串口发送缓冲区地址固定（DR 寄存器）
  → 每次都往同一个地址写数据
  → 不需要自增

存储器（RAM）地址自增 = Enable ✅
  → 数组中的数据在内存中连续存放
  → 每发完一个字节，地址 +1，取下一个数据
  → 必须自增
```

### 2.6 Normal vs Circular 模式

| 模式 | 行为 | 效果 |
|------|------|------|
| **Normal** | 传输完成停止 | 发送一次后停止 |
| **Circular** | 传输完成自动回到起始地址继续 | 循环发送，不停刷屏 |

---

## 三、CubeMX 生成的代码位置

### 3.1 与存储器到存储器模式的区别

| 对比项 | 存储器到存储器 | 内存到串口 |
|--------|:-------------:|:---------:|
| 配置入口 | System Core → DMA | USART1 → DMA Settings |
| DMA 初始化代码 | **dma.c** | **usart.c**（核心） |
| DMA 句柄变量 | dma.c 中定义 | usart.c 中定义 |
| 中断服务 | it.c 中 | it.c 中 |

### 3.2 usart.c 中生成的 DMA 配置代码

```c
// 串口句柄中包含 DMA 句柄
static DMA_HandleTypeDef hdma_usart1_tx;

void MX_USART1_UART_Init(void)
{
    // ... 串口基本配置 ...

    // DMA 发送通道配置
    hdma_usart1_tx.Instance = DMA1_Channel4;
    hdma_usart1_tx.Init.Direction = DMA_MEMORY_TO_PERIPH;
    hdma_usart1_tx.Init.PeriphInc = DMA_PINC_DISABLE;   // 串口地址不自增
    hdma_usart1_tx.Init.MemInc = DMA_MINC_ENABLE;       // 内存地址自增
    hdma_usart1_tx.Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
    hdma_usart1_tx.Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
    hdma_usart1_tx.Init.Mode = DMA_NORMAL;
    hdma_usart1_tx.Init.Priority = DMA_PRIORITY_LOW;
    HAL_DMA_Init(&hdma_usart1_tx);

    // 将 DMA 句柄关联到串口句柄
    __HAL_LINKDMA(&huart1, hdmatx, hdma_usart1_tx);
}
```

---

## 四、HAL 库关键函数

### 4.1 DMA 串口发送（本实验核心）

```c
HAL_UART_Transmit_DMA(&huart1, src, 5);
```

| 参数 | 类型 | 说明 |
|------|------|------|
| huart | UART_HandleTypeDef* | 串口句柄地址 |
| pData | uint8_t* | 发送数据指针 |
| Size | uint16_t | 数据长度 |

### 4.2 三种串口发送方式对比

| 函数 | 方式 | CPU 参与 | 特点 |
|------|------|:--------:|------|
| `HAL_UART_Transmit()` | **阻塞轮询** | ✅ 全程 | CPU 等待发送完成 |
| `HAL_UART_Transmit_IT()` | **中断** | ✅ 触发和响应 | CPU 响应中断 |
| `HAL_UART_Transmit_DMA()` | **DMA** | ❌ 几乎不参与 | **最高效** |

### 4.3 不需要强转类型

```c
// HAL_UART_Transmit_DMA 的参数是 uint8_t* 类型
// 数组名本身就是 uint8_t* 类型
// 不需要像之前那样强转为 uint32_t

HAL_UART_Transmit_DMA(&huart1, src, 5);    // 直接传，无需强转
```

---

## 五、HAL_UART_Transmit_DMA 底层分析

### 5.1 函数内部流程

```c
HAL_StatusTypeDef HAL_UART_Transmit_DMA(UART_HandleTypeDef *huart,
                                         uint8_t *pData, uint16_t Size)
{
    // ① 检查发送缓冲区是否就绪
    if (huart->gState == HAL_UART_STATE_READY)
    {
        // ② 设置发送缓冲区和长度
        huart->pTxBuffPtr = pData;
        huart->TxXferSize = Size;
        huart->TxXferCount = Size;

        // ③ 注册回调函数
        huart->hdmatx->XferCpltCallback   = UART_DMATransmitCplt;
        huart->hdmatx->XferHalfCpltCallback = UART_DMATxHalfCplt;
        huart->hdmatx->XferErrorCallback   = UART_DMAError;

        // ④ 清除 TC 标志
        __HAL_UART_CLEAR_FLAG(huart, UART_FLAG_TC);

        // ⑤ 开启 USART 发送 DMA 使能
        SET_BIT(huart->Instance->CR3, USART_CR3_DMAT);

        // ⑥ 启动 DMA 通道（带中断）
        HAL_DMA_Start_IT(huart->hdmatx,
                         (uint32_t)huart->pTxBuffPtr,
                         (uint32_t)&huart->Instance->DR,
                         Size);
    }
}
```

### 5.2 关键操作

```
① 检查串口是否空闲（READY）
② 设置发送数据指针和长度
③ 注册 DMA 回调函数
④ 清除传输完成标志 TC
⑤ 开启 USART 的 DMA 发送使能（CR3.DMAT）
⑥ 调用 HAL_DMA_Start_IT 启动 DMA 通道

→ 本质上就是之前我们手动做的事情，全部自动完成
```

### 5.3 传输完成回调

```c
// Normal 模式下的传输完成回调
static void UART_DMATransmitCplt(DMA_HandleTypeDef *hdma)
{
    UART_HandleTypeDef *huart = (UART_HandleTypeDef *)hdma->Parent;

    // 关闭 DMA 发送使能
    CLEAR_BIT(huart->Instance->CR3, USART_CR3_DMAT);

    // 开启传输完成中断（TCIE）
    SET_BIT(huart->Instance->CR1, USART_CR1_TCIE);
}
```

```
传输完成后的操作：
  → 关闭 USART 的 DMA 发送使能
  → 开启 TC 中断（等待最后一个字节真正发完）
  → 最终调用 HAL_UART_TxCpltCallback（用户可重写）
```

---

## 六、DMA 通道分配（硬件固定）

### 6.1 串口 TX 和 RX 对应的 DMA 通道

| 串口 | TX 通道 | RX 通道 |
|------|:-------:|:-------:|
| USART1 | DMA1 **Channel 4** | DMA1 Channel 5 |
| USART2 | DMA1 Channel 7 | DMA1 Channel 6 |
| USART3 | DMA1 Channel 2 | DMA1 Channel 3 |
| UART4 | DMA2 Channel 5 | DMA2 Channel 3 |
| UART5 | 无 DMA | 无 DMA |

### 6.2 CubeMX 中自动匹配

```
选择 USART1_TX → 自动选择 DMA1 Channel 4
选择 USART1_RX → 自动选择 DMA1 Channel 5

通道不可更改（硬件固定连线）
```

---

## 七、Normal 模式 vs Circular 模式

### 7.1 CubeMX 配置

| 模式 | CubeMX 选项 | CCR.CIRC |
|------|:-----------:|:--------:|
| **Normal** | Normal | 0 |
| **Circular** | Circular | 1 |

### 7.2 行为差异

```
Normal 模式：
  发送完 5 个字节 → DMA 停止 → 只发一次
  串口输出：abcde（一次）

Circular 模式：
  发送完 5 个字节 → 回到起始地址 → 继续发送 → 循环往复
  串口输出：abcdeabcdeabcde...（不停刷屏）
```

### 7.3 Circular 模式的底层操作

```
当 CNDTR 减到 0 时：
  Normal 模式：停止，产生 TC 事件
  Circular 模式：CNDTR 自动重装为初始值，继续传输
                 源地址自动回到起始位置
                 不产生 TC 事件（或持续产生）
```

---

## 八、主函数实现

### 8.1 Normal 模式

```c
#include "main.h"
#include "usart.h"
#include <stdio.h>

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_USART1_UART_Init();

    // 定义发送数据（在 RAM 中）
    uint8_t src[5] = {'a', 'b', 'c', 'd', 'e'};

    // DMA 方式发送（一行代码搞定）
    HAL_UART_Transmit_DMA(&huart1, src, 5);

    while (1)
    {
    }
}
```

### 8.2 Circular 模式

```c
// CubeMX 中 Mode 改为 Circular
// 代码完全相同
HAL_UART_Transmit_DMA(&huart1, src, 5);
// → 循环发送，不停刷屏
```

---

## 九、运行结果

### Normal 模式

```
abcde
（只发送一次）
```

### Circular 模式

```
abcdeabcdeabcdeabcdeabcde...
（不停循环发送，刷屏）
```

---

## 十、CubeMX 配置与寄存器对照

| CubeMX 配置 | 寄存器 | 值 |
|-------------|--------|:--:|
| Direction = Memory To Peripheral | CCR.DIR | 1 |
| Mode = Normal | CCR.CIRC | 0 |
| Mode = Circular | CCR.CIRC | 1 |
| Peripheral Inc = Disable | CCR.PINC | 0 |
| Memory Inc = Enable | CCR.MINC | 1 |
| Peripheral Width = Byte | CCR.PSIZE | 00 |
| Memory Width = Byte | CCR.MSIZE | 00 |
| Priority = Low | CCR.PL | 00 |

额外配置（HAL 库自动完成）：
| 操作 | 寄存器 | 说明 |
|------|--------|------|
| 串口 DMA 发送使能 | USART1->CR3.DMAT | 由 HAL 自动开启 |
| CPAR | &USART1->DR | 串口数据寄存器地址 |
| CMAR | 数组起始地址 | RAM 中的数据 |
| CNDTR | 数组长度 | 传输数量 |

---

## 十一、HAL 库 DMA 相关串口函数

| 函数 | 功能 |
|------|------|
| `HAL_UART_Transmit()` | 阻塞轮询发送 |
| `HAL_UART_Transmit_IT()` | 中断方式发送 |
| `HAL_UART_Transmit_DMA()` | **DMA 方式发送** |
| `HAL_UART_Receive()` | 阻塞轮询接收 |
| `HAL_UART_Receive_IT()` | 中断方式接收 |
| `HAL_UART_Receive_DMA()` | **DMA 方式接收** |

---

## 十二、HAL 库自动完成的操作

```
调用 HAL_UART_Transmit_DMA 后，HAL 库自动：

① 检查串口状态是否就绪
② 设置发送缓冲区指针和长度
③ 注册 DMA 回调函数
④ 清除 TC 标志
⑤ 开启 USART CR3.DMAT（串口 DMA 发送使能）
⑥ 设置 CPAR = &USART1->DR
⑦ 设置 CMAR = 数据数组地址
⑧ 设置 CNDTR = 数据长度
⑨ 调用 HAL_DMA_Start_IT 启动 DMA 通道
⑩ 开启 DMA 中断

传输完成后自动：
⑪ 关闭 CR3.DMAT
⑫ 开启 TC 中断
⑬ 调用用户可重写的回调函数
```

---

## 十三、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| DMA 配置 | 手动配置 CCR/CPAR/CMAR/CNDTR | CubeMX 图形化 |
| 串口 DMA 使能 | 手动 CR3.DMAT | HAL 自动 |
| 启动传输 | 手动 CCR.EN | `HAL_UART_Transmit_DMA()` |
| 中断处理 | 手动判断/清除 ISR | HAL 自动分发+回调 |
| 代码量 | 较多 | **一行函数调用** |
| 类型转换 | 需要强转 | 不需要 |

---

## 十四、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 串口无输出 | DMA 通道未配置 | CubeMX 中添加 USART1_TX DMA |
| 串口无输出 | USART1 未初始化 | 确认 MX_USART1_UART_Init 调用 |
| 只发送一次 | Normal 模式 | 改为 Circular 循环发送 |
| 循环刷屏 | Circular 模式 | 改为 Normal 单次发送 |
| 数据乱码 | 波特率不匹配 | 确认 115200 |
| 数据乱码 | 数据宽度不匹配 | 确认都是 Byte |
| MicroLib 未勾选 | printf 无法使用 | Keil 中勾选 Use MicroLib |

---

## 十五、从存储器到存储器 → 内存到串口 的对比

| 对比项 | 存储器到存储器 | 内存到串口 |
|--------|:-------------:|:---------:|
| DMA 配置入口 | System Core → DMA | USART1 → DMA Settings |
| MEM2MEM | ✅ | ❌ |
| 通道选择 | 任意 | **硬件固定** |
| DIR | 0（从 ROM 读） | 1（存储器→外设） |
| PINC（外设自增） | ✅（ROM 地址自增） | ❌（串口地址固定） |
| MINC（存储器自增） | ✅（RAM 地址自增） | ✅（数组地址自增） |
| CPAR | ROM 起始地址 | &USART1->DR |
| CMAR | RAM 起始地址 | 数组起始地址 |
| 发送函数 | `HAL_DMA_Start_IT` | `HAL_UART_Transmit_DMA` |
| 循环模式 | 无意义 | **可用** |
| 代码量 | 较多 | **极少** |

---

## 十六、扩展：Circular 模式的底层寄存器操作

```
Circular 模式 vs Normal 模式的区别（CCR.CIRC 位）：

Normal（CIRC=0）：
  CNDTR 减到 0 → 停止 DMA → 产生 TC 事件

Circular（CIRC=1）：
  CNDTR 减到 0 → CNDTR 自动重装为初始值
               → 源地址自动回到起始
               → 继续传输（不停止）

应用场景：
  → 音频循环播放（DAC + DMA + Circular）
  → ADC 循环采样（ADC + DMA + Circular）
  → 串口循环发送（本实验 Circular 模式）
```