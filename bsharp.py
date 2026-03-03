import sys, re
import math    as _math
import random  as _random
import json    as _json
import os      as _os
import time    as _time

# ── Core exceptions ───────────────────────────────────────────────────────────

class BSharpError(Exception):
    def __init__(self, msg, line=0):
        self.bsharp_message = msg; self.line = line; super().__init__(msg)
    def friendly(self):
        return f"Error{f' (line {self.line})' if self.line else ''}: {self.bsharp_message}"

class BSharpReturn(Exception):
    def __init__(self, v): self.value = v

class ModuleObject:
    def __init__(self, name, exports):
        self.name = name; self.exports = exports

KEYWORDS = {
    'let','be','change','to','say','ask','and','store','in','as','if','then','else','end',
    'while','do','for','each','from','define','function','with','return','call','list','of',
    'dictionary','try','catch','use','library','note','not','or','integer','float','boolean',
    'string','true','false','read','write','explain','plus','minus','times','divided','by',
    'modulo','is','equal','greater','less','than','at','least','most','does','contain',
    'contains','the'
}
MODULE_KEYWORDS = {'string', 'list'}

def lex(source):
    tokens = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if line.lstrip().startswith('note'): continue
        pos = 0
        while pos < len(line):
            if line[pos] in ' \t': pos += 1; continue
            if line[pos] == '"':
                end = line.find('"', pos+1)
                if end == -1: raise BSharpError(f'Unclosed string at column {pos+1}', lineno)
                tokens.append(('STRING', line[pos+1:end], lineno)); pos = end+1; continue
            m = re.match(r'\d+\.\d+', line[pos:])
            if m: tokens.append(('FLOAT', float(m.group()), lineno)); pos += len(m.group()); continue
            m = re.match(r'\d+', line[pos:])
            if m: tokens.append(('INTEGER', int(m.group()), lineno)); pos += len(m.group()); continue
            if line[pos] == '[': tokens.append(('LBRACKET','[',lineno)); pos+=1; continue
            if line[pos] == ']': tokens.append(('RBRACKET',']',lineno)); pos+=1; continue
            if line[pos] == ',': tokens.append(('COMMA',',',lineno)); pos+=1; continue
            if line[pos] == '.': tokens.append(('DOT','.',lineno)); pos+=1; continue
            m = re.match(r'[A-Za-z_][A-Za-z0-9_]*', line[pos:])
            if m:
                w = m.group(); lw = w.lower()
                tokens.append(('KEYWORD' if lw in KEYWORDS else 'IDENTIFIER',
                                lw if lw in KEYWORDS else w, lineno))
                pos += len(w); continue
            raise BSharpError(f'Unknown character "{line[pos]}" at column {pos+1}', lineno)
    tokens.append(('EOF', None, 0))
    return tokens

