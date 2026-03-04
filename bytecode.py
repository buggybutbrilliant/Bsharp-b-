# B# Bytecode — opcode definitions and instruction format
# This file is the single source of truth for all VM instructions.
# Both compiler.py and vm.py import from here.

# ── Opcodes 

class Op:
    # Stack operations
    LOAD_CONST      = 'LOAD_CONST'      # push a constant onto the stack
    LOAD_VAR        = 'LOAD_VAR'        # push a variable's value onto the stack
    STORE_VAR       = 'STORE_VAR'       # pop stack → store in variable
    UPDATE_VAR      = 'UPDATE_VAR'      # pop stack → update existing variable

    # Arithmetic
    ADD             = 'ADD'
    SUB             = 'SUB'
    MUL             = 'MUL'
    DIV             = 'DIV'
    MOD             = 'MOD'

    # Comparison
    CMP_EQ          = 'CMP_EQ'          # ==
    CMP_NEQ         = 'CMP_NEQ'         # !=
    CMP_GT          = 'CMP_GT'          # >
    CMP_LT          = 'CMP_LT'          # <
    CMP_GTE         = 'CMP_GTE'         # >=
    CMP_LTE         = 'CMP_LTE'         # <=
    CMP_IN          = 'CMP_IN'          # contains
    CMP_NOTIN       = 'CMP_NOTIN'       # does not contain

    # Logic
    AND             = 'AND'
    OR              = 'OR'
    NOT             = 'NOT'

    # Control flow
    JUMP            = 'JUMP'            # unconditional jump to offset
    JUMP_IF_FALSE   = 'JUMP_IF_FALSE'   # pop + jump if falsy
    JUMP_IF_TRUE    = 'JUMP_IF_TRUE'    # pop + jump if truthy (for 'or')

    # I/O
    PRINT           = 'PRINT'           # pop + print (arg = number of items)
    INPUT           = 'INPUT'           # push input string
    INPUT_TYPED     = 'INPUT_TYPED'     # push input coerced to type

    # Functions
    CALL_FUNC       = 'CALL_FUNC'       # call a B# function (arg = nargs)
    CALL_MODULE     = 'CALL_MODULE'     # call a module method (arg = (mod,fn,nargs))
    RETURN          = 'RETURN'          # return from function
    MAKE_FUNC       = 'MAKE_FUNC'       # define a function object

    # Collections
    BUILD_LIST      = 'BUILD_LIST'      # pop n items → build list (arg = n)
    BUILD_DICT      = 'BUILD_DICT'      # pop n pairs → build dict (arg = n)
    GET_ATTR        = 'GET_ATTR'        # access module.attr (arg = (mod, attr))
    GET_INDEX       = 'GET_INDEX'       # list[index]
    GET_LEN         = 'GET_LEN'         # len of top of stack
    LIST_APPEND     = 'LIST_APPEND'     # append to list variable (arg = var name)
    LIST_REMOVE     = 'LIST_REMOVE'     # remove from list variable (arg = var name)
    JOIN_STR        = 'JOIN_STR'        # join list with separator

    # Files
    READ_FILE       = 'READ_FILE'       # read file → push contents
    WRITE_FILE      = 'WRITE_FILE'      # write to file

    # Libraries
    USE_LIB         = 'USE_LIB'         # load a stdlib or package (arg = name)

    # Error handling
    TRY_START       = 'TRY_START'       # mark start of try block (arg = catch offset)
    TRY_END         = 'TRY_END'         # end of try block
    CATCH           = 'CATCH'           # start of catch block (arg = err_var name)

    # Misc
    POP             = 'POP'             # discard top of stack
    DUP             = 'DUP'             # duplicate top of stack
    NOP             = 'NOP'             # no operation
    HALT            = 'HALT'            # end of program
    EXPLAIN         = 'EXPLAIN'         # print last operation description


# ── Instruction 

class Instruction:
    """A single bytecode instruction."""
    __slots__ = ('op', 'arg', 'line')

    def __init__(self, op, arg=None, line=0):
        self.op   = op    # str opcode from Op
        self.arg  = arg   # optional argument (constant, var name, offset, etc.)
        self.line = line  # source line number for error reporting

    def __repr__(self):
        arg_str = f'  {self.arg!r}' if self.arg is not None else ''
        return f'{self.op:<20}{arg_str}'


# ── Bytecode chunk 

class Chunk:
    """
    A compiled unit of B# code — a function body or the top-level program.
    Contains a flat list of Instructions and a constants pool.
    """
    def __init__(self, name='<main>'):
        self.name         = name
        self.instructions = []      # list of Instruction
        self.constants    = []      # constant pool (deduplicated)

    def emit(self, op, arg=None, line=0):
        """Append an instruction and return its index."""
        instr = Instruction(op, arg, line)
        self.instructions.append(instr)
        return len(self.instructions) - 1

    def patch(self, idx, new_arg):
        """Update the arg of an already-emitted instruction (used for forward jumps)."""
        self.instructions[idx].arg = new_arg

    def add_const(self, value):
        """Add a constant to the pool (deduplicated). Returns its index."""
        try:
            return self.constants.index(value)
        except ValueError:
            self.constants.append(value)
            return len(self.constants) - 1

    def disassemble(self):
        """Return a human-readable listing of the bytecode."""
        lines = [f'=== Chunk: {self.name} ===']
        for i, instr in enumerate(self.instructions):
            arg_str = f'  {instr.arg!r}' if instr.arg is not None else ''
            lines.append(f'  {i:04d}  (L{instr.line:03d})  {instr.op:<20}{arg_str}')
        return '\n'.join(lines)

    def __len__(self):
        return len(self.instructions)


# ── .bsc file format 
# .bsc files are JSON with this structure:
# {
#   "bsc_version": 1,
#   "bsharp_version": "1.2.0",
#   "source_file": "example.bsharp",
#   "source_mtime": 1234567890.0,
#   "chunks": [
#     {
#       "name": "<main>",
#       "constants": [...],
#       "instructions": [
#         {"op": "LOAD_CONST", "arg": 0, "line": 1},
#         ...
#       ]
#     }
#   ]
# }

BSC_VERSION = 1


def chunk_to_dict(chunk):
    """Serialise a Chunk to a JSON-compatible dict."""
    return {
        'name':         chunk.name,
        'constants':    chunk.constants,
        'instructions': [
            {'op': i.op, 'arg': i.arg, 'line': i.line}
            for i in chunk.instructions
        ]
    }


def chunk_from_dict(d):
    """Deserialise a Chunk from a dict."""
    c = Chunk(d['name'])
    c.constants = d['constants']
    c.instructions = [
        Instruction(i['op'], i['arg'], i['line'])
        for i in d['instructions']
    ]
    return c