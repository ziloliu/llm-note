# I²C 通信 — HAL 库实现 AT24C02 读写 笔记

---

## 一、CubeMX 配置

### 1.1 基础配置

| 配置项 | 操作 |
|--------|------|
| Debug | SYS → Serial Wire |
| RCC | HSE + LSE |
| 时钟树 | HSE → PLL ×9 → 72MHz，APB1 /2 → **36MHz** |
| USART1 | Asynchronous（用于串口打印） |

### 1.2 I²C2 配置

| 配置项 | 路径 | 设置值 |
|--------|------|--------|
| 启用 I²C2 | Connectivity → I²C2 → Mode → **I2C** | 开启 I²C 模式 |
| 速度模式 | Parameter Settings → Speed Mode | **Standard Mode**（100kHz） |
| 时钟频率 | 自动生成 | 100 kHz（SCL 频率） |

### 1.3 自动配置的引脚

选择 I²C 模式后，CubeMX 自动分配引脚：

| 引脚 | 功能 | GPIO 配置 |
|------|------|-----------|
| **PB10** | I2C2_SCL | **复用开漏输出** |
| **PB11** | I2C2_SDA | **复用开漏输出** |

### 1.4 不需要配置的选项

| 选项 | 说明 |
|------|------|
| 从模式地址 | 三二作为主设备，不配自身地址 |
| 双地址模式 | 不需要 |
| 广播地址检测 | 不需要 |
| NVIC 中断 | 不使用中断 |
| DMA | 不使用 DMA |

> HAL 库自动处理了 CR2（输入时钟频率）、CCR（分频系数）、TRISE（上升时间）等底层寄存器配置。

### 1.5 与寄存器方式配置对比

| 配置项 | 寄存器方式（手动） | HAL 库（CubeMX） |
|--------|-------------------|------------------|
| CR2 FREQ | 手动写 36 | 自动生成 |
| CCR | 手动计算 180 | 根据 100kHz 自动算 |
| TRISE | 手动计算 37 | 自动生成 |
| CR1 ACK | 手动置位 | 自动生成 |
| CR1 PE | 最后手动使能 | 自动生成 |
| GPIO 模式 | 手动配复用开漏 | 自动配复用开漏 |

---

## 二、CubeMX 生成的代码结构

### 2.1 初始化函数

```c
// 自动生成的初始化函数
MX_I2C2_Init();   // 在 main() 中调用
```

### 2.2 I²C 句柄

```c
I2C_HandleTypeDef hi2c2;   // 类似于串口的 huart1
```

---

## 三、HAL 库 I²C 写入函数 — HAL_I2C_Mem_Write

### 3.1 函数原型

```c
HAL_StatusTypeDef HAL_I2C_Mem_Write(
    I2C_HandleTypeDef *hi2c,    // I²C 句柄指针
    uint16_t DevAddress,        // 设备地址（含读写方向位）
    uint16_t MemAddress,        // 存储器内部地址
    uint16_t MemAddSize,        // 存储器地址大小（8位/16位）
    uint8_t *pData,             // 待写入数据的指针
    uint16_t Size,              // 写入字节数
    uint32_t Timeout            // 超时时间（毫秒）
);
```

### 3.2 参数详解

| 参数 | 类型 | 本实验传入值 | 说明 |
|------|------|-------------|------|
| hi2c | `I2C_HandleTypeDef *` | `&hi2c2` | I²C2 句柄地址 |
| DevAddress | `uint16_t` | `W_ADDR (0xA0)` | 写地址 |
| MemAddress | `uint16_t` | `inner_addr` | EEPROM 内部存储地址 |
| MemAddSize | `uint16_t` | `I2C_MEMADD_SIZE_8BIT` | **8 位**地址（256 字节） |
| pData | `uint8_t *` | `&byte` 或数据数组 | 数据指针 |
| Size | `uint16_t` | `1` 或 `size` | 字节数 |
| Timeout | `uint32_t` | `1000` | 超时毫秒数 |

### 3.3 MemAddSize 说明

| 参数 | 含义 | 适用场景 |
|------|------|----------|
| `I2C_MEMADD_SIZE_8BIT` | 8 位内部地址 | AT24C02（256 字节，地址 0x00~0xFF） |
| `I2C_MEMADD_SIZE_16BIT` | 16 位内部地址 | 更大容量的 EEPROM |

> 注意：使用宏定义 `I2C_MEMADD_SIZE_8BIT`，不要直接写数字 8。

### 3.4 函数封装了什么

```
HAL_I2C_Mem_Write 内部自动完成：
  → I2C_Start()
  → I2C_SendAddr(W_ADDR)      // 发送设备写地址
  → I2C_SendByte(inner_addr)   // 发送内部存储地址
  → I2C_SendByte(data)         // 发送数据（循环 Size 次）
  → I2C_Stop()
  → 等待 ACK（检测 ADDR/BTF 标志）
  → 超时保护
```

---

## 四、HAL 库 I²C 读取函数 — HAL_I2C_Mem_Read

### 4.1 函数原型

