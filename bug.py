#!/usr/bin/env python3
import sys, os, json, shutil
from urllib.request import urlopen, Request
from urllib.error   import URLError, HTTPError

BUG_VERSION   = "1.1.1"
PACKAGES_DIR  = "bsharp_packages"
MANIFEST_FILE = "bsharp.json"
REGISTRY_URL  = "https://raw.githubusercontent.com/buggybutbrilliant/bsharp-b--packages/main/registry.json"

def _c(t, c): return f'\033[{c}m{t}\033[0m'
def green(t):  return _c(t, '32')
def red(t):    return _c(t, '31')
def yellow(t): return _c(t, '33')
def cyan(t):   return _c(t, '36')
def bold(t):   return _c(t, '1')
def ok(m):     print(f'  {green("+")} {m}')
def err(m):    print(f'  {red("x")} {m}')
def warn(m):   print(f'  {yellow("!")} {m}')
def info(m):   print(f'  {cyan(">")} {m}')
def die(m):    print(f'\n{red("Error:")} {m}\n'); sys.exit(1)
BAR = "-" * 52

def read_manifest():
    if not os.path.isfile(MANIFEST_FILE): return None
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        try:    return json.load(f)
        except: die(f"{MANIFEST_FILE} invalid JSON")

def write_manifest(d):
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

def fetch(url, label=""):
    try:
        req = Request(url, headers={"User-Agent": f"bug-bsharp/{BUG_VERSION}"})
        with urlopen(req, timeout=20) as r: return r.read()
    except HTTPError as e: die(f"HTTP {e.code} ({label or url})")
    except URLError  as e: die(f"Network error: {e.reason}")

def fetch_registry():
    info("Connecting to registry...")
    raw = fetch(REGISTRY_URL, "registry")
    try:    return json.loads(raw.decode("utf-8"))
    except: die("registry.json is not valid JSON")

def installed_version(name):
    meta = os.path.join(PACKAGES_DIR, name, ".bug_meta.json")
    if not os.path.isfile(meta): return None
    with open(meta) as f: return json.load(f).get("version")

def cmd_init(_):
    if os.path.isfile(MANIFEST_FILE):
        warn(f"{MANIFEST_FILE} already exists.")
        if input("  Overwrite? (y/N): ").strip().lower() != "y":
            print("  Cancelled."); return
    write_manifest({
        "name": os.path.basename(os.getcwd()), "version": "1.1.1",
        "description": "", "author": "", "license": "MIT", "dependencies": {}
    })
    ok(f"Created {MANIFEST_FILE}")
    print(f"\n  Install packages with: {cyan('bug install <package>')}\n")

def install_one(spec, registry, save=True):
    pkg_name, want_ver = (spec.split("@", 1) if "@" in spec else (spec, None))
    pkg_name = pkg_name.strip().lower()
    if pkg_name not in registry:
        err(f'Package "{pkg_name}" not found.')
        info(f"Try: bug search {pkg_name}"); return False
    entry    = registry[pkg_name]
    version  = want_ver or entry.get("latest", "1.0.0")
    versions = entry.get("versions", {})
    if version not in versions:
        err(f'Version "{version}" of "{pkg_name}" not found.')
        info("Available: " + ", ".join(sorted(versions.keys()))); return False
    install_dir = os.path.join(PACKAGES_DIR, pkg_name)
    meta_path   = os.path.join(install_dir, ".bug_meta.json")
    if os.path.isdir(install_dir) and os.path.isfile(meta_path):
        if json.load(open(meta_path)).get("version") == version:
            ok(f"{pkg_name}@{version} already installed"); return True
        shutil.rmtree(install_dir)
    # ── Key change: files are stored inline in registry.json ──────────────────
    # registry format:
    # "versions": {
    #   "1.0.0": {
    #     "files": {
    #       "colors.py":   "<full python source>",
    #       "bsharp.json": "<manifest string>"
    #     },
    #     "dependencies": {}
    #   }
    # }
    files = versions[version].get("files")
    if not files:
        err(f'No files for {pkg_name}@{version} — registry entry missing "files" key.')
        return False
    print(f"\n  {bold('Installing')} {cyan(pkg_name)} {yellow('v'+version)}")
    os.makedirs(install_dir, exist_ok=True)
    for filename, content in files.items():
        with open(os.path.join(install_dir, filename), "w", encoding="utf-8") as fh:
            fh.write(content)
        ok(f"Wrote {filename}")
    meta = {"name": pkg_name, "version": version, "description": entry.get("description", "")}
    json.dump(meta, open(meta_path, "w"), indent=2)
    ok(f"Installed  =>  {PACKAGES_DIR}/{pkg_name}/")
    sub = versions[version].get("dependencies", {})
    if sub:
        info(f"Resolving {len(sub)} sub-dependenc{'y' if len(sub)==1 else 'ies'}...")
        for dn, dv in sub.items(): install_one(f"{dn}@{dv}", registry, save=False)
    if save:
        m = read_manifest()
        if m is not None:
            m.setdefault("dependencies", {})[pkg_name] = version
            write_manifest(m); ok(f"Saved to {MANIFEST_FILE}")
    return True

def cmd_install(args):
    pkgs = [a for a in args if not a.startswith("--")]
    if not pkgs:
        m = read_manifest()
        if m is None: die(f'No {MANIFEST_FILE}. Run "bug init" or pass a package name.')
        deps = m.get("dependencies", {})
        if not deps: warn("No dependencies in bsharp.json."); return
        pkgs = [f"{n}@{v}" for n, v in deps.items()]
        print(f"\n{bold('Installing from bsharp.json...')}")
    reg = fetch_registry()
    os.makedirs(PACKAGES_DIR, exist_ok=True)
    for spec in pkgs: install_one(spec, reg)
    print()