class Parser:
    def __init__(self, tokens): self.t = tokens; self.pos = 0
    def cur(self):   return self.t[min(self.pos, len(self.t)-1)]
    def peek(self):  return self.t[min(self.pos+1, len(self.t)-1)]
    def adv(self):
        t = self.t[self.pos]
        if self.pos < len(self.t)-1: self.pos += 1
        return t
    def ln(self):       return self.cur()[2]
    def iskw(self, *w): return self.cur()[0]=='KEYWORD' and self.cur()[1] in w
    def exkw(self, *w):
        t = self.cur()
        if t[0]=='KEYWORD' and t[1] in w: return self.adv()
        raise BSharpError(f'Expected "{" or ".join(w)}" but got "{t[1]}"', t[2])
    def exid(self):
        t = self.cur()
        if t[0]=='IDENTIFIER': self.adv(); return t[1]
        raise BSharpError(f'Expected a variable name but got "{t[1]}"', t[2])
    def nd(self, k, ln=None, **kw): return {'kind':k,'line':ln if ln is not None else self.ln(),**kw}

    def parse(self):
        s = []
        while self.cur()[0] != 'EOF':
            st = self.stmt()
            if st: s.append(st)
        return self.nd('Program', 0, statements=s)

    def block(self, stop=('end',)):
        s = []
        while self.cur()[0] != 'EOF':
            if self.cur()[0]=='KEYWORD' and self.cur()[1] in stop: break
            st = self.stmt()
            if st: s.append(st)
        return s

    def stmt(self):
        t = self.cur(); ln = t[2]
        if t[0]=='EOF': return None
        if t[0]=='IDENTIFIER':
            if t[1]=='add':    return self.p_add()
            if t[1]=='remove': return self.p_remove()
            if t[1]=='get':    return self.p_get()
            if t[1]=='join':   return self.p_join()
        if t[0]=='KEYWORD':
            k = t[1]
            if k=='let':     return self.p_let()
            if k=='change':  return self.p_change()
            if k=='say':     return self.p_say()
            if k=='ask':     return self.p_ask()
            if k=='if':      return self.p_if()
            if k=='while':   return self.p_while()
            if k=='for':     return self.p_for()
            if k=='define':  return self.p_def()
            if k=='return':  return self.p_return()
            if k=='call':    return self.nd('CallStmt', ln, call=self.p_callexpr())
            if k=='try':     return self.p_try()
            if k=='use':     return self.p_use()
            if k=='read':    return self.p_read()
            if k=='write':   return self.p_write()
            if k=='explain': self.adv(); return self.nd('Explain', ln)
        raise BSharpError(f'Did not understand line starting with "{t[1]}"', ln)

    def p_let(self):
        ln=self.ln(); self.exkw('let'); name=self.exid(); self.exkw('be')
        th=None
        if self.iskw('integer','float','boolean','string'): th=self.adv()[1]
        if self.iskw('list'):
            self.adv(); self.exkw('of')
            return self.nd('Let',ln,name=name,th='list',value=self.nd('LL',ln,items=self.p_csv()))
        if self.iskw('dictionary'):
            self.adv(); self.exkw('with'); pairs=[]
            while not self.iskw('end') and self.cur()[0]!='EOF':
                key=self.exid(); self.exkw('as'); val=self.p_expr(); pairs.append((key,val))
            self.exkw('end')
            return self.nd('Let',ln,name=name,th='dict',value=self.nd('DL',ln,pairs=pairs))
        if self.iskw('call'):  return self.nd('Let',ln,name=name,th=th,value=self.p_callexpr())
        if self.cur()[0]=='IDENTIFIER' and self.cur()[1]=='get':
            return self.nd('Let',ln,name=name,th=th,value=self.p_get())
        if self.cur()[0]=='IDENTIFIER' and self.cur()[1]=='join':
            return self.nd('Let',ln,name=name,th=th,value=self.p_join())
        return self.nd('Let',ln,name=name,th=th,value=self.p_expr())

    def p_change(self):
        ln=self.ln(); self.exkw('change'); name=self.exid(); self.exkw('to')
        if self.iskw('call'):  return self.nd('Change',ln,name=name,value=self.p_callexpr())
        if self.cur()[0]=='IDENTIFIER' and self.cur()[1]=='get':
            return self.nd('Change',ln,name=name,value=self.p_get())
        if self.cur()[0]=='IDENTIFIER' and self.cur()[1]=='join':
            return self.nd('Change',ln,name=name,value=self.p_join())
        return self.nd('Change',ln,name=name,value=self.p_expr())

    def p_say(self):
        ln=self.ln(); self.exkw('say')
        return self.nd('Say',ln,items=self.p_csv())

    def p_ask(self):
        ln=self.ln(); self.exkw('ask'); prompt=self.p_primary(); th=None
        if self.iskw('as'):
            self.adv()
            if self.iskw('integer','float','boolean','string'): th=self.adv()[1]
        self.exkw('and'); self.exkw('store'); self.exkw('in')
        return self.nd('Ask',ln,prompt=prompt,th=th,variable=self.exid())

    def p_if(self):
        ln=self.ln(); self.exkw('if'); cond=self.p_cond(); self.exkw('then')
        body=self.block(('end','else')); elseifs=[]; else_body=None
        while self.iskw('else'):
            self.adv()
            if self.iskw('if'):
                self.adv(); ec=self.p_cond(); self.exkw('then')
                elseifs.append((ec, self.block(('end','else'))))
            else: else_body=self.block(('end',)); break
        self.exkw('end')
        return self.nd('If',ln,cond=cond,body=body,elseifs=elseifs,else_body=else_body)

    def p_while(self):
        ln=self.ln(); self.exkw('while'); cond=self.p_cond(); self.exkw('do')
        body=self.block(); self.exkw('end')
        return self.nd('While',ln,cond=cond,body=body)

    def p_for(self):
        ln=self.ln(); self.exkw('for'); self.exkw('each'); var=self.exid()
        if self.iskw('from'):
            self.adv(); start=self.p_expr(); self.exkw('to'); end=self.p_expr()
            self.exkw('do'); body=self.block(); self.exkw('end')
            return self.nd('ForRange',ln,var=var,start=start,end=end,body=body)
        self.exkw('in'); it=self.p_expr(); self.exkw('do')
        body=self.block(); self.exkw('end')
        return self.nd('ForEach',ln,var=var,iterable=it,body=body)

    def p_def(self):
        ln=self.ln(); self.exkw('define'); self.exkw('function'); name=self.exid(); params=[]
        if self.iskw('with'):
            self.adv(); params.append(self.exid())
            while self.iskw('and'): self.adv(); params.append(self.exid())
        self.exkw('do'); body=self.block(); self.exkw('end')
        return self.nd('FuncDef',ln,name=name,params=params,body=body)

    def p_return(self):
        ln=self.ln(); self.exkw('return')
        if self.cur()[0]=='EOF': return self.nd('Return',ln,value=None)
        return self.nd('Return',ln,value=self.p_expr())

    def p_callexpr(self):
        ln=self.ln(); self.exkw('call')
        t = self.cur()
        if t[0]!='IDENTIFIER' and not (t[0]=='KEYWORD' and t[1] in MODULE_KEYWORDS):
            raise BSharpError(f'Expected function or module name after "call", got "{t[1]}"', ln)
        name = self.adv()[1]; attr = None
        if self.cur()[0]=='DOT':
            self.adv()
            at = self.cur()
            if at[0] not in ('IDENTIFIER','KEYWORD'):
                raise BSharpError(f'Expected attribute name after "." in call', ln)
            attr = self.adv()[1]
        args=[]
        if self.iskw('with'):
            self.adv(); args.append(self.p_expr())
            while self.iskw('and'): self.adv(); args.append(self.p_expr())
        if attr is not None:
            return self.nd('DottedCallExpr',ln,obj=name,attr=attr,args=args)
        return self.nd('CallExpr',ln,name=name,args=args)

    def p_try(self):
        ln=self.ln(); self.exkw('try'); tb=self.block(('catch',)); self.exkw('catch')
        ev=self.exid(); cb=self.block(); self.exkw('end')
        return self.nd('TryCatch',ln,try_body=tb,err_var=ev,catch_body=cb)

    def p_use(self):
        ln=self.ln(); self.exkw('use')
        if self.iskw('library'): self.adv()
        t = self.cur()
        if t[0]=='IDENTIFIER' or (t[0]=='KEYWORD' and t[1] in MODULE_KEYWORDS):
            name = self.adv()[1]
        else:
            raise BSharpError(f'Expected a library name but got "{t[1]}"', ln)
        return self.nd('UseLib',ln,name=name)

    def p_read(self):
        ln=self.ln(); self.exkw('read'); self.exkw('from'); fn=self.p_primary()
        self.exkw('and'); self.exkw('store'); self.exkw('in')
        return self.nd('ReadFile',ln,filename=fn,var=self.exid())

    def p_write(self):
        ln=self.ln(); self.exkw('write'); value=self.p_expr(); self.exkw('to')
        return self.nd('WriteFile',ln,value=value,filename=self.p_primary())

    def p_add(self):
        ln=self.ln(); self.adv(); value=self.p_expr(); self.exkw('to')
        return self.nd('AddList',ln,value=value,lst=self.exid())

    def p_remove(self):
        ln=self.ln(); self.adv(); value=self.p_expr(); self.exkw('from')
        return self.nd('RemList',ln,value=value,lst=self.exid())

    def p_get(self):
        ln=self.ln(); self.adv()
        if self.cur()[0]!='IDENTIFIER' or self.cur()[1]!='length':
            raise BSharpError('Expected "length" after "get"', ln)
        self.adv(); self.exkw('of')
        return self.nd('GetLen',ln,target=self.p_primary())

    def p_join(self):
        ln=self.ln(); self.adv(); target=self.p_primary(); self.exkw('with')
        return self.nd('JoinStr',ln,target=target,sep=self.p_primary())

    def p_csv(self):
        if self.cur()[0]=='EOF' or self.iskw('end','then','do','else'): return []
        items=[self.p_expr()]
        while self.cur()[0]=='COMMA': self.adv(); items.append(self.p_expr())
        return items

    def p_cond(self):
        left=self.p_cmp()
        while self.iskw('and','or'):
            op=self.adv()[1]; right=self.p_cmp()
            left=self.nd('Logic',left['line'],op=op,left=left,right=right)
        return left

    def p_cmp(self):
        ln=self.ln()
        if self.iskw('not'): self.adv(); return self.nd('NotOp',ln,operand=self.p_cmp())
        left=self.p_expr()
        if self.iskw('is'):
            self.adv()
            if self.iskw('not'):     self.adv(); self.exkw('equal'); self.exkw('to'); return self.nd('Cmp',ln,op='!=',left=left,right=self.p_expr())
            if self.iskw('equal'):   self.adv(); self.exkw('to');    return self.nd('Cmp',ln,op='==',left=left,right=self.p_expr())
            if self.iskw('greater'): self.adv(); self.exkw('than');  return self.nd('Cmp',ln,op='>',left=left,right=self.p_expr())
            if self.iskw('less'):    self.adv(); self.exkw('than');  return self.nd('Cmp',ln,op='<',left=left,right=self.p_expr())
            if self.iskw('at'):
                self.adv(); q=self.adv()[1]
                return self.nd('Cmp',ln,op='>=' if q=='least' else '<=',left=left,right=self.p_expr())
            raise BSharpError('After "is" expected: "equal to", "not equal to", "greater/less than", "at least/most"', ln)
        if self.iskw('does'):
            self.adv(); neg=self.iskw('not')
            if neg: self.adv()
            if self.iskw('contain','contains'):
                self.adv(); return self.nd('Cmp',ln,op='notin' if neg else 'in',left=left,right=self.p_expr())
        return left

    def p_expr(self):
        left=self.p_primary()
        while self.iskw('plus','minus','times','divided','modulo'):
            op=self.adv()[1]
            if op=='divided': self.exkw('by'); op='/'
            elif op=='times':  op='*'
            elif op=='plus':   op='+'
            elif op=='minus':  op='-'
            elif op=='modulo': op='%'
            left=self.nd('BinOp',left['line'],op=op,left=left,right=self.p_primary())
        return left

    def p_primary(self):
        t=self.cur(); ln=t[2]
        if t[0]=='INTEGER': self.adv(); return self.nd('Num',ln,value=t[1])
        if t[0]=='FLOAT':   self.adv(); return self.nd('Num',ln,value=t[1])
        if t[0]=='STRING':  self.adv(); return self.nd('Str',ln,value=t[1])
        if t[0]=='KEYWORD' and t[1]=='true':  self.adv(); return self.nd('Bool',ln,value=True)
        if t[0]=='KEYWORD' and t[1]=='false': self.adv(); return self.nd('Bool',ln,value=False)
        if t[0]=='LBRACKET':
            self.adv(); items=[]
            while self.cur()[0]!='RBRACKET' and self.cur()[0]!='EOF':
                items.append(self.p_expr())
                if self.cur()[0]=='COMMA': self.adv()
            if self.cur()[0]=='RBRACKET': self.adv()
            return self.nd('LL',ln,items=items)
        if t[0]=='KEYWORD' and t[1]=='call': return self.p_callexpr()
        if t[0]=='IDENTIFIER' and t[1]=='get':  return self.p_get()
        if t[0]=='IDENTIFIER' and t[1]=='join': return self.p_join()
        if t[0]=='KEYWORD' and t[1] in MODULE_KEYWORDS and self.peek()[0]=='DOT':
            self.adv(); node=self.nd('Var',ln,name=t[1]); self.adv()
            at=self.cur()
            if at[0] not in ('IDENTIFIER','KEYWORD'):
                raise BSharpError(f'Expected attribute name after "."', ln)
            return self.nd('AttrAccess',ln,obj=node,attr=self.adv()[1])
        if t[0]=='IDENTIFIER':
            self.adv(); node=self.nd('Var',ln,name=t[1])
            if self.cur()[0]=='DOT':
                self.adv(); at=self.cur()
                if at[0] not in ('IDENTIFIER','KEYWORD'):
                    raise BSharpError(f'Expected attribute name after "."', ln)
                node=self.nd('AttrAccess',ln,obj=node,attr=self.adv()[1])
            return node
        raise BSharpError(f'Expected a value but got "{t[1]}"', ln)


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

        BG = '#1e1e2e'; SURFACE = '#313244'; FG = '#cdd6f4'
        ACCENT = '#89b4fa'; FONT = ('Courier New',13); FONT_H = ('Courier New',10,'bold')

        def _open(title='B# Window'):
            title = str(title)
            if title in rt._tk_windows:
                rt._tk_active = title
                return None
            if not rt._tk_windows:
                root = tk.Tk()
            else:
                root = tk.Toplevel()
            root.title(title); root.geometry('720x460')
            root.configure(bg=BG); root.resizable(True, True)
            hdr = tk.Frame(root, bg=SURFACE, height=32); hdr.pack(fill='x', side='top')
            tk.Label(hdr, text=f'  ♯  {title}', bg=SURFACE, fg=ACCENT,
                     font=FONT_H, anchor='w').pack(side='left', padx=8, pady=6)
            cf = tk.Frame(root, bg=BG); cf.pack(fill='both', expand=True, padx=16, pady=16)
            tv = tk.StringVar(value='')
            tk.Label(cf, textvariable=tv, bg=BG, fg=FG, font=FONT,
                     wraplength=680, justify='left', anchor='nw').pack(fill='both', expand=True)
            rt._tk_windows[title] = {'root': root, 'tv': tv}
            rt._tk_active = title
            root.update()
            return None

        def _display(content):
            if rt._tk_active is None or rt._tk_active not in rt._tk_windows:
                raise BSharpError('window.display: no window is open — call window.open first')
            win = rt._tk_windows[rt._tk_active]
            win['tv'].set(rt.tostr(content))
            win['root'].update()
            return None

        def _exit_win():
            if rt._tk_active and rt._tk_active in rt._tk_windows:
                try: rt._tk_windows[rt._tk_active]['root'].destroy()
                except Exception: pass
                del rt._tk_windows[rt._tk_active]
                rt._tk_active = next(iter(rt._tk_windows), None)
            return None

        return ModuleObject('window', {'open':_open,'display':_display,'exit':_exit_win})

