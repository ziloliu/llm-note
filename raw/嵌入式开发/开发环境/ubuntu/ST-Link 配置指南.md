---
title: "ST-Link配置指南"
category: "STM32/调试工具"
tags: [ST-Link, 调试器, udev, 权限配置, Ubuntu]
abstract: "ST-Link调试器的完整配置指南，包括工具安装、udev规则设置和连接测试"
source: "原创"
update_time: 2026-04-24
status: 完成
type: 实操
---

# ST-Link配置指南

## 1. ST-Link工具安装

```bash                                                                   
 # 安装ST-Link工具包                                                       
 sudo apt install -y stlink-tools stlink-gui                               
   
 # 安装OpenOCD（开源片上调试器）        
 sudo apt install -y openocd                                               
    
 # 验证安装                                                                
 st-info --version                                                         
 openocd --version                                                         
```

### 1.1 创建udev规则文件

```bash
# 创建udev规则文件
sudo nano /etc/udev/rules.d/49-stlinkv2.rules
```

添加以下内容：

```
# ST-Link V2
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="3748", MODE="0666", GROUP="plugdev"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374b", MODE="0666", GROUP="plugdev"

# ST-Link V2-1
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374d", MODE="0666", GROUP="plugdev"

# ST-Link V3
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374e", MODE="0666", GROUP="plugdev"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374f", MODE="0666", GROUP="plugdev"
```

**代码解释**:
- `/etc/udev/rules.d/`: Linux系统中udev规则文件的存储目录
- `49-stlinkv2.rules`: 规则文件名，49是优先级编号
- `SUBSYSTEMS=="usb"`: 匹配USB子系统
- `ATTRS{idVendor}=="0483"`: 匹配厂商ID，0483是STMicroelectronics的ID
- `ATTRS{idProduct}=="3748"`: 匹配产品ID，不同ST-Link型号有不同的ID
- `MODE="0666"`: 设置设备文件权限为0666（所有用户可读可写）
- `GROUP="plugdev"`: 将设备分配给plugdev组

### 1.2 重新加载udev规则和用户组配置

```bash
# 重新加载udev规则
sudo udevadm control --reload-rules
sudo udevadm trigger

# 将当前用户添加到plugdev组（如果尚未添加）
sudo usermod -a -G plugdev $USER

# 需要重新登录使组更改生效
```

**代码解释**:
- `udevadm control --reload-rules`: 重新加载udev规则配置
- `udevadm trigger`: 触发udev事件，重新处理设备
- `usermod -a -G plugdev $USER`: 将当前用户添加到plugdev用户组
- 需要重新登录才能使组权限更改生效

### 1.3 测试ST-Link连接

```bash
# 连接ST-Link到电脑
# 运行以下命令检查设备
lsusb | grep -i stlink

# 使用st-info检查连接
st-info --probe

# 如果看到设备信息，说明连接成功
```

**代码解释**:
- `lsusb | grep -i stlink`: 列出USB设备并过滤ST-Link相关信息
- `st-info --probe`: 使用st-info工具探测ST-Link设备
- 成功标准：能看到设备信息输出

## 相关笔记
- [[ARM工具链安装与配置]]
- [[STM32调试指南]]

## 参考来源
- 原创文档
