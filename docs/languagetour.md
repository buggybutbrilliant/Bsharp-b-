# B# Language Tour

A hands-on walkthrough of every feature in B#, from your first variable to error handling and libraries. Each section builds on the last — work through it top to bottom or jump to any topic you need.

---

## 1. Hello, World

Every B# program is plain English. No semicolons, no brackets, no boilerplate.

```bsharp
say "Hello, World!"
```

`say` prints to the console. You can print multiple values on one line by separating them with commas.

```bsharp
let name be "Raunak"
say "Hello,", name
```

Output:
```
Hello, Raunak
```

---

## 2. Comments

Use `note` to write a comment. The rest of that line is ignored.

```bsharp
note This is a comment
say "This runs"   note this part is ignored too
```

---

## 3. Variables

### Creating a variable

```bsharp
let x be 10
let greeting be "Hello"
let active be true
let price be 9.99
```

### Updating a variable

```bsharp
let score be 0
change score to 100
say score
```

### Typed variables

You can declare a type to enforce conversion at assignment time.

```bsharp
let age be integer 21
let ratio be float 0.5
let label be string 42
let flag be boolean true
```

If the value cannot be converted, B# raises a helpful error.

---

## 4. Types

B# has four primitive types:

| Type | Example values |
|---|---|
| `integer` | `0`, `42`, `-7` |
| `float` | `3.14`, `0.5`, `-1.0` |
| `string` | `"hello"`, `"B#"` |
| `boolean` | `true`, `false` |

You do not need to declare a type — B# infers it from the value. Types matter when you use `as integer` in `ask`, or when you want explicit coercion with `let x be integer ...`.

---

## 5. Arithmetic

Use plain English words for all arithmetic operations.

```bsharp
let a be 10
let b be 3

say a plus b        note 13
say a minus b       note 7
say a times b       note 30
say a divided by b  note 3
say a modulo b      note 1
```

String concatenation uses `plus` too:

```bsharp
let full be "Hello" plus " " plus "World"
say full
```

---

## 6. Input

Use `ask` to read input from the user and store it in a variable.

```bsharp
ask "What is your name?" and store in name
say "Nice to meet you,", name
```

### Typed input

Add `as <type>` to automatically parse and validate the input.

```bsharp
ask "Enter your age:" as integer and store in age
ask "Enter a price:" as float and store in price
ask "Continue? (true/false):" as boolean and store in confirmed
```

If the user types something that cannot be converted, B# raises an error with a clear message.

---

## 7. Conditions

```bsharp
let score be 85

if score is at least 90 then
    say "Grade: A"
else if score is at least 80 then
    say "Grade: B"
else if score is at least 70 then
    say "Grade: C"
else
    say "Grade: F"
end
```

### Comparison operators

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

### Logical operators

```bsharp
if age is at least 18 and age is at most 65 then
    say "Working age"
end

if name is equal to "admin" or name is equal to "root" then
    say "Privileged user"
end

if not active then
    say "Inactive"
end
```

### Checking membership

```bsharp
let fruits be list of "apple", "banana", "cherry"

if fruits does contain "banana" then
    say "Found it"
end

if fruits does not contain "mango" then
    say "Not in list"
end
```

---

## 8. Loops

### While loop

```bsharp
let count be 1

while count is at most 5 do
    say count
    change count to count plus 1
end
```

### For loop — range

```bsharp
for each n from 1 to 5 do
    say n
end
```

Both ends are inclusive, so this prints 1, 2, 3, 4, 5.

### For loop — iterate a list

```bsharp
let colors be list of "red", "green", "blue"

for each color in colors do
    say color
end
```

### Iterating a string character by character

```bsharp
let word be "hello"

for each letter in word do
    say letter
end
```

### Iterating a dictionary

```bsharp
let person be dictionary with
    name as "Alice"
    age as 30
end

for each key in person do
    say key
end
```

---

## 9. Functions

### Defining a function

```bsharp
define function greet with name do
    say "Hello,", name
end
```

### Calling a function

```bsharp
call greet with "Raunak"
```

### Functions with multiple parameters

```bsharp
define function add with a and b do
    return a plus b
end

let result be call add with 3 and 5
say result
```

### Functions with no parameters

```bsharp
define function show_banner do
    say "===================="
    say "  Welcome to B#"
    say "===================="
end

call show_banner
```

### Returning values

Use `return` to send a value back to the caller. Execution stops at `return`.

```bsharp
define function max_of with a and b do
    if a is greater than b then
        return a
    end
    return b
end

let biggest be call max_of with 10 and 7
say biggest
```

