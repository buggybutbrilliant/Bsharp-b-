# B# (B-sharp) Programming Language

A human-centric programming language written in plain English.

**Version:** 1.2.1 &nbsp;·&nbsp; **Runtime:** Python 3.8+

---

## Quick Start

```bash
# Run a program
python bsharp.py run examples/hello.bsharp

# Run with step-by-step trace
python bsharp.py run examples/fibonacci.bsharp --trace

# Compile to bytecode
python bsharp.py build examples/hello.bsharp

# Lint a file for errors and bad patterns
python bsharp.py lint examples/hello.bsharp

# Run all tests
python bsharp.py test

# Check version
python bsharp.py version

# Get help
python bsharp.py help
```

---

## CLI Reference

| Command | Description |
|---|---|
| `bsharp run <file>` | Run a `.bsharp` or `.bsc` file |
| `bsharp run <file> --trace` | Run with step-by-step trace |
| `bsharp run <file> --debug` | Same as `--trace` |
| `bsharp run <file> --disasm` | Print bytecode disassembly before running |
| `bsharp build <file>` | Compile `.bsharp` → `.bsc` bytecode file |
| `bsharp build <file> --disasm` | Compile and print full bytecode listing |
| `bsharp lint <file>` | Check for errors, warnings, and bad patterns |
| `bsharp test` | Run all tests in `tests/cases/` |
| `bsharp test <folder>` | Run tests in a custom folder |
| `bsharp version` | Show version, Python runtime, platform |
| `bsharp help` | Show help |

---

## How Execution Works

B# compiles your source to bytecode before running it:

```
.bsharp source  →  compiler  →  .bsc bytecode  →  VM
```

On first run, a `.bsc` cache file is saved next to your source. On subsequent runs, if the source hasn't changed, B# skips recompilation and loads the cache directly — making startup faster.

You can also run a pre-compiled `.bsc` file directly:

```bash
bsharp run program.bsc
```

---

## Language Reference

### Variables

| Feature | Syntax |
|---|---|
| Create variable | `let x be 5` |
| Update variable | `change x to 10` |
| Typed variable | `let name be string "Alice"` |
| Integer type | `let age be integer 21` |
| Float type | `let pi be float 3.14` |
| Boolean type | `let flag be boolean true` |

### Input / Output

| Feature | Syntax |
|---|---|
| Print output | `say "Hello", name` |
| Read input | `ask "Your name?" and store in n` |
| Typed input | `ask "Age?" as integer and store in age` |

### Control Flow

| Feature | Syntax |
|---|---|
| Condition | `if x is greater than 5 then ... end` |
| Else / Else if | `if ... then ... else if ... then ... else ... end` |
| While loop | `while x is less than 10 do ... end` |
| For loop (range) | `for each n from 1 to 10 do ... end` |
| For loop (list) | `for each item in myList do ... end` |

### Functions

| Feature | Syntax |
|---|---|
| Define function | `define function add with a and b do ... end` |
| Call function | `call add with 3 and 5` |
| Call and store result | `let r be call add with 3 and 5` |
| Return value | `return a plus b` |

### Lists

| Feature | Syntax |
|---|---|
| Create list | `let nums be list of 1, 2, 3` |
| Add to list | `add 5 to nums` |
| Remove from list | `remove 5 from nums` |
| Get length | `let len be get length of nums` |
| Join list to string | `let s be join nums with ", "` |

### Dictionaries

| Feature | Syntax |
|---|---|
| Create dictionary | `let d be dictionary with key as value end` |
| Access key | `d key` |

### File I/O (built-in)

| Feature | Syntax |
|---|---|
| Read file | `read from "data.txt" and store in content` |
| Write file | `write content to "output.txt"` |

### Error Handling

| Feature | Syntax |
|---|---|
| Try / catch | `try ... catch err ... end` |
| Describe last operation | `explain` |
| Comment | `note This is a comment` |

---

## Comparisons

| English | Meaning |
|---|---|
| `is equal to` | `==` |
| `is not equal to` | `!=` |
| `is greater than` | `>` |
| `is less than` | `<` |
| `is at least` | `>=` |
| `is at most` | `<=` |
| `does contain` | `in` |
| `does not contain` | `not in` |

---

## Standard Libraries

Import any library with `use <name>` before using it.

```bsharp
use math
let result be call math.sqrt with 144
say result
```

### io
| Function | Description |
|---|---|
| `io.print(value)` | Print a value to the console |
| `io.input(prompt)` | Read a line of input from the user |
| `io.read_file(path)` | Read entire file contents as a string |
| `io.write_file(path, content)` | Write a string to a file |

### math
| Function / Constant | Description |
|---|---|
| `math.PI` | 3.141592653589793 |
| `math.E` | Euler's number |
| `math.sqrt(x)` | Square root |
| `math.pow(base, exp)` | Power |
| `math.abs(x)` | Absolute value |
| `math.min(a, b)` | Smaller of two values |
| `math.max(a, b)` | Larger of two values |
| `math.random()` | Random float between 0 and 1 |
| `math.floor(x)` | Round down |
| `math.ceil(x)` | Round up |

