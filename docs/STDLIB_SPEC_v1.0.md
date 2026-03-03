# 📘 STDLIB_SPEC_v1.0.md  
**B# Standard Library Specification v1.0**  
Status: Draft  
Version: 1.0  
Language Version: B# 1.0.1  

---

# 1️⃣ Overview

The B# Standard Library (stdlib) defines the official built-in modules that provide essential functionality beyond core language features.

This document defines:

- Stable module names
- Function signatures
- Return types
- Error behavior
- Deterministic behavior rules

⚠️ This is a specification only.  
No implementation details are included.

---

# 2️⃣ Import Model

Future import syntax (reserved):

```bsharp
import math
import strings
import lists
import files
import time
import system
```

Modules are namespaced:

```bsharp
math.sqrt(25)
strings.upper("hello")
```

---

# 3️⃣ Module: math

Purpose: Mathematical utilities.

## 3.1 Constants

| Name     | Type  | Description                |
|----------|-------|---------------------------|
| math.PI  | float | 3.141592653589793         |
| math.E   | float | Euler’s number            |

---

## 3.2 Functions

### math.sqrt(x: number) → float
Returns square root of x.  
Error if x < 0.

### math.pow(base: number, exp: number) → float
Returns base raised to exponent.

### math.abs(x: number) → number
Returns absolute value.

### math.round(x: number) → int
Rounds to nearest integer.

### math.floor(x: number) → int
Largest integer ≤ x.

### math.ceil(x: number) → int
Smallest integer ≥ x.

### math.min(a: number, b: number) → number
Returns smaller value.

### math.max(a: number, b: number) → number
Returns larger value.

---

# 4️⃣ Module: strings

Purpose: String manipulation utilities.

## 4.1 Functions

### strings.length(s: string) → int
Returns character length.

### strings.upper(s: string) → string
Returns uppercase version.

### strings.lower(s: string) → string
Returns lowercase version.

### strings.trim(s: string) → string
Removes leading and trailing whitespace.

### strings.contains(s: string, sub: string) → bool
Returns true if substring exists.

### strings.replace(s: string, old: string, new: string) → string
Replaces occurrences of old with new.

### strings.split(s: string, delimiter: string) → list
Splits string into list.

### strings.join(lst: list, delimiter: string) → string
Joins list elements into string.

---

# 5️⃣ Module: lists

Purpose: List utilities beyond core list syntax.

## 5.1 Functions

### lists.length(lst: list) → int
Returns number of elements.

### lists.append(lst: list, value: any) → list
Returns new list with value appended.  
(Does NOT mutate original list.)

### lists.pop(lst: list) → list
Returns new list without last element.  
Error if empty.

### lists.get(lst: list, index: int) → any
Returns element at index.  
Error if out of range.

### lists.set(lst: list, index: int, value: any) → list
Returns new list with modified value.

### lists.slice(lst: list, start: int, end: int) → list
Returns sublist [start, end).

### lists.reverse(lst: list) → list
Returns reversed list.

---

# 6️⃣ Module: files

Purpose: File I/O abstraction.

⚠️ File operations may throw runtime errors.

## 6.1 Functions

### files.read(path: string) → string
Returns entire file contents.

### files.write(path: string, content: string) → bool
Writes content.  
Returns true if successful.

### files.append(path: string, content: string) → bool
Appends to file.

### files.exists(path: string) → bool
Returns true if file exists.

### files.delete(path: string) → bool
Deletes file.

---

# 7️⃣ Module: time

Purpose: Time utilities.

## 7.1 Functions

### time.now() → int
Returns Unix timestamp (seconds).

### time.sleep(seconds: int) → void
Pauses execution.

### time.format(timestamp: int) → string
Returns human-readable time string.

---

# 8️⃣ Module: system

Purpose: System-level utilities.

## 8.1 Functions

### system.exit(code: int) → void
Terminates program.

### system.print(value: any) → void
Prints to console.

### system.input(prompt: string) → string
Reads input from user.

---

# 9️⃣ Error Handling Rules

1. Type mismatch → Runtime Error  
2. Invalid index → Runtime Error  
3. File access failure → Runtime Error  
4. Negative sqrt → Runtime Error  

All errors must:
- Stop execution
- Provide line number
- Provide descriptive message

---

# 🔟 Determinism Policy

All stdlib functions must be:

- Deterministic (except time.now and system.input)
- Side-effect free except:
  - files.*
  - system.*
  - time.sleep

---

# 11️⃣ Versioning Rules

This specification is:

STDLIB_SPEC_v1.0  
Compatible with: B# 1.0.x

Future updates must:
- Never break existing signatures
- Only add new functions

---

# 12️⃣ Reserved for Future

Planned (v1.1+):

- random module
- json module
- http module
- os module
- error handling system
- async support

---

# ✅ End of Specification