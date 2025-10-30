import sys
import os
import xml.etree.ElementTree as ET
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def load_config(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    tree = ET.parse(path)
    root = tree.getroot()
    def get(tag):
        el = root.find(tag)
        if el is None or el.text is None or el.text.strip() == "":
            raise ValueError(f"Missing or empty <{tag}>")
        return el.text.strip()
    package = get("package")
    repo = get("repo")
    test_mode_raw = get("test_mode").lower()
    if test_mode_raw in ("1", "true", "yes"):
        test_mode = True
    elif test_mode_raw in ("0", "false", "no"):
        test_mode = False
    else:
        raise ValueError("Invalid test_mode: use true/false")
    max_depth_raw = get("max_depth")
    try:
        max_depth = int(max_depth_raw)
        if max_depth < 0:
            raise ValueError
    except:
        raise ValueError("Invalid max_depth: must be non-negative integer")
    if test_mode and not os.path.exists(repo):
        raise ValueError("In test_mode repo path does not exist")
    return {"package": package, "repo": repo, "test_mode": test_mode, "max_depth": max_depth}

def print_kv(cfg):
    print(f"package={cfg['package']}")
    print(f"repo={cfg['repo']}")
    print(f"test_mode={cfg['test_mode']}")
    print(f"max_depth={cfg['max_depth']}")

def read_local_package_json(path):
    pj = os.path.join(path, "package.json")
    if not os.path.exists(pj):
        raise FileNotFoundError(f"Local package.json not found in {path}")
    with open(pj, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_package_metadata_from_registry(registry_url, package_name):
    base = registry_url.rstrip("/")
    url = f"{base}/{package_name}"
    req = Request(url, headers={"User-Agent": "stage2-script"})
    try:
        with urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except HTTPError as e:
        raise RuntimeError(f"HTTP error: {e.code} {e.reason}")
    except URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")

def get_deps_from_registry_meta(meta):
    try:
        latest = meta.get("dist-tags", {}).get("latest")
        if not latest:
            versions = sorted(meta.get("versions", {}).keys())
            if versions:
                latest = versions[-1]
        if not latest:
            return {}, latest
        ver_info = meta["versions"].get(latest, {})
        deps = ver_info.get("dependencies", {}) or {}
        return deps, latest
    except Exception:
        return {}, None

def traverse_dependencies(package, cfg, depth, visited):
    if depth < 0:
        return
    indent = "  " * (cfg['max_depth'] - depth)
    try:
        if cfg['test_mode']:
            if depth == cfg['max_depth']:
                pj = read_local_package_json(cfg['repo'])
                version = pj.get("version", "local")
                deps = pj.get("dependencies", {}) or {}
                print(f"{indent}{package}@{version}")
            else:
                print(f"{indent}{package}")
                deps = {}
        else:
            meta = fetch_package_metadata_from_registry(cfg['repo'], package)
            deps, version = get_deps_from_registry_meta(meta)
            print(f"{indent}{package}@{version if version else 'unknown'}")
    except Exception as e:
        print(f"{indent}{package}  (error: {e})")
        return
    if not deps:
        return
    for dep_name in deps:
        if dep_name in visited:
            print(f"{indent}  {dep_name} (cycle)")
            continue
        visited.add(dep_name)
        traverse_dependencies(dep_name, cfg, depth - 1, visited)
        visited.remove(dep_name)

def get_direct_dependencies(package, cfg):
    if cfg['test_mode']:
        pj = read_local_package_json(cfg['repo'])
        deps = pj.get("dependencies", {}) or {}
        return deps
    else:
        meta = fetch_package_metadata_from_registry(cfg['repo'], package)
        deps, version = get_deps_from_registry_meta(meta)
        return deps or {}

def save_direct_deps_to_file(package, cfg, deps):
    fname = f"direct_deps_{package.replace('/', '_')}.json"
    out = {
        "package": package,
        "repo": cfg['repo'],
        "test_mode": cfg['test_mode'],
        "max_depth": cfg['max_depth'],
        "direct_dependencies": deps
    }
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return fname

def stage1(cfg):
    print_kv(cfg)

def stage2(cfg):
    print_kv(cfg)
    deps = {}
    try:
        deps = get_direct_dependencies(cfg['package'], cfg)
    except Exception as e:
        print("error: failed to get direct dependencies:", e)
        deps = {}
    print("direct dependencies:")
    if not deps:
        print("  (none)")
    else:
        for name, ver in deps.items():
            print(f"  {name}: {ver}")
    print("\ndependency tree (limited by max_depth):")
    visited = set()
    visited.add(cfg['package'])
    traverse_dependencies(cfg['package'], cfg, cfg['max_depth'], visited)

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.xml"
    stage = 1
    if len(sys.argv) > 2:
        try:
            stage = int(sys.argv[2])
        except:
            pass
    try:
        cfg = load_config(cfg_path)
    except Exception as e:
        print("error:", e)
        sys.exit(1)
    try:
        if stage == 1:
            stage1(cfg)
        elif stage == 2:
            stage2(cfg)
        else:
            print("error: unknown stage (use 1 or 2)")
            sys.exit(1)
    except Exception as e:
        print("error:", e)
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