VERSION = "1.1.1-beta"

HELP = """
B# (B-sharp) Programming Language  v{version}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage:
  bsharp run <file.bsharp> [flags]   Run a B# program
  bsharp test [folder]               Run all tests in tests/cases/
  bsharp version                     Show version info
  bsharp help                        Show this help

Flags:
  --trace     Print every statement as it executes
  --debug     Alias for --trace
  --explain   (reserved for future use)

Standard Libraries  (use <n> to import):
  io      print(v)  input(prompt)  read_file(path)  write_file(path, content)
  math    sqrt  pow  abs  min  max  random  floor  ceil   +PI +E
  string  length  upper  lower  trim  split  join  replace  contains
  list    length  append  pop  get  set  slice  reverse  sort
  time    now()  sleep(s)  format(timestamp)
  system  exit(code)  args()
  random  int(min,max)  float()  choice(list)
  json    parse(str)  stringify(value)
  os      cwd()  listdir(path)  mkdir(path)
  error   raise(message)  try(fn)
  files   exists(path)  append(path,content)  delete(path)
          size(path)  read_lines(path)  write_lines(path,lines)
  window  open(title?)  display(content)  exit()
""".format(version=VERSION)


def _run_file(fname, trace=False):
    """Load and execute a single .bsharp file. Returns True on success."""
    try:
        with open(fname, 'r', encoding='utf-8') as f: source = f.read()
    except FileNotFoundError:
        print(f'Error: File "{fname}" not found.'); return False
    sl = source.splitlines()
    if trace: print(f'[trace] Running "{fname}" — {len(sl)} lines\n{"─"*50}')
    try:
        tokens = lex(source)
        prog   = Parser(tokens).parse()
        script_dir=_os.path.dirname(_os.path.abspath(fname))
        Runtime(trace=trace, src=sl, script_dir=script_dir).run(prog)
        return True
    except BSharpError as e:
        print(f'\n{"━"*50}\n{e.friendly()}\n{"━"*50}'); return False
    except KeyboardInterrupt:
        print('\n[stopped]'); return False


