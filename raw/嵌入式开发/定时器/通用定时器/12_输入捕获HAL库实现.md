# 输入捕获测量 PWM 周期和频率 — HAL 库实现 笔记

---

## 一、CubeMX 配置

### 1.1 基础配置

| 配置项 | 设置 |
|--------|------|
| Debug | Serial Wire |
| RCC | HSE 外部高速晶振 |
| 时钟树 | HSE → PLL ×9 → 72MHz, APB1 /2 → 36MHz |
| Connectivity | USART1 异步模式 |

### 1.2 TIM5 配置（PWM 输出 — 信号源）

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| Clock Source | Internal Clock | 内部时钟 |
| Channel 2 | PWM Generation CH2 | PWM 输出 |
| Prescaler (PSC) | 7199 | 7200 分频 → 10kHz |
| Counter Mode | Up | 向上计数 |
| Counter Period (ARR) | 99 | 100 级 |
| **Pulse (CCR)** | **60** | **不能为 0 或 100** |
| PWM Mode | Mode 1 | PWM 模式 1 |
| CH Polarity | High | 高电平有效 |

```
⚠️ Pulse（CCR）不能为 0 或 100
   → 0：输出恒低电平，无方波
   → 100：输出恒高电平，无方波
   → 无方波 = 无法检测周期和频率
```

### 1.3 TIM4 配置（输入捕获）

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| Slave Mode | **Disable** | 不使用从模式 |
| Trigger Source | Disable | 不使用触发源 |
| Clock Source | **Internal Clock** | 72MHz 内部时钟 |
| Channel 1 | **Input Capture direct mode** | 直连模式 |
| Prescaler (PSC) | **71** | 72 分频 → 1MHz（1μs 精度） |
| Counter Mode | Up | 向上计数 |
| Counter Period (ARR) | 65535 | 最大值，防止溢出 |

#### 通道 1 配置

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| Polarity Selection | **Rising Edge** | 上升沿捕获 |
| IC Selection | **Direct** | 直连模式 |
| IC Prescaler | No Division | 不分频 |
| IC Filter | 0 | 不滤波 |

### 1.4 与寄存器版本的对比

| 配置项 | 寄存器版本 | HAL 库版本 |
|--------|-----------|-----------|
| 从模式 | 不配置 | Disable |
| 触发源 | 不配置 | Disable |
| 时钟源 | 内部时钟 | Internal Clock |
| 通道模式 | CCMR1.CC1S=01 | Input Capture direct mode |
| 极性 | CCER.CC1P=0 | Rising Edge |
| 滤波 | CCMR1.IC1F=0 | IC Filter=0 |
| 预分频 | CCMR1.IC1PSC=0 | No Division |
| NVIC | 手动配置 | 勾选 TIM4 中断 |

### 1.5 与 PWM 输入模式的区别

| 对比项 | 本实验（简单输入捕获） | PWM 输入模式 |
|--------|----------------------|-------------|
| 通道数 | **1 个**（CH1） | **2 个**（CH1+CH2） |
| 从模式 | **不用** | Reset Mode |
| 触发源 | **不用** | TI1FP1 |
| 捕获内容 | 仅周期 | 周期 + 占空比 |
| 中断 | **需要** | 不需要 |
| 全局变量 | 不需要 | 不需要 |
| 复杂度 | 较低 | 较高 |

---

## 二、GPIO 重映射问题

### 2.1 问题现象

```
CubeMX 默认将 TIM4_CH1 映射到 PD12（重映射）
而非 PB6（默认复用）

原因：PB6 同时是 I2C1_SCL 的默认复用引脚
     HAL 库优先将 PB6 分配给 I2C1
```

### 2.2 数据手册确认

```
PB6 的复用功能：
  ① I2C1_SCL（默认复用功能 — 优先）
  ② TIM4_CH1（重定义功能）

PD12 的复用功能：
  ① TIM4_CH1（重定义位置）
  ② 其他功能

TIM4_CH1 默认应在 PB6，重映射到 PD12
CubeMX 因 I2C1 优先而选择 PD12
```

### 2.3 解决步骤

```
① GPIO 页面找到 PD12 → 点击 Reset 释放
② 滚动找到 PB6 → 点击选择
③ 复用功能列表中选择 TIM4_CH1
④ 回到 TIM4 页面，通道 1 变为 Disable（黄色警告）
⑤ 重新勾选 Channel 1 → Input Capture direct mode
⑥ 重新配置极性、滤波等参数
⑦ 确认 PB6 引脚变绿 ✅
⑧ 确认 TIM4 页面无黄色警告 ✅
```

