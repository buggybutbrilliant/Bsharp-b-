# B# CLI — command line interface
import sys
import os as _os
from core import BSharpError
from lexer import lex
from parser import Parser
from interpreter import Runtime

VERSION = "1.2.0"


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