def cmd_run(argv):
    """bsharp run <file> [--trace] [--debug]"""
    files = [a for a in argv if not a.startswith('--')]
    flags = [a for a in argv if a.startswith('--')]
    trace = '--trace' in flags or '--debug' in flags
    if not files:
        print('Usage: bsharp run <file.bsharp> [--trace|--debug]')
        sys.exit(1)
    ok = _run_file(files[0], trace=trace)
    sys.exit(0 if ok else 1)


def cmd_test(argv):
    """bsharp test [folder] [--trace|--debug]"""
    import glob, io as _io

    flags      = [a for a in argv if a.startswith('--')]
    positional = [a for a in argv if not a.startswith('--')]
    trace      = '--trace' in flags or '--debug' in flags

    if positional:
        test_root = positional[0]
    else:
        script_dir = _os.path.dirname(_os.path.abspath(__file__))
        test_root  = _os.path.join(script_dir, 'tests')

    cases_dir    = _os.path.join(test_root, 'cases')
    expected_dir = _os.path.join(test_root, 'expected')

    if not _os.path.isdir(cases_dir):
        print(f'Error: No "cases" folder found inside "{test_root}".')
        print( '  Expected layout:  tests/cases/*.bsharp  +  tests/expected/*.txt')
        sys.exit(1)

    case_files = sorted(glob.glob(_os.path.join(cases_dir, '*.bsharp')))
    if not case_files:
        print(f'No .bsharp test files found in "{cases_dir}".'); sys.exit(0)

    passed = failed = 0
    bar = '─' * 50
    print(f'\nB# Test Runner  v{VERSION}\n{bar}')

    for path in case_files:
        name     = _os.path.splitext(_os.path.basename(path))[0]
        exp_path = _os.path.join(expected_dir, name + '.txt')

        # Capture stdout
        buf = _io.StringIO(); old_out = sys.stdout; sys.stdout = buf
        error_msg = None
        try:
            with open(path, 'r', encoding='utf-8') as f: source = f.read()
            sl = source.splitlines()
            Runtime(trace=trace, src=sl).run(Parser(lex(source)).parse())
        except BSharpError as e:
            error_msg = e.friendly()
            buf.write('\n' + '━'*50 + '\n' + error_msg + '\n' + '━'*50)
        except Exception as e:
            error_msg = str(e)
        finally:
            sys.stdout = old_out

        got = buf.getvalue().strip()

        if _os.path.isfile(exp_path):
            with open(exp_path, 'r', encoding='utf-8') as f:
                expected = f.read().strip().replace('\r\n', '\n')
            if got.replace('\r\n', '\n') == expected:
                print(f'  PASS  {name}'); passed += 1
            else:
                print(f'  FAIL  {name}')
                el = expected.splitlines(); gl = got.splitlines()
                for i, (e_ln, g_ln) in enumerate(zip(el, gl), 1):
                    if e_ln != g_ln:
                        print(f'         line {i}  expected: {e_ln!r}')
                        print(f'                  got:      {g_ln!r}')
                        break
                else:
                    if len(el) != len(gl):
                        print(f'         expected {len(el)} lines, got {len(gl)}')
                failed += 1
        else:
            if error_msg is None:
                print(f'  PASS  {name}  (no expected file — ran clean)'); passed += 1
            else:
                print(f'  FAIL  {name}  — {error_msg}'); failed += 1

    print(f'{bar}\n  Passed: {passed}   Failed: {failed}   Total: {passed+failed}\n{bar}\n')
    sys.exit(0 if failed == 0 else 1)


def cmd_version():
    """bsharp version"""
    print(f'B# (B-sharp) Programming Language')
    print(f'Version : {VERSION}')
    print(f'Runtime : Python {sys.version.split()[0]}')
    print(f'Platform: {sys.platform}')


def main():
    argv = sys.argv[1:]

    if not argv or argv[0] in ('help', '--help', '-h'):
        print(HELP); return

    cmd = argv[0]

    if cmd in ('version', '--version', '-v'):
        cmd_version(); return

    if cmd == 'run':
        cmd_run(argv[1:]); return

    if cmd == 'test':
        cmd_test(argv[1:]); return

    # Legacy fallback: python bsharp.py <file.bsharp> [--trace]
    if cmd.endswith('.bsharp') or _os.path.isfile(cmd):
        trace = '--trace' in argv or '--debug' in argv
        sys.exit(0 if _run_file(cmd, trace=trace) else 1)
        return

    print(f'Unknown command "{cmd}". Run "bsharp help" for usage.')
    sys.exit(1)


if __name__=='__main__': main()
# b# for beginners — a simple, readable, fun programming language
# b# is fun HEHEHE