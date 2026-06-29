# ADC 独立模式多通道采集（DMA 方式）— HAL 库实现 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| 功能 | 双通道模拟信号采集，串口打印 |
| ADC 模块 | ADC1（独立模式） |
| 通道 | 通道 10（PC0，可变电阻）+ 通道 12（PC2） |
| 工作模式 | 扫描模式 + 连续转换 + 软件触发 |
| 数据传输 | DMA |
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

### 2.2 ADC 通道选择

```
Analog → ADC1：
  ✅ IN10（PC0）  ← 可变电阻器
  ✅ IN12（PC2）  ← 悬空/外接信号

两个通道勾选后，PC0 和 PC2 自动亮起
```

### 2.3 ADC 参数配置

| 参数 | 值 | 说明 |
|------|:--:|------|
| Mode | **Independent mode** | 独立模式 |
| Data Alignment | **Right alignment** | 右对齐 |
| Scan Conversion Mode | **Enable**（自动） | 多通道自动开启 |
| Continuous Conversion Mode | **Enable** | 连续转换（列表循环） |
| Discontinuous Conversion Mode | **Disable** | 与循环模式矛盾 |
| Number Of Conversion | **2** | 2 个通道 |
| External Trigger | **Software trigger** | 软件触发 |
| Rank 1 Channel | **10** | 通道 10 |
| Rank 2 Channel | **12** | 通道 12 |
| Sampling Time | 1.5/7.5 Cycles | 各通道可独立配置 |

### 2.4 CubeMX 智能行为

```
① Number of Conversion 从 1 改为 2 时：
   → Scan Conversion Mode 自动从 Disable 变为 Enable
   → 因为多通道必须开启扫描模式

② Continuous Conversion Mode 设为 Enable 时：
   → Discontinuous Conversion Mode 自动灰掉
   → 因为循环模式和间断模式互相矛盾

③ 数据宽度自动设为 Half Word（16 位）：
   → 匹配 ADC DR 寄存器的 16 位宽度
```

### 2.5 ADC 时钟分频

```
Clock Configuration 页签：
  ADC Prescaler → /6
  72MHz / 6 = 12MHz（< 14MHz ✅）

⚠️ 必须先开启 ADC1 模块，才能配置分频
  → 未开启 ADC1 时，分频选项是灰色的
  → 先勾选 ADC 通道 → 再回到 Clock Configuration 配置
```

### 2.6 DMA 配置

```
两种入口（效果相同）：
  ① System Core → DMA → Add → ADC1
  ② Analog → ADC1 → DMA Settings → Add

配置参数：
```

| 参数 | 值 | 说明 |
|------|:--:|------|
| DMA Request | **ADC1** | ADC1 的 DMA 请求 |
| Direction | **Peripheral To Memory** | 外设→存储器（固定） |
| Peripheral Inc | **Disable** | DR 地址不自增 |
| Memory Inc | **Enable** | 数组地址自增 |
| Peripheral Data Width | **Half Word** | 16 位 |
| Memory Data Width | **Half Word** | 16 位 |
| Mode | **Circular** | 循环模式（配合 ADC 连续转换） |

### 2.7 NVIC 配置（重要！）

```
⚠️ 必须关闭 DMA 中断！

问题：
  → CubeMX 默认勾选 "Force DMA channels interrupt"
  → DMA 传输速度极快，中断极其频繁
  → 频繁中断会卡死程序

解决：
  ① 取消勾选 "Force DMA channels interrupt"
  ② 取消勾选 DMA1 Channel1 中断

NVIC 页签：
  ❌ DMA1 Channel1 global interrupt（取消勾选）
```

---

## 三、CubeMX 生成的代码

### 3.1 生成文件

```
adc.c    → MX_ADC1_Init() + DMA 通道配置
adc.h    → ADC 句柄声明
dma.c    → MX_DMA_Init()（几乎为空）
dma.h    → DMA 头文件
```

### 3.2 ADC 初始化代码（adc.c 自动生成）

```c
ADC_HandleTypeDef hadc1;
DMA_HandleTypeDef hdma_adc1;

void MX_ADC1_Init(void)
{
    ADC_ChannelConfTypeDef sConfig = {0};

    hadc1.Instance = ADC1;
    hadc1.Init.ScanConvMode = ADC_SCAN_ENABLE;        // 扫描开启
    hadc1.Init.ContinuousConvMode = ENABLE;            // 连续转换
    hadc1.Init.DiscontinuousConvMode = DISABLE;        // 间断禁用
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;  // 软件触发
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;        // 右对齐
    hadc1.Init.NbrOfConversion = 2;                    // 2 个通道
    hadc1.Init.DMAContinuousRequests = ENABLE;         // DMA 连续请求
    HAL_ADC_Init(&hadc1);

    // 通道 10
    sConfig.Channel = ADC_CHANNEL_10;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_1CYCLE5;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    // 通道 12
    sConfig.Channel = ADC_CHANNEL_12;
    sConfig.Rank = ADC_REGULAR_RANK_2;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
}
```

