# 认知空间

这是一个由 Python 生成的静态网站。内容按文件夹形成层级，浏览时通过同一个空间舞台切换，生成后可直接部署到 GitHub Pages。

## 添加内容

每个目录使用一个 `index.md`。目录中的其他 Markdown 文件会自动成为这个目录下的叶子节点：

```text
content/
├─ index.md
└─ 技术/
   ├─ index.md
   ├─ 人工智能/
   │  └─ index.md
   └─ 一篇文章.md
```

文件开头可以填写：

```yaml
---
title: 人工智能
description: 这个节点在空间中的简短说明
order: 20
---

# 正文标题

这里写 Markdown 正文。
```

当前内置 Markdown 支持标题、段落、无序列表、引用、代码块、粗体、行内代码和链接。

这个项目只用于已经沉淀的长期主题。内容选择、层级组织和视觉原则见 [DESIGN.md](DESIGN.md)。不适合进入空间的目录可以在元数据中设置 `space: false`，文件会保留，但不会参与生成。

## 本地部署

最简单的方式是：

```shell
python serve.py
```

它会先生成最新内容，然后在下面的地址持续提供网站：

```text
http://127.0.0.1:8000/
```

Windows 也可以直接双击项目根目录中的 `start-local.bat`，它会自动生成网站并打开浏览器。回到启动窗口按 `Ctrl+C` 即可停止。

如果希望手机或同一局域网中的其他电脑访问：

```shell
python serve.py --host 0.0.0.0
```

启动后终端会显示局域网访问地址。此模式会向同一网络开放站点，只应在可信网络中使用。

其他可用参数：

```shell
python serve.py --port 9000    # 更换端口
python serve.py --no-build     # 不重新生成，直接使用现有 dist
python serve.py --open         # 启动后自动打开浏览器
```

## 只生成网站

需要 Python 3.10 或更高版本，不需要安装第三方包：

```shell
python build.py
```

结果生成到 `dist/`。

资源路径会根据当前站点位置自动确定，本地部署和 GitHub Pages 项目路径都能工作。

## GitHub Pages

`site.json` 中的 `base_path` 用于记录正式部署路径。默认仓库名为 `MyBlog`：

```json
"base_path": "/MyBlog/"
```

仓库改名后请同步修改它。推送到 `main` 分支时，工作流会验证网站能够正常生成；正式发布由下面的 `deploy.py` 完成，避免自动工作流和 `gh-pages` 分支同时发布产生冲突。

### 手动发布到 gh-pages 分支

项目已经提供独立发布脚本。它会重新生成网站，在临时目录创建一个只包含 `dist` 内容的提交，然后推送到远程 `gh-pages` 分支；当前源码分支和工作目录不会被切换或清理。

首次使用前，确保项目已经是 Git 仓库并配置了 GitHub 远程：

```shell
git init
git remote add origin https://github.com/<用户名>/<仓库名>.git
```

发布：

```shell
python deploy.py
```

Windows 也可以双击 `deploy-gh-pages.bat`。

其他选项：

```shell
python deploy.py --dry-run                 # 生成发布提交，但不推送
python deploy.py --no-build                # 直接发布现有 dist
python deploy.py --message "更新认知空间"  # 自定义提交信息
python deploy.py --remote upstream         # 使用其他远程名称
```

脚本使用带版本校验的强制推送：如果远程 `gh-pages` 在发布过程中被其他人更新，本次推送会停止，而不是覆盖对方的更新。

在 GitHub 仓库的 **Settings → Pages** 中，将发布来源设置为 **Deploy from a branch**，分支选择 `gh-pages`，目录选择 `/ (root)`。这个设置通常只需要做一次。
