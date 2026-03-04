# B# Compiler — walks the AST and emits bytecode into a Chunk
# Input:  AST (dict) from parser.py
# Output: Chunk (from bytecode.py)

from bsharp_core.core import BSharpError
from bsharp_core.bytecode import Op, Chunk

class Compiler:
    def __init__(self):
        self.chunk   = Chunk('<main>')
        self._stack  = [self.chunk]   # chunk stack for nested functions

    # ── Public entry point ────────────────────────────────────────────────────

    def compile(self, ast):
        """Compile a Program AST node. Returns the top-level Chunk."""
        if ast['kind'] != 'Program':
            raise BSharpError('Compiler.compile() expects a Program node')
        for stmt in ast['statements']:
            self._stmt(stmt)
        self._emit(Op.HALT)
        return self.chunk

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def _cur(self):
        return self._stack[-1]

    def _emit(self, op, arg=None, line=0):
        return self._cur.emit(op, arg, line)

    def _here(self):
        """Index of the NEXT instruction to be emitted."""
        return len(self._cur.instructions)

    def _patch(self, idx, target):
        self._cur.patch(idx, target)

    # ── Statements ────────────────────────────────────────────────────────────

    def _stmt(self, s):
        k = s['kind']; ln = s.get('line', 0)

        if k == 'Let':
            self._expr(s['value'])
            if s.get('th'):
                self._emit(Op.LOAD_CONST, s['th'], ln)  # type hint for VM coerce
                self._emit(Op.STORE_VAR, '__coerce__', ln)
            self._emit(Op.STORE_VAR, s['name'], ln)

        elif k == 'Change':
            self._expr(s['value'])
            self._emit(Op.UPDATE_VAR, s['name'], ln)

        elif k == 'Say':
            for item in s['items']:
                self._expr(item)
            self._emit(Op.PRINT, len(s['items']), ln)

        elif k == 'Ask':
            self._expr(s['prompt'])
            th = s.get('th')
            if th:
                self._emit(Op.INPUT_TYPED, th, ln)
            else:
                self._emit(Op.INPUT, None, ln)
            self._emit(Op.STORE_VAR, s['variable'], ln)

        elif k == 'If':
            self._compile_if(s)

        elif k == 'While':
            self._compile_while(s)

        elif k == 'ForRange':
            self._compile_for_range(s)

        elif k == 'ForEach':
            self._compile_for_each(s)

        elif k == 'FuncDef':
            self._compile_funcdef(s)

        elif k == 'Return':
            if s.get('value'):
                self._expr(s['value'])
            else:
                self._emit(Op.LOAD_CONST, None, ln)
            self._emit(Op.RETURN, None, ln)

        elif k == 'CallStmt':
            self._expr(s['call'])
            self._emit(Op.POP, None, ln)   # discard return value

        elif k == 'TryCatch':
            self._compile_try(s)

        elif k == 'UseLib':
            self._emit(Op.USE_LIB, s['name'], ln)

        elif k == 'AddList':
            self._expr(s['value'])
            self._emit(Op.LIST_APPEND, s['lst'], ln)

        elif k == 'RemList':
            self._expr(s['value'])
            self._emit(Op.LIST_REMOVE, s['lst'], ln)

        elif k == 'ReadFile':
            self._expr(s['filename'])
            self._emit(Op.READ_FILE, s['var'], ln)

        elif k == 'WriteFile':
            self._expr(s['value'])
            self._expr(s['filename'])
            self._emit(Op.WRITE_FILE, None, ln)

        elif k == 'Explain':
            self._emit(Op.EXPLAIN, None, ln)

        else:
            raise BSharpError(f'Compiler: unknown statement kind "{k}"', ln)

    def _block(self, stmts):
        for s in stmts:
            self._stmt(s)

    # ── Control flow ──────────────────────────────────────────────────────────

    def _compile_if(self, s):
        ln = s.get('line', 0)

        # Compile condition
        self._cond(s['cond'])

        # JUMP_IF_FALSE past the body
        jf = self._emit(Op.JUMP_IF_FALSE, None, ln)

        # Body
        self._block(s['body'])

        # Handle elseifs + else
        elseifs   = s.get('elseifs', [])
        else_body = s.get('else_body')

        if elseifs or else_body:
            # Jump over else/elseif chain at end of body
            jump_ends = [self._emit(Op.JUMP, None, ln)]

            # Patch the JUMP_IF_FALSE to here
            self._patch(jf, self._here())

            for (ec, eb) in elseifs:
                self._cond(ec)
                jf2 = self._emit(Op.JUMP_IF_FALSE, None, ln)
                self._block(eb)
                jump_ends.append(self._emit(Op.JUMP, None, ln))
                self._patch(jf2, self._here())

            if else_body:
                self._block(else_body)

            end = self._here()
            for je in jump_ends:
                self._patch(je, end)
        else:
            self._patch(jf, self._here())

    def _compile_while(self, s):
        ln     = s.get('line', 0)
        loop_start = self._here()
        self._cond(s['cond'])
        jf = self._emit(Op.JUMP_IF_FALSE, None, ln)
        self._block(s['body'])
        self._emit(Op.JUMP, loop_start, ln)
        self._patch(jf, self._here())

    def _compile_for_range(self, s):
        ln = s.get('line', 0)
        # Store iterator variable = start
        self._expr(s['start'])
        self._emit(Op.STORE_VAR, s['var'], ln)

        loop_start = self._here()

        # Condition: var <= end
        self._emit(Op.LOAD_VAR, s['var'], ln)
        self._expr(s['end'])
        self._emit(Op.CMP_LTE, None, ln)
        jf = self._emit(Op.JUMP_IF_FALSE, None, ln)

        self._block(s['body'])

        # Increment: var = var + 1
        self._emit(Op.LOAD_VAR, s['var'], ln)
        self._emit(Op.LOAD_CONST, 1, ln)
        self._emit(Op.ADD, None, ln)
        self._emit(Op.UPDATE_VAR, s['var'], ln)

        self._emit(Op.JUMP, loop_start, ln)
        self._patch(jf, self._here())

    def _compile_for_each(self, s):
        ln = s.get('line', 0)
        # Build the iterable, store in a hidden var
        hidden_iter  = f'__iter_{s["var"]}__'
        hidden_index = f'__idx_{s["var"]}__'

        self._expr(s['iterable'])
        self._emit(Op.STORE_VAR, hidden_iter, ln)

        # index = 0
        self._emit(Op.LOAD_CONST, 0, ln)
        self._emit(Op.STORE_VAR, hidden_index, ln)

        loop_start = self._here()

        # Condition: index < len(iter)
        self._emit(Op.LOAD_VAR, hidden_index, ln)
        self._emit(Op.LOAD_VAR, hidden_iter, ln)
        self._emit(Op.GET_LEN, None, ln)
        self._emit(Op.CMP_LT, None, ln)
        jf = self._emit(Op.JUMP_IF_FALSE, None, ln)

        # var = iter[index]
        self._emit(Op.LOAD_VAR, hidden_iter, ln)
        self._emit(Op.LOAD_VAR, hidden_index, ln)
        self._emit(Op.GET_INDEX, None, ln)
        self._emit(Op.STORE_VAR, s['var'], ln)

        self._block(s['body'])

        # index += 1
        self._emit(Op.LOAD_VAR, hidden_index, ln)
        self._emit(Op.LOAD_CONST, 1, ln)
        self._emit(Op.ADD, None, ln)
        self._emit(Op.UPDATE_VAR, hidden_index, ln)

        self._emit(Op.JUMP, loop_start, ln)
        self._patch(jf, self._here())

    def _compile_funcdef(self, s):
        ln = s.get('line', 0)
        # Compile the function body into a new Chunk
        fn_chunk = Chunk(s['name'])
        self._stack.append(fn_chunk)
        self._block(s['body'])
        self._emit(Op.LOAD_CONST, None, ln)   # implicit return None
        self._emit(Op.RETURN, None, ln)
        self._stack.pop()
        # Emit MAKE_FUNC with the chunk and param list
        self._emit(Op.MAKE_FUNC, (s['name'], s['params'], fn_chunk), ln)
        self._emit(Op.STORE_VAR, s['name'], ln)

    def _compile_try(self, s):
        ln = s.get('line', 0)
        try_start = self._emit(Op.TRY_START, None, ln)
        self._block(s['try_body'])
        self._emit(Op.TRY_END, None, ln)
        jump_over = self._emit(Op.JUMP, None, ln)
        catch_pos = self._here()
        self._patch(try_start, catch_pos)
        self._emit(Op.CATCH, s['err_var'], ln)
        self._block(s['catch_body'])
        self._patch(jump_over, self._here())

    # ── Expressions ───────────────────────────────────────────────────────────

    def _expr(self, x):
        if x is None:
            self._emit(Op.LOAD_CONST, None)
            return
        k = x['kind']; ln = x.get('line', 0)

        if k == 'Num':
            self._emit(Op.LOAD_CONST, x['value'], ln)

        elif k == 'Str':
            self._emit(Op.LOAD_CONST, x['value'], ln)

        elif k == 'Bool':
            self._emit(Op.LOAD_CONST, x['value'], ln)

        elif k == 'Var':
            self._emit(Op.LOAD_VAR, x['name'], ln)

        elif k == 'LL':
            for item in x['items']:
                self._expr(item)
            self._emit(Op.BUILD_LIST, len(x['items']), ln)

        elif k == 'DL':
            for key, val in x['pairs']:
                self._emit(Op.LOAD_CONST, key, ln)
                self._expr(val)
            self._emit(Op.BUILD_DICT, len(x['pairs']), ln)

        elif k == 'BinOp':
            self._expr(x['left'])
            self._expr(x['right'])
            op_map = {
                '+': Op.ADD, '-': Op.SUB,
                '*': Op.MUL, '/': Op.DIV, '%': Op.MOD
            }
            self._emit(op_map[x['op']], None, ln)

        elif k == 'Cmp':
            self._compile_cmp(x)

        elif k == 'Logic':
            self._compile_logic(x)

        elif k == 'NotOp':
            self._expr(x['operand'])
            self._emit(Op.NOT, None, ln)

        elif k == 'GetLen':
            self._expr(x['target'])
            self._emit(Op.GET_LEN, None, ln)

        elif k == 'JoinStr':
            self._expr(x['target'])
            self._expr(x['sep'])
            self._emit(Op.JOIN_STR, None, ln)

        elif k == 'AttrAccess':
            obj_name = x['obj']['name']
            self._emit(Op.GET_ATTR, (obj_name, x['attr']), ln)

        elif k == 'CallExpr':
            for arg in x['args']:
                self._expr(arg)
            self._emit(Op.CALL_FUNC, (x['name'], len(x['args'])), ln)

        elif k == 'DottedCallExpr':
            for arg in x['args']:
                self._expr(arg)
            self._emit(Op.CALL_MODULE, (x['obj'], x['attr'], len(x['args'])), ln)

        else:
            raise BSharpError(f'Compiler: unknown expression kind "{k}"', ln)

    def _compile_cmp(self, x):
        ln = x.get('line', 0)
        self._expr(x['left'])
        self._expr(x['right'])
        op_map = {
            '==':    Op.CMP_EQ,
            '!=':    Op.CMP_NEQ,
            '>':     Op.CMP_GT,
            '<':     Op.CMP_LT,
            '>=':    Op.CMP_GTE,
            '<=':    Op.CMP_LTE,
            'in':    Op.CMP_IN,
            'notin': Op.CMP_NOTIN,
        }
        self._emit(op_map[x['op']], None, ln)

    def _compile_logic(self, x):
        ln = x.get('line', 0)
        if x['op'] == 'and':
            self._expr(x['left'])
            # DUP so result stays on stack if we short-circuit
            self._emit(Op.DUP, None, ln)
            jf = self._emit(Op.JUMP_IF_FALSE, None, ln)
            # Left was truthy — discard the dup, evaluate right as result
            self._emit(Op.POP, None, ln)
            self._expr(x['right'])
            self._patch(jf, self._here())
        else:  # or
            self._expr(x['left'])
            # DUP so result stays on stack if we short-circuit
            self._emit(Op.DUP, None, ln)
            jt = self._emit(Op.JUMP_IF_TRUE, None, ln)
            # Left was falsy — discard the dup, evaluate right as result
            self._emit(Op.POP, None, ln)
            self._expr(x['right'])
            self._patch(jt, self._here())

    def _cond(self, node):
        """Compile a condition expression (same as _expr — result is truthy/falsy)."""
        self._expr(node)


# ── Convenience function ──────────────────────────────────────────────────────

def compile_ast(ast):
    """Compile a parsed B# AST. Returns the main Chunk."""
    return Compiler().compile(ast)