```c
HAL_StatusTypeDef HAL_I2C_Mem_Read(
    I2C_HandleTypeDef *hi2c,    // I²C 句柄指针
    uint16_t DevAddress,        // 设备地址（含读写方向位）
    uint16_t MemAddress,        // 存储器内部地址
    uint16_t MemAddSize,        // 存储器地址大小
    uint8_t *pData,             // 接收缓冲区指针
    uint16_t Size,              // 读取字节数
    uint32_t Timeout            // 超时时间
);
```

### 4.2 参数详解

| 参数 | 本实验传入值 | 说明 |
|------|-------------|------|
| DevAddress | `R_ADDR (0xA1)` | 读地址 |
| MemAddress | `inner_addr` | 从哪个内部地址开始读 |
| MemAddSize | `I2C_MEMADD_SIZE_8BIT` | 8 位地址 |
| pData | `&byte` 或 `buffer` | 接收缓冲区 |
| Size | `1` 或 `size` | 读取字节数 |
| Timeout | `1000` | 超时毫秒数 |

### 4.3 函数封装了什么

```
HAL_I2C_Mem_Read 内部自动完成（假写真读）：
  → I2C_Start()
  → I2C_SendAddr(W_ADDR)       // 假写：发送写地址
  → I2C_SendByte(inner_addr)   // 发送内部存储地址
  → I2C_Start()                // 重复起始
  → I2C_SendAddr(R_ADDR)       // 真读：发送读地址
  → I2C_ReceiveByte()          // 接收数据（循环 Size 次）
    → 前 N-1 字节自动 ACK
    → 最后 1 字节自动 NACK + STOP
```

---

## 五、接口层实现（m24c02.c）

### 5.1 写入一个字节

```c
void EEPROM_WriteByte(uint8_t inner_addr, uint8_t byte)
{
    HAL_I2C_Mem_Write(&hi2c2, W_ADDR, inner_addr,
                      I2C_MEMADD_SIZE_8BIT, &byte, 1, 1000);
    Delay_ms(5);    // 等待写入周期
}
```

### 5.2 读取一个字节

```c
uint8_t EEPROM_ReadByte(uint8_t inner_addr)
{
    uint8_t byte;
    HAL_I2C_Mem_Read(&hi2c2, R_ADDR, inner_addr,
                     I2C_MEMADD_SIZE_8BIT, &byte, 1, 1000);
    return byte;
}
```

### 5.3 连续写入多个字节

```c
void EEPROM_WriteBytes(uint8_t inner_addr, uint8_t *data, uint8_t size)
{
    HAL_I2C_Mem_Write(&hi2c2, W_ADDR, inner_addr,
                      I2C_MEMADD_SIZE_8BIT, data, size, 1000);
    Delay_ms(5);
}
```

### 5.4 连续读取多个字节

```c
void EEPROM_ReadBytes(uint8_t inner_addr, uint8_t *buffer, uint8_t size)
{
    HAL_I2C_Mem_Read(&hi2c2, R_ADDR, inner_addr,
                     I2C_MEMADD_SIZE_8BIT, buffer, size, 1000);
}
```

---

## 六、三种实现方式完整对比

| 对比项 | 软件模拟 I²C | 硬件 I²C（寄存器） | 硬件 I²C（HAL 库） |
|--------|-------------|-------------------|-------------------|
| 初始化 | 手动配 GPIO | 手动配 GPIO + CR2 + CCR + TRISE + CR1 | **CubeMX 自动生成** |
| GPIO 模式 | 通用开漏输出 | 复用开漏输出 | **CubeMX 自动配** |
| START 信号 | 手动拉高拉低 | `CR1.START = 1; while(!SB);` | **函数内部自动** |
| STOP 信号 | 手动拉高拉低 | `CR1.STOP = 1;` | **函数内部自动** |
| 发送字节 | `for(8次){设SDA;翻SCL;}` | `while(!TXE); DR=byte; while(!BTF);` | **函数内部自动** |
| 接收字节 | `for(8次){翻SCL;读SDA;}` | `while(!RXNE); return DR;` | **函数内部自动** |
| 等待 ACK | `READ_SDA()` 读电平 | 检测 ADDR/BTF 标志 | **函数内部自动** |
| 假写真读 | 手动实现两段式 | 手动实现两段式 | **函数内部自动** |
| 写 EEPROM | 调 I2C_Start/SendByte/Stop 等 | 调 I2C_Start/SendAddr/SendByte/Stop 等 | **一行 HAL_I2C_Mem_Write** |
| 读 EEPROM | 调 I2C_Start/SendByte/ReceiveByte 等 | 调 I2C_Start/SendAddr/ReceiveByte 等 | **一行 HAL_I2C_Mem_Read** |
| 代码量 | **最大** | 中等 | **最小** |
| 可读性 | 低（底层细节多） | 中等 | **高**（参数直观） |

---

## 七、HAL_I2C_Mem_Write / Read 内部流程

### 7.1 写入内部流程

