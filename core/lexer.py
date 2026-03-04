# B# Lexer — tokenises B# source code
import re
from core.core import BSharpError

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