---

## 三、HAL 库关键函数

### 3.1 启动函数

```c
// TIM5 PWM 输出
HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2);

// TIM4 输入捕获（带中断）
HAL_TIM_IC_Start_IT(&htim4, TIM_CHANNEL_1);
```

### 3.2 函数选择逻辑

```
HAL_TIM_xxx_Start / HAL_TIM_xxx_Start_IT / HAL_TIM_xxx_Start_DMA

功能前缀：
  PWM_     → PWM 输出
  IC_      → 输入捕获
  OC_      → 输出比较
  Base_    → 基本定时

后缀：
  _Start     → 不带中断
  _Start_IT  → 带中断
  _Start_DMA → 带 DMA

本实验：输入捕获 + 中断 → HAL_TIM_IC_Start_IT
```

### 3.3 设置计数器值（清零）

```c
__HAL_TIM_SET_COUNTER(&htim4, 0);
```

```
__HAL_TIM_SET_COUNTER 是宏定义函数：
  参数1：定时器句柄地址
  参数2：新的计数值

底层操作：TIM4->CNT = 0
```

### 3.4 获取 CCR 值

```c
__HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1);
```

```
⚠️ 没有 __HAL_TIM_GET_CAPTURE 函数
   输入捕获和输出比较共用 CCR 寄存器
   底层操作的是同一个寄存器
   所以用 __HAL_TIM_GET_COMPARE 即可
```

---

## 四、中断回调函数

### 4.1 回调函数选择

```
HAL 库中的输入捕获回调函数：

HAL_TIM_IC_CaptureCallback()       ← 完整捕获回调
HAL_TIM_IC_CaptureHalfCpltCallback() ← 半完成回调

本实验使用：HAL_TIM_IC_CaptureCallback
```

### 4.2 回调函数实现

```c
void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM4)
    {
        __HAL_TIM_SET_COUNTER(&htim4, 0);    // 清零计数器
    }
}
```

### 4.3 回调触发机制

```
TIM4 检测到上升沿
  → 硬件捕获事件：CCR1 = CNT（快照）
  → 中断标志位置位：SR.CC1IF = 1
  → 中断处理：HAL_TIM_IRQHandler()
    → 识别为输入捕获中断
    → 调用 HAL_TIM_IC_CaptureCallback()
      → 清零 CNT
```

### 4.4 为什么这里用回调函数

```
TIM1 有专用中断入口：TIM1_UP_IRQHandler（更新中断）
  → 可以直接在 IRQHandler 中处理

TIM4 只有一个入口：TIM4_IRQHandler
  → 内部由 HAL_TIM_IRQHandler 统一分发
  → 根据中断类型调用不同回调函数
  → 所以用回调函数更清晰

可用的回调函数：
  HAL_TIM_PeriodElapsedCallback()    → 更新（溢出）
  HAL_TIM_IC_CaptureCallback()       → 输入捕获
  HAL_TIM_OC_DelayElapsedCallback()  → 输出比较
```

---

## 五、封装自定义函数

### 5.1 函数声明（tim.h）

```c
/* USER CODE BEGIN Prototypes */
double TIM4_GetPWMPeriod(void);
double TIM4_GetPWMFrequency(void);
/* USER CODE END Prototypes */
```

### 5.2 函数实现（tim.c）

```c
/* USER CODE BEGIN 1 */

double TIM4_GetPWMPeriod(void)
{
    return (double)__HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1) / 1000.0;
}

double TIM4_GetPWMFrequency(void)
{
    uint32_t ccr1 = __HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1);
    if (ccr1 == 0)
        return 0;
    return 1000000.0 / (double)ccr1;
}

/* USER CODE END 1 */
```

### 5.3 单位换算

```
CCR1 值单位：μs（因为 PSC=71 → 1MHz → 1μs/次）

周期 = CCR1 / 1000.0    → ms
频率 = 1000000.0 / CCR1 → Hz
```

---

## 六、重写 fputc（串口重定向）

```c
// usart.c 中添加
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 1000);
    return ch;
}
```

---

## 七、主函数

### 7.1 完整代码

