# 通用定时器 TIM5 PWM 呼吸灯 — 寄存器方式实现 笔记

---

## 一、实验需求

| 项目 | 说明 |
|------|------|
| 功能 | LED2 呼吸灯效果（渐亮→渐暗循环） |
| LED2 引脚 | PA1，低电平点亮 |
| 定时器 | **TIM5**，**通道 2** |
| PWM 频率 | 100Hz（周期 10ms） |
| 分辨率 | 100 级（ARR = 99） |

---

## 二、工程搭建

| 操作 | 说明 |
|------|------|
| 复制源 | 018_basic_timer |
| 新工程名 | 020_led_breathe |
| 新增文件 | `Hardware/TIM/tim5.c` / `tim5.h`（替代 tim6） |
| Keil 配置 | 添加 tim5.c，Include Path 已有 |
| Debug | ST-Link, Reset and Run, Pack 去掉 |

---

## 三、GPIO 复用关系

| 引脚 | TIM2 通道 | TIM5 通道 | 本实验 |
|:----:|:---------:|:---------:|:------:|
| **PA1** | TIM2_CH2 | **TIM5_CH2** | ✅ |

---

## 四、PWM 参数计算

### 4.1 设计目标

```
PWM 频率 = 100Hz → 周期 = 10ms（人眼完全看不出闪烁）
分辨率 = 100 级（ARR = 99，CCR 0~99 对应占空比 0%~99%）
```

### 4.2 计算过程

```
① ARR = 99 → 计数次数 = 100
② 目标计数频率 = 100 × 100Hz = 10kHz
③ PSC = 72MHz / 10kHz - 1 = 7199

验证：
  PWM 频率 = 72MHz / ((7199+1) × (99+1)) = 72MHz / 720000 = 100Hz ✅
  占空比 = CCR / 100 × 100%
  CCR = 0  → 0%   → LED 熄灭
  CCR = 50 → 50%  → LED 半亮
  CCR = 99 → 99%  → LED 接近最亮
```

### 4.3 为什么 ARR = 99

```
ARR = 99 → 计数范围 0~99 共 100 个值
→ CCR 值直接等于占空比百分数
→ 设占空比 = 60%，直接写 CCR = 60
→ 无需额外计算，非常方便
```

---

## 五、涉及的寄存器操作汇总

| 步骤 | 寄存器 | 操作 | 含义 |
|:----:|--------|------|------|
| ① | RCC->APB1ENR | OR TIM5EN | 开启 TIM5 时钟 |
| ② | RCC->APB2ENR | OR IOPAEN | **必须**开启 GPIOA 时钟 |
| ③ | GPIOA->CRL | PA1 = 复用推挽输出 | CNF=10, MODE=11 |
| ④ | TIM5->PSC | = 7199 | 7200 分频 → 10kHz |
| ⑤ | TIM5->ARR | = 99 | 100 级计数 |
| ⑥ | TIM5->CCR2 | = 50 | 初始占空比（可任意） |
| ⑦ | TIM5->CCMR1 | CC2S=00, OC2M=110 | 输出模式 + PWM 模式 1 |
| ⑧ | TIM5->CCER | CC2E=1 | 使能通道 2 输出 |
| ⑨ | TIM5->CR1 | CEN=1 | 启动定时器 |

---

## 六、代码实现

### 6.1 tim5.h

```c
#ifndef __TIM5_H
#define __TIM5_H

#include "stm32f10x.h"

void TIM5_Init(void);
void TIM5_Start(void);
void TIM5_Stop(void);
void TIM5_SetDutyCycle(uint8_t duty_cycle);

#endif
```

### 6.2 tim5.c

