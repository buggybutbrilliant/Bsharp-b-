# B# Interpreter — tree-walking execution engine
import sys
import math    as _math
import random  as _random
import json    as _json
import os      as _os
import time    as _time
from core import BSharpError, BSharpReturn, ModuleObject

class Env:
    def __init__(self, parent=None): self.vars={}; self.parent=parent
    def get(self, name, line=0):
        if name in self.vars: return self.vars[name]
        if self.parent: return self.parent.get(name, line)
        raise BSharpError(f'Variable "{name}" not found. Create it with "let {name} be ..."', line)
    def set(self, name, v): self.vars[name]=v
    def update(self, name, v, line=0):
        if name in self.vars: self.vars[name]=v; return
        if self.parent: self.parent.update(name,v,line); return
        raise BSharpError(f'Cannot change "{name}" — create it first with "let {name} be ..."', line)


class Runtime:
    def __init__(self, trace=False, src=None, script_dir=None):
        self.ge       = Env()
        self.libs     = set()
        self.trace    = trace
        self.src      = src or []
        self.last_op  = None
        self.script_dir = script_dir
        self._tk_windows = {}
        self._tk_active  = None
        self.stdlib   = {
            'io':     self._load_io,
            'math':   self._load_math,
            'string': self._load_string,
            'list':   self._load_list,
            'time':   self._load_time,
            'system': self._load_system,
            'random': self._load_random,
            'json':   self._load_json,
            'os':     self._load_os,
            'error':  self._load_error,
            'window': self._load_window,
            'files':  self._load_files,
        }

    def run(self, prog):
        self.blk(prog['statements'], self.ge)
        if self._tk_windows:
            try:
                next(iter(self._tk_windows.values()))['root'].mainloop()
            except Exception: pass

    def blk(self, ss, env):
        for s in ss:
            if s: self.ex(s, env)

    def ex(self, s, env):
        k=s['kind']; ln=s.get('line',0)
        if self.trace:
            src=self.src[ln-1].strip() if ln and ln<=len(self.src) else ''
            print(f'  [trace {ln:3d}] {src}')
        if k=='Let':
            v=self.ev(s['value'],env); v=self.coerce(v,s.get('th'),ln)
            env.set(s['name'],v); self.last_op=f'Created "{s["name"]}" = {self.desc(v)}'
        elif k=='Change':
            v=self.ev(s['value'],env); env.update(s['name'],v,ln)
            self.last_op=f'Changed "{s["name"]}" → {self.desc(v)}'
        elif k=='Say':
            out=' '.join(self.tostr(self.ev(i,env)) for i in s['items'])
            print(out); self.last_op=f'Printed: {out}'
        elif k=='Ask':
            pr=self.tostr(self.ev(s['prompt'],env)); raw=input(pr+' ')
            th=s.get('th')
            if th=='integer':
                try: raw=int(raw)
                except: raise BSharpError(f'Expected integer, got "{raw}"', ln)
            elif th=='float':
                try: raw=float(raw)
                except: raise BSharpError(f'Expected number, got "{raw}"', ln)
            elif th=='boolean':
                if raw.lower() in ('true','yes','1'): raw=True
                elif raw.lower() in ('false','no','0'): raw=False
                else: raise BSharpError(f'Expected true/false, got "{raw}"', ln)
            env.set(s['variable'],raw); self.last_op=f'Read input → "{s["variable"]}"'
        elif k=='If':
            if self.truthy(self.ev(s['cond'],env)): self.blk(s['body'],Env(env)); return
            for ec,eb in s.get('elseifs',[]):
                if self.truthy(self.ev(ec,env)): self.blk(eb,Env(env)); return
            if s.get('else_body'): self.blk(s['else_body'],Env(env))
        elif k=='While':
            i=0
            while self.truthy(self.ev(s['cond'],env)):
                self.blk(s['body'],Env(env)); i+=1
                if i>100000: raise BSharpError('Loop ran over 100,000 times — possible infinite loop.', ln)
        elif k=='ForRange':
            for i in range(int(self.ev(s['start'],env)), int(self.ev(s['end'],env))+1):
                c=Env(env); c.set(s['var'],i); self.blk(s['body'],c)
        elif k=='ForEach':
            it=self.ev(s['iterable'],env)
            if isinstance(it,list): items=it
            elif isinstance(it,dict): items=list(it.keys())
            elif isinstance(it,str): items=list(it)
            else: raise BSharpError(f'Cannot iterate {self.desc(it)}',ln)
            for item in items:
                c=Env(env); c.set(s['var'],item); self.blk(s['body'],c)
        elif k=='FuncDef':
            env.set(s['name'],{'__func__':True,'params':s['params'],'body':s['body'],'cl':env})
            self.last_op=f'Defined function "{s["name"]}"'
        elif k=='Return': raise BSharpReturn(self.ev(s['value'],env) if s.get('value') else None)
        elif k=='CallStmt': self.ev(s['call'],env)
        elif k=='TryCatch':
            try: self.blk(s['try_body'],Env(env))
            except BSharpError as e:
                ce=Env(env); ce.set(s['err_var'],e.bsharp_message); self.blk(s['catch_body'],ce)
        elif k=='UseLib':
            name=s['name']
            if name not in self.stdlib:
                mod = self._load_package(name, ln)
                if mod is None:
                    avail=', '.join(f'"{m}"' for m in sorted(self.stdlib))
                    raise BSharpError(
                        f'Unknown library "{name}". Not in stdlib and not installed.\n'
                        f'  Try: bug install {name}', ln)
                if name not in self.libs:
                    self.ge.set(name, mod); self.libs.add(name)
            elif name not in self.libs:
                mod=self.stdlib[name](); self.ge.set(name,mod); self.libs.add(name)
            self.last_op=f'Loaded library "{name}"'
        elif k=='AddList':
            v=self.ev(s['value'],env); lst=env.get(s['lst'],ln)
            if not isinstance(lst,list): raise BSharpError(f'"{s["lst"]}" is not a list',ln)
            lst.append(v); self.last_op=f'Added {self.desc(v)} to "{s["lst"]}"'
        elif k=='RemList':
            v=self.ev(s['value'],env); lst=env.get(s['lst'],ln)
            if not isinstance(lst,list): raise BSharpError(f'"{s["lst"]}" is not a list',ln)
            if v not in lst: raise BSharpError(f'{self.desc(v)} not found in "{s["lst"]}"',ln)
            lst.remove(v); self.last_op=f'Removed {self.desc(v)} from "{s["lst"]}"'
        elif k=='ReadFile':
            fn=self.tostr(self.ev(s['filename'],env))
            try:
                with open(fn,'r',encoding='utf-8') as f: content=f.read()
            except FileNotFoundError: raise BSharpError(f'File "{fn}" not found',ln)
            except PermissionError:   raise BSharpError(f'Permission denied: "{fn}"',ln)
            env.set(s['var'],content); self.last_op=f'Read {len(content)} chars from "{fn}"'
        elif k=='WriteFile':
            v=self.tostr(self.ev(s['value'],env)); fn=self.tostr(self.ev(s['filename'],env))
            with open(fn,'w',encoding='utf-8') as f: f.write(v)
            self.last_op=f'Wrote {len(v)} chars to "{fn}"'
        elif k=='Explain':
            print(f'[explain] {self.last_op or "No operation has been performed yet."}')
        else:
            raise BSharpError(f'Unknown statement: {k}', ln)

    def call(self, c, env):
        name=c['name']; ln=c.get('line',0)
        fn=env.get(name,ln)
        if not isinstance(fn,dict) or not fn.get('__func__'):
            raise BSharpError(f'"{name}" is not a function — define it with "define function {name} ..."', ln)
        args=[self.ev(a,env) for a in c['args']]
        if len(args)!=len(fn['params']):
            raise BSharpError(f'"{name}" expects {len(fn["params"])} arg(s), got {len(args)}', ln)
        ce=Env(fn['cl'])
        for p,v in zip(fn['params'],args): ce.set(p,v)
        try: self.blk(fn['body'],ce); return None
        except BSharpReturn as r:
            self.last_op=f'Called "{name}" → {self.desc(r.value)}'; return r.value

    def ev(self, x, env):
        if x is None: return None
        k=x['kind']; ln=x.get('line',0)
        if k=='Num':  return x['value']
        if k=='Str':  return x['value']
        if k=='Bool': return x['value']
        if k=='Var':  return env.get(x['name'],ln)
        if k=='LL':   return [self.ev(i,env) for i in x['items']]
        if k=='DL':   return {p[0]:self.ev(p[1],env) for p in x['pairs']}
        if k=='AttrAccess':
            obj=self.ev(x['obj'],env); self._chk_mod(obj,x['attr'],ln)
            attr=x['attr']
            if attr not in obj.exports: raise BSharpError(f'Module "{obj.name}" has no member "{attr}"',ln)
            return obj.exports[attr]
        if k=='DottedCallExpr':
            obj_val=env.get(x['obj'],ln); self._chk_mod(obj_val,x['attr'],ln,x['obj'])
            attr=x['attr']
            if attr not in obj_val.exports: raise BSharpError(f'Module "{obj_val.name}" has no member "{attr}"',ln)
            fn=obj_val.exports[attr]
            if not callable(fn):
                raise BSharpError(f'"{obj_val.name}.{attr}" is a constant, not a function. Access it as: let x be {obj_val.name}.{attr}',ln)
            args=[self.ev(a,env) for a in x['args']]
            try:
                result=fn(*args); self.last_op=f'Called "{x["obj"]}.{attr}" → {self.desc(result)}'; return result
            except BSharpError: raise
            except TypeError as e: raise BSharpError(f'Wrong number of arguments for "{obj_val.name}.{attr}": {e}',ln)
            except Exception as e: raise BSharpError(str(e),ln)
        if k=='BinOp':
            l=self.ev(x['left'],env); r=self.ev(x['right'],env); op=x['op']
            if op=='+': return (str(l)+str(r)) if isinstance(l,str) or isinstance(r,str) else l+r
            if op=='-': return l-r
            if op=='*': return l*r
            if op=='/':
                if r==0: raise BSharpError('Cannot divide by zero.',ln)
                res=l/r; return int(res) if isinstance(res,float) and res==int(res) else res
            if op=='%':
                if r==0: raise BSharpError('Cannot compute remainder when dividing by zero.',ln)
                return l%r
        if k=='Cmp':
            l=self.ev(x['left'],env); r=self.ev(x['right'],env); op=x['op']
            if op=='==': return l==r
            if op=='!=': return l!=r
            if op=='>':  return l>r
            if op=='<':  return l<r
            if op=='>=': return l>=r
            if op=='<=': return l<=r
            if op=='in': return l in r
            if op=='notin': return l not in r
        if k=='Logic':
            l=self.truthy(self.ev(x['left'],env))
            if x['op']=='and': return l and self.truthy(self.ev(x['right'],env))
            return l or self.truthy(self.ev(x['right'],env))
        if k=='NotOp': return not self.truthy(self.ev(x['operand'],env))
        if k=='GetLen':
            t=self.ev(x['target'],env)
            if hasattr(t,'__len__'): return len(t)
            raise BSharpError(f'Cannot get length of {self.desc(t)}',ln)
        if k=='JoinStr':
            t=self.ev(x['target'],env); sep=self.tostr(self.ev(x['sep'],env))
            if not isinstance(t,list): raise BSharpError(f'join needs a list, got {self.desc(t)}',ln)
            return sep.join(self.tostr(i) for i in t)
        if k=='CallExpr':
            r=self.call(x,env); self.last_op=f'Called "{x["name"]}" → {self.desc(r)}'; return r
        raise BSharpError(f'Unknown expression: {k}', ln)

    def _chk_mod(self, obj, attr, ln, obj_name=None):
        if not isinstance(obj, ModuleObject):
            hint = f' Did you forget "use {obj_name}"?' if obj_name else ''
            raise BSharpError(f'Cannot access ".{attr}" — {self.desc(obj)} is not a module.{hint}', ln)

    def coerce(self, v, th, ln):
        if not th or th in ('list','dict'): return v
        if th=='integer':
            try: return int(v)
            except: raise BSharpError(f'Cannot convert {self.desc(v)} to integer', ln)
        if th=='float':
            try: return float(v)
            except: raise BSharpError(f'Cannot convert {self.desc(v)} to float', ln)
        if th=='string': return self.tostr(v)
        if th=='boolean':
            if isinstance(v,bool): return v
            if str(v).lower() in ('true','yes','1'): return True
            if str(v).lower() in ('false','no','0'): return False
            raise BSharpError(f'Cannot convert {self.desc(v)} to boolean', ln)
        return v

    def truthy(self, v):
        if v is None: return False
        if isinstance(v,bool): return v
        if isinstance(v,(int,float)): return v!=0
        if isinstance(v,(str,list,dict)): return len(v)>0
        return True

    def tostr(self, v):
        if v is None: return ''
        if isinstance(v,bool): return 'true' if v else 'false'
        if isinstance(v,float): return str(int(v)) if v==int(v) else str(v)
        if isinstance(v,list): return '['+', '.join(self.tostr(i) for i in v)+']'
        if isinstance(v,ModuleObject): return f'<module:{v.name}>'
        if isinstance(v,dict) and not v.get('__func__'):
            return '{'+', '.join(f'{k}: {self.tostr(val)}' for k,val in v.items())+'}'
        return str(v)

    def desc(self, v):
        if v is None: return 'nothing'
        if isinstance(v,bool):  return f'boolean {"true" if v else "false"}'
        if isinstance(v,int):   return f'integer {v}'
        if isinstance(v,float): return f'decimal {v}'
        if isinstance(v,str):   return f'text "{v}"'
        if isinstance(v,list):  return f'list({len(v)} items)'
        if isinstance(v,ModuleObject): return f'module "{v.name}"'
        if isinstance(v,dict):  return 'a function' if v.get('__func__') else f'dictionary({len(v)} keys)'
        return str(type(v).__name__)

    # =========================================================================
    # Standard Library Loaders
    # =========================================================================

    def _load_io(self):
        rt = self
        def _print(value):
            print(rt.tostr(value)); return None
        def _input(prompt=''):
            return input(str(prompt)+(' ' if prompt else ''))
        def _read_file(path):
            try:
                with open(str(path),'r',encoding='utf-8') as f: return f.read()
            except FileNotFoundError: raise BSharpError(f'io.read_file: file "{path}" not found')
            except PermissionError:   raise BSharpError(f'io.read_file: permission denied for "{path}"')
        def _write_file(path, content):
            try:
                with open(str(path),'w',encoding='utf-8') as f: f.write(rt.tostr(content))
                return True
            except PermissionError: raise BSharpError(f'io.write_file: permission denied for "{path}"')
        return ModuleObject('io', {
            'print':      _print,
            'input':      _input,
            'read_file':  _read_file,
            'write_file': _write_file,
        })

    def _load_math(self):
        rt = self
        def _sqrt(x):
            if not isinstance(x,(int,float)): raise BSharpError(f'math.sqrt expects a number, got {rt.desc(x)}')
            if x < 0: raise BSharpError('math.sqrt: cannot take square root of a negative number')
            return _math.sqrt(x)
        return ModuleObject('math', {
            'PI':     _math.pi,
            'E':      _math.e,
            'sqrt':   _sqrt,
            'pow':    lambda base,exp: _math.pow(base,exp),
            'abs':    lambda x: abs(x),
            'min':    lambda a,b: min(a,b),
            'max':    lambda a,b: max(a,b),
            'random': lambda: _random.random(),
            'floor':  lambda x: _math.floor(x),
            'ceil':   lambda x: _math.ceil(x),
        })

    def _load_string(self):
        rt = self
        def chk(v, fn):
            if not isinstance(v,str): raise BSharpError(f'string.{fn} expects a string, got {rt.desc(v)}')
        def _length(s):           chk(s,'length');   return len(s)
        def _upper(s):            chk(s,'upper');     return s.upper()
        def _lower(s):            chk(s,'lower');     return s.lower()
        def _trim(s):             chk(s,'trim');      return s.strip()
        def _split(s, delim=''):  chk(s,'split');     return list(s) if delim=='' else s.split(str(delim))
        def _join(lst, delim=''):
            if not isinstance(lst,list): raise BSharpError(f'string.join expects a list, got {rt.desc(lst)}')
            return str(delim).join(rt.tostr(i) for i in lst)
        def _replace(s, old, new):chk(s,'replace');   return s.replace(str(old),str(new))
        def _contains(s, sub):    chk(s,'contains');  return str(sub) in s
        return ModuleObject('string', {
            'length':   _length,
            'upper':    _upper,
            'lower':    _lower,
            'trim':     _trim,
            'split':    _split,
            'join':     _join,
            'replace':  _replace,
            'contains': _contains,
        })

    def _load_list(self):
        rt = self
        def chk(v, fn):
            if not isinstance(v,list): raise BSharpError(f'list.{fn} expects a list, got {rt.desc(v)}')
        def _length(lst):    chk(lst,'length');  return len(lst)
        def _append(lst, v): chk(lst,'append');  return lst+[v]
        def _pop(lst):
            chk(lst,'pop')
            if not lst: raise BSharpError('list.pop: cannot pop from an empty list')
            return lst[:-1]
        def _get(lst, idx):
            chk(lst,'get'); i=int(idx)
            if i<0 or i>=len(lst): raise BSharpError(f'list.get: index {i} out of range (length {len(lst)})')
            return lst[i]
        def _set(lst, idx, val):
            chk(lst,'set'); i=int(idx)
            if i<0 or i>=len(lst): raise BSharpError(f'list.set: index {i} out of range (length {len(lst)})')
            r=lst[:]; r[i]=val; return r
        def _slice(lst, start, end): chk(lst,'slice'); return lst[int(start):int(end)]
        def _reverse(lst):           chk(lst,'reverse'); return lst[::-1]
        def _sort(lst):
            chk(lst,'sort')
            try: return sorted(lst)
            except TypeError: return sorted(lst, key=lambda x: rt.tostr(x))
        return ModuleObject('list', {
            'length':  _length,
            'append':  _append,
            'pop':     _pop,
            'get':     _get,
            'set':     _set,
            'slice':   _slice,
            'reverse': _reverse,
            'sort':    _sort,
        })

    def _load_time(self):
        import datetime as _dt
        def _now():    return int(_time.time())
        def _sleep(s): _time.sleep(float(s)); return None
        def _format(ts):
            try: return _dt.datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e: raise BSharpError(f'time.format: {e}')
        return ModuleObject('time', {'now':_now,'sleep':_sleep,'format':_format})

    def _load_system(self):
        def _exit(code=0): sys.exit(int(code))
        def _args():       return sys.argv[2:]
        return ModuleObject('system', {'exit':_exit,'args':_args})

    def _load_random(self):
        rt = self
        def _int(mn, mx): return _random.randint(int(mn),int(mx))
        def _float():     return _random.random()
        def _choice(lst):
            if not isinstance(lst,list): raise BSharpError(f'random.choice expects a list, got {rt.desc(lst)}')
            if not lst: raise BSharpError('random.choice: cannot choose from an empty list')
            return _random.choice(lst)
        return ModuleObject('random', {'int':_int,'float':_float,'choice':_choice})

    def _load_json(self):
        rt = self
        def _to_py(v):
            if v is None or isinstance(v,(bool,int,float,str)): return v
            if isinstance(v,list): return [_to_py(i) for i in v]
            if isinstance(v,dict):
                if v.get('__func__'): raise BSharpError('json.stringify: cannot serialise a function')
                return {str(k):_to_py(val) for k,val in v.items() if k!='__func__'}
            if isinstance(v,ModuleObject): raise BSharpError(f'json.stringify: cannot serialise {rt.desc(v)}')
            return str(v)
        def _parse(s):
            if not isinstance(s,str): raise BSharpError(f'json.parse expects a string, got {rt.desc(s)}')
            try: return _json.loads(s)
            except _json.JSONDecodeError as e: raise BSharpError(f'json.parse: invalid JSON — {e}')
        def _stringify(v):
            try: return _json.dumps(_to_py(v), ensure_ascii=False)
            except BSharpError: raise
            except Exception as e: raise BSharpError(f'json.stringify: {e}')
        return ModuleObject('json', {'parse':_parse,'stringify':_stringify})

    def _load_os(self):
        def _cwd(): return _os.getcwd()
        def _listdir(path='.'):
            try: return _os.listdir(str(path))
            except FileNotFoundError: raise BSharpError(f'os.listdir: path "{path}" not found')
            except PermissionError:   raise BSharpError(f'os.listdir: permission denied for "{path}"')
        def _mkdir(path):
            try: _os.makedirs(str(path),exist_ok=True); return True
            except PermissionError:   raise BSharpError(f'os.mkdir: permission denied for "{path}"')
            except Exception as e:    raise BSharpError(f'os.mkdir: {e}')
        return ModuleObject('os', {'cwd':_cwd,'listdir':_listdir,'mkdir':_mkdir})

    def _load_error(self):
        rt = self
        def _raise(message='An error occurred'): raise BSharpError(str(message))
        def _try(fn):
            if not isinstance(fn,dict) or not fn.get('__func__'):
                raise BSharpError('error.try expects a B# function as its argument')
            ce=Env(fn['cl'])
            try: rt.blk(fn['body'],ce); return ''
            except BSharpError as e: return e.bsharp_message
            except BSharpReturn:     return ''
        return ModuleObject('error', {'raise':_raise,'try':_try})

    def _load_files(self):
        rt = self
        def _exists(path):
            return _os.path.isfile(str(path))
        def _append(path, content):
            try:
                with open(str(path),'a',encoding='utf-8') as f:
                    f.write(rt.tostr(content))
                return True
            except PermissionError: raise BSharpError(f'files.append: permission denied for "{path}"')
            except Exception as e:  raise BSharpError(f'files.append: {e}')
        def _delete(path):
            p = str(path)
            if not _os.path.isfile(p):
                raise BSharpError(f'files.delete: file "{path}" not found')
            try: _os.remove(p); return True
            except PermissionError: raise BSharpError(f'files.delete: permission denied for "{path}"')
        def _size(path):
            p = str(path)
            if not _os.path.isfile(p):
                raise BSharpError(f'files.size: file "{path}" not found')
            return _os.path.getsize(p)
        def _read_lines(path):
            try:
                with open(str(path),'r',encoding='utf-8') as f:
                    return [line.rstrip('\n') for line in f.readlines()]
            except FileNotFoundError: raise BSharpError(f'files.read_lines: file "{path}" not found')
            except PermissionError:   raise BSharpError(f'files.read_lines: permission denied for "{path}"')
        def _write_lines(path, lines):
            if not isinstance(lines, list):
                raise BSharpError(f'files.write_lines: expected a list, got {rt.desc(lines)}')
            try:
                with open(str(path),'w',encoding='utf-8') as f:
                    f.write('\n'.join(rt.tostr(l) for l in lines))
                return True
            except PermissionError: raise BSharpError(f'files.write_lines: permission denied for "{path}"')
        return ModuleObject('files', {
            'exists':      _exists,
            'append':      _append,
            'delete':      _delete,
            'size':        _size,
            'read_lines':  _read_lines,
            'write_lines': _write_lines,
        })

    def _load_package(self, name, ln=0):
        """Try to load a community package from bsharp_packages/<n>/<n>.py"""
        import importlib.util as _ilu
        variants = [name, name.replace("_", "-")]
        script_dir = _os.path.dirname(_os.path.abspath(__file__))
        search_roots = list(dict.fromkeys([_os.getcwd(), self.script_dir or "", script_dir]))
        for root in search_roots:
            for folder in variants:
                pkg_file = _os.path.join(root, "bsharp_packages", folder, folder + ".py")
                if not _os.path.isfile(pkg_file):
                    pkg_file = _os.path.join(root, "bsharp_packages", folder, name + ".py")
                if _os.path.isfile(pkg_file):
                    try:
                        spec = _ilu.spec_from_file_location(f"bsharp_pkg_{name}", pkg_file)
                        mod_py = _ilu.module_from_spec(spec)
                        spec.loader.exec_module(mod_py)
                        if not hasattr(mod_py, "load"):
                            raise BSharpError('Package ' + name + ' missing load() in ' + pkg_file, ln)
                        result = mod_py.load()
                        if not (hasattr(result, "name") and hasattr(result, "exports") and isinstance(result.exports, dict)):
                            raise BSharpError('Package ' + name + ' load() must return ModuleObject', ln)
                        return ModuleObject(result.name, result.exports)
                    except BSharpError: raise
                    except Exception as e:
                        raise BSharpError('Load failed: ' + str(e), ln)
        return None

    def _load_window(self):
        rt = self
        try:
            import tkinter as tk
        except ImportError:
            raise BSharpError(
                'window library requires tkinter.\n'
                '  Linux: sudo apt-get install python3-tk\n'
                '  macOS: install Python from python.org')
        import time as _tm

        _state = {
            'root': None, 'canvas': None,
            'keys': set(), 'closed': False,
            'last_frame': 0.0,
        }

        def _open(title='B# Game'):
            if _state['root'] is not None: return None
            root = tk.Tk()
            root.title(str(title))
            root.resizable(True, True)
            root.geometry('800x600')
            canvas = tk.Canvas(root, width=800, height=600,
                               bg='black', highlightthickness=0)
            canvas.pack()
            def _kp(e): _state['keys'].add(e.keysym)
            def _kr(e): _state['keys'].discard(e.keysym)
            def _close():
                _state['closed'] = True
                try: root.destroy()
                except: pass
            root.bind('<KeyPress>',   _kp)
            root.bind('<KeyRelease>', _kr)
            root.protocol('WM_DELETE_WINDOW', _close)
            root.focus_force()
            _state['root'] = root; _state['canvas'] = canvas
            root.update()
            return None

        def _clear(color='black'):
            c = _state.get('canvas')
            if c is None: return None
            c.delete('all')
            c.configure(bg=str(color))
            return None

        def _rect(x, y, w, h, fill='white'):
            c = _state.get('canvas')
            if c is None: return None
            x,y,w,h = float(x),float(y),float(w),float(h)
            c.create_rectangle(x, y, x+w, y+h, fill=str(fill), outline='')
            return None

        def _oval(x, y, w, h, fill='white'):
            c = _state.get('canvas')
            if c is None: return None
            x,y,w,h = float(x),float(y),float(w),float(h)
            c.create_oval(x, y, x+w, y+h, fill=str(fill), outline='')
            return None

        def _text(x, y, msg, color='white', size=14):
            c = _state.get('canvas')
            if c is None: return None
            c.create_text(float(x), float(y), text=str(msg),
                          fill=str(color),
                          font=('Courier New', max(1,int(size)), 'bold'),
                          anchor='nw')
            return None

        def _line(x1, y1, x2, y2, color='white'):
            c = _state.get('canvas')
            if c is None: return None
            c.create_line(float(x1),float(y1),float(x2),float(y2),
                          fill=str(color), width=2)
            return None

        def _key_down(key):
            k = str(key)
            return (k in _state['keys'] or
                    k.lower() in _state['keys'] or
                    k.capitalize() in _state['keys'])

        def _update(fps=60):
            if _state['closed']: return False
            r = _state.get('root')
            if r is None: return False
            try: r.update()
            except Exception:
                _state['closed'] = True; return False
            now    = _tm.time()
            target = 1.0 / max(1, float(fps))
            diff   = now - _state['last_frame']
            if diff < target: _tm.sleep(target - diff)
            _state['last_frame'] = _tm.time()
            return not _state['closed']

        def _width():  return 800
        def _height(): return 600

        def _display(content):
            c = _state.get('canvas')
            if c is None: return None
            c.create_text(10, 10, text=str(content),
                          fill='#cdd6f4', font=('Courier New', 13), anchor='nw')
            r = _state.get('root')
            if r:
                try: r.update()
                except: pass
            return None

        def _exit_win():
            r = _state.get('root')
            if r:
                try: r.destroy()
                except: pass
            _state['closed'] = True
            _state['root'] = None; _state['canvas'] = None
            return None

        return ModuleObject('window', {
            'open':     _open,   'clear':    _clear,
            'rect':     _rect,   'oval':     _oval,
            'text':     _text,   'line':     _line,
            'key_down': _key_down, 'update': _update,
            'width':    _width,  'height':   _height,
            'display':  _display,'exit':     _exit_win,
        })