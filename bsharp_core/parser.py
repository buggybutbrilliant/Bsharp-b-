# B# Parser — builds AST from token stream
import re
from bsharp_core.core import BSharpError
from bsharp_core.lexer import MODULE_KEYWORDS

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