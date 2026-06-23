# ADC 独立模式单通道采集 — HAL 库实现 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| 功能 | 采集可变电阻器电压，串口打印 |
| ADC 模块 | ADC1 |
| 通道 | 通道 10（PC0） |
| 模式 | 独立模式 + 连续转换 + 软件触发 |
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

### 2.2 ADC 配置

```
位置：Analog → ADC1

选择通道：
  勾选 IN10（PC0 自动亮起）
```

### 2.3 ADC 参数配置

| 参数 | 值 | 说明 |
|------|:--:|------|
| Mode | **Independent mode** | 独立模式 |
| Data Alignment | **Right alignment** | 右对齐 |
| Scan Conversion Mode | **Disable** | 单通道不需扫描 |
| Continuous Conversion Mode | **Enable** | 连续转换（单曲循环） |
| Discontinuous Conversion Mode | **Disable** | 不用间断模式 |
| Number Of Conversion | **1** | 1 个通道 |
| External Trigger Conversion Source | **Software trigger** | 软件触发（111） |
| Rank 1 Channel | **10** | 通道 10 |
| Sampling Time | **7.5 Cycles** | 采样时间 |

### 2.4 时钟分频配置

```
⚠️ CubeMX 不会自动配置 ADC 分频！

Clock Configuration 页签：
  ADC Prescaler → /6
  72MHz / 6 = 12MHz（< 14MHz ✅）

如果忘记配置：
  → CubeMX 会飘红提示
  → 点击 Cancel 手动配置
  → 不要让它自动调整（可能改变 PLL 配置）
```

### 2.5 不需要的配置

| 配置项 | 说明 |
|--------|------|
| Injected Conversion | 不使用注入通道 |
| Analog Watchdog | 不使用模拟看门狗 |
| DMA | 不使用 DMA |
| NVIC | 不使用中断 |

---

## 三、CubeMX 生成的 ADC 初始化代码

### 3.1 生成的文件

```
adc.c  → MX_ADC1_Init()
adc.h  → ADC 句柄声明
```

### 3.2 ADC 句柄结构体

```c
ADC_HandleTypeDef hadc1;
```

### 3.3 初始化代码（adc.c）

```c
void MX_ADC1_Init(void)
{
    ADC_ChannelConfTypeDef sConfig = {0};

    hadc1.Instance = ADC1;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.ContinuousConvMode = ENABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 1;
    HAL_ADC_Init(&hadc1);

    sConfig.Channel = ADC_CHANNEL_10;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_7CYCLES5;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
}
```

---

## 四、HAL 库关键函数

### 4.1 启动 ADC 转换

```c
HAL_ADC_Start(&hadc1);
```

| 参数 | 说明 |
|------|------|
| hadc | ADC 句柄地址 |

```
函数内部操作：
  → 上电唤醒 ADC
  → 配置触发源
  → 启动规则通道转换
```

### 4.2 校准（关键！）

```c
HAL_ADCEx_Calibration_Start(&hadc1);
```

```
⚠️ 这一步不能省略！

如果不校准：
  → 测量结果有偏差
  → 最大值到不了 3.3V（如只能到 3.25V）

校准位置：
  → 在 HAL_ADC_Start 之前调用
  → 相当于寄存器方式中的 CAL 位操作

函数名含义：
  HAL   = HAL 库
  ADCEx = ADC Extended（扩展功能）
  Calibration_Start = 开始校准
```

### 4.3 获取转换结果

```c
uint32_t value = HAL_ADC_GetValue(&hadc1);
```

| 参数 | 说明 |
|------|------|
| hadc | ADC 句柄地址 |
| 返回值 | DR 寄存器中的 12 位数字量（0~4095） |

```
函数内部操作：
  → 读取 ADC->DR 寄存器
  → 返回 12 位转换结果（右对齐时低 12 位有效）
```

### 4.4 三种启动方式对比

| 函数 | 功能 |
|------|------|
| `HAL_ADC_Start()` | 启动 ADC 转换（轮询） |
| `HAL_ADC_Start_IT()` | 启动 ADC 转换（中断） |
| `HAL_ADC_Start_DMA()` | 启动 ADC 转换（DMA） |

---

## 五、主函数实现

### 5.1 完整代码

```c
#include "main.h"
#include "adc.h"
#include "usart.h"
#include "delay.h"
#include <stdio.h>

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_USART1_UART_Init();

    printf("Hello World!\n");

    // ⚠️ 校准（必须！）
    HAL_ADCEx_Calibration_Start(&hadc1);

    // 启动 ADC 转换
    HAL_ADC_Start(&hadc1);

    while (1)
    {
        // 获取转换结果
        double v = HAL_ADC_GetValue(&hadc1) * 3.3 / 4095;

        // 打印电压值
        printf("V = %.2f V\n", v);

        HAL_Delay(1000);              // 每秒打印一次
    }
}
```

### 5.2 电压计算

```c
double v = HAL_ADC_GetValue(&hadc1) * 3.3 / 4095;

  HAL_ADC_GetValue(&hadc1)  → 读取 12 位数字量（0~4095）
  × 3.3                     → 乘以参考电压
  / 4095                    → 除以最大数字量（2^12 - 1）
  → 得到实际电压值（0V ~ 3.3V）
```

---

## 六、运行结果

### 6.1 校准前（有偏差）

