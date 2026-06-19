# 高级定时器有限次数 PWM 输出 — HAL 库实现 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| 定时器 | **TIM1**（高级定时器） |
| 功能 | 输出固定次数的 PWM 方波（闪 5 次后停止） |
| 输出引脚 | **PA8**（TIM1_CH1） |
| PWM 频率 | 2Hz（周期 0.5s） |
| 占空比 | 50% |
| 闪烁次数 | **5 次** |
| 总时长 | 2.5 秒 |

---

## 二、CubeMX 配置

### 2.1 基础配置

| 配置项 | 设置 |
|--------|------|
| Debug | Serial Wire |
| RCC | HSE 外部高速晶振 |
| 时钟树 | HSE → PLL ×9 → 72MHz, APB1 /2 → 36MHz |
| Connectivity | USART1 异步模式（串口打印） |

### 2.2 TIM1 配置

#### 时基部分

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| Clock Source | Internal Clock | 内部时钟 |
| Channel 1 | PWM Generation CH1 | PWM 输出 |
| **Prescaler (PSC)** | **7199** | 7200 分频 → 10kHz |
| **Counter Mode** | Up | 向上计数 |
| **Counter Period (ARR)** | **4999** | 5000 次计数 → 0.5 秒 |
| **Repetition Counter (RCR)** | **4** | 重复计数 = 4 → 更新事件在第 5 次溢出时产生 |
| Internal Clock Division | No Division | 不分频 |
| Auto-reload Preload | Disable | 立即生效 |

#### PWM 通道部分

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| PWM Mode | Mode 1 | PWM 模式 1 |
| **Pulse (CCR)** | **2500** | 50% 占空比 |
| Output Compare Preload | Enable | 预装载使能 |
| Fast Mode | Disable | 关闭 |
| CH Polarity | **Low** | **低电平有效** |
| **OC Idle State** | **Set** | **空闲状态为高电平** |

#### PWM 参数计算

```
计数频率 = 72MHz / 7200 = 10kHz
一个 PWM 周期 = 5000 次计数 / 10kHz = 0.5 秒
PWM 频率 = 1 / 0.5 = 2Hz
占空比 = CCR / (ARR+1) = 2500 / 5000 = 50%

总闪烁次数 = RCR + 1 = 4 + 1 = 5 次
总时长 = 5 × 0.5 = 2.5 秒
```

### 2.3 GPIO 重映射问题

```
CubeMX 默认将 TIM1_CH1 映射到 PE 9（重映射）
实际需要 PA 8（默认复用）

解决步骤：
  ① GPIO 页面找到 PE 9 → Reset 释放
  ② 找到 PA 8 → 选择 TIM1_CH1
  ③ 回到 TIM1 页面重新勾选 Channel 1
  ④ 重新配置占空比（会被重置）
  ⑤ 确认 PA 8 变绿
```

### 2.4 NVIC 配置

| 中断 | 勾选 |
|------|:----:|
| **TIM1 update interrupt** | ✅ |

---

## 三、RCR（重复计数寄存器）原理

### 3.1 RCR 工作机制

```
RCR = 4 时：

溢出次数:  第1次   第2次   第3次   第4次   第5次
           ↓      ↓      ↓      ↓      ↓
RCR 递减:   4→3    3→2    2→1    1→0    0→产生更新事件
PWM 输出:   ✅      ✅      ✅      ✅      ✅（最后一次）
                                                  ↓
                                              定时器停止

总 PWM 周期数 = RCR + 1 = 5
```

### 3.2 关键区别

| 定时器类型 | RCR 行为 |
|-----------|----------|
| 基本定时器（TIM6/7） | 无 RCR |
| 通用定时器（TIM2~5） | 无 RCR |
| **高级定时器（TIM1/8）** | **有 RCR**，可控制更新事件产生频率 |

---

## 四、占空比配置注意事项

### 4.1 初始错误

```
ARR = 4999（计数 0~4999，共 5000 个值）
CCR = 50 → 占空比 = 50/5000 = 1%

→ 几乎全部是低电平（低电平点亮）
→ LED 看起来像常亮
→ 只有微弱闪烁
```

### 4.2 正确配置

```
ARR = 4999
CCR = 2500 → 占空比 = 2500/5000 = 50%

→ 高电平 2500 个计数周期（0.25 秒）
→ 低电平 2500 个计数周期（0.25 秒）
→ 正常闪烁
```

---

## 五、HAL 库关键函数

### 5.1 启动函数

```c
// ✅ 正确：只启动 PWM，不开启中断
HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);

// ❌ 错误：HAL_TIM_PWM_Start_IT 开启的是 CC 中断，不是更新中断
HAL_TIM_PWM_Start_IT(&htim1, TIM_CHANNEL_1);  // 不要用！
```