```c
#include "tim5.h"

/**
 * @brief  TIM5 初始化：PWM 模式 1，通道 2，PA1
 *         PWM 频率 = 100Hz，分辨率 = 100 级
 */
void TIM5_Init(void)
{
    /* ① 开启时钟 */
    RCC->APB1ENR |= RCC_APB1ENR_TIM5EN;     // TIM5 时钟
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;     // GPIOA 时钟（必须开启）

    /* ② GPIO 配置：PA1 复用推挽输出 50MHz */
    GPIOA->CRL |=  (GPIO_CRL_MODE1);        // MODE = 11 (50MHz)
    GPIOA->CRL |=  (GPIO_CRL_CNF1_1);       // CNF = 10 (复用推挽)
    GPIOA->CRL &= ~(GPIO_CRL_CNF1_0);       //

    /* ③ 预分频器：7200 分频 → 10kHz 计数频率 */
    TIM5->PSC = 7199;

    /* ④ 自动重装载值：100 级计数 */
    TIM5->ARR = 99;

    /* ⑤ 捕获/比较寄存器：初始占空比 */
    TIM5->CCR2 = 50;

    /* ⑥ CCMR1：通道 2 配置为输出模式，PWM 模式 1 */
    // CC2S = 00（输出模式）
    TIM5->CCMR1 &= ~TIM_CCMR1_CC2S_0;      // bit[9] = 0
    TIM5->CCMR1 &= ~TIM_CCMR1_CC2S_1;      // bit[8] = 0
    // OC2M = 110（PWM 模式 1）
    TIM5->CCMR1 |=  TIM_CCMR1_OC2M_2;      // bit[14] = 1
    TIM5->CCMR1 |=  TIM_CCMR1_OC2M_1;      // bit[13] = 1
    TIM5->CCMR1 &= ~TIM_CCMR1_OC2M_0;      // bit[12] = 0

    /* ⑦ CCER：使能通道 2 输出 */
    TIM5->CCER |= TIM_CCER_CC2E;            // CC2E = 1

    /* ⑧ 使能定时器 */
    TIM5->CR1 |= TIM_CR1_CEN;
}

/**
 * @brief  启动 TIM5
 */
void TIM5_Start(void)
{
    TIM5->CR1 |= TIM_CR1_CEN;
}

/**
 * @brief  停止 TIM5
 */
void TIM5_Stop(void)
{
    TIM5->CR1 &= ~TIM_CR1_CEN;
}

/**
 * @brief  设置占空比
 * @param  duty_cycle: 占空比百分数 (0~99)
 */
void TIM5_SetDutyCycle(uint8_t duty_cycle)
{
    TIM5->CCR2 = duty_cycle;
}
```

### 6.3 main.c

```c
#include "stm32f10x.h"
#include "tim5.h"
#include "delay.h"
#include <stdio.h>

int main(void)
{
    uint8_t duty_cycle = 0;
    uint8_t dir = 0;   // 0=增大, 1=减小

    TIM5_Init();
    TIM5_Start();

    printf("Hello World!\n");

    while (1)
    {
        /* 根据方向改变占空比 */
        if (dir == 0)   // 增大
        {
            duty_cycle += 1;
            if (duty_cycle >= 99)
            {
                dir = 1;   // 到达最大，开始减小
            }
        }
        else             // 减小
        {
            duty_cycle -= 1;
            if (duty_cycle <= 1)
            {
                dir = 0;   // 到达最小，开始增大
            }
        }

        /* 设置新的占空比 */
        TIM5_SetDutyCycle(duty_cycle);

        /* 延迟，保持当前亮度一段时间 */
        Delay_ms(20);
    }
}
```

---

## 七、GPIO 时钟必须开启

### 7.1 为什么复用输出也需要 GPIO 时钟

```
PA1 输出信号路径：

  TIM5 通道 2 → [复用功能多路选择器] → [输出控制电路] → [MOS 管驱动] → PA1 引脚
                       ↑                      ↑
                  TIM5 时钟驱动           GPIO 时钟驱动

  → 复用信号通过多路选择器（由 TIM5 时钟驱动）
  → 但输出控制电路和 MOS 管驱动器由 GPIO 模块时钟驱动
  → 两者都需要时钟！
```

### 7.2 实验验证

```
❌ 不开启 GPIOA 时钟：LED 不亮（输出驱动器无时钟）
✅ 开启 GPIOA 时钟：LED 正常呼吸

结论：复用功能输出也需要开启对应 GPIO 端口的时钟
      前面课程中省略是因为其他代码已开启过
```

---

## 八、CCMR1 配置详解

### 8.1 通道 2 的位映射（高 8 位）

```
CCMR1（16 位）：
  低 8 位 [7:0]  → 通道 1
  高 8 位 [15:8] → 通道 2

通道 2 关键位：
  bit[9:8]  = CC2S    → 方向选择（00=输出）
  bit[12:10] = OC2M   → 输出模式（110=PWM 模式 1）
  bit[13]   = OC2PE   → 预装载使能
```

### 8.2 配置步骤

```c
// 步骤 1：CC2S = 00（输出模式）
TIM5->CCMR1 &= ~TIM_CCMR1_CC2S_0;    // bit8 = 0
TIM5->CCMR1 &= ~TIM_CCMR1_CC2S_1;    // bit9 = 0

// 步骤 2：OC2M = 110（PWM 模式 1）
TIM5->CCMR1 |=  TIM_CCMR1_OC2M_2;    // bit14 = 1
TIM5->CCMR1 |=  TIM_CCMR1_OC2M_1;    // bit13 = 1
TIM5->CCMR1 &= ~TIM_CCMR1_OC2M_0;    // bit12 = 0
```

