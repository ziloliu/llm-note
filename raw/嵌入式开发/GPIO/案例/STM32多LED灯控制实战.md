---
title: STM32多LED灯控制实战
category: STM32/实战案例
tags: [多LED, 流水灯, 位操作, 批量控制]
abstract: 实现多LED灯的独立控制和流水灯效果，掌握多引脚配置、批量操作和状态管理技巧
source: 原创
update_time: 2026-04-27
status: 完成
type: 实操
---
## 一句话定义
多LED灯控制是GPIO操作的进阶实战，通过控制多个GPIO引脚实现LED的独立控制、流水灯效果、呼吸灯等功能，进一步掌握位操作和寄存器批量操作技巧。

## 核心内容
### 1. 硬件电路说明
本案例使用3个LED灯，电路连接如下：
| LED编号 | 颜色 | 连接引脚 | 点亮电平 | 限流电阻 |
| --- | --- | --- | --- | --- |
| LED1 | 黄色 | PA0 | 低电平 | 1kΩ |
| LED2 | 蓝色 | PA1 | 低电平 | 1kΩ |
| LED3 | 绿色 | PA8 | 低电平 | 1kΩ |
- 所有LED均为共阳接法，正极接3.3V，负极接STM32引脚
- 引脚输出低电平时点亮，高电平时熄灭
- PA0/PA1属于低8位引脚，使用CRL寄存器配置；PA8属于高8位引脚，使用CRH寄存器配置

### 2. 实现功能
1. 三个LED独立控制，可单独点亮、熄灭、翻转
2. 流水灯效果：LED1→LED2→LED3→LED1循环点亮，间隔500ms
3. 闪烁效果：三个LED同时闪烁，间隔1s
4. 二进制计数效果：三个LED组成二进制计数器，从0到7循环计数

### 3. 代码实现
#### 3.1 GPIO初始化函数
```c
#include "stm32f10x.h"

void delay_ms(uint32_t ms) {
    uint32_t i, j;
    for (i = 0; i < ms; i++) {
        for (j = 0; j < 7200; j++);
    }
}

// GPIO初始化，配置PA0、PA1、PA8为推挽输出
void LED_GPIO_Init(void) {
    // 开启GPIOA时钟
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
    
    // 配置PA0（低8位，CRL寄存器）
    GPIOA->CRL &= ~(GPIO_CRL_CNF0 | GPIO_CRL_MODE0);
    GPIOA->CRL |= GPIO_CRL_MODE0; // 推挽输出50MHz
    
    // 配置PA1（低8位，CRL寄存器）
    GPIOA->CRL &= ~(GPIO_CRL_CNF1 | GPIO_CRL_MODE1);
    GPIOA->CRL |= GPIO_CRL_MODE1; // 推挽输出50MHz
    
    // 配置PA8（高8位，CRH寄存器）
    GPIOA->CRH &= ~(GPIO_CRH_CNF8 | GPIO_CRH_MODE8);
    GPIOA->CRH |= GPIO_CRH_MODE8; // 推挽输出50MHz
    
    // 初始状态全部熄灭（输出高电平）
    GPIOA->ODR |= (GPIO_ODR_ODR0 | GPIO_ODR_ODR1 | GPIO_ODR_ODR8);
}
```

#### 3.2 LED操作函数
```c
// 点亮指定LED
// led: 0=LED1(PA0), 1=LED2(PA1), 2=LED3(PA8)
void LED_On(uint8_t led) {
    switch(led) {
        case 0: GPIOA->ODR &= ~GPIO_ODR_ODR0; break;
        case 1: GPIOA->ODR &= ~GPIO_ODR_ODR1; break;
        case 2: GPIOA->ODR &= ~GPIO_ODR_ODR8; break;
        default: break;
    }
}

// 熄灭指定LED
void LED_Off(uint8_t led) {
    switch(led) {
        case 0: GPIOA->ODR |= GPIO_ODR_ODR0; break;
        case 1: GPIOA->ODR |= GPIO_ODR_ODR1; break;
        case 2: GPIOA->ODR |= GPIO_ODR_ODR8; break;
        default: break;
    }
}

// 翻转指定LED
void LED_Toggle(uint8_t led) {
    switch(led) {
        case 0: GPIOA->ODR ^= GPIO_ODR_ODR0; break;
        case 1: GPIOA->ODR ^= GPIO_ODR_ODR1; break;
        case 2: GPIOA->ODR ^= GPIO_ODR_ODR8; break;
        default: break;
    }
}

// 所有LED同时点亮
void LED_All_On(void) {
    GPIOA->ODR &= ~(GPIO_ODR_ODR0 | GPIO_ODR_ODR1 | GPIO_ODR_ODR8);
}

// 所有LED同时熄灭
void LED_All_Off(void) {
    GPIOA->ODR |= (GPIO_ODR_ODR0 | GPIO_ODR_ODR1 | GPIO_ODR_ODR8);
}
```

