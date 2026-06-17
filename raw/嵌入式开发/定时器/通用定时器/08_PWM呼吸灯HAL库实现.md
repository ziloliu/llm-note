# 通用定时器 TIM5 PWM 呼吸灯 — HAL 库实现 笔记

---

## 一、CubeMX 配置

### 1.1 基础配置

| 配置项 | 路径 | 设置 |
|--------|------|------|
| Debug | SYS | Serial Wire |
| RCC | HSE + LSE | 外部高速/低速晶振 |
| 时钟树 | HSE → PLL ×9 | 72MHz，APB1 /2 → 36MHz |

### 1.2 TIM5 配置

| 配置项 | Parameter Settings | 值 |
|--------|-------------------|:--:|
| **Clock Source** | Internal Clock | ✅ 勾选 |
| **Channel 2** | PWM Generation CH2 | ✅ 选择 |
| **Prescaler** (PSC) | 7199 | 7200 分频 |
| **Counter Mode** | Up | 向上计数 |
| **Counter Period** (ARR) | 99 | 100 级分辨率 |
| **Internal Clock Division** | No Division | 不分频 |
| **Auto-reload Preload** | Disable | 立即生效 |
| **PWM Mode 1** | Mode 1 | 选 Mode 1 |
| **Pulse** (CCR) | 0 | 初始占空比（后续动态修改） |
| **Output Compare Preload** | Enable | 可选 |
| **Fast Mode** | Disable | 不使用 |
| **CH Polarity** | High | 高电平有效 |

### 1.3 GPIO 自动配置

选择 PWM Generation CH2 后，CubeMX **自动**将 PA1 配置为：

| 引脚 | 功能 | GPIO 模式 |
|:----:|------|-----------|
| **PA1** | TIM5_CH2 | **复用推挽输出** |

> 无需手动在 GPIO 页面配置，CubeMX 自动完成。

---

## 二、HAL 库 PWM 相关函数

### 2.1 启动函数

| 函数 | 功能 | 本实验 |
|------|------|:------:|
| `HAL_TIM_Base_Start()` | 启动定时器（轮询） | — |
| `HAL_TIM_Base_Start_IT()` | 启动定时器（中断） | — |
| `HAL_TIM_PWM_Start()` | **启动 PWM 输出** | ✅ |

### 2.2 HAL_TIM_PWM_Start 调用

```c
HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2);
```

| 参数 | 说明 |
|------|------|
| `&htim5` | TIM5 句柄地址 |
| `TIM_CHANNEL_2` | 通道 2 |

### 2.3 设置占空比函数

```c
__HAL_TIM_SET_COMPARE(&htim5, TIM_CHANNEL_2, compare_value);
```

| 参数 | 说明 |
|------|------|
| `&htim5` | TIM5 句柄地址 |
| `TIM_CHANNEL_2` | 通道 2 |
| `compare_value` | 比较值（CCR，即占空比） |

> 这是一个**宏定义函数**，内部操作 CCR 寄存器。

### 2.4 延时函数

```c
HAL_Delay(20);    // 延时 20ms（基于 SysTick 中断）
```

---

## 三、HAL 库中 PWM 相关函数分类

```
HAL_TIM_PWM_Start()       ← 启动 PWM 输出
HAL_TIM_PWM_Stop()        ← 停止 PWM 输出

HAL_TIM_OC_Start()        ← 启动输出比较
HAL_TIM_OC_Stop()         ← 停止输出比较

HAL_TIM_IC_Start()        ← 启动输入捕获
HAL_TIM_IC_Stop()         ← 停止输入捕获

HAL_TIM_Base_Start()      ← 仅启动定时器（无通道功能）
HAL_TIM_Base_Stop()       ← 停止定时器
```

---

## 四、代码实现

### 4.1 封装设置占空比函数

在 `tim.c` 中添加自定义函数：