### 5.2 为什么不能用 HAL_TIM_PWM_Start_IT

```
HAL_TIM_PWM_Start_IT 内部操作：
  → 使能的是 CC1IE（捕获/比较中断）
  → 不是 UIE（更新中断）
  → 高级定时器的更新中断由 RCR 控制
  → 需要单独开启

正确做法：
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);     // 启动 PWM
  __HAL_TIM_ENABLE_IT(&htim1, TIM_IT_UPDATE);   // 单独开启更新中断
```

### 5.3 开启更新中断

```c
// 单独开启更新中断
__HAL_TIM_ENABLE_IT(&htim1, TIM_IT_UPDATE);
```

```
__HAL_TIM_ENABLE_IT 是宏定义函数：
  参数1：定时器句柄地址
  参数2：中断类型标志

TIM_IT_UPDATE：更新中断标志
  → 对应 DIER 寄存器中的 UIE 位
```

### 5.4 停止定时器

```c
// 标准 PWM 停止（不带 IT 后缀）
HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
```

> 停止时用 `HAL_TIM_PWM_Stop`，不需要 `HAL_TIM_PWM_Stop_IT`。

### 5.5 清除中断标志

```c
// 清除更新中断标志（防止初始化后立即进入中断）
__HAL_TIM_CLEAR_FLAG(&htim1, TIM_FLAG_UPDATE);
```

```
__HAL_TIM_CLEAR_FLAG 内部操作：
  → 清除 SR 寄存器中的 UIF 位
  → 防止初始化产生的更新事件导致第一次误进中断
```

---

## 六、中断服务函数

### 6.1 it.c 中的实现

```c
void TIM1_UP_IRQHandler(void)
{
    // 直接关闭定时器
    HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
}
```

### 6.2 也可以用回调函数

```c
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM1)
    {
        HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
    }
}
```

> 高级定时器有专用的更新中断入口 `TIM1_UP_IRQHandler`，可以直接在其中处理，不必使用回调函数。

---

## 七、空闲状态与极性配置

### 7.1 问题现象

```
未配置空闲状态时：
  → 5 次闪烁后 LED 保持常亮（低电平）

原因：
  → 定时器停止后，输出引脚保持最后的状态
  → PWM 模式 1 + 高电平有效 → 最后可能是低电平
  → 低电平点亮 LED → LED 常亮
```

### 7.2 解决方案

| 配置项 | 修改前 | 修改后 | 说明 |
|--------|:------:|:------:|------|
| **OC Idle State** | Reset (低) | **Set (高)** | 空闲时输出高电平 |
| **CH Polarity** | High | **Low** | 低电平有效 |

### 7.3 修改后的效果

```
PWM 输出时：
  → 低电平点亮 LED（因为极性改为低电平有效）
  → 正常闪烁 5 次

定时器停止后：
  → 空闲状态为高电平（Set）
  → 高电平 → LED 不亮（关闭）
  → 完美关闭！
```

### 7.4 OC Idle State 含义

| 值 | 含义 | 定时器停止后输出 |
|:--:|------|:----------------:|
| **Reset** | 空闲状态为低电平 | 低电平 |
| **Set** | 空闲状态为高电平 | 高电平 |

> OC Idle State 在 CR2 寄存器中配置，控制 MOE 关闭时输出引脚的默认电平。

---

## 八、初始化后误进中断的问题

### 8.1 原因

```
HAL_TIM_PWM_Start 内部会调用 TIM_Base_SetConfig
  → 最后执行 EGR |= UG（产生更新事件）
  → 更新事件 → SR.UIF 置位
  → 如果已开启更新中断 → 第一次误进中断
```

### 8.2 解决方案

```c
// 开启 PWM
HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);

// 清除更新标志（在开启中断之前）
__HAL_TIM_CLEAR_FLAG(&htim1, TIM_FLAG_UPDATE);

// 开启更新中断
__HAL_TIM_ENABLE_IT(&htim1, TIM_IT_UPDATE);
```

### 8.3 配置顺序

```
正确顺序：
  ① HAL_TIM_PWM_Start()        → 启动 PWM
  ② __HAL_TIM_CLEAR_FLAG()     → 清除更新标志
  ③ __HAL_TIM_ENABLE_IT()      → 开启更新中断

错误顺序（会误进中断）：
  ① __HAL_TIM_ENABLE_IT()      → 先开中断
  ② HAL_TIM_PWM_Start()        → 产生更新事件 → 误进中断！
```

---

