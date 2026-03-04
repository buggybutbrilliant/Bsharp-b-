# B# Linter — Error & Warning Reference

Complete reference for all codes reported by `bsharp lint`. Run the linter with:

```bash
bsharp lint <file.bsharp>
```

Exit code is `0` if no errors are found (warnings are fine to ship), `1` if any error-level issues exist.

---

## Levels

| Level | Symbol | Meaning |
|---|---|---|
| **Error** | `[E]` | Will definitely fail at runtime — must fix before running |
| **Warning** | `[W]` | Likely a bug or bad pattern — strongly recommended to fix |
| **Info** | `[I]` | Style suggestion or improvement — safe to ignore |

---

## Errors

### E001 — Variable used before being defined

Triggered when a variable is read or updated before a `let` statement has created it.

```bsharp
say x          note [E001] Variable "x" used before being defined
```

**Fix:** Add a `let` statement before the first use.

```bsharp
let x be 0
say x
```

Also triggered when a list is used with `add` or `remove` before it exists:

```bsharp
add 5 to scores     note [E001] List "scores" used before being defined
```

---

### E002 — Module used before being loaded

Triggered when a library function or constant is accessed without a preceding `use` statement.

```bsharp
let r be call math.sqrt with 9    note [E002] Module "math" used before being loaded
```

**Fix:** Add `use math` at the top of your file.

```bsharp
use math
let r be call math.sqrt with 9
```

---

### E003 — Function called but never defined

Triggered when a function is called but no matching `define function` exists anywhere in the file.

```bsharp
let r be call mystery with 42    note [E003] Function "mystery" called but never defined
```

**Fix:** Define the function, or check for a typo in the name.

```bsharp
define function mystery with x do
    return x times 2
end
```

---

### E004 — Wrong number of arguments

Triggered when a function is called with a different number of arguments than its definition expects.

```bsharp
define function add with a and b do
    return a plus b
end

let r be call add with 1 and 2 and 3    note [E004] Function "add" expects 2 argument(s), got 3
```

**Fix:** Match the number of arguments to the function signature.

---

## Warnings

### W001 — Variable defined but never used

Triggered when a `let` statement creates a variable that is never read anywhere after it is set.

```bsharp
let x be 42       note [W001] Variable "x" is defined but never used
let y be 10
say y
```

**Fix:** Either use the variable, or remove the `let` statement if it is not needed.

> Loop variables (`for each n from ...`) and catch variables (`catch err`) are checked too, but internal VM variables (prefixed with `__`) are excluded.

---

### W002 — Function defined more than once

Triggered when two `define function` blocks use the same name. The second definition silently overwrites the first at runtime, which is almost always a mistake.

```bsharp
define function greet do
    say "Hello"
end

define function greet do    note [W002] Function "greet" is defined more than once
    say "Hi"
end
```

**Fix:** Rename one of the functions, or remove the duplicate.

---

### W003 — Unreachable code after return

Triggered when one or more statements follow a `return` inside a function body. Those statements can never execute.

```bsharp
define function double with x do
    return x times 2
    say "This never runs"    note [W003] Unreachable code after "return"
end
```

**Fix:** Remove or move the unreachable statements.

---

### W004 — Possible infinite loop

Triggered when a `while true` loop contains no `return`, `change`, or function call in its body. Without any of these, the loop can never exit.

```bsharp
while true do        note [W004] Possible infinite loop
    let x be 1
end
```

**Fix:** Add a way to exit or modify state inside the loop.

```bsharp
while true do
    change count to count plus 1
    if count is greater than 10 then
        return count
    end
end
```

---

## Info

### I001 — `say` with no items

Triggered when a `say` statement is written with nothing after it. This prints a blank line, which may or may not be intentional.

```bsharp
say    note [I001] "say" with no items — nothing will be printed
```

**Fix:** Add a value to print, or remove the `say` if the blank line is not needed.

---

### I002 — Library imported more than once

Triggered when the same library is loaded with `use` more than once in a file.

```bsharp
use math
use math    note [I002] Library "math" imported more than once
```

**Fix:** Remove the duplicate `use` statement. Importing twice has no effect but adds noise.

---

## Full Code Table

| Code | Level | Summary |
|---|---|---|
| E001 | Error | Variable or list used before being defined |
| E002 | Error | Module accessed before `use` statement |
| E003 | Error | Function called but never defined |
| E004 | Error | Wrong number of arguments passed to function |
| W001 | Warning | Variable defined but never used |
| W002 | Warning | Function defined more than once |
| W003 | Warning | Unreachable code after `return` |
| W004 | Warning | Possible infinite loop (`while true` with no exit) |
| I001 | Info | `say` with no items |
| I002 | Info | Library imported more than once |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | No errors found (warnings and info may still be present) |
| `1` | One or more errors found |