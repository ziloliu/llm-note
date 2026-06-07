## 笔记 2：STM32CubeMX 安装

> **覆盖原笔记**：`STM32CubeMX安装笔记`

### 推荐方法：Flatpak

```bash
sudo apt install -y flatpak default-jre
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub com.st.STM32CubeMX
```

验证：

```bash
flatpak list | grep -i stm32
# STM32CubeMX   com.st.STM32CubeMX   6.17.0   stable   system
```

启动：`flatpak run com.st.STM32CubeMX`

### 更新与卸载

```bash
flatpak update com.st.STM32CubeMX        # 更新
flatpak uninstall --delete-data com.st.STM32CubeMX  # 卸载
```

### 首次使用

1. 启动后下载 MCU 数据库（需联网）
2. Help → Manage embedded software packages → 安装 STM32F1 系列固件包
3. 新建项目时选择 Makefile 作为 Toolchain，可直接导出寄存器级项目骨架

---