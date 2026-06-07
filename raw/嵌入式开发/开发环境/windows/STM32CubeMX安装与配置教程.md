---
title: "STM32CubeMX安装与配置教程"
category: "STM32/开发工具"
tags: ["STM32CubeMX", "安装教程", "开发环境"]
abstract: "STM32CubeMX图形化配置工具的详细安装与配置步骤"
source: "课程笔记33.md"
update_time: 2025-04-27
status: 完成
type: 实操
---
## 一句话定义
STM32CubeMX是ST官方推出的免费图形化开发工具，用于快速创建STM32工程和完成硬件配置。
## 核心内容
### 1. 环境依赖安装
STM32CubeMX基于JAVA开发，必须先安装Java 8运行环境：
- 版本要求：仅支持Java 8（1.8.x）版本，Java 11/17等高版本不兼容
- 验证方法：命令行执行`java -version`查看当前版本
- 安装包：使用`jre-8u381-windows-x64.exe`，双击即可完成安装
### 2. STM32CubeMX安装步骤
1. 获取安装包：官方下载或使用课程提供的`en.stm32cubemx-win-v6-10-0.zip`
2. 解压后运行`SetupSTM32CubeMX-6.10.0-Win.exe`
3. 接受软件许可协议和隐私条款
4. 选择安装路径：建议保持默认或选择无中文/空格的目录，空间需求约508MB
5. 选择创建桌面和开始菜单快捷方式
6. 等待安装完成，显示"Installation has completed successfully"即为成功
7. 建议勾选"Generate an automatic installation script"选项，方便后续批量部署
### 3. 基础配置
- 仓库路径设置：默认路径为`C:\Users\[用户名]\STM32Cube\Repository`，可通过`Help → Updater Settings`修改
- 网络配置：如有代理需在设置中配置网络代理，保证在线下载功能正常
## 注意事项&踩坑
1. 安装路径不能包含中文或特殊字符，否则可能导致功能异常
2. 必须先安装Java 8环境，再安装STM32CubeMX，顺序不可颠倒
3. 安装过程中需要管理员权限，建议右键选择"以管理员身份运行"安装程序
4. 建议安装完成后重启一次电脑，保证环境变量生效
## 相关笔记
[[STM32CubeMX芯片支持包安装指南]]、[[STM32 HAL库介绍与核心优势]]
## 参考来源
33.md STM32CubeMX安装部分