```
HAL_I2C_Mem_Write(&hi2c2, 0xA0, 0x3A, SIZE_8BIT, &data, 1, 1000)
    │
    ├── ① 产生 START 信号
    ├── ② 发送设备写地址 0xA0
    │      └── 等待 ADDR 标志
    │      └── 清除 ADDR（读 SR1 + 读 SR2）
    ├── ③ 发送内部地址 0x3A
    │      └── 等待 BTF 标志
    ├── ④ 发送数据 data
    │      └── 等待 BTF 标志
    ├── ⑤ 产生 STOP 信号
    └── 返回 HAL_OK / HAL_TIMEOUT
```

### 7.2 读取内部流程（假写真读）

```
HAL_I2C_Mem_Read(&hi2c2, 0xA1, 0x3A, SIZE_8BIT, &byte, 1, 1000)
    │
    ├── 假写阶段：
    │   ├── ① 产生 START
    │   ├── ② 发送写地址 0xA0（保持总线控制权）
    │   └── ③ 发送内部地址 0x3A
    │
    ├── 真读阶段：
    │   ├── ④ 重复 START
    │   ├── ⑤ 发送读地址 0xA1
    │   ├── ⑥ 等待 RXNE → 读取数据
    │   ├── ⑦ 发送 NACK（最后一个字节）
    │   └── ⑧ 产生 STOP
    │
    └── 返回 HAL_OK / HAL_TIMEOUT
```

---

## 八、接口层头文件（m24c02.h）— 无需修改

```c
#define W_ADDR    0xA0
#define R_ADDR    0xA1

void    EEPROM_Init(void);
void    EEPROM_WriteByte(uint8_t inner_addr, uint8_t byte);
uint8_t EEPROM_ReadByte(uint8_t inner_addr);
void    EEPROM_WriteBytes(uint8_t inner_addr, uint8_t *data, uint8_t size);
void    EEPROM_ReadBytes(uint8_t inner_addr, uint8_t *buffer, uint8_t size);
```

> 接口层声明与软件模拟和寄存器方式**完全一致**，体现了分层设计的优势。

---

## 九、printf 重定向（同串口 HAL 库版本）

```c
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 1000);
    return ch;
}
```

> Keil 需勾选 **Use MicroLib**。

---

## 十、主函数 — 与之前版本一致

```c
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_I2C2_Init();         // CubeMX 生成的 I²C2 初始化

    printf("I2C HAL库方式实验开始\n");

    // 单字节读写
    EEPROM_WriteByte(0x00, 'A');
    EEPROM_WriteByte(0x01, 'B');
    EEPROM_WriteByte(0x02, 'C');
    uint8_t b1 = EEPROM_ReadByte(0x00);
    uint8_t b2 = EEPROM_ReadByte(0x01);
    uint8_t b3 = EEPROM_ReadByte(0x02);
    printf("byte1=%c\tbyte2=%c\tbyte3=%c\n", b1, b2, b3);

    // 多字节读写
    EEPROM_WriteBytes(0x00, "123456", 6);
    uint8_t buffer[100] = {0};
    EEPROM_ReadBytes(0x00, buffer, 6);
    printf("buffer=%s\n", buffer);

    // 超16字节测试
    memset(buffer, 0, sizeof(buffer));
    EEPROM_WriteBytes(0x00, "1234567890abcdefjhijk", 21);
    EEPROM_ReadBytes(0x00, buffer, 21);
    printf("buffer=%s\n", buffer);

    while (1) {}
}
```

> 主函数代码与软件模拟、寄存器方式**完全一致**，无需修改。

---

## 十一、HAL 库函数命名规律

```
HAL_I2C_Mem_Write     ← I²C 存储器写入
HAL_I2C_Mem_Read      ← I²C 存储器读取
HAL_I2C_Master_...    ← I²C 主模式操作
HAL_I2C_Slave_...     ← I²C 从模式操作
HAL_I2C_IsDeviceReady ← 检测设备是否就绪
```

| 后缀 | 说明 |
|------|------|
| 无后缀 | 轮询方式（阻塞） |
| `_IT` | 中断方式（非阻塞） |
| `_DMA` | DMA 方式 |

---

## 十二、测试结果

| 测试项 | 预期 | 结果 |
|--------|------|:----:|
| 单字节写入 ABC | byte1=A byte2=B byte3=C | ✓ |
| 多字节写入 "123456" | buffer=123456 | ✓ |
| 超 16 字节写入 | 绕回覆盖，结果符合预期 | ✓ |

---

## 十三、I²C 相关 HAL 库函数汇总

| 函数 | 功能 | 阻塞 |
|------|------|:----:|
| `HAL_I2C_Master_Transmit()` | 主设备发送原始数据 | 是 |
| `HAL_I2C_Master_Receive()` | 主设备接收原始数据 | 是 |
| `HAL_I2C_Mem_Write()` | 写入存储器（自动处理地址） | 是 |
| `HAL_I2C_Mem_Read()` | 读取存储器（自动假写真读） | 是 |
| `HAL_I2C_IsDeviceReady()` | 检测设备是否在线 | 是 |

> 本实验使用 `HAL_I2C_Mem_Write` 和 `HAL_I2C_Mem_Read`，它们内部自动完成了假写真读等复杂操作。