```
V = 1.39 V
V = 2.99 V
V = 3.25 V    ← 最大只能到 3.25V，到不了 3.3V
V = 0.00 V    ← 最小可以到 0V
```

### 6.2 校准后（准确）

```
V = 1.39 V
V = 2.99 V
V = 3.30 V    ← 最大可以到 3.3V ✅
V = 0.00 V    ← 最小可以到 0V ✅
```

---

## 七、校准问题详解

### 7.1 问题现象

```
未校准时：
  → 最大电压只能到 3.25V 左右
  → 与预期的 3.3V 有偏差

原因：
  → ADC 转换器存在固有偏差
  → 类似天平没有调零就开始称重
  → 需要先校准（调零）才能保证精度
```

### 7.2 校准原理

```
天平类比：
  天平使用前 → 调零（让游标归零）
  ADC 使用前 → 校准（消除固有偏差）

校准过程：
  ① HAL_ADCEx_Calibration_Start(&hadc1)
  ② 硬件自动执行校准（类似调零）
  ③ 校准完成，偏差被消除
  ④ 之后的转换结果更加准确
```

### 7.3 校准时机

```
正确顺序：
  ① HAL_ADCEx_Calibration_Start(&hadc1)  ← 先校准
  ② HAL_ADC_Start(&hadc1)                ← 再启动

错误顺序：
  ① HAL_ADC_Start(&hadc1)                ← 先启动
  ② HAL_ADCEx_Calibration_Start(&hadc1)  ← 再校准（可能不生效）
```

---

## 八、HAL 库 ADC 函数汇总

| 函数 | 功能 |
|------|------|
| `HAL_ADC_Init()` | 初始化 ADC |
| `HAL_ADC_ConfigChannel()` | 配置 ADC 通道 |
| `HAL_ADCEx_Calibration_Start()` | **ADC 校准** |
| `HAL_ADC_Start()` | 启动 ADC 转换 |
| `HAL_ADC_Start_IT()` | 启动 ADC 转换（中断） |
| `HAL_ADC_Start_DMA()` | 启动 ADC 转换（DMA） |
| `HAL_ADC_Stop()` | 停止 ADC 转换 |
| `HAL_ADC_GetValue()` | 获取转换结果（读 DR） |
| `HAL_ADC_PollForConversion()` | 等待转换完成 |

---

## 九、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 时钟配置 | 手动 RCC->CFGR | CubeMX 图形化 |
| GPIO 配置 | 手动 CRL/CNF | CubeMX 自动生成 |
| CR1 配置 | 手动 SCAN 位 | CubeMX 参数化 |
| CR2 配置 | 手动 CONT/ALIGN/EXTTRIG/EXTSEL | CubeMX 参数化 |
| SMPR 配置 | 手动 SMP10 位 | CubeMX 下拉选择 |
| SQR 配置 | 手动 SQ1 + L | CubeMX 参数化 |
| 校准 | 手动 CAL 位 + 等待 | `HAL_ADCEx_Calibration_Start()` |
| 启动 | 手动 SWSTART 位 | `HAL_ADC_Start()` |
| 读取 | 手动读 SR + DR | `HAL_ADC_GetValue()` |
| 代码量 | 较多 | **极少** |

---

## 十、CubeMX 配置与寄存器对照

| CubeMX 配置 | 寄存器 | 位 |
|-------------|--------|:--:|
| Independent Mode | CR1.DUALMOD | 0000 |
| Right Alignment | CR2.ALIGN | 0 |
| Scan Disable | CR1.SCAN | 0 |
| Continuous Enable | CR2.CONT | 1 |
| Discontinuous Disable | CR1.DISCEN | 0 |
| Software Trigger | CR2.EXTTRIG=1, EXTSEL=111 | — |
| Number=1 | SQR1.L | 0000 |
| Channel 10 | SQR3.SQ1 | 01010 |
| Sampling 7.5 Cycles | SMPR1.SMP10 | 001 |

---

## 十一、串口打印配置（重写 fputc）

```c
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 1000);
    return ch;
}
```

---

## 十二、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 最大电压不到 3.3V | 未校准 | 添加 `HAL_ADCEx_Calibration_Start()` |
| 读数恒为 0 | 未启动 ADC | 添加 `HAL_ADC_Start()` |
| CubeMX 时钟飘红 | ADC 分频未配 | 手动设置 ADC Prescaler = /6 |
| 读数不变化 | 连续模式未开启 | CubeMX 中 Enable Continuous |
| 通道选择错误 | 引脚不对应 | 确认 PC0 = ADC123_IN10 |
| MicroLib 未勾选 | printf 无法使用 | Keil 中勾选 Use MicroLib |

---

## 十三、调用顺序总结

```
初始化阶段（CubeMX 自动生成）：
  MX_GPIO_Init()      → GPIO 配置
  MX_ADC1_Init()      → ADC 配置
  MX_USART1_UART_Init() → 串口配置

运行阶段（用户代码）：
  ① HAL_ADCEx_Calibration_Start(&hadc1)  → 校准
  ② HAL_ADC_Start(&hadc1)                → 启动转换
  ③ HAL_ADC_GetValue(&hadc1)             → 读取结果
  ④ 电压 = 结果 × 3.3 / 4095             → 计算电压
  ⑤ printf 打印                           → 输出
```