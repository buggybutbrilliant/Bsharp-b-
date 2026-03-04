# B# CLI — command line interface
import sys
import os      as _os
import json    as _json
import time    as _time
from core        import BSharpError
from lexer       import lex
from parser      import Parser
from interpreter import Runtime
from compiler    import compile_ast
from vm          import run_chunk
from bytecode    import BSC_VERSION, chunk_to_dict, chunk_from_dict, Chunk

VERSION = "1.2.0"

HELP = """
B# (B-sharp) Programming Language  v{version}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage:
  bsharp run   <file>  [flags]    Run a .bsharp or .bsc file
  bsharp build <file>  [flags]    Compile .bsharp → .bsc bytecode
  bsharp test  [folder][flags]    Run all tests in tests/cases/
  bsharp version                  Show version info
  bsharp help                     Show this help

Flags:
  --vm        Force VM execution (default)
  --interp    Force interpreter (tree-walking) execution
  --trace     Print every statement/instruction as it executes
  --debug     Alias for --trace
  --disasm    Print bytecode disassembly before running

Execution modes:
  Default     Compile to bytecode → cache .bsc → run on VM
  --interp    Skip compiler, run AST directly (original mode)
  --vm        Explicitly use VM (same as default)

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


# ── .bsc helpers ──────────────────────────────────────────────────────────────

def _bsc_path(bs_path):
    """Return the .bsc path for a given .bsharp file."""
    return _os.path.splitext(bs_path)[0] + '.bsc'


def _bsc_is_fresh(bs_path, bsc_path):
    """Return True if the .bsc exists and is newer than the .bsharp source."""
    if not _os.path.isfile(bsc_path):
        return False
    try:
        src_mtime = _os.path.getmtime(bs_path)
        bsc_mtime = _os.path.getmtime(bsc_path)
        if bsc_mtime < src_mtime:
            return False
        # Also check BSC_VERSION inside the file
        with open(bsc_path, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        return data.get('bsc_version') == BSC_VERSION
    except Exception:
        return False


def _save_bsc(bs_path, chunk):
    """Save a compiled Chunk to a .bsc file."""
    bsc_path = _bsc_path(bs_path)
    data = {
        'bsc_version':    BSC_VERSION,
        'bsharp_version': VERSION,
        'source_file':    _os.path.basename(bs_path),
        'source_mtime':   _os.path.getmtime(bs_path),
        'chunks':         [chunk_to_dict(chunk)],
    }
    with open(bsc_path, 'w', encoding='utf-8') as f:
        _json.dump(data, f)
    return bsc_path


def _load_bsc(bsc_path):
    """Load a Chunk from a .bsc file. Returns chunk or None on error."""
    try:
        with open(bsc_path, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        if data.get('bsc_version') != BSC_VERSION:
            return None
        return chunk_from_dict(data['chunks'][0])
    except Exception:
        return None


# ── Run modes ─────────────────────────────────────────────────────────────────

def _run_interp(fname, trace=False):
    """Run a .bsharp file using the tree-walking interpreter."""
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f'Error: File "{fname}" not found.'); return False
    sl = source.splitlines()
    if trace:
        print(f'[interp] Running "{fname}" — {len(sl)} lines\n{"─"*50}')
    try:
        tokens     = lex(source)
        prog       = Parser(tokens).parse()
        script_dir = _os.path.dirname(_os.path.abspath(fname))
        Runtime(trace=trace, src=sl, script_dir=script_dir).run(prog)
        return True
    except BSharpError as e:
        print(f'\n{"━"*50}\n{e.friendly()}\n{"━"*50}'); return False
    except KeyboardInterrupt:
        print('\n[stopped]'); return False


def _run_vm(fname, trace=False, disasm=False):
    """Run a .bsharp file using the bytecode VM (with .bsc caching)."""
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f'Error: File "{fname}" not found.'); return False

    bsc_path = _bsc_path(fname)
    chunk    = None

    if _bsc_is_fresh(fname, bsc_path):
        chunk = _load_bsc(bsc_path)
        if trace:
            print(f'[vm] Using cached bytecode: {bsc_path}')

    if chunk is None:
        if trace:
            print(f'[vm] Compiling "{fname}"...')
        try:
            sl     = source.splitlines()
            tokens = lex(source)
            prog   = Parser(tokens).parse()
            chunk  = compile_ast(prog)
            _save_bsc(fname, chunk)
            if trace:
                print(f'[vm] Saved bytecode → {bsc_path}')
        except BSharpError as e:
            print(f'\n{"━"*50}\n{e.friendly()}\n{"━"*50}'); return False

    if disasm:
        print(chunk.disassemble())
        print()

    try:
        script_dir = _os.path.dirname(_os.path.abspath(fname))
        run_chunk(chunk, trace=trace, script_dir=script_dir)
        return True
    except BSharpError as e:
        print(f'\n{"━"*50}\n{e.friendly()}\n{"━"*50}'); return False
    except KeyboardInterrupt:
        print('\n[stopped]'); return False


def _run_bsc(fname, trace=False, disasm=False):
    """Run a pre-compiled .bsc file directly."""
    chunk = _load_bsc(fname)
    if chunk is None:
        print(f'Error: "{fname}" is not a valid .bsc file or version mismatch.')
        print(f'  Re-compile with: bsharp build <source.bsharp>')
        return False
    if disasm:
        print(chunk.disassemble())
        print()
    try:
        script_dir = _os.path.dirname(_os.path.abspath(fname))
        run_chunk(chunk, trace=trace, script_dir=script_dir)
        return True
    except BSharpError as e:
        print(f'\n{"━"*50}\n{e.friendly()}\n{"━"*50}'); return False
    except KeyboardInterrupt:
        print('\n[stopped]'); return False


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_run(argv):
    """bsharp run <file> [--vm|--interp] [--trace] [--debug] [--disasm]"""
    files  = [a for a in argv if not a.startswith('--')]
    flags  = [a for a in argv if a.startswith('--')]
    trace  = '--trace' in flags or '--debug' in flags
    disasm = '--disasm' in flags
    interp = '--interp' in flags

    if not files:
        print('Usage: bsharp run <file.bsharp|file.bsc> [--vm|--interp] [--trace]')
        sys.exit(1)

    fname = files[0]

    # Running a pre-compiled .bsc file
    if fname.endswith('.bsc'):
        ok = _run_bsc(fname, trace=trace, disasm=disasm)
        sys.exit(0 if ok else 1)

    # Running a .bsharp source file
    if interp:
        ok = _run_interp(fname, trace=trace)
    else:
        ok = _run_vm(fname, trace=trace, disasm=disasm)

    sys.exit(0 if ok else 1)


def cmd_build(argv):
    """bsharp build <file.bsharp> [--disasm]"""
    files  = [a for a in argv if not a.startswith('--')]
    flags  = [a for a in argv if a.startswith('--')]
    disasm = '--disasm' in flags

    if not files:
        print('Usage: bsharp build <file.bsharp> [--disasm]')
        sys.exit(1)

    fname = files[0]
    if not fname.endswith('.bsharp'):
        print(f'Error: "{fname}" is not a .bsharp file.')
        sys.exit(1)

    if not _os.path.isfile(fname):
        print(f'Error: File "{fname}" not found.')
        sys.exit(1)

    print(f'Compiling {fname}...')
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            source = f.read()
        tokens = lex(source)
        prog   = Parser(tokens).parse()
        chunk  = compile_ast(prog)
    except BSharpError as e:
        print(f'\n{"━"*50}\n{e.friendly()}\n{"━"*50}')
        sys.exit(1)

    bsc_path = _save_bsc(fname, chunk)
    print(f'  Done  →  {bsc_path}')
    print(f'  {len(chunk)} instructions')

    if disasm:
        print()
        print(chunk.disassemble())


def cmd_test(argv):
    """bsharp test [folder] [--vm|--interp] [--trace|--debug]"""
    import glob, io as _io

    flags      = [a for a in argv if a.startswith('--')]
    positional = [a for a in argv if not a.startswith('--')]
    trace      = '--trace' in flags or '--debug' in flags
    interp     = '--interp' in flags

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

    mode   = 'interp' if interp else 'vm'
    passed = failed = 0
    bar    = '─' * 50
    print(f'\nB# Test Runner  v{VERSION}  [{mode}]\n{bar}')

    for path in case_files:
        name     = _os.path.splitext(_os.path.basename(path))[0]
        exp_path = _os.path.join(expected_dir, name + '.txt')

        buf = _io.StringIO(); old_out = sys.stdout; sys.stdout = buf
        error_msg = None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                source = f.read()
            sl = source.splitlines()
            if interp:
                Runtime(trace=trace, src=sl).run(Parser(lex(source)).parse())
            else:
                chunk = compile_ast(Parser(lex(source)).parse())
                run_chunk(chunk, trace=trace)
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
    print(f'Version  : {VERSION}')
    print(f'Runtime  : Python {sys.version.split()[0]}')
    print(f'Platform : {sys.platform}')
    print(f'Mode     : VM (bytecode) + Interpreter (fallback)')


def main():
    argv = sys.argv[1:]

    if not argv or argv[0] in ('help', '--help', '-h'):
        print(HELP); return

    cmd = argv[0]

    if cmd in ('version', '--version', '-v'):
        cmd_version(); return

    if cmd == 'run':
        cmd_run(argv[1:]); return

    if cmd == 'build':
        cmd_build(argv[1:]); return

    if cmd == 'test':
        cmd_test(argv[1:]); return

    # Legacy fallback: python bsharp.py <file.bsharp>
    if cmd.endswith('.bsharp') or cmd.endswith('.bsc') or _os.path.isfile(cmd):
        flags  = argv[1:]
        trace  = '--trace' in flags or '--debug' in flags
        interp = '--interp' in flags
        if cmd.endswith('.bsc'):
            sys.exit(0 if _run_bsc(cmd, trace=trace) else 1)
        elif interp:
            sys.exit(0 if _run_interp(cmd, trace=trace) else 1)
        else:
            sys.exit(0 if _run_vm(cmd, trace=trace) else 1)
        return

    print(f'Unknown command "{cmd}". Run "bsharp help" for usage.')
    sys.exit(1)


if __name__ == '__main__': main()
# b# for beginners — a simple, readable, fun programming language