### 3.3 DMA 初始化（dma.c 自动生成，几乎为空）

```c
void MX_DMA_Init(void)
{
    __HAL_RCC_DMA1_CLK_ENABLE();
    // DMA 通道配置已在 adc.c 中通过 HAL_ADC_Init 自动完成
}
```

---

## 四、HAL 库关键函数

### 4.1 校准（必须！）

```c
HAL_ADCEx_Calibration_Start(&hadc1);
```

```
⚠️ 必须在启动转换之前调用
  → 不校准：最大电压只能到约 3.25V
  → 校准后：最大电压可达 3.3V
```

### 4.2 DMA 方式启动 ADC

```c
HAL_ADC_Start_DMA(&hadc1, (uint32_t *)data, 2);
```

| 参数 | 类型 | 说明 |
|------|------|------|
| hadc | ADC_HandleTypeDef* | ADC 句柄地址 |
| pData | uint32_t* | 目标数组地址（**需强转**） |
| Length | uint32_t | 数据长度 |

```
⚠️ 类型转换注意：
  data 是 uint16_t 数组（uint16_t* 类型）
  函数需要 uint32_t* 类型
  → 必须强转：(uint32_t *)data

函数内部自动完成：
  → 配置 DMA 外设地址 = ADC1->DR
  → 配置 DMA 存储器地址 = data 数组首地址
  → 配置 DMA 数据量 = 2
  → 开启 DMA 通道
  → 开启 ADC
  → 启动转换
```

### 4.3 三种 ADC 启动方式对比

| 函数 | 功能 | DMA | 中断 |
|------|------|:---:|:----:|
| `HAL_ADC_Start()` | 轮询启动 | ❌ | ❌ |
| `HAL_ADC_Start_IT()` | 中断启动 | ❌ | ✅ |
| `HAL_ADC_Start_DMA()` | **DMA 启动** | ✅ | ❌ |

---

## 五、主函数实现

### 5.1 完整代码

```c
#include "main.h"
#include "adc.h"
#include "dma.h"
#include "usart.h"
#include "delay.h"
#include <stdio.h>

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_DMA_Init();                   // DMA 初始化
    MX_ADC1_Init();                  // ADC 初始化
    MX_USART1_UART_Init();

    printf("Hello World!\n");

    // 校准
    HAL_ADCEx_Calibration_Start(&hadc1);

    // DMA 方式启动 ADC 转换
    uint16_t data[2] = {0, 0};
    HAL_ADC_Start_DMA(&hadc1, (uint32_t *)data, 2);

    while (1)
    {
        // 打印两个通道的电压值
        printf("可变电阻(ADC10): %.2f V\t", data[0] * 3.3 / 4095);
        printf("PC2(ADC12): %.2f V\n", data[1] * 3.3 / 4095);
        HAL_Delay(1000);
    }
}
```

### 5.2 关键点

```
① MX_DMA_Init() 必须在 MX_ADC1_Init() 之前调用
   → DMA 必须先初始化，ADC 才能关联 DMA 句柄

② HAL_ADCEx_Calibration_Start() 在 Start_DMA 之前调用

③ data[2] 数组直接存储转换结果
   → 不需要 GetValue 函数
   → DMA 自动将 DR 值写入数组

④ 电压计算公式：data[i] × 3.3 / 4095
```

### 5.3 类型转换说明

```c
// data 是 uint16_t[2] 数组
// data 的类型是 uint16_t*
// 函数参数需要 uint32_t*

HAL_ADC_Start_DMA(&hadc1, (uint32_t *)data, 2);
//                        ↑ 必须强转

// 也可以用更明确的写法：
HAL_ADC_Start_DMA(&hadc1, (uint32_t *)&data[0], 2);
```

---

## 六、运行结果

### 6.1 校准后

```
Hello World!
可变电阻(ADC10): 3.30 V    PC2(ADC12): 3.29 V   ← PC2 接 3.3V
可变电阻(ADC10): 2.00 V    PC2(ADC12): 1.50 V   ← PC2 浮空，受干扰
可变电阻(ADC10): 0.00 V    PC2(ADC12): 1.00 V   ← PC2 浮空
可变电阻(ADC10): 0.00 V    PC2(ADC12): 0.00 V   ← PC2 接 GND
```

### 6.2 浮空输入现象

```
PC2 悬空时：
  → 电压约 1.64V
  → 会随 PC0 可变电阻调节而漂移
  → 因为两个引脚距离近，互相感应

PC2 接 3.3V：→ 约 3.29V
PC2 接 GND：→ 约 0.00V
```

