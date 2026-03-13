# Texas Hold'em APK 打包说明

## 文件结构
```
D:\texas-holdem\
  ├── main.py          # 游戏主程序
  ├── buildozer.spec   # Buildozer 打包配置
  ├── requirements.txt # Python 依赖
  ├── Dockerfile       # Docker 打包环境
  ├── build_apk.sh     # Docker 打包脚本
  └── PACKAGING.md     # 本说明文档
```

---

## 方案一：Docker 打包（推荐，最简单）

> 前提：安装 Docker Desktop for Windows（https://www.docker.com/products/docker-desktop/）

### 步骤

1. 安装并启动 Docker Desktop

2. 在 PowerShell 中执行：
```powershell
cd D:\texas-holdem
docker build -t kivy-buildozer .
docker run --rm -v "D:\texas-holdem:/app" kivy-buildozer
```

3. 等待 20-40 分钟（首次需下载 Android SDK/NDK）

4. APK 生成路径：`D:\texas-holdem\bin\texasholdem-1.0.0-arm64-v8a-debug.apk`

---

## 方案二：GitHub Actions 自动打包（免费云端）

### 步骤

1. 在 GitHub 创建新仓库，上传 `D:\texas-holdem\` 目录所有文件

2. 创建 `.github/workflows/build_apk.yml` 文件，内容如下：

```yaml
name: Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install buildozer dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
          pip install buildozer cython
      - name: Build APK
        run: buildozer android debug
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: texas-holdem-apk
          path: bin/*.apk
```

3. Push 代码后，在 Actions 标签页等待构建完成（约 20-30 分钟）

4. 在 Actions → 构建任务 → Artifacts 下载 APK

---

## 方案三：Google Colab 在线打包

1. 打开 https://colab.research.google.com/

2. 新建笔记本，依次执行：

```python
# 安装依赖
!sudo apt-get update
!sudo apt-get install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev
!pip install buildozer cython
```

```python
# 上传代码（运行后点击上传按钮）
from google.colab import files
uploaded = files.upload()  # 上传 main.py 和 buildozer.spec
```

```python
# 打包
!buildozer android debug
```

```python
# 下载 APK
from google.colab import files
import glob
apk_files = glob.glob('bin/*.apk')
if apk_files:
    files.download(apk_files[0])
```

---

## 方案四：WSL2 打包（Windows 本地）

> 需要先安装 WSL2 + Ubuntu

```powershell
# 安装 WSL2（管理员 PowerShell）
wsl --install -d Ubuntu

# 重启后进入 Ubuntu
wsl

# Ubuntu 内执行
sudo apt update && sudo apt upgrade -y
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev
pip3 install buildozer cython kivy

# 进入项目目录（Windows D盘映射到 /mnt/d/）
cd /mnt/d/texas-holdem

# 打包（首次 20-40 分钟）
buildozer android debug

# APK 在 bin/ 目录下
ls bin/
```

---

## 在手机上安装 APK

1. 手机设置 → 安全 → 开启"未知来源"（或"安装未知应用"）
2. 将 APK 传输到手机（微信/QQ/USB/云盘）
3. 点击 APK 文件安装
4. 打开游戏即可

---

## 本地测试（Windows，无需打包）

```powershell
# 安装 Kivy
pip install kivy

# 运行游戏（桌面窗口测试）
cd D:\texas-holdem
python main.py
```

---

## 游戏说明

- **玩家**：You（人类玩家）vs Alice（正常风格 AI）vs Bob（激进风格 AI）
- **起始筹码**：每人 $1000
- **小盲/大盲**：$10 / $20
- **操作**：Fold（弃牌）、Check/Call（过牌/跟注）、Raise（加注）、All-In（全押）
- **界面**：横屏，适配手机触屏