```c
/* USER CODE BEGIN 1 */

/**
 * @brief  设置 TIM5 通道 2 占空比
 * @param  duty_cycle: 占空比百分数 (0~99)
 */
void TIM5_SetDutyCycle(uint8_t duty_cycle)
{
    __HAL_TIM_SET_COMPARE(&htim5, TIM_CHANNEL_2, duty_cycle);
}

/* USER CODE END 1 */
```

在 `tim.h` 中声明：

```c
/* USER CODE BEGIN Prototypes */
void TIM5_SetDutyCycle(uint8_t duty_cycle);
/* USER CODE END Prototypes */
```

### 4.2 main.c — 主函数

```c
#include "main.h"
#include "tim.h"

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM5_Init();

    /* 启动 PWM 输出 */
    HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2);

    /* 定义占空比和步长 */
    uint8_t duty_cycle = 1;     // 初始占空比（不能为 0，避免边界问题）
    int8_t step = -1;           // 初始步长为 -1（因为初始值 1 会触发边界翻转）

    while (1)
    {
        /* 边界检测：超出范围则反向 */
        if (duty_cycle <= 1 || duty_cycle >= 99)
        {
            step = -step;       // 步长取反，改变方向
        }

        /* 更新占空比 */
        duty_cycle += step;

        /* 设置占空比 */
        TIM5_SetDutyCycle(duty_cycle);

        /* 延时 */
        HAL_Delay(20);
    }
}
```

---

## 五、代码优化：步长取反法

### 5.1 原始版本（dir 方向变量）

```c
uint8_t duty_cycle = 0;
uint8_t dir = 0;       // 0=增大, 1=减小

while (1)
{
    if (dir == 0)
    {
        duty_cycle += 1;
        if (duty_cycle >= 99) dir = 1;
    }
    else
    {
        duty_cycle -= 1;
        if (duty_cycle <= 1) dir = 0;
    }
    TIM5_SetDutyCycle(duty_cycle);
    HAL_Delay(20);
}
```

### 5.2 优化版本（步长取反法）

```c
uint8_t duty_cycle = 1;
int8_t step = -1;

while (1)
{
    if (duty_cycle <= 1 || duty_cycle >= 99)
    {
        step = -step;           // 步长取反
    }
    duty_cycle += step;
    TIM5_SetDutyCycle(duty_cycle);
    HAL_Delay(20);
}
```

### 5.3 优化对比

| 对比项 | 原始版本 | 优化版本 |
|--------|----------|----------|
| 方向变量 | `dir`（0 或 1） | `step`（+1 或 -1） |
| 方向改变 | `dir = 1` 或 `dir = 0` | `step = -step` |
| 占空比更新 | 分别 `+=1` 和 `-=1` | 统一 `+= step` |
| 代码行数 | 较多 | **更少** |
| 逻辑 | 分支较多 | **更简洁** |

---

## 六、初始值边界问题

### 6.1 问题说明

```
duty_cycle 初始值 = 0，step 初始值 = 1：

  第 1 次循环：duty_cycle=0 ≤ 1 → step=-1（翻转）
  第 2 次循环：duty_cycle=0+(-1)=-1 → uint8 溢出为 255 ❌

duty_cycle 初始值 = 0，step 初始值 = -1：

  第 1 次循环：duty_cycle=0 ≤ 1 → step=1（翻转）
  第 2 次循环：duty_cycle=0+1=1 ≤ 1 → step=-1（又翻转！）
  连续翻转，逻辑错误 ❌
```

### 6.2 解决方案

```
✅ 方案 1：duty_cycle=1, step=-1
  第 1 次：duty_cycle=1 ≤ 1 → step=1（翻转）
  第 2 次：duty_cycle=1+1=2 → 不在边界，正常
  后续正常递增到 99 ✅

✅ 方案 2：duty_cycle=1, step=1
  第 1 次：duty_cycle=1+1=2 → 不在边界
  正常递增到 99 ✅

✅ 方案 3：duty_cycle=0, step=1，判断条件改为 <1 而不是 ≤1
  避免初始值 0 触发边界判断 ✅
```

