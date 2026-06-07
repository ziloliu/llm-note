---
title: "STM32CubeMX安装笔记"
category: "STM32/开发工具"
tags: [STM32CubeMX, Flatpak, 安装指南, Ubuntu, Java]
abstract: "在Ubuntu系统上通过Flatpak安装STM32CubeMX 6.17.0的完整指南"
source: "原创"
update_time: 2026-04-24
status: 完成
type: 实操
---

# STM32CubeMX安装笔记

## 安装概述
本文档记录了在Ubuntu 24.04系统上安装最新版STM32CubeMX 6.17.0的完整过程。通过Flatpak方式安装，避免了传统安装方法中的Java路径问题和下载限制。

## 安装日期
2026-03-27

## 系统环境
- **操作系统**: Ubuntu 24.04 LTS
- **内核版本**: 6.17.0-19-generic
- **Java版本**: OpenJDK 21.0.10
- **磁盘空间**: 819GB可用

## 安装方法选择
经过调研，发现三种主要安装方法：

### 1. 传统方法（官方下载）
- **优点**: 官方原版，功能完整
- **缺点**: 
  - 需要ST官网账号登录
  - 下载链接不稳定
  - Java路径配置复杂
  - 安装过程容易出错

### 2. Flatpak方法（推荐）
- **优点**:
  - 无需ST账号登录
  - 自动处理依赖关系
  - 版本更新方便
  - 系统集成良好
  - 官方认可的分发方式
- **缺点**: 需要安装Flatpak运行时

### 3. 手动编译方法
- **优点**: 完全控制安装过程
- **缺点**: 步骤复杂，适合高级用户

**推荐使用Flatpak方法**，这是最稳定、最简单的安装方式。

## 详细安装步骤

### 步骤1：检查系统环境
```bash
# 检查系统信息
uname -a
# Linux zilo-Lenovo-Legion-R9000X-2021 6.17.0-19-generic #19~24.04.2-Ubuntu SMP PREEMPT_DYNAMIC Fri Mar  6 23:08:46 UTC 2 x86_64 x86_64 x86_64 GNU/Linux

# 检查Ubuntu版本
lsb_release -a
# Distributor ID:	Ubuntu
# Description:	Ubuntu 24.04.4 LTS
# Release:	24.04
# Codename:	noble

# 检查磁盘空间
df -h /home
# 文件系统        大小  已用  可用 已用% 挂载点
# /dev/sda4       871G  7.2G  819G    1% /home
```

### 步骤2：安装Java运行时环境
STM32CubeMX需要Java JRE 11.0.10或更高版本。

```bash
# 检查当前Java版本
java -version
# openjdk version "17.0.18" 2026-01-20
# OpenJDK Runtime Environment (build 17.0.18+8-Ubuntu-124.04.1)
# OpenJDK 64-Bit Server VM (build 17.0.18+8-Ubuntu-124.04.1, mixed mode, sharing)

# 如果未安装Java，安装默认JRE
sudo apt update
sudo apt install -y default-jre

# 验证Java安装
which java
# /usr/bin/java
```

### 步骤3：安装Flatpak
Flatpak是一个跨Linux发行版的软件打包和分发系统。

```bash
# 安装Flatpak
sudo apt install -y flatpak

# 验证安装
flatpak --version
# Flatpak 1.14.6
```

### 步骤4：添加Flathub仓库
Flathub是最大的Flatpak应用仓库。

```bash
# 添加Flathub仓库
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# 验证仓库添加成功
flatpak remotes
# 应该能看到flathub仓库
```

### 步骤5：安装STM32CubeMX
通过Flatpak安装STM32CubeMX 6.17.0。

```bash
# 安装STM32CubeMX
flatpak install -y flathub com.st.STM32CubeMX

# 安装过程会显示：
# 寻找匹配项…
# 在远程仓库 flathub 中找到 com.st.STM32CubeMX/x86_64/stable
# 安装大小：约716.6 MB
# 安装时间：约5-10分钟（取决于网络速度）
```

