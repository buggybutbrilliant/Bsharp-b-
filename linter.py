# B# Linter / Static Analyzer
from core   import BSharpError
from lexer  import lex
from parser import Parser

class Level:
    ERROR   = 'error'
    WARNING = 'warning'
    INFO    = 'info'

class LintWarning:
    def __init__(self, level, code, message, line=0):
        self.level = level; self.code = code
        self.message = message; self.line = line
    def __str__(self):
        icon = {'error':'E','warning':'W','info':'I'}.get(self.level,'?')
        loc  = f'line {self.line}' if self.line else 'global'
        return f'  [{icon}] ({loc}) {self.code}: {self.message}'

class Scope:
    def __init__(self, parent=None, name='<global>'):
        self.parent=parent; self.name=name
        self.defined={}; self.used=set()
    def define(self, name, line): self.defined[name]=line
    def use(self, name):
        self.used.add(name)
        if self.parent: self.parent.use(name)
    def unused(self):
        return [(n,l) for n,l in self.defined.items() if n not in self.used]
    def is_defined(self, name):
        if name in self.defined: return True
        if self.parent: return self.parent.is_defined(name)
        return False
    def child(self, name='<block>'): return Scope(self, name)

class Linter:
    def __init__(self):
        self.warnings=[]; self._scope=Scope(); self._funcs={}; self._libs=set()

    def lint(self, ast):
        if ast['kind'] != 'Program': return []
        for s in ast['statements']:
            if s['kind'] == 'FuncDef':
                self._funcs[s['name']] = {'params':s['params'],'line':s.get('line',0)}
                self._scope.define(s['name'], s.get('line',0))
        for s in ast['statements']:
            self._stmt(s, self._scope)
        self._check_unused(self._scope)
        return self.warnings

    def _warn(self,level,code,msg,line=0): self.warnings.append(LintWarning(level,code,msg,line))
    def _err(self,code,msg,line=0):  self._warn(Level.ERROR,   code,msg,line)
    def _w(self,  code,msg,line=0):  self._warn(Level.WARNING,  code,msg,line)
    def _info(self,code,msg,line=0): self._warn(Level.INFO,     code,msg,line)

    def _check_unused(self, scope):
        for name,line in scope.unused():
            if not name.startswith('__'):
                self._w('W001', f'Variable "{name}" is defined but never used', line)

    def _stmt(self, s, scope):
        if s is None: return False
        k=s['kind']; ln=s.get('line',0)

        if k=='Let':
            self._expr(s['value'], scope); scope.define(s['name'], ln)
        elif k=='Change':
            if not scope.is_defined(s['name']):
                self._err('E001', f'Variable "{s["name"]}" used before being defined — create it with "let {s["name"]} be ..."', ln)
            self._expr(s['value'], scope); scope.use(s['name'])
        elif k=='Say':
            if not s['items']: self._info('I001', '"say" with no items — nothing will be printed', ln)
            for item in s['items']: self._expr(item, scope)
        elif k=='Ask':
            self._expr(s['prompt'], scope); scope.define(s['variable'], ln)
        elif k=='If':
            self._expr(s['cond'], scope)
            c=scope.child('if'); self._block(s['body'],c); self._check_unused(c)
            for ec,eb in s.get('elseifs',[]):
                self._expr(ec,scope); ec2=scope.child('elseif'); self._block(eb,ec2); self._check_unused(ec2)
            if s.get('else_body'):
                el=scope.child('else'); self._block(s['else_body'],el); self._check_unused(el)
        elif k=='While':
            self._check_infinite_loop(s,scope); self._expr(s['cond'],scope)
            c=scope.child('while'); self._block(s['body'],c); self._check_unused(c)
        elif k=='ForRange':
            self._expr(s['start'],scope); self._expr(s['end'],scope)
            c=scope.child('for'); c.define(s['var'],ln); self._block(s['body'],c); self._check_unused(c)
        elif k=='ForEach':
            self._expr(s['iterable'],scope)
            c=scope.child('foreach'); c.define(s['var'],ln); self._block(s['body'],c); self._check_unused(c)
        elif k=='FuncDef':
            fn=scope.child(s['name'])
            for p in s['params']: fn.define(p,ln)
            self._block(s['body'],fn); self._check_unused(fn)
        elif k=='Return':
            if s.get('value'): self._expr(s['value'],scope)
            return True
        elif k=='CallStmt':
            self._expr(s['call'],scope)
        elif k=='TryCatch':
            t=scope.child('try'); self._block(s['try_body'],t); self._check_unused(t)
            c=scope.child('catch'); c.define(s['err_var'],ln); self._block(s['catch_body'],c); self._check_unused(c)
        elif k=='UseLib':
            if s['name'] in self._libs: self._info('I002', f'Library "{s["name"]}" imported more than once', ln)
            self._libs.add(s['name']); scope.define(s['name'],ln); scope.use(s['name'])
        elif k=='AddList':
            self._expr(s['value'],scope)
            if not scope.is_defined(s['lst']): self._err('E001',f'List "{s["lst"]}" used before being defined',ln)
            else: scope.use(s['lst'])
        elif k=='RemList':
            self._expr(s['value'],scope)
            if not scope.is_defined(s['lst']): self._err('E001',f'List "{s["lst"]}" used before being defined',ln)
            else: scope.use(s['lst'])
        elif k=='ReadFile':
            self._expr(s['filename'],scope); scope.define(s['var'],ln)
        elif k=='WriteFile':
            self._expr(s['value'],scope); self._expr(s['filename'],scope)
        return False

    def _block(self, stmts, scope):
        returned=False
        for s in stmts:
            if returned:
                self._w('W003','Unreachable code after "return" statement',s.get('line',0)); break
            if self._stmt(s,scope) is True: returned=True

    def _check_infinite_loop(self,s,scope):
        ln=s.get('line',0); cond=s['cond']
        if cond.get('kind')=='Bool' and cond.get('value') is True:
            if not self._body_has_exit(s['body']):
                self._w('W004','Possible infinite loop — "while true" with no "return", "change", or call in body',ln)

    def _body_has_exit(self, stmts):
        for s in stmts:
            if s is None: continue
            k=s['kind']
            if k in ('Return','Change','CallStmt'): return True
            if k=='If' and self._body_has_exit(s['body']): return True
            if k in ('While','ForRange','ForEach') and self._body_has_exit(s.get('body',[])): return True
        return False

    def _expr(self, x, scope):
        if x is None: return
        k=x['kind']; ln=x.get('line',0)
        if k in ('Num','Str','Bool'): pass
        elif k=='Var':
            n=x['name']
            if not scope.is_defined(n): self._err('E001',f'Variable "{n}" used before being defined — create it with "let {n} be ..."',ln)
            else: scope.use(n)
        elif k=='LL':
            for item in x['items']: self._expr(item,scope)
        elif k=='DL':
            for _key,val in x['pairs']: self._expr(val,scope)
        elif k in ('BinOp','Cmp','Logic'):
            self._expr(x['left'],scope); self._expr(x['right'],scope)
        elif k=='NotOp':
            self._expr(x['operand'],scope)
        elif k=='GetLen':
            self._expr(x['target'],scope)
        elif k=='JoinStr':
            self._expr(x['target'],scope); self._expr(x['sep'],scope)
        elif k=='AttrAccess':
            obj_name=x['obj']['name']
            if not scope.is_defined(obj_name): self._err('E002',f'Module "{obj_name}" used before being loaded — add "use {obj_name}" at the top',ln)
            else: scope.use(obj_name)
        elif k=='CallExpr':
            n=x['name']
            if not scope.is_defined(n) and n not in self._funcs: self._err('E003',f'Function "{n}" called but never defined',ln)
            else: scope.use(n)
            if n in self._funcs:
                exp=len(self._funcs[n]['params']); got=len(x['args'])
                if got!=exp: self._err('E004',f'Function "{n}" expects {exp} argument(s), got {got}',ln)
            for arg in x['args']: self._expr(arg,scope)
        elif k=='DottedCallExpr':
            mod=x['obj']
            if not scope.is_defined(mod): self._err('E002',f'Module "{mod}" used before being loaded — add "use {mod}" at the top',ln)
            else: scope.use(mod)
            for arg in x['args']: self._expr(arg,scope)
        elif k=='GetIndex':
            self._expr(x['target'],scope); self._expr(x['index'],scope)

def lint_ast(ast):    return Linter().lint(ast)
def lint_source(src):
    try: return lint_ast(Parser(lex(src)).parse()), None
    except BSharpError as e: return [], e
def lint_file(path):
    try:
        with open(path,'r',encoding='utf-8') as f: src=f.read()
    except FileNotFoundError: return [], BSharpError(f'File "{path}" not found')
    return lint_source(src)