### 6.3 关键原则

```
初始值必须在 [2, 98] 范围内
或 初始值在边界但初始步长方向正确（不会立即再次触发边界）

确保：步长改变后的下一个值不会再次触发边界判断
```

---

## 七、完整执行流程

```
系统上电
    │
    ├── HAL_Init()
    ├── SystemClock_Config()      → 72MHz
    ├── MX_GPIO_Init()            → PA1 自动配为复用推挽输出
    ├── MX_TIM5_Init()            → PSC=7199, ARR=99, PWM 模式 1
    │
    ├── HAL_TIM_PWM_Start()       → 启动 PWM 输出
    │
    └── 主循环：
        ├── 判断边界 → step 取反
        ├── duty_cycle += step
        ├── TIM5_SetDutyCycle()   → 更新 CCR2
        └── HAL_Delay(20)         → 保持 20ms
```

---

## 八、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 时钟开启 | 手动 RCC->APB1ENR + APB2ENR | CubeMX 自动生成 |
| GPIO 配置 | 手动 CRL 位操作 | CubeMX 自动配复用推挽 |
| PSC/ARR | 手动写寄存器 | CubeMX 配置 + 函数初始化 |
| CCMR1 配置 | 手动配 CC2S + OC2M | CubeMX 自动生成 |
| CCER 配置 | 手动配 CC2E | CubeMX 自动生成 |
| 启动 PWM | 手动 CR1.CEN=1 | `HAL_TIM_PWM_Start()` |
| 设置占空比 | `TIM5->CCR2 = value` | `__HAL_TIM_SET_COMPARE()` |
| 停止 PWM | 手动 CR1.CEN=0 | `HAL_TIM_PWM_Stop()` |
| 代码量 | 较多 | **更少** |

---

## 九、PWM 关键参数总结

| 参数 | 公式 | 本实验值 |
|------|------|:--------:|
| 计数频率 | 72MHz / (PSC+1) | 72MHz / 7200 = 10kHz |
| PWM 频率 | 计数频率 / (ARR+1) | 10kHz / 100 = **100Hz** |
| PWM 周期 | 1 / PWM 频率 | **10ms** |
| 占空比 | CCR / (ARR+1) × 100% | CCR / 100 × 100% |
| 分辨率 | 1 / (ARR+1) | **1%** |

---

## 十、呼吸灯效果控制

| 参数 | 作用 | 调整方式 |
|------|------|----------|
| **HAL_Delay 时间** | 每级占空比保持时间 | 增大→呼吸变慢，减小→呼吸变快 |
| **步长 (step)** | 每次占空比变化量 | 增大→变化更快但不平滑 |
| **ARR 值** | 分辨率 | 越大越平滑 |
| **PSC 值** | PWM 频率 | 减小→频率更高→更看不到闪烁 |

### 推荐参数

```
步长 = 1（最平滑）
延迟 = 20ms
ARR = 99（100 级分辨率）
PSC = 7199（100Hz PWM 频率）

一个完整呼吸周期 = 2 × 99 × 20ms ≈ 4 秒
```

---

## 十一、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| LED 不亮 | 未调用 `HAL_TIM_PWM_Start()` | 确认已启动 PWM |
| LED 不亮 | GPIO 未正确配置 | CubeMX 检查 PA1 配置 |
| LED 亮度不变 | 未调用 `SetDutyCycle` | 循环中更新 CCR |
| 呼吸不平滑 | 步长太大 | 步长改为 1 |
| 呼吸太快 | Delay 时间太短 | 增大延迟 |
| 初始闪烁异常 | 边界值处理不当 | 调整初始 duty_cycle 和 step |
| 占空比溢出 | uint8 下溢/上溢 | 确保边界判断正确 |