## 九、完整主函数代码

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
    MX_TIM1_Init();

    printf("Hello World!\n");

    /* 启动 PWM 输出 */
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);

    /* 清除更新标志（防止初始化后误进中断） */
    __HAL_TIM_CLEAR_FLAG(&htim1, TIM_FLAG_UPDATE);

    /* 开启更新中断 */
    __HAL_TIM_ENABLE_IT(&htim1, TIM_IT_UPDATE);

    while (1)
    {
        // 主循环为空，所有操作在中断中完成
    }
}
```

### 9.1 it.c 中断函数

```c
#include "tim.h"

void TIM1_UP_IRQHandler(void)
{
    HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
}
```

---

## 十、运行结果

```
上电 → LED 闪烁：
  第 1 次闪烁（0.5s）
  第 2 次闪烁（0.5s）
  第 3 次闪烁（0.5s）
  第 4 次闪烁（0.5s）
  第 5 次闪烁（0.5s）
  → LED 熄灭（空闲状态为高电平）

总时长：2.5 秒
```

---

## 十一、CubeMX 修改后重新生成代码

### 11.1 注意事项

```
重新生成代码时：
  → USER CODE BEGIN / END 之间的代码会被保留
  → 之外的代码会被覆盖

安全做法：
  → 所有自定义代码写在 USER CODE BEGIN/END 之间
  → 重新生成后检查代码是否保留
```

### 11.2 直接在 CubeMX 中修改 vs 直接改代码

| 方式 | 优点 | 缺点 |
|------|------|------|
| CubeMX 修改 | 图形化直观 | 需要重新生成代码 |
| 直接改代码 | 不需要重新生成 | 代码不会被覆盖 |

```
直接在 tim.c 中修改效果等同于 CubeMX：
  sConfig.OCIdleState = TIM_OCIDLESTATE_SET;
  sConfig.OCPolarity  = TIM_OCPOLARITY_LOW;
```

---

## 十二、HAL 库 PWM 相关函数对比

| 函数 | 功能 | 开启中断 |
|------|------|:--------:|
| `HAL_TIM_PWM_Start()` | 启动 PWM 输出 | ❌ |
| `HAL_TIM_PWM_Start_IT()` | 启动 PWM + CC 中断 | ✅ CC 中断 |
| `HAL_TIM_PWM_Stop()` | 停止 PWM 输出 | — |
| `__HAL_TIM_ENABLE_IT()` | 单独开启指定中断 | ✅ 指定中断 |
| `__HAL_TIM_CLEAR_FLAG()` | 清除指定标志位 | — |

### 12.1 本实验正确的函数调用

```c
// 启动
HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);        // PWM 输出
__HAL_TIM_CLEAR_FLAG(&htim1, TIM_FLAG_UPDATE);    // 清标志
__HAL_TIM_ENABLE_IT(&htim1, TIM_IT_UPDATE);       // 更新中断

// 停止（中断中）
HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);          // 关闭 PWM
```

---

## 十三、高级定时器特殊功能总结

| 功能 | 说明 | 本实验 |
|------|------|:------:|
| **RCR** | 重复计数器，控制更新事件频率 | ✅ RCR=4 |
| **MOE** | 主输出使能，高级定时器必须开启 | 自动 |
| **Idle State** | MOE 关闭时的输出电平 | ✅ Set |
| **互补输出** | CH1/CH1N 互补输出 | 不使用 |
| **Break/Dead Time** | 刹车和死区时间 | 不使用 |
| **专用中断入口** | TIM1_UP_IRQHandler | ✅ |

---

## 十四、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| LED 不闪（看起来常亮） | CCR 值太小（如 50） | CCR = 2500（50%） |
| LED 不停止（一直闪） | 未开启更新中断 | `__HAL_TIM_ENABLE_IT` |
| LED 不停止 | 用了 `HAL_TIM_PWM_Start_IT` | 改用 `__HAL_TIM_ENABLE_IT` |
| 停止后 LED 常亮 | Idle State = Reset | 改为 Set |
| 一进中断就停止 | 初始化产生更新事件 | 开启中断前清除标志 |
| 引脚映射错误 | CubeMX 重映射到 PE9 | 手动改回 PA8 |
| 闪烁次数不对 | RCR 值配错 | RCR = 4（5 次） |

---

## 十五、RCR 值与闪烁次数对照

| RCR | 闪烁次数 | ARR=4999 时总时长 |
|:---:|:--------:|:----------------:|
| 0 | 1 | 0.5s |
| 1 | 2 | 1.0s |
| 2 | 3 | 1.5s |
| 3 | 4 | 2.0s |
| **4** | **5** | **2.5s** |
| 9 | 10 | 5.0s |
| 99 | 100 | 50.0s |

> 闪烁次数 = RCR + 1