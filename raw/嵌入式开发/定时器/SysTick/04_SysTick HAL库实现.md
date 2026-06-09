# SysTick 系统滴答定时器 — HAL 库实现 LED 闪烁 笔记

---

## 一、CubeMX 配置

### 1.1 基础配置

| 配置项 | 路径 | 设置 |
|--------|------|------|
| Debug | SYS | Serial Wire |
| Time Base Source | SYS | **SysTick**（默认） |
| RCC | HSE + LSE | 外部高速/低速晶振 |
| 时钟树 | HSE → PLL ×9 | 72MHz，APB1 /2 → 36MHz |

### 1.2 Time Base Source 选项

| 选项 | 说明 |
|------|------|
| **SysTick**（默认） | 系统滴答定时器（内核定时器） |
| 其他定时器（TIM1~TIM8） | 也可以作为时基来源 |

> 一般使用默认的 SysTick 即可，无需更改。

### 1.3 GPIO 配置（LED）

| 引脚 | 配置 | 标签 |
|------|------|------|
| PA0 | GPIO_Output, High Speed, Push-Pull, 默认高电平 | LED1 |

### 1.4 SysTick 特殊性

```
SysTick 不在 Timers 菜单中配置
  → 它是 Cortex-M3 内核定时器，不是外设
  → CubeMX 不提供单独的配置界面
  → HAL_Init() 内部自动完成配置
```

### 1.5 NVIC 中断优先级

| 配置 | 默认值 | 说明 |
|------|:------:|------|
| SysTick 中断优先级 | **15**（最低） | NVIIC 菜单中可见，但一般不需修改 |

> 如果系统中还有其他中断且对实时性要求高，可适当提高 SysTick 优先级。

---

## 二、HAL_Init() 内部流程

### 2.1 HAL_Init() 做了什么

```
HAL_Init()
    ├── ① 复位所有外设
    ├── ② 初始化 Flash 接口
    ├── ③ 初始化系统时基（SysTick）
    └── ④ 配置中断优先级分组
```

### 2.2 中断优先级分组配置

```c
// HAL_Init() 内部调用
HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);
// 参数 4 → 4 位全部用于抢占优先级
// 即模式 3：4 位抢占，0 位子优先级
```

### 2.3 SysTick 初始化过程

```c
// HAL_Init() 内部调用链：

HAL_InitTick(TickPriority = 15)
    │
    └── HAL_InitTick 内部：
        │
        ├── ① HAL_SYSTICK_Config(SystemCoreClock / 1000)
        │      // SystemCoreClock = 72000000
        │      // 72000000 / 1000 = 72000
        │
        │   └── SysTick_Config(72000)        // CMSIS 函数
        │       │
        │       ├── SysTick->LOAD = 72000 - 1 = 71999
        │       ├── SysTick->VAL  = 0
        │       ├── SysTick->CTRL = ENABLE | TICKINT | CLKSOURCE  // 0x07
        │       └── NVIC_SetPriority(SysTick_IRQn, 15)
        │
        └── ② HAL_NVIC_SetPriority(SysTick_IRQn, 15, 0)
               // 设置中断优先级为 15
```

### 2.4 HAL 库配置的寄存器值

| 寄存器 | 值 | 与寄存器方式对比 |
|--------|:--:|:----------------:|
| LOAD | **71999** | ✅ 完全一致 |
| VAL | 0 | ✅ 完全一致 |
| CTRL | **0x07**（111） | ✅ 完全一致 |
| 时钟源 | AHB 72MHz | ✅ 完全一致 |
| 中断 | 使能 | ✅ 完全一致 |

---

## 三、HAL 库中的全局滴答计数器

### 3.1 uwTick 变量

```c
// HAL 库内部定义（HAL 库源码中）
__IO uint32_t uwTick;       // 全局变量，32 位，以毫秒为单位递增
```

| 特性 | 说明 |
|------|------|
| 类型 | `__IO`（volatile）uint32_t |
| 单位 | **毫秒** |
| 递增方式 | 每次 SysTick 中断 +1 |
| 最大值 | 32 位 → 可运行约 49.7 天才溢出 |

### 3.2 中断服务函数中的递增

```c
// stm32f1xx_it.c 中的中断服务函数
void SysTick_Handler(void)
{
    HAL_IncTick();    // HAL 库提供的递增函数
}

// HAL_IncTick() 内部实现（__weak 可重写）
void HAL_IncTick(void)
{
    uwTick += uwTickFreq;    // uwTickFreq 默认 = 1
}
```

### 3.3 uwTick 的作用

```
uwTick 被以下功能使用：
  ├── HAL_Delay()    → 基于 uwTick 实现毫秒延时
  ├── 超时检测       → HAL 库内部各种 Timeout 判断
  └── 用户自定义     → 可直接读取 uwTick 获取系统运行毫秒数
```

---

## 四、代码实现

### 4.1 stm32f1xx_it.c — 中断服务函数

```c
// 已有默认实现（弱函数）
void SysTick_Handler(void)
{
    HAL_IncTick();    // 默认：递增 uwTick

    // 用户代码：在 HAL_IncTick() 后面添加
    if (uwTick % 1000 == 0)     // 每 1000ms = 1s
    {
        HAL_GPIO_TogglePin(GPIOA, LED1_Pin);   // 翻转 LED1
    }
}
```

### 4.2 两种处理方式

#### 方式一：直接在 SysTick_Handler 中操作（简单）

