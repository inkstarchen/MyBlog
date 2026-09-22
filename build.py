from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent
FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)(.*)$", re.S)
INLINE_TOKEN = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))")


@dataclass
class Node:
    slug: str
    path: str
    title: str
    description: str
    order: int
    body_html: str
    source: str
    parent: str | None
    children: list["Node"] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        return {
            "id": stable_id(self.path or "root"),
            "slug": self.slug,
            "path": self.path,
            "title": self.title,
            "description": self.description,
            "order": self.order,
            "body": self.body_html,
            "parent": self.parent,
            "children": [child.path for child in self.children],
        }


def stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def scalar(value: str) -> Any:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_document(text: str) -> tuple[dict[str, Any], str]:
    match = FRONT_MATTER.match(text.replace("\r\n", "\n"))
    if not match:
        return {}, text
    metadata: dict[str, Any] = {}
    for line_number, line in enumerate(match.group(1).splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"第 {line_number} 行不是有效的元数据：{line}")
        key, value = line.split(":", 1)
        metadata[key.strip()] = scalar(value)
    return metadata, match.group(2).strip()


def render_inline(text: str) -> str:
    pieces: list[str] = []
    cursor = 0
    for match in INLINE_TOKEN.finditer(text):
        pieces.append(html.escape(text[cursor : match.start()]))
        token = match.group(0)
        if token.startswith("`"):
            pieces.append(f"<code>{html.escape(token[1:-1])}</code>")
        elif token.startswith("**"):
            pieces.append(f"<strong>{html.escape(token[2:-2])}</strong>")
        else:
            link = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            assert link
            label = html.escape(link.group(1))
            href = html.escape(link.group(2), quote=True)
            pieces.append(f'<a href="{href}">{label}</a>')
        cursor = match.end()
    pieces.append(html.escape(text[cursor:]))
    return "".join(pieces)


