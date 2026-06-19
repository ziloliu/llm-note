
## 一、前置条件

| 工具 | 最低版本 | 验证命令 |
|------|---------|---------|
| Git | 2.x+ | `git --version` |
| Python | **3.12**（3.13 不兼容 open3d） | `python --version` |
| winget | 1.x+ | `winget --version` |

> **关键约束**：`open3d 0.19.0` 无 Python 3.13 预编译包，必须使用 Python 3.12。

---

## 二、获取项目代码

项目全部处理脚本托管在内部 GitLab 仓库，需通过 `git clone` 拉取到本地：

```powershell
# 创建项目根目录
if (!(Test-Path "C:\projects")) { mkdir C:\projects }
cd C:\projects

# 从远程仓库拉取处理脚本
git clone http://192.168.18.200:53000/hezitian/3dgs_pcd_ground_mesh_pipeline

# 确认拉取成功
cd 3dgs_pcd_ground_mesh_pipeline
ls
```

**仓库地址**：`http://192.168.18.200:53000/hezitian/3dgs_pcd_ground_mesh_pipeline`

> 此为内网 GitLab 地址，需确保当前网络可访问 `192.168.18.200:53000`。若仓库设为私有，clone 时会提示输入用户名和密码。

拉取完成后，项目目录结构如下：

```
3dgs_pcd_ground_mesh_pipeline/
├── run_3dgs_to_pcd_ground_mesh.sh   # 主入口脚本（Git Bash 运行）
├── scripts/
│   ├── check_environment.py          # 环境检查脚本
│   └── ...                           # 各阶段处理脚本
├── requirements.txt                  # Python 依赖清单
└── ...
```

---

## 三、Python 3.12 环境搭建

### 3.1 安装 Python 3.12

```powershell
# 方式一：winget（推荐）
winget install Python.Python.3.12

# 方式二：国内镜像手动下载
$url = "https://registry.npmmirror.com/-/binary/python/3.12.10/python-3.12.10-amd64.exe"
$output = "C:\Users\$env:USERNAME\Downloads\python-3.12.10-amd64.exe"
Invoke-WebRequest -Uri $url -OutFile $output -TimeoutSec 300
Start-Process -Wait -FilePath $output -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_launcher=1"

# 验证
py -3.12 --version   # 预期：Python 3.12.10
```

### 3.2 创建虚拟环境

```powershell
cd C:\projects\3dgs_pcd_ground_mesh_pipeline

# 清理旧环境 → 创建新环境 → 激活
if (Test-Path -LiteralPath ".venv") { Remove-Item -Recurse -Force ".venv" }
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python --version   # 预期：Python 3.12.x
```

### 3.3 安装依赖

```powershell
python -m pip install -U pip

# 配置清华镜像（持久生效）
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn

# 安装依赖
python -m pip install -r requirements.txt

# 若清华源不可用，切换阿里云镜像
python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
```

### 3.4 验证环境

```powershell
python scripts/check_environment.py
```

预期输出（全部显示 `[ok]`）：

```
Python: C:\projects\3dgs_pcd_ground_mesh_pipeline\.venv\Scripts\python.exe
[ok] numpy: 2.4.6
[ok] plyfile: unknown
[ok] open3d: 0.19.0
[ok] scipy: 1.17.1
[ok] scikit-learn: 1.9.0
[ok] opencv-python: 4.13.0
[ok] matplotlib: 3.11.0
```

---

## 四、Git Bash 配置

### 4.1 为什么必须用 Git Bash

| 问题 | 说明 |
|------|------|
| 脚本格式 | 项目入口为 `.sh` 脚本，PowerShell 无法直接执行 |
| 路径差异 | Windows 用 `\`，Git Bash 用 `/` |
| 编码冲突 | Python 输出 Unicode 字符时，Windows 控制台会报 `gbk` 编码错误 |

### 4.2 路径转换规则

```
Windows:  C:\projects\lcc\...\point_cloud.ply
Git Bash: /c/projects/lcc/.../point_cloud.ply

