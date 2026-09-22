from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from build import ROOT, build


REF_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class DeployError(RuntimeError):
    pass


def git(args: list[str], cwd: Path, *, capture: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError as error:
        raise DeployError("找不到 Git，请先安装 Git 并确认 git 命令可用。") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "Git 命令执行失败").strip()
        raise DeployError(detail) from error
    return (result.stdout or "").strip()


def validate_ref(value: str, label: str) -> str:
    if not REF_NAME.fullmatch(value) or ".." in value or value.endswith("/"):
        raise DeployError(f"{label}名称无效：{value}")
    return value


def repository_root() -> Path:
    try:
        root = Path(git(["rev-parse", "--show-toplevel"], ROOT)).resolve()
    except DeployError as error:
        raise DeployError(
            "当前项目还不是 Git 仓库。请先运行 git init，并添加 GitHub 远程仓库。"
        ) from error
    if not ROOT.resolve().is_relative_to(root):
        raise DeployError("项目目录不在当前 Git 仓库内。")
    return root


def config_value(repo: Path, key: str, fallback: str) -> str:
    try:
        value = git(["config", "--get", key], repo)
        return value or fallback
    except DeployError:
        return fallback


def remote_head(repo: Path, remote: str, branch: str) -> str:
    output = git(["ls-remote", "--heads", remote, f"refs/heads/{branch}"], repo)
    return output.split()[0] if output else ""


def deploy(args: argparse.Namespace) -> None:
    branch = validate_ref(args.branch, "分支")
    remote = validate_ref(args.remote, "远程")
    repo = repository_root()

    try:
        remote_url = git(["remote", "get-url", remote], repo)
    except DeployError as error:
        raise DeployError(
            f"没有找到远程仓库“{remote}”。请先用 git remote add {remote} <GitHub仓库地址> 添加。"
        ) from error

    if args.no_build:
        output_dir = ROOT / "dist"
        if not (output_dir / "index.html").exists():
            raise DeployError("dist/index.html 不存在，请去掉 --no-build 重新生成。")
    else:
        output_dir = build(ROOT / "site.json")

    dirty = git(["status", "--porcelain"], repo)
    if dirty:
        print("提醒：当前源码有未提交改动，本次发布会包含这些改动生成的结果。")

    source_revision = "未提交版本"
    try:
        source_revision = git(["rev-parse", "--short", "HEAD"], repo)
    except DeployError:
        pass

    message = args.message or (
        f"Deploy {source_revision} · {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}"
    )

    with tempfile.TemporaryDirectory(prefix="cognitive-space-gh-pages-") as temporary:
        deployment = Path(temporary).resolve()
        if deployment == repo or deployment == ROOT.resolve():
            raise DeployError("临时发布目录异常，已停止发布。")

        git(["init", "--quiet"], deployment)
        git(["checkout", "--orphan", branch], deployment)
        git(["config", "user.name", config_value(repo, "user.name", "Cognitive Space Deploy")], deployment)
        git(["config", "user.email", config_value(repo, "user.email", "deploy@localhost")], deployment)
        git(["remote", "add", remote, remote_url], deployment)
        shutil.copytree(output_dir, deployment, dirs_exist_ok=True)
        git(["add", "--all"], deployment)
        git(["commit", "--quiet", "-m", message], deployment)

        if args.dry_run:
            print(f"发布预演完成：已生成只包含 dist 的 {branch} 提交，但没有推送。")
            return

        expected = remote_head(repo, remote, branch)
        lease = f"--force-with-lease=refs/heads/{branch}:{expected}"
        print(f"正在推送到 {remote}/{branch} …")
        git(["push", lease, remote, f"HEAD:refs/heads/{branch}"], deployment, capture=False)

    print(f"发布完成：生成内容已推送到 {remote}/{branch}。")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成网站并安全推送到 GitHub Pages 分支")
    parser.add_argument("--remote", default="origin", help="Git 远程名称，默认 origin")
    parser.add_argument("--branch", default="gh-pages", help="发布分支，默认 gh-pages")
    parser.add_argument("--message", help="自定义发布提交信息")
    parser.add_argument("--no-build", action="store_true", help="跳过生成，直接发布现有 dist")
    parser.add_argument("--dry-run", action="store_true", help="创建发布提交但不推送")
    args = parser.parse_args()

    try:
        deploy(args)
    except DeployError as error:
        raise SystemExit(f"发布失败：{error}") from error


if __name__ == "__main__":
    main()