def cmd_uninstall(args):
    if not args: die("Usage: bug uninstall <package>")
    pkg_name = args[0].lower()
    d = os.path.join(PACKAGES_DIR, pkg_name)
    if not os.path.isdir(d): err(f'"{pkg_name}" is not installed.'); return
    shutil.rmtree(d); ok(f"Removed {d}")
    m = read_manifest()
    if m and pkg_name in m.get("dependencies", {}):
        del m["dependencies"][pkg_name]; write_manifest(m); ok(f"Removed from {MANIFEST_FILE}")
    print()

def cmd_update(args):
    if not args: die("Usage: bug update <package>")
    pkg_name = args[0].lower()
    reg = fetch_registry()
    if pkg_name not in reg: die(f'Package "{pkg_name}" not found.')
    latest  = reg[pkg_name].get("latest", "1.0.0")
    current = installed_version(pkg_name)
    if current == latest: ok(f"{pkg_name} already up to date (v{latest})"); return
    print(f"\n  Updating {cyan(pkg_name)}: {yellow(current or '?')} => {green(latest)}\n")
    d = os.path.join(PACKAGES_DIR, pkg_name)
    if os.path.isdir(d): shutil.rmtree(d)
    install_one(f"{pkg_name}@{latest}", reg)

def cmd_search(args):
    query = " ".join(args).lower().strip()
    reg   = fetch_registry()
    print(f"\n{bold('B# Package Registry')}\n{BAR}")
    results = [(n, e) for n, e in reg.items()
               if not query or query in (n + " " + e.get("description", "") + " " + " ".join(e.get("tags", []))).lower()]
    if not results:
        warn(f'No packages matching "{query}".' if query else "No packages yet.")
    else:
        for name, entry in sorted(results):
            badge = f" {green('[installed]')}" if installed_version(name) else ""
            print(f"  {cyan(name):<26} {yellow('v'+entry.get('latest','?')):<10} {entry.get('description','')}{badge}")
    print(BAR)
    print(f"  {len(results)} package(s)  |  bug install <n>  to install\n")

def cmd_list(_):
    print(f"\n{bold('Installed Packages')}\n{BAR}")
    if not os.path.isdir(PACKAGES_DIR): warn("Nothing installed yet."); print(); return
    found = False
    for n in sorted(os.listdir(PACKAGES_DIR)):
        mp = os.path.join(PACKAGES_DIR, n, ".bug_meta.json")
        if os.path.isfile(mp):
            meta = json.load(open(mp))
            print(f"  {cyan(n):<26} {yellow('v'+meta.get('version','?')):<10} {meta.get('description','')}")
            found = True
    if not found: warn("No packages found.")
    print(BAR + "\n")

def cmd_publish(_):
    print(f"""
{bold("Publishing a B# Package")}
{BAR}

All packages live inside registry.json in:
  {cyan("https://github.com/buggybutbrilliant/bsharp-b--packages")}

Add your entry to registry.json like this:

  "my_package": {{
    "description": "What it does",
    "author":      "your-name",
    "tags":        ["utility"],
    "latest":      "1.0.0",
    "versions": {{
      "1.0.0": {{
        "dependencies": {{}},
        "files": {{
          "my_package.py": "<full python source here>",
          "bsharp.json":   "<manifest as a json string>"
        }}
      }}
    }}
  }}

my_package.py must define load():

  class ModuleObject:
      def __init__(self, name, exports):
          self.name = name
          self.exports = exports

  def load():
      return ModuleObject("my_package", {{
          "hello": lambda n: print(f"Hello {{n}}!")
      }})

{BAR}
After committing to main: {cyan("bug install my_package")} works for everyone.
""")

def cmd_version(_=None):
    print(f"bug - B# Package Manager  v{BUG_VERSION}")
    print(f"Registry : {REGISTRY_URL}")
    print(f"Packages : {os.path.abspath(PACKAGES_DIR)}")

HELP = f"""
{bold("bug")} - The B# Package Manager  v{BUG_VERSION}
{BAR}
  bug init                   Create bsharp.json
  bug install <pkg>          Install a package
  bug install <pkg>@<ver>    Install a specific version
  bug install                Install all deps from bsharp.json
  bug uninstall <pkg>        Remove a package
  bug update <pkg>           Update to latest version
  bug search [query]         Search the registry
  bug list                   List installed packages
  bug publish                How to add your package to the registry
  bug version                Show version info
  bug help                   Show this help
{BAR}
Registry : {cyan(REGISTRY_URL)}
Packages : {cyan(PACKAGES_DIR + "/")}
"""

CMDS = {
    "init": cmd_init, "install": cmd_install, "uninstall": cmd_uninstall,
    "update": cmd_update, "search": cmd_search, "list": cmd_list,
    "publish": cmd_publish, "version": cmd_version, "--version": cmd_version,
    "-v": cmd_version, "help": lambda _: print(HELP),
    "--help": lambda _: print(HELP), "-h": lambda _: print(HELP),
}

def main():
    argv = sys.argv[1:]
    if not argv: print(HELP); return
    cmd = argv[0]
    if cmd in CMDS: CMDS[cmd](argv[1:])
    else: print(f'  Unknown command "{cmd}". Run "bug help".'); sys.exit(1)

if __name__ == "__main__": main()