规则：盘符 C: → /c，反斜杠 \ → 正斜杠 /
```

### 4.3 设置环境变量

```bash
export PYTHON_CMD='/c/projects/3dgs_pcd_ground_mesh_pipeline/.venv/Scripts/python.exe'
export PYTHONIOENCODING=utf-8
```

---

## 五、运行处理

### 5.1 执行流程

```bash
# 1. 打开 Git Bash
# 2. 进入项目目录
cd /c/projects/3dgs_pcd_ground_mesh_pipeline

# 3. 设置环境变量
export PYTHON_CMD='/c/projects/3dgs_pcd_ground_mesh_pipeline/.venv/Scripts/python.exe'
export PYTHONIOENCODING=utf-8

# 4. 运行（传入 PLY 文件的 Git Bash 格式路径）
./run_3dgs_to_pcd_ground_mesh.sh /c/projects/lcc/SU_E_0245_K1_260613_DJI_260613/ply-result/point_cloud/iteration_100/point_cloud.ply
```

### 5.2 正常运行输出

```
[1/2] 3DGS PLY -> PCD
原始点数: 15437066, 过滤后点数: 7042973
✅ 已成功保存至: C:\projects\lcc\...\point_cloud.pcd

[2/2] PCD -> no-XODR ground mesh
SEGMENT_VOXEL_SIZE: 0.2
SURFACE_CELL_SIZE: 0.3
```

### 5.3 进度检查（PowerShell）

```powershell
# 检查中间产物
Test-Path -LiteralPath "C:\projects\lcc\...\point_cloud.pcd"

# 检查输出目录
Get-ChildItem -Path "C:\projects\lcc\...\ground_output_pcd_no_xodr"

# 检查 Python 进程是否仍在运行
Get-Process -Name "python" -ErrorAction SilentlyContinue
```

### 5.4 输出文件

运行完成后，输出目录 `ground_output_pcd_no_xodr/` 中包含：

| 文件 | 说明 |
|------|------|
| `ground_points.ply` | 地面点云（25–50 MB） |
| `ground_low_heightfield.ply` | 地面网格 |
| `ground_low_heightfield.obj` | OBJ 格式网格（200–400 MB） |
| `ground_low_heightfield.mtl` | 材质文件 |
| `texture_atlas.png` | 纹理图集（20–50 MB） |
| `obj_export_metadata.json` | 导出元数据 |
| `evaluation_ground_fit/` | 拟合评估结果 |

---

## 六、常见问题速查

| 现象 | 原因 | 解决 |
|------|------|------|
| `git clone` 超时或拒绝连接 | 无法访问内网 GitLab | 确认网络可达 `192.168.18.200:53000`，或联系管理员 |
| `No matching distribution found for open3d` | Python 版本为 3.13 | 降级到 3.12，重建虚拟环境 |
| `Input path does not exist: /mnt/c/...` | 路径格式错误（WSL 风格） | 使用 `/c/...` 而非 `/mnt/c/...` |
| `UnicodeEncodeError: 'gbk' codec can't encode` | 控制台编码不匹配 | `export PYTHONIOENCODING=utf-8` |
| `Could not install packages due to EnvironmentError` | 网络/镜像问题 | 换用阿里云镜像，或 `pip cache purge` |

---

## 七、一键快速部署（可直接复制执行）

### PowerShell — 拉取代码 + 环境搭建

```powershell
# 1. 检查 Python 3.12
py -3.12 --version
if ($LASTEXITCODE -ne 0) { winget install Python.Python.3.12 }

# 2. 从远程仓库拉取处理脚本
if (!(Test-Path "C:\projects")) { mkdir C:\projects }
cd C:\projects
if (!(Test-Path "3dgs_pcd_ground_mesh_pipeline")) {
    git clone http://192.168.18.200:53000/hezitian/3dgs_pcd_ground_mesh_pipeline
}
cd 3dgs_pcd_ground_mesh_pipeline

# 3. 配置 Python 虚拟环境 + 安装依赖
if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 验证环境
python scripts/check_environment.py
```

### Git Bash — 运行处理

```bash
cd /c/projects/3dgs_pcd_ground_mesh_pipeline
export PYTHON_CMD='/c/projects/3dgs_pcd_ground_mesh_pipeline/.venv/Scripts/python.exe'
export PYTHONIOENCODING=utf-8
./run_3dgs_to_pcd_ground_mesh.sh /你的实际路径/point_cloud.ply
```