### Recursive functions

```bsharp
define function factorial with n do
    if n is at most 1 then
        return 1
    end
    return n times call factorial with n minus 1
end

say call factorial with 6
```

---

## 10. Lists

### Creating a list

```bsharp
let nums be list of 1, 2, 3, 4, 5
let names be list of "Alice", "Bob", "Carol"
let empty be list of
```

### Adding and removing items

```bsharp
let items be list of "a", "b"
add "c" to items
remove "a" from items
say items
```

> Note: `add` and `remove` mutate the list in place.

### Getting the length

```bsharp
let len be get length of nums
say len
```

### Joining a list into a string

```bsharp
let words be list of "one", "two", "three"
let sentence be join words with " "
say sentence
```

### Iterating

```bsharp
for each n in nums do
    say n times 2
end
```

---

## 11. Dictionaries

### Creating a dictionary

```bsharp
let user be dictionary with
    name as "Alice"
    age as 30
    active as true
end
```

### Accessing values

```bsharp
say user
```

### Iterating keys

```bsharp
for each key in user do
    say key
end
```

---

## 12. File I/O (built-in)

These are built-in statements, no `use` required.

### Reading a file

```bsharp
read from "data.txt" and store in content
say content
```

### Writing a file

```bsharp
let output be "Hello from B#"
write output to "result.txt"
```

> For more advanced file operations (`append`, `delete`, `size`, `read_lines`, `write_lines`) use the `files` library — see the Standard Library Docs.

---

## 13. Error Handling

### Try / catch

```bsharp
try
    let result be 10 divided by 0
catch err
    say "Caught an error:", err
end
```

The variable after `catch` (here `err`) holds the error message as a string, so you can inspect or display it.

### Nested try / catch

```bsharp
define function risky with x do
    if x is less than 0 then
        note error library needed for manual raises
        let bad be 1 divided by 0
    end
    return x times 2
end

try
    let val be call risky with 0 minus 5
    say val
catch err
    say "Something went wrong:", err
end
```

---

## 14. Using Standard Libraries

Import a library with `use` before calling any of its functions.

```bsharp
use math

let root be call math.sqrt with 144
say root

say math.PI
```

Module functions are called with `call <module>.<function> with <args>`. Module constants (like `math.PI`) are accessed as values without `call`.

### Multiple libraries

```bsharp
use math
use string
use random

let words be list of "hello", "world", "bsharp"
let chosen be call random.choice with words
let upper be call string.upper with chosen
say upper
```

---

## 15. The `explain` keyword

After any operation, type `explain` on its own line to get a plain-English description of what just happened. Useful for learning and debugging.

```bsharp
let x be 42
explain

add 10 to nums
explain

call greet with "Alice"
explain
```

---

## 16. Putting It All Together

Here is a complete program that uses variables, loops, functions, lists, error handling, and a library.

```bsharp
use math
use string

note === Fibonacci with square roots ===

define function fibonacci with n do
    if n is at most 1 then
        return n
    end
    return call fibonacci with n minus 1 plus call fibonacci with n minus 2
end

let results be list of

for each i from 0 to 10 do
    let fib be call fibonacci with i
    add fib to results
end

say "Fibonacci sequence:"
say results

note Find the square roots of even Fibonacci numbers
say "Square roots of even Fibonacci numbers:"

for each num in results do
    if num modulo 2 is equal to 0 then
        try
            let root be call math.sqrt with num
            say num, "→", root
        catch err
            say "Error computing root of", num
        end
    end
end

note Count how many were even
let count be 0
for each num in results do
    if num modulo 2 is equal to 0 then
        change count to count plus 1
    end
end

say "Even Fibonacci numbers found:", count
```

---

## Quick Reference Card

```
Variables       let x be 5
                change x to 10

Output          say "hello", x

Input           ask "prompt?" and store in x
                ask "prompt?" as integer and store in x

Conditions      if x is greater than 5 then ... else ... end

Loops           while x is less than 10 do ... end
                for each n from 1 to 10 do ... end
                for each item in list do ... end

Functions       define function name with a and b do ... end
                call name with a and b
                let r be call name with a and b
                return value

Lists           let nums be list of 1, 2, 3
                add 4 to nums
                remove 1 from nums
                get length of nums
                join nums with ", "

Dictionaries    let d be dictionary with key as val end

Files           read from "file.txt" and store in x
                write x to "file.txt"

Errors          try ... catch err ... end

Libraries       use math
                call math.sqrt with 16
                let pi be math.PI

Comments        note anything here

Debug           explain
```