#### 3.3 功能实现函数
```c
// 流水灯效果
void LED_Waterfall(void) {
    LED_All_Off();
    LED_On(0);
    delay_ms(500);
    
    LED_All_Off();
    LED_On(1);
    delay_ms(500);
    
    LED_All_Off();
    LED_On(2);
    delay_ms(500);
}

// 闪烁效果
void LED_Blink(void) {
    LED_All_On();
    delay_ms(1000);
    LED_All_Off();
    delay_ms(1000);
}

// 二进制计数效果
void LED_Binary_Count(void) {
    static uint8_t count = 0;
    count++;
    if (count > 7) count = 0;
    
    LED_All_Off();
    if (count & 0x01) LED_On(0); // 最低位控制LED1
    if (count & 0x02) LED_On(1); // 中间位控制LED2
    if (count & 0x04) LED_On(2); // 最高位控制LED3
    
    delay_ms(500);
}
```

#### 3.4 主函数
```c
int main(void) {
    LED_GPIO_Init(); // 初始化GPIO
    
    while(1) {
        // 选择要运行的功能，取消注释对应行即可
        // LED_Waterfall();      // 流水灯
        // LED_Blink();          // 闪烁
        LED_Binary_Count();    // 二进制计数
    }
}

// 中断处理函数省略，同上一案例
```

### 4. 代码优化技巧
#### 4.1 批量操作优化
利用ODR寄存器可以同时控制多个引脚的特性，实现LED状态的批量更新：
```c
// 一次性设置三个LED的状态，bit0=LED1, bit1=LED2, bit2=LED3
void LED_Set_All(uint8_t state) {
    uint32_t odr = GPIOA->ODR;
    // 先清除三个LED对应的位
    odr &= ~(GPIO_ODR_ODR0 | GPIO_ODR_ODR1 | GPIO_ODR_ODR8);
    // 根据state设置对应位，低电平点亮所以取反
    odr |= ((~state & 0x01) << 0) | ((~state & 0x02) << 0) | ((~state & 0x04) << 6);
    GPIOA->ODR = odr;
}
```
- 优势：仅需一次ODR寄存器操作即可同时更新三个LED状态，比单独操作速度快3倍

#### 4.2 宏定义优化操作
```c
#define LED1_ON()  GPIOA->ODR &= ~GPIO_ODR_ODR0
#define LED1_OFF() GPIOA->ODR |= GPIO_ODR_ODR0
#define LED1_TOG() GPIOA->ODR ^= GPIO_ODR_ODR0

#define LED2_ON()  GPIOA->ODR &= ~GPIO_ODR_ODR1
#define LED2_OFF() GPIOA->ODR |= GPIO_ODR_ODR1
#define LED2_TOG() GPIOA->ODR ^= GPIO_ODR_ODR1

#define LED3_ON()  GPIOA->ODR &= ~GPIO_ODR_ODR8
#define LED3_OFF() GPIOA->ODR |= GPIO_ODR_ODR8
#define LED3_TOG() GPIOA->ODR ^= GPIO_ODR_ODR8
```
- 优势：使用宏定义简化操作，代码更简洁，可读性更高

### 5. 拓展功能实现思路
#### 5.1 呼吸灯效果
通过定时器PWM输出，控制LED的亮度渐变，实现呼吸灯效果
#### 5.2 按键控制LED
通过按键输入控制LED的亮灭、模式切换等功能
#### 5.3 动态亮度调节
通过PWM占空比调节，实现LED的多级亮度控制
#### 5.4 LED点阵控制
扩展到8x8 LED点阵，实现字符显示、动画效果等

## 注意事项&踩坑
1. 高低引脚寄存器区分：PA8属于高8位引脚，必须使用CRH寄存器配置，不要误用CRL寄存器
2. 位偏移计算正确：PA8在CRH寄存器对应位[3:0]，ODR寄存器对应位8，不要搞错偏移
3. 批量操作注意其他引脚：修改ODR寄存器时不要影响其他未使用的引脚，使用位操作而非直接赋值
4. 电流限制：多个LED同时点亮时注意总电流不要超过芯片最大电流限制，否则可能烧毁芯片
5. 共阴共阳区别：如果是共阴接法，输出高电平点亮，代码需要对应修改

## 相关笔记

- [[GPIO工作原理与配置]]
- [[STM32点亮LED灯实战（寄存器版）]]