### string
| Function | Description |
|---|---|
| `string.length(s)` | Character count |
| `string.upper(s)` | Uppercase |
| `string.lower(s)` | Lowercase |
| `string.trim(s)` | Remove leading/trailing whitespace |
| `string.split(s, delimiter)` | Split into list |
| `string.join(list, delimiter)` | Join list into string |
| `string.replace(s, old, new)` | Replace substring |
| `string.contains(s, sub)` | Check if substring exists |

### list
| Function | Description |
|---|---|
| `list.length(lst)` | Number of items |
| `list.append(lst, value)` | New list with value added at end |
| `list.pop(lst)` | New list without last item |
| `list.get(lst, index)` | Item at index |
| `list.set(lst, index, value)` | New list with item replaced |
| `list.slice(lst, start, end)` | Sublist |
| `list.reverse(lst)` | Reversed list |
| `list.sort(lst)` | Sorted list |

### files
| Function | Description |
|---|---|
| `files.exists(path)` | Returns `true` if file exists |
| `files.append(path, content)` | Append content to a file |
| `files.delete(path)` | Delete a file |
| `files.size(path)` | File size in bytes |
| `files.read_lines(path)` | Read file as a list of lines |
| `files.write_lines(path, lines)` | Write a list of lines to a file |

### time
| Function | Description |
|---|---|
| `time.now()` | Current Unix timestamp (integer) |
| `time.sleep(seconds)` | Pause execution |
| `time.format(timestamp)` | Format timestamp as `YYYY-MM-DD HH:MM:SS` |

### random
| Function | Description |
|---|---|
| `random.int(min, max)` | Random integer between min and max (inclusive) |
| `random.float()` | Random float between 0 and 1 |
| `random.choice(list)` | Random item from a list |

### json
| Function | Description |
|---|---|
| `json.parse(string)` | Parse a JSON string into a B# value |
| `json.stringify(value)` | Convert a B# value to a JSON string |

### os
| Function | Description |
|---|---|
| `os.cwd()` | Current working directory |
| `os.listdir(path)` | List files in a directory |
| `os.mkdir(path)` | Create a directory (including parents) |

### system
| Function | Description |
|---|---|
| `system.exit(code)` | Exit the program with a status code |
| `system.args()` | Command-line arguments passed to the script |

### error
| Function | Description |
|---|---|
| `error.raise(message)` | Throw a runtime error with a custom message |
| `error.try(fn)` | Call a function and return the error message if it fails, or `""` if clean |

### window
Requires Python's built-in `tkinter`.

| Function | Description |
|---|---|
| `window.open(title)` | Open a new window with the given title |
| `window.display(content)` | Display content in the most recently opened window |
| `window.exit()` | Close the currently active window |

> Each `window.open` call creates a separate independent window. `window.display` always targets the window opened most recently.

---

## Examples

### Hello World
```bsharp
say "Hello, World!"
```

### Using a Library
```bsharp
use math
use string

let msg be "hello world"
say call string.upper with msg
say call math.sqrt with 25
```

### Multiple Windows
```bsharp
use window

call window.open with "Window One"
call window.display with "Content for window one"

call window.open with "Window Two"
call window.display with "Content for window two"
```

### File Scripting
```bsharp
use files

let lines be list of "Alice", "Bob", "Carol"
call files.write_lines with "names.txt" and lines

let exists be call files.exists with "names.txt"
say exists

let back be call files.read_lines with "names.txt"
for each name in back do
    say name
end
```

---

## Project Structure

```
bsharp/
├── bsharp.py           ← Entry point (calls cli.main)
├── cli.py              ← CLI commands: run, build, lint, test, version
├── core.py             ← Shared error types and base classes
├── lexer.py            ← Tokenizer
├── parser.py           ← AST builder
├── compiler.py         ← AST → bytecode compiler
├── bytecode.py         ← Opcode definitions and .bsc format
├── vm.py               ← Stack-based bytecode virtual machine
├── linter.py           ← Static analyzer (bsharp lint)
├── interpreter.py      ← Standard library implementations
├── README.md
├── LINT_ERRORS.md      ← Linter error and warning reference
└── vscode-extension/
    ├── package.json
    ├── language-configuration.json
    └── syntaxes/
        └── bsharp.tmLanguage.json
```

---

## VS Code Extension

1. Copy the `vscode-extension/` folder to `~/.vscode/extensions/bsharp/`
2. Restart VS Code
3. `.bsharp` files now have full syntax highlighting for keywords, modules, strings, numbers, and comments

---

## Requirements

- Python 3.8 or higher
- No external libraries required
- `tkinter` required only for the `window` library (included with most Python installations)