import sys
import os
import xml.etree.ElementTree as ET

def load_config(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Invalid XML: {e}")
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
    return {"package": package, "repo": repo, "test_mode": str(test_mode), "max_depth": str(max_depth)}

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.xml"
    try:
        cfg = load_config(cfg_path)
    except Exception as e:
        print("error:", e)
        sys.exit(1)
    for k, v in cfg.items():
        print(f"{k}={v}")

if __name__ == "__main__":
    main()
