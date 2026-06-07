---
title: STM32开发环境搭建
category: STM32/开发环境
tags: [Keil, ST-Link, 驱动安装, 工程创建, 程序下载]
abstract: 详细讲解STM32开发环境搭建完整流程，包括Keil安装配置、ST-Link驱动、工程创建规范、程序下载方法
source: 原创
update_time: 2026-04-27
status: 完成
type: 实操
---
## 一句话定义
STM32开发环境主要由编译器、调试器、下载工具三部分组成，主流方案为Keil MDK + ST-Link调试器。

## 核心内容
### 1. 开发工具选型
| 工具名称 | 开发商 | 优势 | 适用场景 |
| --- | --- | --- | --- |
| Keil MDK | ARM | 老牌工具、调试功能强、资料最多 | 主流开发首选 |
| STM32CubeIDE | ST | 官方免费、集成CubeMX图形配置、HAL库支持好 | HAL库开发首选 |
| IAR | IAR Systems | 编译优化好、代码密度高 | 工业级项目开发 |
| CLion | JetBrains | 代码编辑体验好、智能提示强 | 熟悉JetBrains生态的开发者 |

### 2. Keil MDK安装配置
#### 安装步骤
1. 下载Keil MDK安装包，优先选择5.36/5.38版本（兼容性最好）
2. 运行安装程序，选择安装路径（建议不要安装在C盘，路径不要包含中文和空格）
3. 安装过程中填写任意注册信息，无需联网验证
4. 安装完成后安装对应芯片的支持包（Pack），STM32F1系列安装`Keil.STM32F1xx_DFP.x.x.x.pack`
5. 注册激活：以管理员身份运行Keil，获取CID后使用注册机生成激活码，激活后可使用至2032年

#### 编译器配置
1. 由于Keil 6版本编译器与STM32标准库不兼容，需手动安装ARM Compiler 5版本
2. 配置路径：`Options for Target → Folders/Extensions → Use ARM Compiler`，选择安装的ARM 5编译器路径
3. 在`Target`标签页选择`Use default compiler version 5`，确认C/C++标签页显示为AC5而非AC6

### 3. ST-Link驱动安装与配置
#### 驱动安装
1. ST-Link是ST官方的调试下载器，支持SWD调试模式，仅需4根线连接（VCC、GND、SWDIO、SWCLK）
2. 驱动安装包可从ST官网下载，或使用STM32CubeProgrammer自带驱动
3. 安装完成后在设备管理器中查看`通用串行总线设备`下是否出现`ST-Link Debug`设备，无感叹号即为安装成功

#### 固件升级
1. 运行`ST-LinkUpgrade.exe`工具，连接ST-Link后点击`Device Connect`
2. 选择`STM32 Debug + VCP`模式，点击升级，升级过程中不要断开连接
3. 升级完成后ST-Link支持虚拟串口功能，可同时实现调试和串口通信

### 4. 标准库工程创建规范
#### 目录结构
```
ProjectName/
├── Libraries/          # 标准库文件
│   ├── CMSIS/          # ARM内核支持文件
│   └── STM32F10x_StdPeriph_Driver/ # 外设驱动文件
├── User/               # 用户代码
│   ├── main.c
│   ├── stm32f10x_conf.h
│   ├── stm32f10x_it.c
│   └── stm32f10x_it.h
├── Output/             # 编译输出文件
└── Project.uvprojx     # Keil工程文件
```

#### 工程配置要点
1. 选择对应芯片型号：如`STM32F103ZE`
2. 添加头文件路径：`./Libraries/CMSIS/CM3/CoreSupport`、`./Libraries/CMSIS/CM3/DeviceSupport/ST/STM32F10x`、`./Libraries/STM32F10x_StdPeriph_Driver/inc`、`./User`
3. 预定义宏：`STM32F10X_HD`（根据芯片容量选择，HD=大容量）、`USE_STDPERIPH_DRIVER`
4. 输出配置：勾选`Create HEX File`，指定输出目录为`Output`
5. 调试器配置：选择`ST-Link Debugger`，进入设置确认SWD模式已识别到芯片

### 5. 程序下载流程
1. 连接ST-Link到开发板，确保供电正常
2. 点击Keil工具栏的`Download`按钮（或快捷键F8）
3. 编译无误后自动下载程序到芯片Flash
4. 下载完成后可点击`Reset`按钮复位运行，或在调试配置中勾选`Reset and Run`实现下载后自动运行
5. 下载成功提示：`Programming Done. Verify OK.`

## 注意事项&踩坑
1. 驱动安装失败：优先卸载旧版本驱动，以管理员身份重新安装，或使用Zadig工具强制替换驱动
2. 芯片识别失败：检查接线是否正确（SWDIO/SWCLK不要接反）、供电是否正常、BOOT引脚是否设置为从Flash启动
3. 下载提示Flash保护：使用`STM32 ST-Link Utility`工具全片擦除解除保护
4. Keil编译慢：禁用杀毒软件实时扫描，将工程目录加入白名单
5. 中文路径问题：工程路径和文件名不要包含中文和特殊字符，否则会出现编译错误

## 相关笔记
- [[STM32点亮LED灯实战（寄存器版）]]
- [[STM32标准库寄存器封装原理]]
