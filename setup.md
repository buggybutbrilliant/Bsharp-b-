# B# (B-sharp) — Setup Guide
**Version 1.2.1**

---

## Requirements

- **Python 3.10 or higher**
- That's it. B# has no external dependencies.

To check your Python version:
```
python --version
```
or on some systems:
```
python3 --version
```

---

## Installation

### Step 1 — Download the files

Download or clone the B# repository and place all the files in a single folder on your computer. For example:

```
C:\bsharp\          (Windows)
/home/you/bsharp/   (Linux / macOS)
```

The folder must contain all of these files:

```
bsharp.py
core.py
lexer.py
parser.py
compiler.py
vm.py
bytecode.py
interpreter.py
linter.py
cli.py
bug.py
```

---

### Step 2 — Run your first program

Create a file called `hello.bsharp` in your B# folder with this content:

```
say "Hello, World!"
```

Then open a terminal in that folder and run:

```
python bsharp.py run hello.bsharp
```

You should see:
```
Hello, World!
```

---

### Step 3 — (Optional) Create a shortcut command

Instead of typing `python bsharp.py` every time, you can set up a short `bsharp` command.

**Windows** — create a file called `bsharp.bat` in your B# folder:
```bat
@echo off
python "%~dp0bsharp.py" %*
```

Then add your B# folder to your system PATH. After that you can run:
```
bsharp run hello.bsharp
```

**Linux / macOS** — create a file called `bsharp` (no extension) in your B# folder:
```bash
#!/bin/bash
python3 "$(dirname "$0")/bsharp.py" "$@"
```

Make it executable:
```
chmod +x bsharp
```

Then add your B# folder to your PATH in `~/.bashrc` or `~/.zshrc`:
```bash
export PATH="$PATH:/home/you/bsharp"
```

After that you can run:
```
bsharp run hello.bsharp
```

---

## Available Commands

| Command | What it does |
|---|---|
| `bsharp run <file.bsharp>` | Run a B# program |
| `bsharp run <file.bsc>` | Run a compiled bytecode file |
| `bsharp build <file.bsharp>` | Compile to `.bsc` bytecode without running |
| `bsharp lint <file.bsharp>` | Check your code for errors and warnings |
| `bsharp version` | Show version info |
| `bsharp help` | Show all commands and flags |

---

## Package Manager

B# comes with `bug` — the B# package manager.

```
python bug.py install <package>
python bug.py list
python bug.py remove <package>
```

---

## Verifying Everything Works

Run this to confirm your installation is complete:

```
python bsharp.py version
```

Expected output:
```
B# (B-sharp) Programming Language
Version  : 1.2.1
Runtime  : Python 3.x.x
Platform : ...
Mode     : VM (bytecode)
```

---

*B# — a simple, readable, fun programming language.*
*B# is fun hehe*