```c
void SysTick_Handler(void)
{
    HAL_IncTick();

    if (uwTick % 1000 == 0)
    {
        HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_0);
    }
}
```

#### 方式二：重写 HAL_IncTick（更规范）

```c
void HAL_IncTick(void)
{
    uwTick += uwTickFreq;

    if (uwTick % 1000 == 0)
    {
        HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_0);
    }
}
```

### 4.3 main.c — 主函数（无需额外操作）

```c
#include "main.h"

int main(void)
{
    HAL_Init();                         // 初始化 HAL（含 SysTick）
    SystemClock_Config();               // 配置系统时钟
    MX_GPIO_Init();                     // 初始化 GPIO（LED）

    while (1)
    {
        // 空循环，LED 翻转完全由中断驱动
    }
}
```

---

## 五、uwTick % 1000 取余方式说明

### 5.1 为什么用取余而不是置零

```
❌ 不修改 uwTick 的原因：
  uwTick 是全局变量
  → HAL_Delay() 依赖 uwTick 判断超时
  → 超时检测依赖 uwTick 持续递增
  → 置零会导致系统计时混乱

✅ 使用取余：
  uwTick 持续增长，不影响系统功能
  → 每隔 1000ms，uwTick % 1000 == 0 自然成立
  → 无需修改 uwTick
```

### 5.2 取余时机

```
uwTick 值：   0    999   1000   1999   2000   2999   3000
                ↑         ↑          ↑          ↑
             初始    %1000=0    %1000=0    %1000=0
                         翻转        翻转        翻转
                         1秒         2秒         3秒
```

### 5.3 uwTick 溢出问题

```
uwTick 为 uint32_t：
  最大值 = 4,294,967,295
  溢出时间 = 4,294,967,295 ms ≈ 49.7 天

  → 一般应用无需担心溢出
  → 溢出后自动从 0 开始，取余逻辑仍然正确
```

---

## 六、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| SysTick 初始化 | 手动配 LOAD/CTRL | `HAL_Init()` 自动完成 |
| LOAD 值 | 手动算 71999 | 自动计算 72000-1 |
| CTRL 配置 | 手动逐步置位 | 自动配置 0x07 |
| 全局计数器 | 手动定义 `counter` | 内置 `uwTick` |
| 中断服务函数 | `counter++; if==1000` | `HAL_IncTick()` + `uwTick%1000` |
| 计数器管理 | 手动清零 | **不清零**，取余判断 |
| 翻转 LED | `LED1_Toggle()` | `HAL_GPIO_TogglePin()` |
| NVIC 配置 | 不需要（内核自动） | 不需要（HAL 自动） |
| 代码量 | 中等 | **更少** |

---

## 七、HAL 库函数调用链完整路径

```
main()
  → HAL_Init()
      → HAL_InitTick(15)
          → HAL_SYSTICK_Config(72000)
              → SysTick_Config(72000)         // CMSIS 内核函数
                  ├── SysTick->LOAD = 71999
                  ├── SysTick->VAL  = 0
                  ├── SysTick->CTRL = 0x07
                  └── NVIC_SetPriority(SysTick_IRQn, 15)
      → HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4)

每 1ms 中断触发：
  SysTick_Handler()                       // stm32f1xx_it.c
      → HAL_IncTick()                     // HAL 库
          → uwTick += 1                   // 全局计数器递增
      → 用户代码                          // 可选：翻转 LED 等
```

---

## 八、HAL_GPIO_TogglePin 函数

```c
// HAL 库提供的 GPIO 翻转函数
void HAL_GPIO_TogglePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin);

// 使用示例
HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_0);    // 翻转 PA0
HAL_GPIO_TogglePin(GPIOA, LED1_Pin);      // 使用 CubeMX 生成的标签
```

| 参数 | 说明 |
|------|------|
| GPIOx | GPIO 端口（GPIOA、GPIOB 等） |
| GPIO_Pin | 引脚号（GPIO_PIN_0、GPIO_PIN_1 等） |

---

## 九、两种方式完整代码对比

### 9.1 寄存器方式

**systick.c：**
```c
uint16_t counter = 0;

void SysTick_Init(void)
{
    SysTick->LOAD = 71999;
    SysTick->CTRL |= SysTick_CTRL_CLKSOURCE_Msk;
    SysTick->CTRL |= SysTick_CTRL_TICKINT_Msk;
    SysTick->CTRL |= SysTick_CTRL_ENABLE_Msk;
}

void SysTick_Handler(void)
{
    counter++;
    if (counter == 1000)
    {
        LED1_Toggle();
        counter = 0;
    }
}
```

**main.c：**
```c
int main(void)
{
    LED_Init();
    SysTick_Init();
    while (1) {}
}
```

### 9.2 HAL 库方式

**stm32f1xx_it.c：**
```c
void SysTick_Handler(void)
{
    HAL_IncTick();
    if (uwTick % 1000 == 0)
    {
        HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_0);
    }
}
```

**main.c：**
```c
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    while (1) {}
}
```

---

## 十、SysTick 中断优先级注意事项

| 场景 | 建议 |
|------|------|
| 仅使用 SysTick | 默认 15 即可 |
| 有其他高优先级中断 | 可降低 SysTick 优先级值（数值越小优先级越高） |
| 使用 RTOS | SysTick 优先级通常设为最低，避免影响实时任务 |

> SysTick 优先级过低时，在其他中断执行期间 SysTick 无法响应，系统计时会暂停。