---

## 七、DMA 配置与 ADC 配置的匹配

| ADC 配置 | DMA 配置 | 匹配 |
|----------|----------|:----:|
| Continuous Mode = Enable | Mode = **Circular** | ✅ |
| Continuous Mode = Enable | Mode = Normal | ❌（DMA 会停） |
| Data = 16 位 | Data Width = Half Word | ✅ |
| DMA Continuous Requests = Enable | — | 自动配置 |

```
ADC 连续转换 + DMA 循环传输 = 完美配合

ADC 转换完一组 → DR 有数据 → DMA 自动传输到数组
→ ADC 继续下一组转换 → DMA 继续传输 → 循环往复

实时更新 data[0] 和 data[1] 中的值
```

---

## 八、NVIC 配置注意事项

### 8.1 为什么必须关闭 DMA 中断

```
DMA 传输速度极快：
  → ADC 转换一次约几微秒
  → DMA 每次传输完成就产生一次中断
  → 每秒可能产生数十万次中断
  → CPU 全程处理中断，主程序无法执行
  → 程序卡死

解决方案：
  → 关闭 DMA 中断
  → DMA 在后台静默传输
  → CPU 正常执行主程序
  → 直接从 data 数组读取最新值
```

### 8.2 CubeMX 中关闭中断

```
① 取消 "Force DMA channels interrupt" 勾选
② 取消 DMA1 Channel1 global interrupt 勾选
③ DMA 通道正常工作，但不产生中断
```

---

## 九、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| ADC 配置 | 手动 20+ 个寄存器位 | CubeMX 图形化 |
| DMA 配置 | 手动 7 个 CCR 位 + 3 个寄存器 | CubeMX 图形化 |
| 启动顺序 | 必须注意 ADC 先上电 | CubeMX 自动处理 |
| 校准 | 手动 CAL 位 | `HAL_ADCEx_Calibration_Start()` |
| 启动转换 | 手动 ADON + SWSTART | `HAL_ADC_Start_DMA()` |
| 获取结果 | 手动读 DR | **直接读 data 数组** |
| 代码量 | 约 100 行 | **约 10 行** |

---

## 十、完整调用流程

```
初始化阶段：
  MX_DMA_Init()                     → DMA 初始化
  MX_ADC1_Init()                    → ADC 初始化
  MX_USART1_UART_Init()            → 串口初始化

运行阶段：
  ① HAL_ADCEx_Calibration_Start()   → 校准
  ② HAL_ADC_Start_DMA()             → DMA 方式启动 ADC
  ③ data[0] × 3.3 / 4095           → 计算通道 10 电压
  ④ data[1] × 3.3 / 4095           → 计算通道 12 电压
  ⑤ printf 打印                     → 串口输出
  ⑥ HAL_Delay(1000)                 → 延时 1 秒
  ⑦ 循环 ③ ~ ⑥
```

---

## 十一、CubeMX 配置与寄存器对照

| CubeMX 配置 | 寄存器 | 位 |
|-------------|--------|:--:|
| Independent Mode | CR1.DUALMOD | 0000 |
| Right Alignment | CR2.ALIGN | 0 |
| Scan Enable | CR1.SCAN | 1 |
| Continuous Enable | CR2.CONT | 1 |
| Software Trigger | CR2.EXTTRIG=1, EXTSEL=111 | — |
| Number = 2 | SQR1.L | 1 |
| Rank 1 = Ch10 | SQR3.SQ1 | 01010 |
| Rank 2 = Ch12 | SQR3.SQ2 | 01100 |
| DMA Continuous Requests | CR2.DMA | 1 |
| DMA Direction | DMA_CCR.DIR | 0 |
| DMA Circular | DMA_CCR.CIRC | 1 |
| DMA Half Word | DMA_CCR.PSIZE/MSIZE | 01 |

---

## 十二、常见问题

| 问题          | 原因          | 解决                              |
| ----------- | ----------- | ------------------------------- |
| 程序卡死        | DMA 中断频繁    | 关闭 DMA 中断                       |
| 最大电压不到 3.3V | 未校准         | `HAL_ADCEx_Calibration_Start()` |
| data 数组不更新  | DMA 未启动     | 检查 `HAL_ADC_Start_DMA` 调用       |
| 类型编译错误      | 未强转         | `(uint32_t *)data`              |
| 浮空引脚数据漂移    | 未接信号源       | 接确定信号或配置上下拉                     |
| CubeMX 分频灰色 | ADC 未开启     | 先勾选 ADC 通道                      |
| DMA 中断无法关闭  | Force 勾选未取消 | 取消 Force DMA channels interrupt |
| 两通道数据反了     | Rank 顺序配反   | 检查 Rank 1=Ch10, Rank 2=Ch12     |