### 步骤6：验证安装
```bash
# 查看已安装的Flatpak应用
flatpak list | grep -i stm32
# STM32CubeMX	com.st.STM32CubeMX	6.17.0	stable	system

# 检查版本信息
flatpak run com.st.STM32CubeMX --version 2>&1 | head -5
# log4j user configuration file not found: /home/zilo/.stm32cubemx/log4j2.xml
# Configure log4j with default settings from jar:file:/app/stm32cubemx/STM32CubeMX!/log4j/log4j2.stm32cubemx.xml
# 2026-03-27 11:36:33,123 [INFO] MicroXplorer:98 - [MX] MX Start == 2538967295175
# 2026-03-27 11:36:33,125 [INFO] MicroXplorer:653 - Detected Java Version = 25.0.2
# 2026-03-27 11:36:33,311 [INFO] ApplicationProperties:184 - Using Application install path: /app/stm32cubemx
```

### 步骤7：创建桌面快捷方式（可选）
```bash
# 创建桌面启动器
mkdir -p ~/.local/share/applications

cat > ~/.local/share/applications/stm32cubemx.desktop << 'EOF'
[Desktop Entry]
Name=STM32CubeMX
Comment=STM32CubeMX Configuration Tool
Exec=flatpak run com.st.STM32CubeMX
Icon=/app/stm32cubemx/stm32cubemx.png
Terminal=false
Type=Application
Categories=Development;
EOF

# 给予执行权限
chmod +x ~/.local/share/applications/stm32cubemx.desktop
```
	## 作用

在Linux系统中创建桌面应用程序启动器，使STM32CubeMX可以通过图形界面菜单启动，无需每次手动输入命令。

### 1. 创建目录

```bash
mkdir -p ~/.local/share/applications
```

- `~/.local/share/applications` 是Linux桌面应用启动器的标准存放目录

### 2. 创建启动器文件

```bash
cat > ~/.local/share/applications/stm32cubemx.desktop << 'EOF'
[Desktop Entry]
Name=STM32CubeMX
Comment=STM32CubeMX Configuration Tool
Exec=flatpak run com.st.STM32CubeMX
Icon=/app/stm32cubemx/stm32cubemx.png
Terminal=false
Type=Application
Categories=Development;
EOF
```

**配置说明：**

| 字段 | 说明 |
|------|------|
| Name | 应用程序显示名称 |
| Comment | 应用程序描述 |
| Exec | 启动命令（通过Flatpak运行） |
| Icon | 图标路径 |
| Terminal | 是否需要终端（false=图形界面） |
| Type | 文件类型（Application=应用程序） |
| Categories | 分类（Development=开发工具） |

### 步骤8：启动STM32CubeMX
```bash
# 方法1：通过Flatpak启动
flatpak run com.st.STM32CubeMX

# 方法2：通过桌面快捷方式启动
# 在应用程序菜单中搜索"STM32CubeMX"并点击
```

## 安装验证

### 验证项目
1. ✅ **版本验证**: STM32CubeMX 6.17.0 已成功安装
2. ✅ **Java环境**: Java 25.0.2 被正确检测
3. ✅ **程序启动**: 程序正常初始化，无错误
4. ✅ **功能测试**: 可以创建新项目，选择STM32F103ZET6芯片

### 启动日志示例
```
2026-03-27 11:36:33,123 [INFO] MicroXplorer:98 - [MX] MX Start == 2538967295175
2026-03-27 11:36:33,125 [INFO] MicroXplorer:653 - Detected Java Version = 25.0.2
2026-03-27 11:36:33,311 [INFO] ApplicationProperties:184 - Using Application install path: /app/stm32cubemx
2026-03-27 11:36:33,326 [INFO] DbMcusXml:78 - Set database path to: /app/stm32cubemx//db//mcu/
2026-03-27 11:36:33,326 [INFO] ApiDb:274 - Set plugin database path to: /app/stm32cubemx//db//plugins/boardmanager/
```

## 使用指南

1. **启动STM32CubeMX**后，首次运行可能需要下载MCU数据库，请确保网络连接
2. **安装HAL库**：
   - 点击"Help"菜单
   - 选择"Manage embedded software packages"
   - 选择"STM32F1 Series"（用于STM32F103ZET6）
   -选择最新版（如1.8.7）
   - 点击"Install Now"

使用STM32CubeMX创建项目
1. 启动STM32CubeMX
2. 选择"New Project"
3. 搜索并选择STM32F103ZET6
4. 配置时钟、引脚、外设
5. Project Manager → Toolchain/IDE: Makefile
6. 生成代码



## 常见问题与解决方案