def markdown_to_html(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").split("\n")
    output: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{render_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            output.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    for line in lines:
        if line.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{render_inline(heading.group(2))}</h{level}>")
            continue
        item = re.match(r"^[-*]\s+(.+)$", line)
        if item:
            flush_paragraph()
            list_items.append(render_inline(item.group(1)))
            continue
        if line.startswith("> "):
            flush_paragraph()
            flush_list()
            output.append(f"<blockquote>{render_inline(line[2:])}</blockquote>")
            continue
        paragraph.append(line.strip())

    flush_paragraph()
    flush_list()
    if in_code:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(output)


def route_for(relative_dir: Path) -> str:
    if str(relative_dir) == ".":
        return ""
    return PurePosixPath(*relative_dir.parts).as_posix().strip("/") + "/"


def scan_content(content_dir: Path) -> tuple[Node, dict[str, Node]]:
    markdown_files = sorted(content_dir.rglob("*.md"))
    documents = {
        source: parse_document(source.read_text(encoding="utf-8"))
        for source in markdown_files
    }
    hidden_roots = [
        source.parent
        for source, (metadata, _) in documents.items()
        if source.name == "index.md" and metadata.get("space") is False
    ]
    markdown_files = [
        source
        for source in markdown_files
        if documents[source][0].get("space") is not False
        and not any(source.is_relative_to(hidden_root) for hidden_root in hidden_roots)
    ]
    index_files = [source for source in markdown_files if source.name == "index.md"]
    root_index = content_dir / "index.md"
    if root_index not in index_files:
        raise ValueError(f"缺少根节点：{root_index}")

    nodes: dict[str, Node] = {}
    for source in markdown_files:
        relative = source.relative_to(content_dir)
        if source.name == "index.md":
            relative_dir = source.parent.relative_to(content_dir)
            path = route_for(relative_dir)
            slug = source.parent.name if path else "root"
            parent = None if not path else route_for(relative_dir.parent)
        else:
            path = PurePosixPath(*relative.with_suffix("").parts).as_posix().strip("/") + "/"
            slug = source.stem
            parent = route_for(relative.parent)
        metadata, body = documents[source]
        title = str(metadata.get("title") or (source.parent.name if path else "未命名空间"))
        description = str(metadata.get("description") or metadata.get("summary") or "")
        order = int(metadata.get("order", 100))
        if path in nodes:
            raise ValueError(f"重复路径：{path}")
        nodes[path] = Node(
            slug=slug,
            path=path,
            title=title,
            description=description,
            order=order,
            body_html=markdown_to_html(body),
            source=str(source.relative_to(ROOT)),
            parent=parent,
        )

    for node in nodes.values():
        if node.parent is not None:
            if node.parent not in nodes:
                raise ValueError(f"{node.source} 的父目录缺少 index.md")
            nodes[node.parent].children.append(node)
    for node in nodes.values():
        node.children.sort(key=lambda child: (child.order, child.title))
    return nodes[""], nodes


def relative_url(from_path: str, to_path: str) -> str:
    from_parts = [part for part in from_path.strip("/").split("/") if part]
    prefix = "../" * len(from_parts)
    return prefix + (quote(to_path, safe="/") if to_path else "")


def static_navigation(node: Node) -> str:
    if not node.children:
        return '<p class="empty-orbit">这里暂时没有更深的入口</p>'
    links = []
    for child in node.children:
        href = relative_url(node.path, child.path)
        links.append(
            f'<a class="orbit-link" href="{href}" data-space-path="{html.escape(child.path)}">'
            f"<span>{html.escape(child.title)}</span></a>"
        )
    return "\n".join(links)


def breadcrumbs(node: Node, nodes: dict[str, Node]) -> str:
    chain: list[Node] = []
    cursor: Node | None = node
    while cursor is not None:
        chain.append(cursor)
        cursor = nodes.get(cursor.parent) if cursor.parent is not None else None
    chain.reverse()
    return "<span aria-hidden=\"true\"> / </span>".join(
        f'<a href="{relative_url(node.path, item.path)}">{html.escape(item.title)}</a>' for item in chain
    )


def page_html(node: Node, nodes: dict[str, Node], config: dict[str, Any]) -> str:
    depth = len([part for part in node.path.split("/") if part])
    depth_text = "起点" if depth == 0 else f"第 {depth} 层"
    is_leaf = not node.children
    body_class = "reading-mode" if is_leaf else ""
    panel_class = "content-panel is-open" if is_leaf else "content-panel"
    panel_hidden = "false" if is_leaf else "true"
    panel_tabindex = "0" if is_leaf else "-1"
    core_expanded = "true" if is_leaf else "false"
    hint_text = "上下滑动阅读 · 返回上一级可收起" if is_leaf else "选择一个主题，慢慢深入 · 点击中心阅读"
    asset_prefix = "../" * depth + "assets/"
    graph = {path: item.public() for path, item in nodes.items()}
    data_json = json.dumps(
        {"site": config, "nodes": graph}, ensure_ascii=False, separators=(",", ":")
    ).replace("<", "\\u003c")
    title = node.title if not node.path else f"{node.title} · {config['title']}"
    description = node.description or config.get("description", "")
    parent_link = ""
    if node.parent is not None:
        parent_link = (
            f'<a class="back-link" href="{relative_url(node.path, node.parent)}" '
            f'data-space-path="{html.escape(node.parent)}" aria-label="返回上一级">'
            '<span aria-hidden="true">←</span><span>返回</span></a>'
        )

    favicon = (
        "data:image/svg+xml,"
        + quote(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="32" fill="#f8faf8"/>'
            '<circle cx="32" cy="32" r="17" fill="none" stroke="#86a99d" stroke-width="2"/>'
            '<circle cx="32" cy="32" r="4" fill="#33423d"/></svg>'
        )
    )
    return f"""<!doctype html>
<html lang="{html.escape(config.get('language', 'zh-CN'))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta name="theme-color" content="#f8faf8">
  <title>{html.escape(title)}</title>
  <link rel="icon" type="image/svg+xml" href="{favicon}">
  <link rel="stylesheet" href="{asset_prefix}space.css">
  <script defer src="{asset_prefix}space.js"></script>
</head>
<body class="{body_class}" data-current-path="{html.escape(node.path)}">
  <a class="skip-link" href="#node-content">跳到正文</a>
  <div class="ambient" aria-hidden="true"><i></i><i></i><i></i></div>
  <header class="site-header">
    <div id="back-slot">{parent_link}</div>
    <nav class="breadcrumbs" aria-label="当前位置">{breadcrumbs(node, nodes)}</nav>
    <button class="soundless-mark" type="button" id="motion-toggle" aria-pressed="false">减弱动态</button>
  </header>

  <main class="space-stage" id="space-stage">
    <p class="depth-label" id="depth-label">{depth_text}</p>
    <div class="orbit" id="orbit" aria-label="下一级目录">
      {static_navigation(node)}
    </div>

    <button class="core" id="core" type="button" aria-controls="content-panel" aria-expanded="{core_expanded}">
      <span class="core-rings" aria-hidden="true"></span>
      <span class="core-copy">
        <small id="core-kicker">此刻所在</small>
        <strong id="core-title">{html.escape(node.title)}</strong>
        <span id="core-description">{html.escape(node.description)}</span>
      </span>
    </button>
    <p class="hint" id="space-hint">{hint_text}</p>
  </main>

  <aside class="{panel_class}" id="content-panel" aria-hidden="{panel_hidden}" tabindex="{panel_tabindex}" aria-label="笔记内容">
    <article id="node-content">
      <p class="article-eyebrow">沉淀记录</p>
      <div id="article-body">{node.body_html}</div>
    </article>
  </aside>
  <div class="reading-scrollbar" id="reading-scrollbar" role="scrollbar" tabindex="{panel_tabindex}"
       aria-label="笔记阅读进度" aria-controls="content-panel" aria-orientation="vertical"
       aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-hidden="{panel_hidden}">
    <span class="reading-track" aria-hidden="true"></span>
    <span class="reading-thumb" id="reading-thumb" aria-hidden="true"></span>
  </div>
  <p class="sr-only" id="space-status" aria-live="polite"></p>
  <script type="application/json" id="space-data">{data_json}</script>
</body>
</html>
"""


def build(config_path: Path) -> Path:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    content_dir = ROOT / config.get("content_dir", "content")
    output_dir = ROOT / config.get("output_dir", "dist")
    root, nodes = scan_content(content_dir)
    max_nodes = int(config.get("max_visible_nodes", 18))
    warnings = [
        f"{node.source} 有 {len(node.children)} 个子节点，超过建议上限 {max_nodes}"
        for node in nodes.values()
        if len(node.children) > max_nodes
    ]

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    public_dir = ROOT / "public"
    if public_dir.exists():
        shutil.copytree(public_dir, output_dir, dirs_exist_ok=True)
    assets_dir = output_dir / "assets"
    shutil.copytree(ROOT / "src" / "assets", assets_dir)

    for node in nodes.values():
        target_dir = output_dir / Path(node.path)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "index.html").write_text(page_html(node, nodes, config), encoding="utf-8")

    (output_dir / "space.json").write_text(
        json.dumps({"root": root.path, "nodes": {p: n.public() for p, n in nodes.items()}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    print(f"已生成 {len(nodes)} 个空间节点 → {output_dir}")
    for warning in warnings:
        print(f"提醒：{warning}")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="生成认知空间静态网站")
    parser.add_argument("--config", default="site.json", help="站点配置文件")
    args = parser.parse_args()
    build(ROOT / args.config)


if __name__ == "__main__":
    main()
