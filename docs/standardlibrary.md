# B# Standard Library Docs

Complete reference for all 12 built-in libraries. Import any library with `use <name>` before calling its functions.

```bsharp
use math
let result be call math.sqrt with 25
say result
```

Module **functions** are called with `call <module>.<fn> with <args>`.  
Module **constants** are accessed as plain values: `let x be math.PI`.

---

## Table of Contents

1. [io](#1-io)
2. [math](#2-math)
3. [string](#3-string)
4. [list](#4-list)
5. [files](#5-files)
6. [time](#6-time)
7. [random](#7-random)
8. [json](#8-json)
9. [os](#9-os)
10. [system](#10-system)
11. [error](#11-error)
12. [window](#12-window)

---

## 1. io

Input and output operations.

```bsharp
use io
```

### `io.print(value)`

Prints a value to the console. Accepts any B# value — lists, booleans, numbers, strings.

```bsharp
call io.print with "Hello, World!"
call io.print with 42
call io.print with true
```

> **Difference from `say`:** `io.print` is a module function you can call like any other. `say` is a built-in statement. Both print to stdout.

---

### `io.input(prompt)`

Reads a line of text from the user and returns it as a string.

```bsharp
let name be call io.input with "Enter your name: "
say "Hello,", name
```

The `prompt` argument is optional:

```bsharp
let raw be call io.input
```

---

### `io.read_file(path)`

Reads the entire contents of a file and returns it as a string.

```bsharp
let content be call io.read_file with "notes.txt"
say content
```

**Errors:**
- File not found → `io.read_file: file "notes.txt" not found`
- No permission → `io.read_file: permission denied for "notes.txt"`

---

### `io.write_file(path, content)`

Writes a string to a file, overwriting it if it already exists. Creates the file if it does not exist.

```bsharp
call io.write_file with "output.txt" and "Hello from B#"
```

Returns `true` on success.

**Errors:**
- No permission → `io.write_file: permission denied for "output.txt"`

---

## 2. math

Mathematical functions and constants.

```bsharp
use math
```

### Constants

| Name | Value |
|---|---|
| `math.PI` | 3.141592653589793 |
| `math.E` | 2.718281828459045 |

```bsharp
say math.PI
say math.E
```

---

### `math.sqrt(x)`

Returns the square root of `x`.

```bsharp
let root be call math.sqrt with 144
say root   note 12.0
```

**Errors:**
- Negative input → `math.sqrt: cannot take square root of a negative number`

---

### `math.pow(base, exp)`

Returns `base` raised to the power of `exp`.

```bsharp
let result be call math.pow with 2 and 8
say result   note 256.0
```

---

### `math.abs(x)`

Returns the absolute value of `x`.

```bsharp
let val be call math.abs with 0 minus 42
say val   note 42
```

---

### `math.min(a, b)`

Returns the smaller of two values.

```bsharp
let smallest be call math.min with 10 and 3
say smallest   note 3
```

---

### `math.max(a, b)`

Returns the larger of two values.

```bsharp
let biggest be call math.max with 10 and 3
say biggest   note 10
```

---

### `math.random()`

Returns a random float between 0.0 (inclusive) and 1.0 (exclusive).

```bsharp
let n be call math.random
say n
```

---

### `math.floor(x)`

Rounds `x` down to the nearest integer.

```bsharp
let n be call math.floor with 4.9
say n   note 4
```

---

### `math.ceil(x)`

Rounds `x` up to the nearest integer.

```bsharp
let n be call math.ceil with 4.1
say n   note 5
```

---

## 3. string

String manipulation functions.

```bsharp
use string
```

---

### `string.length(s)`

Returns the number of characters in `s`.

```bsharp
let n be call string.length with "hello"
say n   note 5
```

---

### `string.upper(s)`

Returns `s` converted to uppercase.

```bsharp
let up be call string.upper with "hello"
say up   note HELLO
```

---

### `string.lower(s)`

Returns `s` converted to lowercase.

```bsharp
let lw be call string.lower with "WORLD"
say lw   note world
```

---

### `string.trim(s)`

Returns `s` with leading and trailing whitespace removed.

```bsharp
let clean be call string.trim with "  hello  "
say clean   note hello
```

---

### `string.split(s, delimiter)`

Splits `s` into a list using `delimiter` as the separator.

```bsharp
let parts be call string.split with "a,b,c" and ","
say parts   note [a, b, c]
```

Omit the delimiter to split into individual characters:

```bsharp
let chars be call string.split with "hello" and ""
say chars   note [h, e, l, l, o]
```

---

### `string.join(list, delimiter)`

Joins a list of values into a single string using `delimiter` between items.

```bsharp
let words be list of "one", "two", "three"
let result be call string.join with words and " - "
say result   note one - two - three
```

---

### `string.replace(s, old, new)`

Returns a copy of `s` with every occurrence of `old` replaced by `new`.

```bsharp
let result be call string.replace with "cat sat on a mat" and "at" and "og"
say result   note cog sog on a mog
```

---

### `string.contains(s, sub)`

Returns `true` if `sub` is found anywhere inside `s`, `false` otherwise.

```bsharp
let found be call string.contains with "hello world" and "world"
say found   note true
```

---

## 4. list

List manipulation functions. All functions return a **new list** — the original is never modified.

```bsharp
use list
```

---

### `list.length(lst)`

Returns the number of items in `lst`.

```bsharp
let nums be list of 10, 20, 30
let n be call list.length with nums
say n   note 3
```

---

### `list.append(lst, value)`

Returns a new list with `value` added at the end.

```bsharp
let nums be list of 1, 2, 3
let updated be call list.append with nums and 4
say updated   note [1, 2, 3, 4]
```

---

### `list.pop(lst)`

Returns a new list with the last item removed.

```bsharp
let nums be list of 1, 2, 3
let shorter be call list.pop with nums
say shorter   note [1, 2]
```

**Errors:**
- Empty list → `list.pop: cannot pop from an empty list`

---

### `list.get(lst, index)`

Returns the item at position `index` (zero-based).

```bsharp
let fruits be list of "apple", "banana", "cherry"
let second be call list.get with fruits and 1
say second   note banana
```

**Errors:**
- Out of range → `list.get: index 5 out of range (length 3)`

---

### `list.set(lst, index, value)`

Returns a new list with the item at `index` replaced by `value`.

```bsharp
let nums be list of 1, 2, 3
let updated be call list.set with nums and 1 and 99
say updated   note [1, 99, 3]
```

---

### `list.slice(lst, start, end)`

Returns a sublist from index `start` up to (but not including) index `end`.

```bsharp
let nums be list of 10, 20, 30, 40, 50
let mid be call list.slice with nums and 1 and 4
say mid   note [20, 30, 40]
```

---

### `list.reverse(lst)`

Returns a new list in reverse order.

```bsharp
let nums be list of 1, 2, 3
let rev be call list.reverse with nums
say rev   note [3, 2, 1]
```

---

### `list.sort(lst)`

Returns a new sorted list (ascending). Works on numbers or strings.

```bsharp
let nums be list of 5, 2, 8, 1
let sorted be call list.sort with nums
say sorted   note [1, 2, 5, 8]
```

---

## 5. files

File system operations beyond basic read/write.

```bsharp
use files
```

---

### `files.exists(path)`

Returns `true` if the file exists at `path`, `false` otherwise.

```bsharp
let found be call files.exists with "config.txt"
if found then
    say "Config file is present"
else
    say "Config file is missing"
end
```

---

### `files.append(path, content)`

Appends `content` to the end of the file without overwriting it. Creates the file if it does not exist.

```bsharp
call files.append with "log.txt" and "New entry"
```

Returns `true` on success.

---

### `files.delete(path)`

Deletes the file at `path`.

```bsharp
call files.delete with "temp.txt"
```

Returns `true` on success.

**Errors:**
- File not found → `files.delete: file "temp.txt" not found`
- No permission → `files.delete: permission denied for "temp.txt"`

---

### `files.size(path)`

Returns the file size in bytes as an integer.

```bsharp
let bytes be call files.size with "data.txt"
say "File is", bytes, "bytes"
```

**Errors:**
- File not found → `files.size: file "data.txt" not found`

---

### `files.read_lines(path)`

Reads the file and returns a list where each item is one line (newline characters stripped).

```bsharp
let lines be call files.read_lines with "names.txt"
for each line in lines do
    say line
end
```

---

### `files.write_lines(path, lines)`

Takes a list and writes each item as a line in the file, separated by newlines. Overwrites the file if it already exists.

```bsharp
let entries be list of "Alice", "Bob", "Carol"
call files.write_lines with "names.txt" and entries
```

Returns `true` on success.

**Errors:**
- `lines` is not a list → `files.write_lines: expected a list, got ...`

---

## 6. time

Date, time, and timing utilities.

```bsharp
use time
```

---

### `time.now()`

Returns the current Unix timestamp as an integer (seconds since 1 Jan 1970).

```bsharp
let ts be call time.now
say ts
```

---

### `time.sleep(seconds)`

Pauses program execution for the given number of seconds. Accepts decimals for sub-second precision.

```bsharp
say "Starting..."
call time.sleep with 2
say "2 seconds later"
```

---

### `time.format(timestamp)`

Converts a Unix timestamp into a human-readable string in `YYYY-MM-DD HH:MM:SS` format.

```bsharp
let ts be call time.now
let readable be call time.format with ts
say readable   note e.g. 2026-03-03 14:30:00
```

---

## 7. random

Random number and selection utilities.

```bsharp
use random
```

---

### `random.int(min, max)`

Returns a random integer between `min` and `max`, inclusive on both ends.

```bsharp
let dice be call random.int with 1 and 6
say dice
```

---

### `random.float()`

Returns a random float between 0.0 (inclusive) and 1.0 (exclusive).

```bsharp
let chance be call random.float
say chance
```

---

### `random.choice(list)`

Returns a randomly selected item from `list`.

```bsharp
let options be list of "rock", "paper", "scissors"
let pick be call random.choice with options
say pick
```

**Errors:**
- Not a list → `random.choice: expects a list, got ...`
- Empty list → `random.choice: cannot choose from an empty list`

---

## 8. json

JSON parsing and serialisation.

```bsharp
use json
```

---

### `json.parse(string)`

Parses a JSON string and returns a B# value. JSON objects become dictionaries, arrays become lists.

```bsharp
let data be call json.parse with "[1, 2, 3]"
say data

let obj be call json.parse with "{\"name\": \"Alice\", \"age\": 30}"
say obj
```

**Errors:**
- Invalid JSON → `json.parse: invalid JSON — ...`
- Not a string → `json.parse: expects a string, got ...`

---

### `json.stringify(value)`

Converts a B# value to a JSON string. Works with numbers, strings, booleans, lists, and dictionaries.

```bsharp
let nums be list of 1, 2, 3
let s be call json.stringify with nums
say s   note [1, 2, 3]

let score be 99
say call json.stringify with score   note 99
```

**Errors:**
- Functions cannot be serialised → `json.stringify: cannot serialise a function`
- Modules cannot be serialised → `json.stringify: cannot serialise module "math"`

---

## 9. os

Operating system and file system utilities.

```bsharp
use os
```

---

### `os.cwd()`

Returns the current working directory as a string.

```bsharp
let dir be call os.cwd
say dir
```

---

### `os.listdir(path)`

Returns a list of file and folder names inside `path`. Omit the argument or pass `"."` for the current directory.

```bsharp
let entries be call os.listdir with "."
for each entry in entries do
    say entry
end
```

**Errors:**
- Path not found → `os.listdir: path "." not found`
- No permission → `os.listdir: permission denied for "..."`

---

### `os.mkdir(path)`

Creates a directory at `path`. Creates all intermediate directories automatically (like `mkdir -p`). Does nothing if the directory already exists.

```bsharp
call os.mkdir with "output/logs/2026"
```

Returns `true` on success.

**Errors:**
- No permission → `os.mkdir: permission denied for "..."`

---

## 10. system

Process and runtime utilities.

```bsharp
use system
```

---

### `system.exit(code)`

Terminates the program immediately with the given exit code. `0` means success, any other number indicates failure.

```bsharp
say "Shutting down"
call system.exit with 0
```

---

### `system.args()`

Returns a list of command-line arguments that were passed after the script name.

```bsharp
note run as: python bsharp.py run myscript.bsharp hello world

use system
let args be call system.args
for each arg in args do
    say arg
end
note prints: hello, world
```

> Arguments at index 0 and 1 (`bsharp.py` and the script filename) are excluded automatically.

---

## 11. error

Custom error raising and safe function execution.

```bsharp
use error
```

---

### `error.raise(message)`

Throws a runtime error with your custom message, immediately stopping execution unless caught by a `try / catch` block.

```bsharp
use error

let age be 0 minus 1
if age is less than 0 then
    call error.raise with "Age cannot be negative"
end
```

Inside a `try / catch`:

```bsharp
use error

try
    call error.raise with "Something went wrong"
catch msg
    say "Caught:", msg
end
```

---

### `error.try(fn)`

Calls a B# function with no arguments in a safe wrapper. Returns the error message string if an error occurred, or an empty string `""` if the function completed cleanly.

This lets you handle errors functionally without a `try / catch` block.

```bsharp
use error

define function risky do
    call error.raise with "Oops"
end

let result be call error.try with risky

if result is not equal to "" then
    say "Error was:", result
else
    say "All good"
end
```

> `error.try` only works with B# functions that take **no parameters**. For functions that need arguments, wrap them in a zero-argument function:

```bsharp
define function run_check do
    call validate with someValue
end

let msg be call error.try with run_check
```

---

## 12. window

Graphical window creation using Python's built-in `tkinter`.

```bsharp
use window
```

> **Requirement:** `tkinter` must be available. It is included with most Python installations.  
> Linux users may need: `sudo apt-get install python3-tk`

---

### `window.open(title)`

Opens a new graphical window with the given title. Each call to `window.open` creates a **separate, independent window**.

The window most recently opened becomes the **active window** — subsequent `window.display` calls go to it.

```bsharp
call window.open with "My App"
```

If a window with that exact title already exists, calling `window.open` again with the same title just switches focus to it instead of creating a duplicate.

---

### `window.display(content)`

Displays content inside the currently active window. Accepts any B# value.

```bsharp
call window.open with "Dashboard"
call window.display with "Loading..."
```

Calling `window.display` again replaces the current content:

```bsharp
call window.display with "Ready"
```

**Errors:**
- No window open → `window.display: no window is open — call window.open first`

---

### `window.exit()`

Closes the currently active window. If other windows are still open, focus shifts back to the most recently opened one.

```bsharp
call window.exit
```

---

### Multiple windows

```bsharp
use window

call window.open with "Panel A"
call window.display with "Content for Panel A"

call window.open with "Panel B"
call window.display with "Content for Panel B"

note Panel A is still open in the background
note Panel B is currently active
```

After your script finishes, any open windows stay alive automatically until the user closes them.

---

### Full window example

```bsharp
use window
use math
use random

call window.open with "Random Numbers"

let result be ""
for each i from 1 to 5 do
    let n be call random.int with 1 and 100
    change result to result plus "Roll " plus i plus ": " plus n plus "\n"
end

call window.display with result
```

---

## Error Messages Reference

When something goes wrong, B# always tells you the line number and a plain-English description. Here are the most common patterns:

| Situation | Message |
|---|---|
| Variable not found | `Variable "x" not found. Create it with "let x be ..."` |
| Wrong number of args | `"add" expects 2 arg(s), got 1` |
| Divide by zero | `Cannot divide by zero.` |
| Negative sqrt | `math.sqrt: cannot take square root of a negative number` |
| File not found | `files.read_lines: file "x.txt" not found` |
| Not a module | `Cannot access ".sqrt" — integer 5 is not a module. Did you forget "use math"?` |
| Unknown library | `Unknown library "xyz". Available: "error", "files", "io", ...` |
| List index out of range | `list.get: index 9 out of range (length 3)` |
| Pop empty list | `list.pop: cannot pop from an empty list` |
| Invalid JSON | `json.parse: invalid JSON — ...` |
| Empty random choice | `random.choice: cannot choose from an empty list` |

---

## Library Quick Reference

```
use io        io.print(v)  io.input(prompt)  io.read_file(p)  io.write_file(p,v)

use math      math.PI  math.E
              math.sqrt(x)  math.pow(b,e)  math.abs(x)
              math.min(a,b)  math.max(a,b)  math.random()
              math.floor(x)  math.ceil(x)

use string    string.length(s)  string.upper(s)  string.lower(s)  string.trim(s)
              string.split(s,d)  string.join(lst,d)
              string.replace(s,old,new)  string.contains(s,sub)

use list      list.length(l)  list.append(l,v)  list.pop(l)
              list.get(l,i)  list.set(l,i,v)  list.slice(l,s,e)
              list.reverse(l)  list.sort(l)

use files     files.exists(p)  files.append(p,v)  files.delete(p)
              files.size(p)  files.read_lines(p)  files.write_lines(p,lst)

use time      time.now()  time.sleep(s)  time.format(ts)

use random    random.int(min,max)  random.float()  random.choice(lst)

use json      json.parse(s)  json.stringify(v)

use os        os.cwd()  os.listdir(p)  os.mkdir(p)

use system    system.exit(code)  system.args()

use error     error.raise(msg)  error.try(fn)

use window    window.open(title)  window.display(content)  window.exit()
```