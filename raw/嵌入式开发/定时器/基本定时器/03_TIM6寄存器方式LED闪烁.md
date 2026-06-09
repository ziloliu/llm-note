# 基本定时器 TIM6 寄存器方式实现 LED2 闪烁 笔记

---

## 一、实验需求

| 项目 | 说明 |
|------|------|
| 功能 | LED2（蓝灯，PA1）每隔 1 秒闪烁一次 |
| 定时器 | TIM6（基本定时器） |
| 方式 | 中断方式 |

---

## 二、工程搭建

| 操作 | 说明 |
|------|------|
| 复制源 | 016_systick 工程 |
| 新工程名 | 018_basic_timer |
| 新增目录 | `Hardware/TIM/` |
| 新增文件 | `tim6.c` / `tim6.h` |
| Keil 添加 | Group: Hardware → 添加 tim6.c |
| Include Path | 添加 `Hardware/TIM` |

---

## 三、TIM6 初始化代码

### 3.1 tim6.h

```c
#ifndef __TIM6_H
#define __TIM6_H
#include "stm32f10x.h"
void TIM6_Init(void);
#endif
```

### 3.2 tim6.c

```c
#include "tim6.h"
#include "led.h"

void TIM6_Init(void)
{
    // ① 开启 TIM6 时钟（APB1 低速总线）
    RCC->APB1ENR |= RCC_APB1ENR_TIM6EN;

    // ② 预分频：7200 分频 → 10kHz
    TIM6->PSC = 7199;

    // ③ 自动重装载：计数 10000 次 → 1s
    TIM6->ARR = 9999;

    // ④ 使能更新中断
    TIM6->DIER |= TIM_DIER_UIE;

    // ⑤ 配置 NVIC
    NVIC_SetPriorityGrouping(3);
    NVIC_SetPriority(TIM6_IRQn, 3);
    NVIC_EnableIRQ(TIM6_IRQn);

    // ⑥ 使能定时器（最后）
    TIM6->CR1 |= TIM_CR1_CEN;
}

void TIM6_IRQHandler(void)
{
    if (TIM6->SR & TIM_SR_UIF)
    {
        TIM6->SR &= ~TIM_SR_UIF;   // 清除中断标志
        LED2_Toggle();               // 翻转 LED2
    }
}
```

### 3.3 main.c

```c
#include "stm32f10x.h"
#include "led.h"
#include "tim6.h"

int main(void)
{
    LED_Init();
    TIM6_Init();
    while (1) {}
}
```

---

## 四、配置流程与寄存器操作

| 步骤 | 寄存器 | 操作 | 值 | 含义 |
|:----:|--------|------|:--:|------|
| ① | RCC->APB1ENR | OR | TIM6EN | 开启 TIM6 时钟 |
| ② | TIM6->PSC | = | 7199 | 7200 分频 → 10kHz |
| ③ | TIM6->ARR | = | 9999 | 计数 10000 次 |
| ④ | TIM6->DIER | OR | UIE | 使能更新中断 |
| ⑤ | NVIC | Enable | TIM6_IRQn | 使能 NVIC 中断 |
| ⑥ | TIM6->CR1 | OR | CEN | 启动计数器 |
| 中断 | TIM6->SR | AND ~UIF | — | 清除中断标志 |

---

## 五、定时参数计算

```
定时时间 = (PSC + 1) × (ARR + 1) / 时钟频率
        = (7199 + 1) × (9999 + 1) / 72MHz
        = 7200 × 10000 / 72000000
        = 72000000 / 72000000
        = 1 秒 ✅
```

---

## 六、注意事项

| 易错点 | 说明 |
|--------|------|
| APB1 不是 APB2 | TIM6 连接 APB1，不要写 `RCC_APB2ENR` |
| PSC/ARR 不超 65535 | 16 位寄存器限制 |
| 必须配 NVIC | 外设中断需手动配置（与 SysTick 不同） |
| 必须清除 UIF | 软件写 0，否则中断反复触发 |
| 最后开启 CEN | 确保所有参数配置完成后再启动 |