```c
#include "main.h"
#include "tim.h"
#include "usart.h"
#include <stdio.h>

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_TIM4_Init();
    MX_TIM5_Init();

    /* 启动 TIM5 PWM 输出 */
    HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2);

    /* 启动 TIM4 输入捕获（带中断） */
    HAL_TIM_IC_Start_IT(&htim4, TIM_CHANNEL_1);

    printf("Hello World!\n");

    while (1)
    {
        printf("T=%.2fms, F=%.2fHz\n",
               TIM4_GetPWMPeriod(),
               TIM4_GetPWMFrequency());

        HAL_Delay(1000);
    }
}
```

---

## 八、运行结果

```
Hello World!
T=10.00ms, F=100.00Hz
T=10.00ms, F=100.00Hz
T=10.00ms, F=100.00Hz
...
```

```
TIM5：PSC=7199, ARR=99, CCR=60
  → PWM 频率 = 100Hz
  → 周期 = 10ms
  → 占空比 = 60%

TIM4 测量：
  CCR1 ≈ 10000 → 周期 ≈ 10ms ✅
  频率 ≈ 100Hz ✅
```

---

## 九、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 时钟开启 | 手动 RCC | CubeMX 自动生成 |
| GPIO 配置 | 手动 CRL 位操作 | CubeMX（注意重映射） |
| CCMR 配置 | 手动 CC1S/IC1F/IC1PSC | CubeMX 下拉选择 |
| CCER 配置 | 手动 CC1P/CC1E | CubeMX Rising/Falling |
| NVIC 配置 | 手动 3 行代码 | CubeMX 勾选 |
| 启动定时器 | `CR1.CEN = 1` | `HAL_TIM_IC_Start_IT()` |
| 中断服务 | `TIM4_IRQHandler` 直接写 | 重写 `HAL_TIM_IC_CaptureCallback` |
| 清零 CNT | `TIM4->CNT = 0` | `__HAL_TIM_SET_COUNTER(&htim4, 0)` |
| 读取 CCR | `TIM4->CCR1` | `__HAL_TIM_GET_COMPARE()` |
| 代码量 | 较多 | **更少** |

---

## 十、事件 vs 中断顺序（HAL 库版本）

```
上升沿到来
    │
    ├─→ 硬件事件：CCR1 = CNT（瞬间完成）
    │
    └─→ 中断处理：
         HAL_TIM_IRQHandler()
           → 识别输入捕获中断
           → 清除 SR.CC1IF
           → 调用 HAL_TIM_IC_CaptureCallback()
             → __HAL_TIM_SET_COUNTER(&htim4, 0)

硬件捕获永远先于中断清零
→ CCR1 中始终保存正确的周期值
→ 无需全局变量，无需 count 状态机
```

---

## 十一、检查清单

```
硬件：
  ✅ 跳线帽连接 PA1（TIM5_CH2）→ PB6（TIM4_CH1）

CubeMX 配置：
  ✅ TIM5：PWM Generation CH2, PSC=7199, ARR=99, CCR=60
  ✅ TIM4：Input Capture direct mode, PSC=71, Rising Edge
  ✅ PB6 正确映射为 TIM4_CH1（非 PD12）
  ✅ NVIC 勾选 TIM4 中断

代码：
  ✅ usart.c 中重写 fputc
  ✅ 勾选 MicroLib
  ✅ Debug 中勾选 Reset and Run
  ✅ HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2)
  ✅ HAL_TIM_IC_Start_IT(&htim4, TIM_CHANNEL_1)
  ✅ 重写 HAL_TIM_IC_CaptureCallback → 清零 CNT
  ✅ 封装 GetPeriod / GetFrequency 函数
```

---

## 十二、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 周期在 10ms/20ms 交替 | 中断中未清零 CNT | 回调中加 `SET_COUNTER(0)` |
| 结果全为 0 | 忘记初始化 TIM4 | 补上 `MX_TIM4_Init()` |
| 结果全为 0 | 忘记启动 TIM4 | 补上 `HAL_TIM_IC_Start_IT` |
| 引脚映射到 PD12 | CubeMX 重映射 | 手动改回 PB6 |
| 结果全为 0 | TIM5 CCR=0（无方波） | CCR 改为 60 |
| 串口无输出 | 未勾选 MicroLib | Keil 中勾选 |
| 首次输出为 0 | 刚启动还未捕获 | 正常现象，第二次开始正常 |
| 函数名冲突 count | systick.c 中也有 count | 改名或删除 systick.c |