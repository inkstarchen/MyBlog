# 环境搭建与运行指南

本文档说明如何在 Windows、macOS 或 Linux 上搭建本仓库的运行环境，并完成本地预览、静态构建和 GitHub Pages 发布。

## 1. 项目环境概览

这是一个使用 Python 生成静态页面的个人博客/认知空间项目。

- 必需：Python 3.10 或更高版本
- 推荐：Python 3.12（与仓库 GitHub Actions 的构建版本一致）
- Python 第三方依赖：无，所有脚本只使用标准库
- 可选：Git，仅在克隆仓库、版本管理或发布到 GitHub Pages 时需要
- 可选：现代浏览器，用于本地预览生成的网站

本项目没有 `requirements.txt`，因此不需要执行 `pip install`，也不要求创建虚拟环境。

## 2. 获取项目

如果已经拥有本仓库目录，可直接进入目录：

```powershell
cd D:\WorkSpace\MyBlog
```

如果需要从 GitHub 获取项目，请先安装 Git，然后执行：

```shell
git clone <仓库地址>
cd MyBlog
```

## 3. 安装 Python

### Windows

推荐安装 Python 3.12。可以从 [Python 官方网站](https://www.python.org/downloads/)下载安装程序，安装时勾选 **Add python.exe to PATH**。

也可以在 PowerShell 中使用 Windows 包管理器：

```powershell
winget install --id Python.Python.3.12 -e
```

安装后关闭并重新打开终端，再验证版本：

```powershell
python --version
```

如果使用 Python Launcher，也可以执行：

```powershell
py -3.12 --version
```

版本应为 `3.10` 或更高，例如：

```text
Python 3.12.x
```

如果执行 `python --version` 后跳转到 Microsoft Store、没有显示版本，或返回退出码 `9009`，说明当前命令只是 Windows 的应用执行别名，Python 尚未正确安装或未加入 `PATH`。完成上述安装并重启终端；如果仍有问题，可在 **设置 → 应用 → 高级应用设置 → 应用执行别名** 中关闭 `python.exe` 和 `python3.exe` 的 Microsoft Store 别名。

### macOS

先检查系统中可用的 Python 3：

```shell
python3 --version
```

如果版本低于 3.10 或命令不存在，可通过 [Python 官方网站](https://www.python.org/downloads/macos/) 安装，或使用 Homebrew：

```shell
brew install python@3.12
```

### Linux

先检查版本：

```shell
python3 --version
```

如果没有 Python 3.10+，请使用发行版的软件包管理器安装。例如 Ubuntu/Debian：

```shell
sudo apt update
sudo apt install python3
```

不同 Linux 发行版提供的默认 Python 版本不同；安装后务必再次执行 `python3 --version` 确认版本满足要求。

## 4. 本地运行

在项目根目录中执行：

```shell
python serve.py
```

macOS/Linux 上如果没有 `python` 命令，请使用：

```shell
python3 serve.py
```

脚本会先根据 `content/` 中的 Markdown 内容重新生成 `dist/`，然后启动本地服务器。浏览器访问：

```text
http://127.0.0.1:8000/
```

按 `Ctrl+C` 停止服务器。

Windows 用户也可以双击项目根目录中的 `start-local.bat`。该脚本等价于运行：

```powershell
python serve.py --open
```

它会生成网站、启动服务器并自动打开浏览器。

### 常用启动参数

```shell
python serve.py --open             # 启动后自动打开浏览器
python serve.py --port 9000        # 使用 9000 端口
python serve.py --no-build         # 跳过构建，直接预览已有 dist
python serve.py --host 0.0.0.0     # 允许同一局域网中的设备访问
```

使用 `--host 0.0.0.0` 时，只应在可信网络中运行。终端会尽可能显示局域网访问地址。

## 5. 只构建静态网站

如果只需要生成可部署的静态文件：

```shell
python build.py
```

macOS/Linux 可使用：

```shell
python3 build.py
```

构建成功后，终端会显示生成的节点数量，结果位于：

```text
dist/
├─ index.html
├─ space.json
├─ assets/
└─ 各内容节点目录/
```

构建脚本会重新创建 `dist/`，不要把需要长期保留的手工文件直接放进该目录。需要随构建复制的公共资源应放在项目根目录的 `public/` 中；该目录存在时会被复制到 `dist/`。

## 6. 内容与配置

- `content/`：Markdown 内容目录
- `content/index.md`：根节点，必须存在
- 各级目录的 `index.md`：对应一个空间节点
- `src/assets/`：网站使用的 CSS 和 JavaScript
- `site.json`：站点标题、语言、内容目录、输出目录和部署路径等配置
- `dist/`：自动生成的静态站点

`site.json` 中的主要配置如下：

```json
{
  "base_path": "/MyBlog/",
  "content_dir": "content",
  "output_dir": "dist"
}
```

如果 GitHub 仓库改名，应同步修改 `base_path`。本地运行通常不需要修改此项。

## 7. 发布到 GitHub Pages（可选）

发布前需要：

1. 安装 Git，并确认 `git --version` 可用。
2. 项目已经是 Git 仓库。
3. 已配置可写入的 GitHub 远程仓库，默认远程名称为 `origin`。
4. GitHub Pages 的发布来源设置为 `gh-pages` 分支的 `/ (root)`。

首次初始化仓库时可执行：

```shell
git init
git remote add origin https://github.com/<用户名>/<仓库名>.git
```

正式发布：

```shell
python deploy.py
```

Windows 也可以双击 `deploy-gh-pages.bat`。发布脚本会重新构建网站，把 `dist/` 内容制作成独立提交并安全推送到 `gh-pages` 分支，不会切换或清理当前源码分支。

建议首次先预演：

```shell
python deploy.py --dry-run
```

其他参数：

```shell
python deploy.py --no-build
python deploy.py --message "更新认知空间"
python deploy.py --remote upstream
```

## 8. 验证环境是否搭建成功

依次完成以下检查：

```shell
python --version
python build.py
python serve.py
```

macOS/Linux 将 `python` 替换为 `python3`。满足以下条件即表示环境正常：

- Python 版本不低于 3.10；
- `python build.py` 正常结束，并在 `dist/` 生成 `index.html`；
- `python serve.py` 启动后可访问 `http://127.0.0.1:8000/`；
- 页面可以正常显示中文内容、样式和交互。

## 9. 常见问题

### `python` 不是可识别的命令

Python 未安装或未加入 `PATH`。重新安装并在 Windows 安装程序中勾选 **Add python.exe to PATH**，然后重启终端。macOS/Linux 通常应使用 `python3`。

### `Address already in use` 或端口不可用

默认的 8000 端口正被其他程序占用，换一个端口：

```shell
python serve.py --port 9000
```

### 使用 `--no-build` 时提示 `dist/index.html` 不存在

先执行：

```shell
python build.py
```

或者去掉 `--no-build`，让 `serve.py` 自动构建。

### 构建提示某个目录缺少 `index.md`

每一个参与空间层级的目录都需要有自己的 `index.md`。为报错目录补充该文件后重新构建。

### Git 提示 `detected dubious ownership`

这表示仓库目录的所有者与当前运行 Git 的用户不同。先确认该目录可信；确认后，再把实际的绝对路径加入 Git 安全目录：

```shell
git config --global --add safe.directory "D:/WorkSpace/MyBlog"
```

不要为不可信或范围过大的目录添加此例外。

### 发布时找不到远程仓库 `origin`

检查当前远程：

```shell
git remote -v
```

如果没有 `origin`，添加远程仓库：

```shell
git remote add origin https://github.com/<用户名>/<仓库名>.git
```

## 10. 最短运行流程

已安装 Python 3.10+ 后，只需：

```shell
cd MyBlog
python serve.py --open
```

本项目没有额外依赖安装步骤。