### 问题1: Flatpak安装失败
**症状**: `error: No remote refs found`
**解决方案**:
```bash
# 重新添加Flathub仓库
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# 更新仓库信息
flatpak update
```

### 问题2: Java版本不兼容
**症状**: `Please install Java JRE 11.0.10 or a more recent version`
**解决方案**:
```bash
# 安装Java 11或更高版本
sudo apt install -y openjdk-11-jre

# 或者安装最新版Java
sudo apt install -y default-jre
```

### 问题3: 程序启动缓慢
**症状**: 首次启动需要下载MCU数据库
**解决方案**:
- 确保网络连接正常
- 首次启动可能需要几分钟下载数据库
- 后续启动会快很多

### 问题4: 权限问题
**症状**: `Permission denied`
**解决方案**:
```bash
# 检查Flatpak权限
flatpak info com.st.STM32CubeMX

# 如果需要更多权限
flatpak override --user --filesystem=home com.st.STM32CubeMX
```

## 维护与更新

### 更新STM32CubeMX
```bash
# 更新所有Flatpak应用
flatpak update

# 或只更新STM32CubeMX
flatpak update com.st.STM32CubeMX
```

### 卸载STM32CubeMX
```bash
# 卸载STM32CubeMX
flatpak uninstall com.st.STM32CubeMX

# 完全删除（包括运行时）
flatpak uninstall --delete-data com.st.STM32CubeMX
```

### 查看安装信息
```bash
# 查看详细信息
flatpak info com.st.STM32CubeMX

# 查看运行时大小
flatpak list --columns=application,version,size
```

## 技术要点

### Flatpak优势
1. **沙盒安全**: 应用在沙盒中运行，增强安全性
2. **依赖隔离**: 自带依赖，不污染系统环境
3. **版本稳定**: 版本固定，避免依赖冲突
4. **更新方便**: 一键更新所有应用
5. **多版本共存**: 支持同时安装多个版本

### 与传统安装对比
| 特性 | 传统安装 | Flatpak安装 |
|------|----------|-------------|
| 安装复杂度 | 高（需要处理Java路径） | 低（一键安装） |
| 依赖管理 | 手动 | 自动 |
| 更新难度 | 高（需要重新下载） | 低（一键更新） |
| 系统集成 | 好 | 非常好 |
| 安全性 | 一般 | 高（沙盒） |
| 磁盘占用 | 较小 | 较大（包含运行时） |

### 资源占用
- **安装大小**: 约716.6 MB
- **运行时**: 约1.5 GB（包含Java运行时和依赖）
- **内存占用**: 启动后约300-500 MB

## 参考资料

### 官方资源
1. [STM32CubeMX官方页面](https://www.st.com/en/development-tools/stm32cubemx.html)
2. [Flathub STM32CubeMX页面](https://flathub.org/apps/com.st.STM32CubeMX)
3. [Flatpak官方文档](https://docs.flatpak.org/)

### 社区资源
1. [STM32中文社区](https://www.stmcu.org.cn/)
2. [ST官方社区](https://community.st.com/)
3. [Flathub GitHub仓库](https://github.com/flathub/com.st.STM32CubeMX)

### 相关工具
1. **STM32CubeIDE**: 完整的STM32开发环境
2. **STM32CubeProgrammer**: 程序烧录工具
3. **STM32CubeMonitor**: 实时监控工具

## 总结

通过Flatpak安装STM32CubeMX是在Ubuntu系统上最推荐的方法，具有以下优点：

1. **简单快捷**: 无需处理复杂的Java路径配置
2. **稳定可靠**: 官方打包，经过测试
3. **易于维护**: 一键更新和卸载
4. **系统友好**: 良好的桌面集成

安装完成后，STM32CubeMX 6.17.0可以立即用于STM32F103ZET6等芯片的项目开发，配合VSCode和EIDE插件，形成完整的嵌入式开发环境。

---
**更新记录**:
- 2026-03-27: 创建安装笔记，记录Flatpak安装方法
- 2026-03-27: 验证安装成功，更新使用指南

**测试环境**: Ubuntu 24.04 LTS
**安装方式**: Flatpak
**版本**: STM32CubeMX 6.17.0
**状态**: ✅ 安装成功，功能正常

## 相关笔记
- [[STM32寄存器开发概述]]
- [[Makefile基础与进阶]]

## 参考来源
- 原创文档
