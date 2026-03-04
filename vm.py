# B# Virtual Machine — executes bytecode Chunks produced by compiler.py
# Stack-based VM with environment frames for variable scoping.

import sys
import os as _os
from core      import BSharpError, BSharpReturn, ModuleObject
from bytecode  import Op
from interpreter import Runtime as _InterpRuntime, Env

# ── VM Frame 

class Frame:
    """A single call frame — one function invocation or the top-level program."""
    __slots__ = ('chunk', 'ip', 'env', 'stack')

    def __init__(self, chunk, env):
        self.chunk = chunk
        self.ip    = 0           # instruction pointer
        self.env   = env         # variable environment for this scope
        self.stack = []          # operand stack

    def push(self, v):  self.stack.append(v)
    def pop(self):      return self.stack.pop()
    def peek(self):     return self.stack[-1]
    def instr(self):    return self.chunk.instructions[self.ip]


# ── VM 

class VM:
    """
    B# stack-based virtual machine.

    Usage:
        vm = VM()
        vm.run(chunk)          # run a compiled Chunk
    """

    def __init__(self, trace=False, script_dir=None):
        self.trace      = trace
        self.script_dir = script_dir
        self.last_op    = None

        # Shared global environment (same across all frames at top level)
        self.globals    = Env()
        self.libs       = set()

        # Borrow all stdlib loaders from the interpreter's Runtime
        self._rt        = _InterpRuntime(script_dir=script_dir)
        self._rt.ge     = self.globals   # share the same global env
        self.stdlib     = self._rt.stdlib

        # Call stack of Frames
        self._frames    = []

        # Try/catch handler stack: list of (frame_index, catch_ip, err_var)
        self._try_stack = []

    # ── Public entry point 

    def run(self, chunk):
        """Run a top-level Chunk. Returns None."""
        frame = Frame(chunk, self.globals)
        self._frames.append(frame)
        self._execute()
        # Handle any open tkinter windows (same as interpreter)
        if self._rt._tk_windows:
            try:
                next(iter(self._rt._tk_windows.values()))['root'].mainloop()
            except Exception:
                pass

    # ── Main execution loop 

    def _execute(self):
        while self._frames:
            frame = self._frames[-1]

            if frame.ip >= len(frame.chunk):
                self._frames.pop()
                continue

            instr = frame.instr()
            op    = instr.op
            arg   = instr.arg
            ln    = instr.line

            if self.trace:
                print(f'  [vm {frame.ip:04d}] {op:<20} {repr(arg):<20}  stack={frame.stack}')

            frame.ip += 1

            try:
                # ── Stack 
                if op == Op.LOAD_CONST:
                    frame.push(arg)

                elif op == Op.LOAD_VAR:
                    frame.push(frame.env.get(arg, ln))

                elif op == Op.STORE_VAR:
                    v = frame.pop()
                    # Check for pending type coercion
                    coerce_type = None
                    if len(frame.stack) > 0:
                        pass   # coercion handled inline below
                    # Check if previous instruction set a coerce hint
                    # (compiler emits LOAD_CONST <type> then STORE_VAR '__coerce__' before STORE_VAR name)
                    coerce_type = frame.env.vars.pop('__coerce__', None)
                    if coerce_type:
                        v = self._coerce(v, coerce_type, ln)
                    frame.env.set(arg, v)
                    self.last_op = f'Created "{arg}" = {self._desc(v)}'

                elif op == Op.UPDATE_VAR:
                    v = frame.pop()
                    frame.env.update(arg, v, ln)
                    self.last_op = f'Changed "{arg}" → {self._desc(v)}'

                elif op == Op.POP:
                    frame.pop()

                elif op == Op.DUP:
                    frame.push(frame.peek())

                elif op == Op.NOP:
                    pass

                # ── Arithmetic 
                elif op == Op.ADD:
                    r = frame.pop(); l = frame.pop()
                    if isinstance(l, str) or isinstance(r, str):
                        frame.push(self._tostr(l) + self._tostr(r))
                    else:
                        frame.push(l + r)

                elif op == Op.SUB:
                    r = frame.pop(); l = frame.pop(); frame.push(l - r)

                elif op == Op.MUL:
                    r = frame.pop(); l = frame.pop(); frame.push(l * r)

                elif op == Op.DIV:
                    r = frame.pop(); l = frame.pop()
                    if r == 0: raise BSharpError('Cannot divide by zero.', ln)
                    res = l / r
                    frame.push(int(res) if isinstance(res, float) and res == int(res) else res)

                elif op == Op.MOD:
                    r = frame.pop(); l = frame.pop()
                    if r == 0: raise BSharpError('Cannot compute remainder when dividing by zero.', ln)
                    frame.push(l % r)

                # ── Comparison 
                elif op == Op.CMP_EQ:    r=frame.pop(); l=frame.pop(); frame.push(l == r)
                elif op == Op.CMP_NEQ:   r=frame.pop(); l=frame.pop(); frame.push(l != r)
                elif op == Op.CMP_GT:    r=frame.pop(); l=frame.pop(); frame.push(l > r)
                elif op == Op.CMP_LT:    r=frame.pop(); l=frame.pop(); frame.push(l < r)
                elif op == Op.CMP_GTE:   r=frame.pop(); l=frame.pop(); frame.push(l >= r)
                elif op == Op.CMP_LTE:   r=frame.pop(); l=frame.pop(); frame.push(l <= r)
                elif op == Op.CMP_IN:    r=frame.pop(); l=frame.pop(); frame.push(l in r)
                elif op == Op.CMP_NOTIN: r=frame.pop(); l=frame.pop(); frame.push(l not in r)

                # ── Logic 
                elif op == Op.NOT:
                    frame.push(not self._truthy(frame.pop()))

                elif op == Op.AND:
                    r = frame.pop(); l = frame.pop()
                    frame.push(self._truthy(l) and self._truthy(r))

                elif op == Op.OR:
                    r = frame.pop(); l = frame.pop()
                    frame.push(self._truthy(l) or self._truthy(r))

                # ── Jumps 
                elif op == Op.JUMP:
                    frame.ip = arg

                elif op == Op.JUMP_IF_FALSE:
                    v = frame.pop()
                    if not self._truthy(v):
                        frame.ip = arg

                elif op == Op.JUMP_IF_TRUE:
                    v = frame.pop()
                    if self._truthy(v):
                        frame.ip = arg
                    # leave v on stack (short-circuit result)
                    else:
                        frame.push(v)

                # ── I/O 
                elif op == Op.PRINT:
                    items = [frame.pop() for _ in range(arg)][::-1]
                    print(' '.join(self._tostr(i) for i in items))
                    self.last_op = f'Printed: {" ".join(self._tostr(i) for i in items)}'

                elif op == Op.INPUT:
                    prompt = frame.pop()
                    frame.push(input(self._tostr(prompt) + ' '))

                elif op == Op.INPUT_TYPED:
                    prompt = frame.pop()
                    raw    = input(self._tostr(prompt) + ' ')
                    frame.push(self._coerce(raw, arg, ln))

                # ── Functions 
                elif op == Op.MAKE_FUNC:
                    name, params, fn_chunk = arg
                    # Push the function dict — STORE_VAR (emitted by compiler) will store it
                    frame.push({
                        '__func__':  True,
                        '__vm__':    True,
                        'params':    params,
                        'chunk':     fn_chunk,
                        'closure':   frame.env,
                    })
                    self.last_op = f'Defined function "{name}"'

                elif op == Op.CALL_FUNC:
                    fname, nargs = arg
                    fn_args = [frame.pop() for _ in range(nargs)][::-1]
                    fn      = frame.env.get(fname, ln)
                    if not isinstance(fn, dict) or not fn.get('__func__'):
                        raise BSharpError(f'"{fname}" is not a function', ln)
                    if len(fn_args) != len(fn['params']):
                        raise BSharpError(
                            f'"{fname}" expects {len(fn["params"])} arg(s), got {len(fn_args)}', ln)
                    if fn.get('__vm__'):
                        fn_env = Env(fn['closure'])
                        for p, v in zip(fn['params'], fn_args):
                            fn_env.set(p, v)
                        self._frames.append(Frame(fn['chunk'], fn_env))
                        continue  # main loop takes over — RETURN pushes result to caller
                    else:
                        fn_env = Env(fn['cl'])
                        for p, v in zip(fn['params'], fn_args):
                            fn_env.set(p, v)
                        try:
                            self._rt.blk(fn['body'], fn_env)
                            frame.push(None)
                        except BSharpReturn as r:
                            frame.push(r.value)

                elif op == Op.CALL_MODULE:
                    mod_name, attr, nargs = arg
                    fn_args  = [frame.pop() for _ in range(nargs)][::-1]
                    mod      = frame.env.get(mod_name, ln)
                    if not isinstance(mod, ModuleObject):
                        raise BSharpError(
                            f'"{mod_name}" is not a module. Did you forget "use {mod_name}"?', ln)
                    if attr not in mod.exports:
                        raise BSharpError(f'Module "{mod_name}" has no member "{attr}"', ln)
                    fn = mod.exports[attr]
                    if not callable(fn):
                        raise BSharpError(
                            f'"{mod_name}.{attr}" is a value, not a function. '
                            f'Access it as: let x be {mod_name}.{attr}', ln)
                    try:
                        result = fn(*fn_args)
                        self.last_op = f'Called "{mod_name}.{attr}" → {self._desc(result)}'
                        frame.push(result)
                    except BSharpError:
                        raise
                    except TypeError as e:
                        raise BSharpError(
                            f'Wrong number of arguments for "{mod_name}.{attr}": {e}', ln)
                    except Exception as e:
                        raise BSharpError(str(e), ln)

                elif op == Op.RETURN:
                    ret_val = frame.pop()
                    self._frames.pop()
                    if self._frames:
                        self._frames[-1].push(ret_val)
                    # Don't return — let the main loop continue with caller frame

                # ── Collections 
                elif op == Op.BUILD_LIST:
                    items = [frame.pop() for _ in range(arg)][::-1]
                    frame.push(items)

                elif op == Op.BUILD_DICT:
                    pairs = {}
                    items = [frame.pop() for _ in range(arg * 2)][::-1]
                    for i in range(0, len(items), 2):
                        pairs[items[i]] = items[i+1]
                    frame.push(pairs)

                elif op == Op.GET_ATTR:
                    mod_name, attr = arg
                    mod = frame.env.get(mod_name, ln)
                    if not isinstance(mod, ModuleObject):
                        raise BSharpError(
                            f'Cannot access ".{attr}" — "{mod_name}" is not a module.', ln)
                    if attr not in mod.exports:
                        raise BSharpError(f'Module "{mod_name}" has no member "{attr}"', ln)
                    frame.push(mod.exports[attr])

                elif op == Op.GET_INDEX:
                    idx = frame.pop(); lst = frame.pop()
                    i   = int(idx)
                    if isinstance(lst, list):
                        if i < 0 or i >= len(lst):
                            raise BSharpError(
                                f'Index {i} out of range (length {len(lst)})', ln)
                        frame.push(lst[i])
                    elif isinstance(lst, str):
                        frame.push(lst[i])
                    elif isinstance(lst, dict):
                        frame.push(lst[idx])
                    else:
                        raise BSharpError(f'Cannot index {self._desc(lst)}', ln)

                elif op == Op.GET_LEN:
                    v = frame.pop()
                    if hasattr(v, '__len__'):
                        frame.push(len(v))
                    else:
                        raise BSharpError(f'Cannot get length of {self._desc(v)}', ln)

                elif op == Op.LIST_APPEND:
                    v   = frame.pop()
                    lst = frame.env.get(arg, ln)
                    if not isinstance(lst, list):
                        raise BSharpError(f'"{arg}" is not a list', ln)
                    lst.append(v)
                    self.last_op = f'Added {self._desc(v)} to "{arg}"'

                elif op == Op.LIST_REMOVE:
                    v   = frame.pop()
                    lst = frame.env.get(arg, ln)
                    if not isinstance(lst, list):
                        raise BSharpError(f'"{arg}" is not a list', ln)
                    if v not in lst:
                        raise BSharpError(
                            f'{self._desc(v)} not found in "{arg}"', ln)
                    lst.remove(v)
                    self.last_op = f'Removed {self._desc(v)} from "{arg}"'

                elif op == Op.JOIN_STR:
                    sep = frame.pop(); lst = frame.pop()
                    if not isinstance(lst, list):
                        raise BSharpError(
                            f'join needs a list, got {self._desc(lst)}', ln)
                    frame.push(self._tostr(sep).join(self._tostr(i) for i in lst))

                # ── Files 
                elif op == Op.READ_FILE:
                    fn = self._tostr(frame.pop())
                    try:
                        with open(fn, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except FileNotFoundError:
                        raise BSharpError(f'File "{fn}" not found', ln)
                    except PermissionError:
                        raise BSharpError(f'Permission denied: "{fn}"', ln)
                    frame.env.set(arg, content)
                    self.last_op = f'Read {len(content)} chars from "{fn}"'

                elif op == Op.WRITE_FILE:
                    fn = self._tostr(frame.pop())
                    v  = self._tostr(frame.pop())
                    with open(fn, 'w', encoding='utf-8') as f:
                        f.write(v)
                    self.last_op = f'Wrote {len(v)} chars to "{fn}"'

                # ── Libraries 
                elif op == Op.USE_LIB:
                    name = arg
                    if name not in self.libs:
                        if name in self.stdlib:
                            mod = self.stdlib[name]()
                        else:
                            mod = self._rt._load_package(name, ln)
                            if mod is None:
                                avail = ', '.join(f'"{m}"' for m in sorted(self.stdlib))
                                raise BSharpError(
                                    f'Unknown library "{name}". Not in stdlib and not installed.\n'
                                    f'  Try: bug install {name}', ln)
                        self.globals.set(name, mod)
                        self.libs.add(name)
                    self.last_op = f'Loaded library "{name}"'

                # ── Error handling 
                elif op == Op.TRY_START:
                    # arg = catch block IP
                    self._try_stack.append((len(self._frames) - 1, arg, None))

                elif op == Op.TRY_END:
                    if self._try_stack:
                        self._try_stack.pop()

                elif op == Op.CATCH:
                    # arg = err_var name — error already stored by exception handler
                    pass

                # ── Misc 
                elif op == Op.EXPLAIN:
                    print(f'[explain] {self.last_op or "No operation performed yet."}')

                elif op == Op.HALT:
                    self._frames.pop()
                    return

                else:
                    raise BSharpError(f'VM: unknown opcode "{op}"', ln)

            except BSharpError as e:
                if self._try_stack:
                    frame_idx, catch_ip, err_var = self._try_stack.pop()
                    # Unwind to the correct frame
                    while len(self._frames) - 1 > frame_idx:
                        self._frames.pop()
                    frame = self._frames[-1]
                    frame.ip = catch_ip + 1  # skip CATCH instruction, execute its body
                    # CATCH instruction stores err_var name — read it
                    catch_instr = frame.chunk.instructions[catch_ip]
                    if catch_instr.op == Op.CATCH:
                        frame.env.set(catch_instr.arg, e.bsharp_message)
                    frame.ip = catch_ip + 1
                else:
                    raise

    # ── Helpers 

    def _truthy(self, v):
        if v is None:             return False
        if isinstance(v, bool):   return v
        if isinstance(v, (int, float)): return v != 0
        if isinstance(v, (str, list, dict)): return len(v) > 0
        return True

    def _tostr(self, v):
        if v is None:             return ''
        if isinstance(v, bool):   return 'true' if v else 'false'
        if isinstance(v, float):  return str(int(v)) if v == int(v) else str(v)
        if isinstance(v, list):   return '[' + ', '.join(self._tostr(i) for i in v) + ']'
        if isinstance(v, ModuleObject): return f'<module:{v.name}>'
        if isinstance(v, dict) and not v.get('__func__'):
            return '{' + ', '.join(f'{k}: {self._tostr(val)}' for k, val in v.items()) + '}'
        return str(v)

    def _desc(self, v):
        if v is None:             return 'nothing'
        if isinstance(v, bool):   return f'boolean {"true" if v else "false"}'
        if isinstance(v, int):    return f'integer {v}'
        if isinstance(v, float):  return f'decimal {v}'
        if isinstance(v, str):    return f'text "{v}"'
        if isinstance(v, list):   return f'list({len(v)} items)'
        if isinstance(v, ModuleObject): return f'module "{v.name}"'
        if isinstance(v, dict):   return 'a function' if v.get('__func__') else f'dictionary({len(v)} keys)'
        return str(type(v).__name__)

    def _coerce(self, v, th, ln):
        if not th or th in ('list', 'dict'): return v
        if th == 'integer':
            try:    return int(v)
            except: raise BSharpError(f'Cannot convert {self._desc(v)} to integer', ln)
        if th == 'float':
            try:    return float(v)
            except: raise BSharpError(f'Cannot convert {self._desc(v)} to float', ln)
        if th == 'string':  return self._tostr(v)
        if th == 'boolean':
            if isinstance(v, bool): return v
            if str(v).lower() in ('true', 'yes', '1'):  return True
            if str(v).lower() in ('false', 'no', '0'): return False
            raise BSharpError(f'Cannot convert {self._desc(v)} to boolean', ln)
        return v


# ── Convenience function 

def run_chunk(chunk, trace=False, script_dir=None):
    """Run a compiled Chunk in the VM."""
    VM(trace=trace, script_dir=script_dir).run(chunk)