#!/usr/bin/env python3
import sys
import os
import json
import math
import subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def fetch_meta(registry_url, package_name, timeout=10):
    base = registry_url.rstrip("/")
    url = f"{base}/{package_name}"
    req = Request(url, headers={"User-Agent": "d2-visualizer"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_deps_from_meta(meta):
    latest = meta.get("dist-tags", {}).get("latest")
    if not latest:
        versions = sorted(meta.get("versions", {}).keys())
        if versions:
            latest = versions[-1]
    if not latest:
        return {}, latest
    ver_info = meta.get("versions", {}).get(latest, {})
    deps = ver_info.get("dependencies", {}) or {}
    return deps, latest

def build_tree_from_registry(package, registry, max_depth):
    tree = {}
    visited = set()
    def _walk(pkg, depth):
        if depth < 0 or pkg in visited:
            return {}
        visited.add(pkg)
        try:
            meta = fetch_meta(registry, pkg)
            deps, version = get_deps_from_meta(meta)
        except Exception:
            deps = {}
            version = None
        node = {"version": version, "deps": {}}
        if depth > 0:
            for dname in deps:
                node["deps"][dname] = _walk(dname, depth-1)
        return node
    tree[package] = _walk(package, max_depth)
    return tree

def build_tree_from_local(package, repo_path, max_depth):
    root_pj = os.path.join(repo_path, "package.json")
    if not os.path.exists(root_pj):
        raise FileNotFoundError(root_pj)
    with open(root_pj, "r", encoding="utf-8") as f:
        pj = json.load(f)
    def _walk_local(pkg, depth, pjobj=None):
        if depth < 0:
            return {}
        if pkg == pjobj.get("name") if pjobj else pkg:
            version = pjobj.get("version") if pjobj else pjobj
            deps = pjobj.get("dependencies", {}) if pjobj else {}
        else:
            version = None
            deps = {}
        node = {"version": version or "local", "deps": {}}
        if depth > 0:
            for d in deps:
                node["deps"][d] = _walk_local(d, depth-1, {})
        return node
    try:
        root = {"version": pj.get("version"), "deps": pj.get("dependencies", {}) or {}}
    except Exception:
        root = {"version": None, "deps": {}}
    tree = {package: {"version": root.get("version", "local"), "deps": {}}}
    for d in (root.get("deps") or {}):
        tree[package]["deps"][d] = {"version": None, "deps": {}}
    return tree

def build_d2_text_from_tree(tree, root_name):
    lines = []
    lines.append(f'graph "{root_name}" {{')
    def add_node_attrs(name, version):
        safe = name.replace('"', '\\"')
        lines.append(f'  {safe}.shape: box')
        lbl = name if version is None else f'{name}\\n{version}'
        lbl = lbl.replace('"', '\\"')
        lines.append(f'  {safe}.label: "{lbl}"')
    def walk(name, node):
        version = node.get("version")
        add_node_attrs(name, version)
        for child, childnode in node.get("deps", {}).items():
            safe_p = name.replace('"', '\\"')
            safe_c = child.replace('"', '\\"')
            lines.append(f'  {safe_p} -> {safe_c}')
            walk(child, childnode)
    walk(root_name, tree[root_name])
    lines.append('}')
    return "\n".join(lines)

def save_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def try_render_d2(d2_path):
    svg_path = d2_path[:-3] + ".svg"
    try:
        subprocess.check_call(["d2", d2_path, svg_path])
        return svg_path
    except FileNotFoundError:
        return None
    except subprocess.CalledProcessError:
        return None

def open_file(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass

def fallback_svg(tree, root_name, out_svg):
    PAD_X = 20
    PAD_Y = 20
    NODE_W = 160
    NODE_H = 36
    LEVEL_V = 100
    def count_leaves(node):
        deps = node.get("deps", {})
        if not deps:
            return 1
        return sum(count_leaves(cn) for cn in deps.values())
    def layout(node, x0, x1, y, positions, parent_name):
        leaves = count_leaves(node)
        cx = (x0 + x1) / 2
        positions[parent_name] = (cx, y)
        deps = node.get("deps", {})
        if not deps:
            return
        cur = x0
        for name, child in deps.items():
            w = count_leaves(child) / leaves * (x1 - x0)
            child_cx = (cur + cur + w) / 2
            layout(child, cur, cur + w, y + LEVEL_V, positions, name)
            cur += w
    total_leaves = count_leaves(tree[root_name])
    width = max(400, int(total_leaves * (NODE_W/2)) + PAD_X*2)
    height = 600
    positions = {}
    layout(tree[root_name], PAD_X, width - PAD_X, PAD_Y + NODE_H/2, positions, root_name)
    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    elems = []
    lines = []
    for name, (cx, cy) in positions.items():
        x = cx - NODE_W/2
        y = cy - NODE_H/2
        node = tree.get(name) if name == root_name else None
        label = name
        if name == root_name:
            v = tree[root_name].get("version")
            if v:
                label = f"{name}\\n{v}"
        else:
            # try to find version in parent deps if possible
            pass
        lines.append(f'<rect x="{x}" y="{y}" rx="6" ry="6" width="{NODE_W}" height="{NODE_H}" fill="#ffffff" stroke="#222" />')
        txt = esc(label).replace("\\n", "\n")
        lines.append(f'<text x="{cx}" y="{cy}" font-family="Arial" font-size="12" text-anchor="middle" alignment-baseline="middle" fill="#000">{txt}</text>')
    # connections
    def find_node_center(n):
        if n in positions:
            return positions[n]
        return None
    def add_edges(node_name, node):
        for child_name, child_node in node.get("deps", {}).items():
            a = find_node_center(node_name)
            b = find_node_center(child_name)
            if a and b:
                ax, ay = a
                bx, by = b
                sx = ax
                sy = ay + NODE_H/2
                tx = bx
                ty = by - NODE_H/2
                lines.append(f'<path d="M {sx} {sy} L {tx} {ty}" stroke="#444" fill="none" marker-end="url(#arrow)"/>')
            add_edges(child_name, child_node)
    add_edges(root_name, tree[root_name])
    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    svg_parts.append('<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker></defs>')
    svg_parts.extend(lines)
    svg_parts.append('</svg>')
    save_text(out_svg, "\n".join(svg_parts))
    return out_svg

def load_direct_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_tree_from_direct_json(data, registry=None, max_depth=1):
    pkg = data.get("package")
    deps = data.get("direct_dependencies", {}) or {}
    def node_from_dep(name, depth):
        if depth <= 0 or registry is None:
            return {"version": None, "deps": {}}
        try:
            meta = fetch_meta(registry, name)
            d, ver = get_deps_from_meta(meta)
            node = {"version": ver, "deps": {}}
            for dn in d:
                node["deps"][dn] = node_from_dep(dn, depth-1)
            return node
        except Exception:
            return {"version": None, "deps": {}}
    root = {"version": data.get("package_version") or None, "deps": {}}
    for dname in deps:
        root["deps"][dname] = node_from_dep(dname, max_depth-1)
    return {pkg: root}

def usage():
    print("Usage:")
    print("  python visualize.py direct_deps_<pkg>.json [--registry https://registry.npmjs.org] [--depth N]")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        usage()
    json_path = sys.argv[1]
    registry = None
    depth = 2
    argv = sys.argv[2:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--registry" and i+1 < len(argv):
            registry = argv[i+1]
            i += 2
        elif a == "--depth" and i+1 < len(argv):
            try:
                depth = int(argv[i+1])
            except:
                depth = 2
            i += 2
        else:
            i += 1
    if not os.path.exists(json_path):
        print("File not found:", json_path)
        sys.exit(1)
    data = load_direct_json(json_path)
    pkg = data.get("package", "pkg")
    if registry:
        tree = build_tree_from_direct_json(data, registry=registry, max_depth=depth)
    else:
        # only direct deps shown
        tree = {pkg: {"version": data.get("package_version"), "deps": {}}}
        for d in (data.get("direct_dependencies") or {}):
            tree[pkg]["deps"][d] = {"version": None, "deps": {}}
    d2_text = build_d2_text_from_tree(tree, pkg)
    d2_fname = f"graph_{pkg.replace('/', '_')}.d2"
    save_text(d2_fname, d2_text)
    print("Saved D2:", d2_fname)
    svg = try_render_d2(d2_fname)
    if svg:
        print("Rendered SVG:", svg)
        open_file(svg)
        sys.exit(0)
    else:
        print("d2 CLI not available or rendering failed. Generating fallback SVG.")
        svg_fallback = f"graph_{pkg.replace('/', '_')}_fallback.svg"
        svg_file = fallback_svg(tree, pkg, svg_fallback)
        print("Saved SVG:", svg_file)
        open_file(svg_file)
        sys.exit(0)

if __name__ == "__main__":
    main()
