# B# CLI — command line interface
import sys
import os      as _os
import json    as _json
from core.core       import BSharpError
from core.lexer       import lex
from core.parser      import Parser
from core.compiler    import compile_ast
from core.vm          import run_chunk
from core.bytecode    import BSC_VERSION, chunk_to_dict, chunk_from_dict
from tools.linter      import lint_file, Level

VERSION = "1.2.1"

HELP = """
B# (B-sharp) Programming Language  v{version}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage:
  bsharp run   <file>  [flags]    Run a .bsharp or .bsc file
  bsharp build <file>  [flags]    Compile .bsharp → .bsc bytecode
  bsharp lint  <file>             Analyse a .bsharp file for warnings
  bsharp test  [folder][flags]    Run all tests in tests/cases/
  bsharp version                  Show version info
  bsharp help                     Show this help

Flags:
  --trace     Print every instruction as it executes
  --debug     Alias for --trace
  --disasm    Print bytecode disassembly before running

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
    return _os.path.splitext(bs_path)[0] + '.bsc'

def _bsc_is_fresh(bs_path, bsc_path):
    if not _os.path.isfile(bsc_path): return False
    try:
        if _os.path.getmtime(bsc_path) < _os.path.getmtime(bs_path): return False
        with open(bsc_path, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        return data.get('bsc_version') == BSC_VERSION
    except Exception:
        return False

def _save_bsc(bs_path, chunk):
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
    try:
        with open(bsc_path, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        if data.get('bsc_version') != BSC_VERSION: return None
        return chunk_from_dict(data['chunks'][0])
    except Exception:
        return None


# ── Run helpers ───────────────────────────────────────────────────────────────

def _run_vm(fname, trace=False, disasm=False):
    """Compile (or load cached .bsc) and run on VM."""
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f'Error: File "{fname}" not found.'); return False

    bsc_path = _bsc_path(fname)
    chunk    = None

    if _bsc_is_fresh(fname, bsc_path):
        chunk = _load_bsc(bsc_path)
        if trace: print(f'[vm] Using cached {bsc_path}')

    if chunk is None:
        if trace: print(f'[vm] Compiling "{fname}"...')
        try:
            chunk = compile_ast(Parser(lex(source)).parse())
            _save_bsc(fname, chunk)
            if trace: print(f'[vm] Saved → {bsc_path}')
        except BSharpError as e:
            print(f'\n{"━"*50}\n{e.friendly()}\n{"━"*50}'); return False

    if disasm:
        print(chunk.disassemble()); print()

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
        print(chunk.disassemble()); print()
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
    files  = [a for a in argv if not a.startswith('--')]
    flags  = [a for a in argv if a.startswith('--')]
    trace  = '--trace' in flags or '--debug' in flags
    disasm = '--disasm' in flags
    if not files:
        print('Usage: bsharp run <file.bsharp|file.bsc> [--trace] [--disasm]')
        sys.exit(1)
    fname = files[0]
    ok = _run_bsc(fname, trace=trace, disasm=disasm) if fname.endswith('.bsc') \
         else _run_vm(fname, trace=trace, disasm=disasm)
    sys.exit(0 if ok else 1)


def cmd_build(argv):
    files  = [a for a in argv if not a.startswith('--')]
    flags  = [a for a in argv if a.startswith('--')]
    disasm = '--disasm' in flags
    if not files:
        print('Usage: bsharp build <file.bsharp> [--disasm]')
        sys.exit(1)
    fname = files[0]
    if not fname.endswith('.bsharp'):
        print(f'Error: "{fname}" is not a .bsharp file.'); sys.exit(1)
    if not _os.path.isfile(fname):
        print(f'Error: File "{fname}" not found.'); sys.exit(1)
    print(f'Compiling {fname}...')
    try:
        with open(fname, 'r', encoding='utf-8') as f: source = f.read()
        chunk = compile_ast(Parser(lex(source)).parse())
    except BSharpError as e:
        print(f'\n{"━"*50}\n{e.friendly()}\n{"━"*50}'); sys.exit(1)
    bsc_path = _save_bsc(fname, chunk)
    print(f'  Done  →  {bsc_path}  ({len(chunk)} instructions)')
    if disasm:
        print(); print(chunk.disassemble())


def cmd_lint(argv):
    files = [a for a in argv if not a.startswith('--')]
    if not files:
        print('Usage: bsharp lint <file.bsharp>'); sys.exit(1)

    fname = files[0]
    bar   = '─' * 50
    print(f'\nB# Linter  v{VERSION}  —  {fname}\n{bar}')

    warnings, err = lint_file(fname)

    if err:
        print(f'\n  Parse error: {err.friendly()}\n{bar}\n')
        sys.exit(1)

    if not warnings:
        print('  No issues found.  ✓\n' + bar + '\n')
        sys.exit(0)

    warnings.sort(key=lambda w: w.line)
    errors = [w for w in warnings if w.level == Level.ERROR]
    warns  = [w for w in warnings if w.level == Level.WARNING]
    infos  = [w for w in warnings if w.level == Level.INFO]

    if errors:
        print(f'\n  Errors ({len(errors)}):')
        for w in errors: print(w)
    if warns:
        print(f'\n  Warnings ({len(warns)}):')
        for w in warns:  print(w)
    if infos:
        print(f'\n  Info ({len(infos)}):')
        for w in infos:  print(w)

    print(f'\n{bar}')
    print(f'  {len(errors)} error(s)   {len(warns)} warning(s)   {len(infos)} info   — {len(warnings)} total')
    print(bar + '\n')
    sys.exit(1 if errors else 0)


def cmd_test(argv):
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
    bar    = '─' * 50
    print(f'\nB# Test Runner  v{VERSION}\n{bar}')

    for path in case_files:
        name     = _os.path.splitext(_os.path.basename(path))[0]
        exp_path = _os.path.join(expected_dir, name + '.txt')

        buf = _io.StringIO(); old_out = sys.stdout; sys.stdout = buf
        error_msg = None
        try:
            with open(path, 'r', encoding='utf-8') as f: source = f.read()
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
    print(f'B# (B-sharp) Programming Language')
    print(f'Version  : {VERSION}')
    print(f'Runtime  : Python {sys.version.split()[0]}')
    print(f'Platform : {sys.platform}')
    print(f'Mode     : VM (bytecode)')


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ('help', '--help', '-h'):
        print(HELP); return
    cmd = argv[0]
    if cmd in ('version', '--version', '-v'): cmd_version(); return
    if cmd == 'run':     cmd_run(argv[1:]);   return
    if cmd == 'build':   cmd_build(argv[1:]); return
    if cmd == 'lint':    cmd_lint(argv[1:]);  return
    if cmd == 'test':    cmd_test(argv[1:]);  return
    # Legacy: python bsharp.py file.bsharp
    if cmd.endswith('.bsharp') or cmd.endswith('.bsc') or _os.path.isfile(cmd):
        flags = argv[1:]
        trace = '--trace' in flags or '--debug' in flags
        ok = _run_bsc(cmd, trace=trace) if cmd.endswith('.bsc') else _run_vm(cmd, trace=trace)
        sys.exit(0 if ok else 1)
        return
    print(f'Unknown command "{cmd}". Run "bsharp help" for usage.')
    sys.exit(1)


if __name__ == '__main__': main()
# b# for beginners — a simple, readable, fun programming language