### 8.3 CCS 与 GPIO MOD 对比

| 对比项 | GPIO CRL/CRH | 定时器 CCMR |
|--------|:------------:|:-----------:|
| 配置输入 | MOD = 00 | CCS ≠ 00 |
| 配置输出 | MOD ≠ 00 | CCS = 00 |
| **刚好相反！** | | |

---

## 九、CCER 配置

```c
// 使能通道 2 输出
TIM5->CCER |= TIM_CCER_CC2E;    // CC2E = 1

// 极性选择（可选，默认高电平有效）
// TIM5->CCER |= TIM_CCER_CC2P;   // CC2P = 1（低电平有效）
```

| 位 | 名称 | 功能 | 配置 |
|:--:|------|------|:----:|
| 4 | **CC2E** | 通道 2 输出使能 | **必须置 1** |
| 5 | CC2P | 通道 2 极性 | 0=高有效（默认） |

---

## 十、呼吸灯控制逻辑

### 10.1 状态机

```
dir = 0（增大）：
  duty_cycle: 0 → 1 → 2 → ... → 98 → 99
                                        ↓
                                     dir = 1

dir = 1（减小）：
  duty_cycle: 99 → 98 → 97 → ... → 1 → 0
                                        ↓
                                     dir = 0

循环往复 → 呼吸效果
```

### 10.2 呼吸速度控制

| 参数 | 影响 | 调整建议 |
|------|------|----------|
| **Delay_ms 时间** | 每级占空比保持时间 | 增大→呼吸变慢，减小→呼吸变快 |
| **步长（+=1）** | 每次占空比变化量 | 增大→变化更快，但可能不平滑 |
| **ARR 值** | 分辨率 | 越大越平滑，但总步数越多 |

### 10.3 推荐参数

```
步长 = 1（最平滑）
延迟 = 20ms
总呼吸周期 = 2 × 99 × 20ms ≈ 4 秒（一次完整呼吸）
```

---

## 十一、Start/Stop 函数的用途

```c
void TIM5_Start(void)   // 启动定时器
void TIM5_Stop(void)    // 停止定时器
```

| 用途 | 说明 |
|------|------|
| 动态控制 | 需要时开启，不需要时关闭 |
| 节省功耗 | 不用时关闭定时器 |
| 与 HAL 库一致 | `HAL_TIM_Base_Start()` / `HAL_TIM_Base_Stop()` |

---

## 十二、寄存器配置与呼吸灯效果对应

```
CCR2 = 0  → 占空比 0%   → LED 熄灭（最暗）
CCR2 = 25 → 占空比 25%  → LED 较暗
CCR2 = 50 → 占空比 50%  → LED 半亮
CCR2 = 75 → 占空比 75%  → LED 较亮
CCR2 = 99 → 占空比 99%  → LED 接近最亮

通过 main 循环中动态修改 CCR2 实现呼吸效果
```

---

## 十三、完整执行流程

```
系统上电
    │
    ├── TIM5_Init()
    │   ├── RCC: 开启 TIM5 + GPIOA 时钟
    │   ├── GPIO: PA1 复用推挽输出
    │   ├── PSC = 7199（10kHz 计数频率）
    │   ├── ARR = 99（100 级分辨率）
    │   ├── CCR2 = 50（初始占空比）
    │   ├── CCMR1: CC2S=00, OC2M=110（PWM 模式 1）
    │   ├── CCER: CC2E=1（使能输出）
    │   └── CR1: CEN=1（启动定时器）
    │
    ├── TIM5_Start()
    │
    └── 主循环：
        ├── 判断方向 dir
        ├── 增大或减小 duty_cycle
        ├── TIM5_SetDutyCycle(duty_cycle)
        └── Delay_ms(20)
```

---

## 十四、常见问题

| 问题       | 原因            | 解决                        |
| -------- | ------------- | ------------------------- |
| LED 不亮   | 未开启 GPIOA 时钟  | `RCC->APB2ENR \|= IOPAEN` |
| LED 不亮   | CCER.CC2E 未使能 | 确认 CC2E = 1               |
| LED 亮度不变 | CCR2 未更新      | 确认循环中调用 `SetDutyCycle`    |
| LED 闪烁明显 | PWM 频率太低      | 减小 PSC 或增大 ARR            |
| 呼吸不平滑    | 步长太大          | 步长改为 1                    |
| 呼吸太快     | Delay 时间太短    | 增大延迟时间                    |