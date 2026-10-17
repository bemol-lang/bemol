#!/usr/bin/env python3
"""
BEMOL ♭ — prototyp tłumacza BEMOL → C (wersja 0)

Użycie:
    python3 bemolc.py program.bmol            # kompilacja testowa → ./program
    python3 bemolc.py -finalbake program.bmol # finalbake (pełna optymalizacja)
    python3 bemolc.py --emit-c program.bmol   # tylko wygenerowany kod C
    python3 bemolc.py --debug program.bmol    # pełny ślad przy błędzie wewnętrznym

Wersja 0 obsługuje podzbiór języka opisany w README prototypu.
Wszystko, czego nie obsługuje, zgłasza błędem BML-E0900 zamiast
po cichu tłumaczyć źle.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Typy
# --------------------------------------------------------------------------

# nazwa → (typ C, rozmiar w bajtach, rodzaj: u/s/f/b, przyrostek funkcji)
TYPES = {
    'byte': ('uint8_t', 1, 'u', 'u8'), 'unsigned_8': ('uint8_t', 1, 'u', 'u8'),
    'unsigned_16': ('uint16_t', 2, 'u', 'u16'), 'unsigned_32': ('uint32_t', 4, 'u', 'u32'),
    'unsigned_64': ('uint64_t', 8, 'u', 'u64'),
    'signed_8': ('int8_t', 1, 's', 'i8'),
    'shortint': ('int16_t', 2, 's', 'i16'), 'signed_16': ('int16_t', 2, 's', 'i16'),
    'int': ('int32_t', 4, 's', 'i32'), 'signed_32': ('int32_t', 4, 's', 'i32'),
    'longint': ('int64_t', 8, 's', 'i64'), 'signed_64': ('int64_t', 8, 's', 'i64'),
    'float': ('float', 4, 'f', 'f32'), 'doublefloat': ('double', 8, 'f', 'f64'),
    'bit': ('uint8_t', 1, 'b', 'u8'),
}
WIDE = {'__wide': 'bm_wide', '__widef': 'long double'}
BLOCK_TYPES = ('pointer', 'text')

KEYWORDS_UPPER = {'MAIN', 'BEGIN', 'END', 'CLASS', 'FUNCTION', 'STRUCT', 'ENUM', 'GLOBAL',
                  'PERSISTENT', 'CONST', 'REF', 'ALIAS', 'PRIVATE'}
RESERVED = {'keyInput', 'if', 'then', 'elseif', 'else', 'for', 'to', 'step', 'do', 'while', 'repeat', 'until',
            'foreach', 'in', 'break', 'continue', 'switch', 'case', 'as', 'return', 'this',
            'and', 'or', 'xor', 'not', 'shl', 'shr', 'rol', 'ror', 'saturate', 'print', 'println',
            'true', 'false'} | KEYWORDS_UPPER
WORD_OPS = ('xor', 'and', 'or', 'shl', 'shr', 'rol', 'ror')
BLOCK_METHODS = ('new', 'update', 'release', 'clear', 'fill', 'append')


class BemolError(Exception):
    def __init__(self, code, msg, line, col=0, detail='', help=''):
        super().__init__(msg)
        self.code, self.msg, self.line, self.col, self.detail, self.help = code, msg, line, col, detail, help


def cnum(v):
    if v == -2**63:
        return 'INT64_MIN'
    return f'{v}LL'


def unsupported(what, line):
    raise BemolError('BML-E0900', f'{what} nie jest jeszcze obsługiwane w prototypie (wersja 0)', line,
                     help='zobacz listę obsługiwanych elementów w prototyp/README.md')


# --------------------------------------------------------------------------
# Lekser
# --------------------------------------------------------------------------

class Tok:
    __slots__ = ('kind', 'val', 'line', 'col', 'bits')

    def __init__(self, kind, val, line, col, bits=0):
        self.kind, self.val, self.line, self.col, self.bits = kind, val, line, col, bits

    def __repr__(self):
        return f'{self.kind}:{self.val!r}@{self.line}'


CONT_OPS = {'+', '-', '*', '/', '%', '=', '==', '!=', '<', '>', '<=', '>=', ',', '(', '[', '{',
            '+=', '-=', '*=', '/=', '%=', ':'} | {w + '=' for w in WORD_OPS}


def lex(src):
    toks = []
    i, line, col = 0, 1, 1
    depth = 0
    n = len(src)

    def add(kind, val, l, c, bits=0):
        toks.append(Tok(kind, val, l, c, bits))

    while i < n:
        ch = src[i]
        if ch == '\n':
            prev = toks[-1] if toks else None
            cont = depth > 0 or (prev and prev.kind == 'OP' and prev.val in CONT_OPS) \
                or (prev and prev.kind == 'NAME' and prev.val in ('and', 'or', 'xor', 'shl', 'shr', 'rol', 'ror'))
            if not cont and prev and prev.kind != 'NL':
                add('NL', '\n', line, col)
            i += 1; line += 1; col = 1
            continue
        if ch in ' \t\r':
            i += 1; col += 1
            continue
        if ch == '#':
            while i < n and src[i] != '\n':
                i += 1
            continue
        if ch == ';':
            if toks and toks[-1].kind != 'NL':
                add('NL', ';', line, col)
            i += 1; col += 1
            continue
        if ch == '"':
            j, buf = i + 1, []
            while j < n and src[j] != '"':
                if src[j] == '\\' and j + 1 < n:
                    esc = src[j + 1]
                    buf.append({'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(esc, esc))
                    j += 2
                else:
                    if src[j] == '\n':
                        raise BemolError('BML-E0010', 'niezamknięty tekst w cudzysłowie', line, col)
                    buf.append(src[j]); j += 1
            if j >= n:
                raise BemolError('BML-E0010', 'niezamknięty tekst w cudzysłowie', line, col)
            add('STR', ''.join(buf), line, col)
            col += j + 1 - i; i = j + 1
            continue
        if ch == '&':
            j = i + 1
            while j < n and src[j].isalnum():
                j += 1
            body = src[i + 1:j]
            if len(body) >= 2 and body[-1] == 'h' and all(c in '0123456789abcdefABCDEF' for c in body[:-1]):
                add('LIT', int(body[:-1], 16), line, col, bits=4 * (len(body) - 1))
            elif len(body) >= 2 and body[-1] == 'b' and all(c in '01' for c in body[:-1]):
                add('LIT', int(body[:-1], 2), line, col, bits=len(body) - 1)
            elif body and all(c in '0123456789abcdefABCDEF' for c in body):
                raise BemolError('BML-E0012', f'literał „&{body}” nie ma znacznika systemu liczbowego', line, col,
                                 detail='na końcu literału stoi h (szesnastkowo) albo b (binarnie)',
                                 help=f'&{body}h' + (f' albo &{body}b' if all(c in '01' for c in body) else ''))
            else:
                raise BemolError('BML-E0011', f'niepoprawny literał „&{body}”', line, col,
                                 help='szesnastkowo: &FF00h, binarnie: &0101b')
            col += j - i; i = j
            continue
        if ch.isdigit():
            j = i
            while j < n and (src[j].isdigit() or src[j] == '_'):
                j += 1
            is_float = False
            if j < n and src[j] == '.' and j + 1 < n and src[j + 1].isdigit():
                is_float = True
                j += 1
                while j < n and src[j].isdigit():
                    j += 1
            text = src[i:j].replace('_', '')
            add('FLT' if is_float else 'NUM', float(text) if is_float else int(text), line, col)
            col += j - i; i = j
            continue
        if ch.isalpha() or ch == '_':
            j = i
            while j < n and (src[j].isalnum() or src[j] == '_'):
                j += 1
            word = src[i:j]
            if word in WORD_OPS and j < n and src[j] == '=' and not (j + 1 < n and src[j + 1] == '='):
                add('OP', word + '=', line, col)
                col += j + 1 - i; i = j + 1
                continue
            add('NAME', word, line, col)
            col += j - i; i = j
            continue
        two = src[i:i + 2]
        if two in ('==', '!=', '<=', '>=', '+=', '-=', '*=', '/=', '%='):
            add('OP', two, line, col); i += 2; col += 2
            continue
        if ch in '+-*/%<>=()[]{},:.@':
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                depth = max(0, depth - 1)
            add('OP', ch, line, col); i += 1; col += 1
            continue
        raise BemolError('BML-E0012', f'nieznany znak „{ch}”', line, col)
    add('NL', '\n', line, col)
    add('EOF', None, line, col)
    return toks


# --------------------------------------------------------------------------
# Drzewo składni
# --------------------------------------------------------------------------

class Node:
    def __init__(self, kind, line, **kw):
        self.kind, self.line = kind, line
        self.__dict__.update(kw)

    def __repr__(self):
        return f'<{self.kind} {self.__dict__}>'


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

class Parser:
    def __init__(self, toks):
        self.t, self.p = toks, 0

    def peek(self, k=0):
        return self.t[min(self.p + k, len(self.t) - 1)]

    def next(self):
        tok = self.t[self.p]; self.p += 1
        return tok

    def at(self, kind, val=None, k=0):
        tok = self.peek(k)
        return tok.kind == kind and (val is None or tok.val == val)

    def accept(self, kind, val=None):
        if self.at(kind, val):
            return self.next()
        return None

    def expect(self, kind, val=None, what=None):
        tok = self.peek()
        if tok.kind == kind and (val is None or tok.val == val):
            return self.next()
        exp = what or (val if val is not None else kind)
        got = 'koniec linii' if tok.kind == 'NL' else ('koniec pliku' if tok.kind == 'EOF' else f'„{tok.val}”')
        raise BemolError('BML-E0020', f'oczekiwano „{exp}”, a jest {got}', tok.line, tok.col)

    def skip_nl(self):
        while self.at('NL'):
            self.next()

    def end_of_stmt(self):
        if self.at('OP', '@'):                      # @ACCEPT ... do końca instrukcji
            while not self.at('NL') and not self.at('EOF'):
                self.next()
        if not self.at('EOF'):
            self.expect('NL', what='koniec instrukcji')

    def at_closer(self, name):
        self.expected_closer = name
        return self.at('NAME', name) and self.at('OP', '.', 1) and self.at('NAME', 'end', 2)

    def eat_closer(self, name):
        if not self.at_closer(name):
            tok = self.peek()
            raise BemolError('BML-E0021', f'oczekiwano zamknięcia bloku „{name}.end”', tok.line, tok.col)
        self.next(); self.next(); self.next()
        self.end_of_stmt()

    # ---- poziom pliku ----------------------------------------------------
    def program(self):
        items = []
        self.skip_nl()
        while not self.at('EOF'):
            items.append(self.item())
            self.skip_nl()
        return items

    def item(self):
        tok = self.peek()
        if self.at('NAME', 'GLOBAL'):
            self.next()
            d = self.decl()
            d.glob = True
            return d
        if self.at('NAME', 'CONST'):
            self.next()
            name = self.expect('NAME').val
            self.expect('NAME', 'as')
            typ = self.typename()
            self.expect('OP', '=')
            val = self.expr()
            self.end_of_stmt()
            return Node('Const', tok.line, col=tok.col, name=name, type=typ, value=val)
        if self.at('NAME', 'ALIAS'):
            self.next()
            name = self.expect('NAME').val
            self.expect('NAME', 'as')
            val = self.expr()
            self.end_of_stmt()
            return Node('Alias', tok.line, col=tok.col, name=name, value=val)
        if self.at('NAME', 'FUNCTION'):
            return self.function()
        if self.at('NAME', 'MAIN'):
            self.next()
            self.expect('NAME', 'BEGIN')
            self.end_of_stmt()
            body = self.block(lambda: self.at('NAME', 'MAIN') and self.at('NAME', 'END', 1))
            self.next(); self.next()
            if not self.at('EOF'):
                self.end_of_stmt()
            return Node('Main', tok.line, col=tok.col, body=body)
        if self.at('NAME') and self.at('NAME', 'as', 1) and self.at('NAME', 'STRUCT', 2):
            name = self.next().val
            self.next(); self.next()
            self.expect('OP', '{')
            fields = []
            while True:
                fname = self.expect('NAME').val
                self.expect('NAME', 'as')
                ftype = self.typename()
                fields.append((fname, ftype))
                if not self.accept('OP', ','):
                    break
            self.expect('OP', '}')
            self.end_of_stmt()
            return Node('Struct', tok.line, col=tok.col, name=name, fields=fields)
        if self.at('NAME', 'CLASS'):
            unsupported('CLASS', tok.line)
        if self.at('NAME', 'ENUM'):
            unsupported('ENUM', tok.line)
        if self.at('NAME') and tok.val in ('if', 'for', 'while', 'foreach', 'print', 'println'):
            raise BemolError('BML-E0022', 'instrukcja poza MAIN i poza funkcją', tok.line, tok.col,
                             help='umieść kod w MAIN BEGIN ... MAIN END albo w funkcji')
        raise BemolError('BML-E0023', f'nieoczekiwane „{tok.val}” na poziomie pliku', tok.line, tok.col)

    def typename(self):
        tok = self.expect('NAME', what='nazwa typu')
        return tok.val

    def decl(self):
        tok = self.expect('NAME')
        self.expect('NAME', 'as')
        typ = self.typename()
        init = None
        newsize = None
        if typ in ('pointer', 'text') and self.at('OP', '.') and self.at('NAME', 'new', 1):
            self.next(); self.next()
            self.expect('OP', '[')
            newsize = self.expr()
            self.expect('OP', ']')
        elif self.accept('OP', '='):
            init = self.expr()
        self.end_of_stmt()
        return Node('Decl', tok.line, col=tok.col, name=tok.val, type=typ, init=init, glob=False, newsize=newsize)

    def function(self):
        tok = self.next()
        name = self.expect('NAME').val
        self.expect('OP', '(')
        params = []
        if not self.at('OP', ')'):
            while True:
                mod = None
                if self.at('NAME', 'CONST') or self.at('NAME', 'REF'):
                    mod = self.next().val
                pname = self.expect('NAME').val
                self.expect('NAME', 'as')
                ptype = self.typename()
                params.append((pname, ptype, mod))
                if not self.accept('OP', ','):
                    break
        self.expect('OP', ')')
        ret = 'void'
        if self.accept('OP', ':'):
            rt = self.peek()
            ret = self.typename()
            if ret == 'void':
                raise BemolError('BML-E0405', 'funkcja bez wyniku nie ma nic po nawiasie', rt.line, rt.col,
                                 help=f'usuń „: void”: FUNCTION {name}(...)')
            if self.at('OP', ','):
                unsupported('zwracanie kilku wartości', tok.line)
        self.end_of_stmt()
        body = self.block(lambda: self.at_closer(name))
        self.eat_closer(name)
        return Node('Function', tok.line, col=tok.col, name=name, params=params, ret=ret, body=body)

    # ---- instrukcje ------------------------------------------------------
    def block(self, stop):
        stmts = []
        self.skip_nl()
        while True:
            self.expected_closer = None
            if stop():
                break
            if self.at('EOF'):
                tok = self.peek()
                raise BemolError('BML-E0024', 'brak zamknięcia bloku przed końcem pliku', tok.line)
            exp = self.expected_closer
            if self.at('NAME') and self.at('OP', '.', 1) and self.at('NAME', 'end', 2) and exp:
                tok = self.peek()
                raise BemolError('BML-E0025', f'„{tok.val}.end” nie pasuje do otwartego bloku', tok.line, tok.col,
                                 detail=f'ostatni otwarty blok to „{exp}”',
                                 help=f'{exp}.end')
            stmts.append(self.statement())
            self.skip_nl()
        return stmts

    def statement(self):
        tok = self.peek()
        v = tok.val if tok.kind == 'NAME' else None
        if tok.kind == 'NAME' and self.at('NAME', 'as', 1):
            return self.decl()
        if v == 'PERSISTENT':
            unsupported('PERSISTENT', tok.line)
        if v == 'GLOBAL':
            raise BemolError('BML-E0025', 'GLOBAL wolno deklarować tylko poza funkcjami i MAIN', tok.line, tok.col)
        if v == 'if':
            self.next()
            branches = []
            cond = self.expr(); self.expect('NAME', 'then'); self.accept('NL')
            stop = lambda: self.at('NAME', 'elseif') or self.at('NAME', 'else') or self.at_closer('if')
            branches.append((cond, self.block(stop)))
            els = None
            while self.at('NAME', 'elseif'):
                self.next()
                cond = self.expr(); self.expect('NAME', 'then'); self.accept('NL')
                branches.append((cond, self.block(stop)))
            if self.accept('NAME', 'else'):
                self.accept('NL')
                els = self.block(lambda: self.at_closer('if'))
            self.eat_closer('if')
            return Node('If', tok.line, col=tok.col, branches=branches, els=els)
        if v == 'for':
            self.next()
            var = self.expect('NAME').val
            vtype = None
            if self.accept('NAME', 'as'):
                vtype = self.typename()
            self.expect('OP', '=')
            a = self.expr(); self.expect('NAME', 'to'); b = self.expr()
            step = None
            if self.accept('NAME', 'step'):
                step = self.expr()
            self.expect('NAME', 'do'); self.accept('NL')
            body = self.block(lambda: self.at_closer('for'))
            self.eat_closer('for')
            return Node('For', tok.line, col=tok.col, var=var, vtype=vtype, a=a, b=b, step=step, body=body)
        if v == 'while':
            self.next()
            cond = self.expr(); self.expect('NAME', 'do'); self.accept('NL')
            body = self.block(lambda: self.at_closer('while'))
            self.eat_closer('while')
            return Node('While', tok.line, col=tok.col, cond=cond, body=body)
        if v == 'repeat':
            self.next(); self.accept('NL')
            body = self.block(lambda: self.at('NAME', 'until'))
            self.next()
            cond = self.expr(); self.end_of_stmt()
            return Node('Repeat', tok.line, col=tok.col, cond=cond, body=body)
        if v == 'foreach':
            self.next()
            var = self.expect('NAME').val
            idx = idxtype = None
            if self.accept('OP', ','):
                it = self.expect('NAME')
                idx = it.val
                if not self.accept('NAME', 'as'):
                    raise BemolError('BML-E0209', f'numer elementu „{idx}” w foreach musi mieć jawny typ', it.line, it.col,
                                     help=f'foreach ..., {idx} as int in ...')
                idxtype = self.typename()
            self.expect('NAME', 'in')
            src = self.expr(); self.expect('NAME', 'do'); self.accept('NL')
            body = self.block(lambda: self.at_closer('foreach'))
            self.eat_closer('foreach')
            return Node('Foreach', tok.line, col=tok.col, var=var, idx=idx, idxtype=idxtype, src=src, body=body)
        if v in ('break', 'continue'):
            self.next(); self.end_of_stmt()
            return Node(v.capitalize(), tok.line)
        if v == 'return':
            self.next()
            val = None
            if not self.at('NL') and not self.at('EOF'):
                val = self.expr()
                if self.at('OP', ','):
                    unsupported('zwracanie kilku wartości', tok.line)
            self.end_of_stmt()
            return Node('Return', tok.line, col=tok.col, value=val)
        if v == 'switch':
            unsupported('switch', tok.line)
        if v == 'keyInput':
            self.next()
            self.expect('OP', '(')
            args = []
            if not self.at('OP', ')'):
                while True:
                    if self.at('STR'):
                        st = self.next()
                        args.append(('str', st.val))
                    else:
                        reft = self.peek()
                        if not self.accept('NAME', 'REF'):
                            raise BemolError('BML-E0120', 'keyInput zmienia zmienne: napisz REF przed nazwą zmiennej',
                                             reft.line, reft.col, help='keyInput("Wybór: ", REF wybor)')
                        args.append(('ref', self.expr()))
                    if not self.accept('OP', ','):
                        break
            self.expect('OP', ')')
            self.end_of_stmt()
            return Node('KeyInput', tok.line, col=tok.col, args=args)
        if v in ('print', 'println'):
            self.next()
            self.expect('OP', '(')
            args = []
            if not self.at('OP', ')'):
                while True:
                    e = self.expr()
                    fmt = None
                    if self.accept('OP', ':'):
                        ft = self.next()
                        fmt = ft.val
                    args.append((e, fmt))
                    if not self.accept('OP', ','):
                        break
            self.expect('OP', ')')
            self.end_of_stmt()
            return Node('Print', tok.line, col=tok.col, args=args, newline=(v == 'println'))
        # przypisanie albo wyrażenie
        target = self.expr()
        if self.at('OP', ','):
            unsupported('przypisanie kilku wartości naraz', tok.line)
        if self.at('OP') and (self.peek().val == '=' or self.peek().val.endswith('=')) and self.peek().val not in ('==', '!=', '<=', '>='):
            op = self.next().val
            rhs = self.expr()
            self.end_of_stmt()
            return Node('Assign', tok.line, col=tok.col, target=target, op=op, value=rhs)
        self.end_of_stmt()
        return Node('ExprStmt', tok.line, col=tok.col, expr=target)

    # ---- wyrażenia -------------------------------------------------------
    def expr(self):
        return self.or_expr()

    def binlevel(self, sub, ops, kind='NAME'):
        left = sub()
        while self.at(kind) and self.peek().val in ops:
            tok = self.next()
            right = sub()
            left = Node('Bin', tok.line, col=tok.col, op=tok.val, l=left, r=right)
        return left

    def or_expr(self):
        return self.binlevel(self.xor_expr, ('or',))

    def xor_expr(self):
        return self.binlevel(self.and_expr, ('xor',))

    def and_expr(self):
        return self.binlevel(self.not_expr, ('and',))

    def not_expr(self):
        if self.at('NAME', 'not'):
            tok = self.next()
            return Node('Un', tok.line, col=tok.col, op='not', e=self.not_expr())
        return self.cmp_expr()

    def cmp_expr(self):
        left = self.shift_expr()
        if self.at('OP') and self.peek().val in ('==', '!=', '<', '>', '<=', '>='):
            tok = self.next()
            right = self.shift_expr()
            return Node('Bin', tok.line, col=tok.col, op=tok.val, l=left, r=right)
        if self.at('OP', '='):
            nxt = self.peek(1)
            # `if x = 5 then` – przypisanie w warunku
            for k in range(1, 6):
                t = self.peek(k)
                if t.kind == 'NAME' and t.val in ('then', 'do'):
                    tok = self.peek()
                    raise BemolError('BML-E0221', 'przypisanie `=` w warunku', tok.line, tok.col,
                                     help='do porównania służy `==`')
                if t.kind == 'NL':
                    break
        return left

    def shift_expr(self):
        return self.binlevel(self.add_expr, ('shl', 'shr', 'rol', 'ror'))

    def add_expr(self):
        return self.binlevel(self.mul_expr, ('+', '-'), 'OP')

    def mul_expr(self):
        return self.binlevel(self.as_expr, ('*', '/', '%'), 'OP')

    def as_expr(self):
        e = self.unary()
        while self.at('NAME', 'as'):
            tok = self.next()
            typ = self.typename()
            e = Node('As', tok.line, col=tok.col, e=e, type=typ)
        return e

    def unary(self):
        if self.at('OP', '-'):
            tok = self.next()
            return Node('Un', tok.line, col=tok.col, op='-', e=self.unary())
        return self.postfix()

    def postfix(self):
        tok = self.peek()
        if tok.kind == 'NUM':
            self.next(); return Node('Num', tok.line, col=tok.col, v=tok.val)
        if tok.kind == 'FLT':
            self.next(); return Node('Flt', tok.line, col=tok.col, v=tok.val)
        if tok.kind == 'LIT':
            self.next(); return Node('Lit', tok.line, col=tok.col, v=tok.val, bits=tok.bits)
        if tok.kind == 'STR':
            self.next()
            node = Node('Str', tok.line, col=tok.col, v=tok.val)
            if self.at('OP', '.'):
                self.next()
                m = self.expect('NAME').val
                if m != 'copy':
                    unsupported(f'„.{m}” na literale tekstowym', tok.line)
                return Node('StrCopy', tok.line, col=tok.col, v=tok.val)
            return node
        if self.accept('OP', '('):
            e = self.expr()
            self.expect('OP', ')')
            return e
        if tok.kind == 'NAME':
            if tok.val in ('true', 'false'):
                self.next(); return Node('Num', tok.line, col=tok.col, v=1 if tok.val == 'true' else 0, isbool=True)
            if tok.val == 'saturate':
                self.next(); self.expect('OP', '(')
                e = self.expr(); self.expect('OP', ')')
                return Node('Sat', tok.line, col=tok.col, e=e)
            if tok.val in RESERVED and tok.val not in ('this',):
                raise BemolError('BML-E0026', f'„{tok.val}” w tym miejscu jest niedozwolone', tok.line, tok.col)
            self.next()
            if self.at('OP', '('):            # wywołanie funkcji
                self.next()
                args = []
                if not self.at('OP', ')'):
                    while True:
                        ref = bool(self.accept('NAME', 'REF'))
                        args.append((self.expr(), ref))
                        if not self.accept('OP', ','):
                            break
                self.expect('OP', ')')
                return Node('Call', tok.line, col=tok.col, name=tok.val, args=args)
            segs = []
            while self.at('OP', '.'):
                self.next()
                st = self.expect('NAME', what='nazwa pola, soczewki albo operacji')
                idx = None
                if self.at('OP', '['):
                    self.next()
                    idx = []
                    if not self.at('OP', ']'):
                        while True:
                            idx.append(self.expr())
                            if not (self.accept('OP', ',') or self.accept('OP', ':')):
                                break
                    self.expect('OP', ']')
                segs.append((st.val, idx, st.line))
            if not segs:
                return Node('Name', tok.line, col=tok.col, name=tok.val)
            return Node('Chain', tok.line, col=tok.col, base=tok.val, segs=segs)
        raise BemolError('BML-E0027', f'oczekiwano wyrażenia, a jest „{tok.val}”', tok.line, tok.col)


# --------------------------------------------------------------------------
# Generator kodu C
# --------------------------------------------------------------------------

class D:
    """Opis rozwiązanego wyrażenia (zmienna, blok, soczewka...)."""

    def __init__(self, kind, **kw):
        self.kind = kind
        self.__dict__.update(kw)


def cident(name, prefix):
    out = []
    for ch in name:
        if ch.isascii() and (ch.isalnum() or ch == '_'):
            out.append(ch)
        else:
            out.append(f'_u{ord(ch):x}_')
    return prefix + ''.join(out)


def c_string(s):
    b = s.encode('utf-8')
    out = []
    for byte in b:
        ch = chr(byte)
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append('\\"')
        elif 32 <= byte < 127:
            out.append(ch)
        else:
            out.append(f'\\{byte:03o}')
    return '"' + ''.join(out) + '"', len(b)


class Gen:
    def __init__(self, items, srcname, finalbake):
        self.items = items
        self.srcname = srcname
        self.finalbake = finalbake
        self.out = []
        self.ind = 1
        self.structs = {}
        self.consts = {}
        self.aliases = {}
        self.funcs = {}
        self.globals = {}
        self.scopes = []
        self.tmpn = 0
        self.temps = []          # (nazwa, przekazany?)
        self.blockidx = None     # indeks elementu w operacji blokowej
        self.func = None
        self.line = 0
        self.col = 0
        self.warnings = []
        self.gone = {}
        self.fctx = None         # Z1: czy bieżące działanie liczone jest w doublefloat

    # ---- pomocnicze -----------------------------------------------------
    def emit(self, s):
        self.out.append('    ' * self.ind + s)

    def err(self, code, msg, line=None, help='', detail='', col=None):
        ln = line if line is not None else self.line
        if col is None:
            col = self.col if ln == self.line else 0
        raise BemolError(code, msg, ln, col, help=help, detail=detail)

    def warn(self, code, msg, line=None, detail='', help=''):
        self.warnings.append((code, msg, line if line is not None else self.line, detail, help))

    def tmp(self, prefix='_t'):
        self.tmpn += 1
        return f'{prefix}{self.tmpn}'

    def size_of(self, typ):
        if typ in TYPES:
            return TYPES[typ][1]
        if typ in self.structs:
            return self.structs[typ]['size']
        self.err('BML-E0030', f'nieznany typ „{typ}”')

    def is_num(self, typ):
        return typ in TYPES or typ in WIDE or typ in ('int_lit', 'float_lit') or (isinstance(typ, tuple) and typ[0] == 'lit')

    def is_float(self, typ):
        return typ in ('float', 'doublefloat', 'float_lit', '__widef')

    def ctype(self, typ):
        if typ in TYPES:
            return TYPES[typ][0]
        if typ in WIDE:
            return WIDE[typ]
        if typ in BLOCK_TYPES:
            return 'uint32_t'
        if typ == 'void':
            return 'void'
        if typ == 'int_lit':
            return 'int64_t'
        if typ == 'float_lit':
            return 'double'
        if isinstance(typ, tuple) and typ[0] == 'lit':
            return 'uint64_t'
        self.err('BML-E0030', f'nieznany typ „{typ}”')

    def suf(self, typ):
        return TYPES[typ][3]

    def lit_type(self, bits):
        for t, b in (('byte', 8), ('unsigned_16', 16), ('unsigned_32', 32), ('unsigned_64', 64)):
            if bits <= b:
                return t
        self.err('BML-E0031', 'literał dłuższy niż 64 bity')

    def join(self, a, b):
        def norm(t):
            if isinstance(t, tuple):
                return self.lit_type(t[1])
            return t
        a, b = norm(a), norm(b)
        if a in ('int_lit', 'float_lit') and b in ('int_lit', 'float_lit'):
            return 'doublefloat' if 'float_lit' in (a, b) else 'longint'
        if a in ('int_lit',):
            return b if b != 'bit' else 'longint'
        if b in ('int_lit',):
            return a if a != 'bit' else 'longint'
        if a == 'float_lit':
            return b if self.is_float(b) else 'doublefloat'
        if b == 'float_lit':
            return a if self.is_float(a) else 'doublefloat'
        if self.is_float(a) or self.is_float(b):
            if 'doublefloat' in (a, b):
                return 'doublefloat'
            return 'float'
        if a == 'bit' and b == 'bit':
            return 'bit'
        sa, sb = TYPES[a][1], TYPES[b][1]
        big = a if sa >= sb else b
        if TYPES[a][2] == 's' or TYPES[b][2] == 's':
            return {1: 'signed_8', 2: 'shortint', 4: 'int', 8: 'longint'}[max(sa, sb)]
        return big if big != 'bit' else 'byte'

    # ---- zasięgi ------------------------------------------------------
    def push(self, loop=False):
        self.scopes.append({'vars': {}, 'drops': [], 'loop': loop})

    def pop(self):
        sc = self.scopes.pop()
        for c in reversed(sc['drops']):
            self.emit(f'bm_drop({c});')

    def lookup(self, name):
        for sc in reversed(self.scopes):
            if name in sc['vars']:
                return sc['vars'][name]
        if name in self.globals:
            return self.globals[name]
        return None

    def declare(self, name, info, line):
        if self.lookup(name) or name in self.consts or name in self.aliases:
            self.err('BML-E0301', f'nazwa „{name}” już istnieje w tym miejscu', line,
                     help='BEMOL nie pozwala przesłaniać nazw: wybierz inną nazwę')
        if name in RESERVED or name == 'INPUT':
            self.err('BML-E0302', f'„{name}” to słowo zastrzeżone', line)
        self.scopes[-1]['vars'][name] = info

    # ---- rozwiązywanie nazw i łańcuchów --------------------------------
    def resolve(self, node):
        if node.kind == 'Name':
            return self.resolve_name(node.name, node.line)
        if node.kind == 'Chain':
            d = self.resolve_name(node.base, node.line)
            for name, idx, line in node.segs:
                d = self.segment(d, name, idx, line)
            return d
        return None

    def resolve_name(self, name, line):
        if name in self.aliases:
            return self.resolve(self.aliases[name])
        v = self.lookup(name)
        if v:
            k = v['kind']
            if k == 'static':
                return D('svar', c=v['c'], type=v['type'], name=name, const=False)
            if k == 'block':
                return D('block', c=v['c'], type=v['type'], name=name, var=v, temp=False)
            if k == 'struct':
                return D('sstruct', c=v['c'], type=v['type'], name=name)
            if k == 'lensalias':
                return D('lens', id=v['id'], type=v['type'], off=v['off'], indexed=True, constblock=v.get('constblock', False))
        if name in self.consts:
            c = self.consts[name]
            return D('svar', c=c['c'], type=c['type'], name=name, const=True)
        if name in TYPES:
            return D('num', c=f'{TYPES[name][1]}', type='int_lit', sizeof=True)
        if name in self.structs:
            return D('num', c=f'{self.structs[name]["size"]}', type='int_lit', sizeof=True)
        if name == 'INPUT':
            return D('input')
        if name == 'BUILD_MODE':
            return D('num', c='BEMOL_BUILD_MODE', type='int_lit')
        if name in ('TEST', 'FINALBAKE'):
            return D('num', c='0' if name == 'TEST' else '1', type='int_lit')
        if name in ('DEFAULT', 'CONTINUE', 'WARNING', 'HALT'):
            return D('num', c=str(('DEFAULT', 'CONTINUE', 'WARNING', 'HALT').index(name)), type='int_lit')
        if name in self.gone:
            fl = self.gone[name]
            self.err('BML-E0300', f'nieznana nazwa „{name}”', line,
                     detail=f'„{name}” istniało tylko w pętli for z linii {fl} i zniknęło po for.end',
                     help=f'jeśli wartość jest potrzebna po pętli, zadeklaruj „{name} as int” przed pętlą i pisz: for {name} = ...')
        self.err('BML-E0300', f'nieznana nazwa „{name}”', line,
                 help='zadeklaruj zmienną: nazwa as typ')

    def new_temp_block(self, cexpr, kind, const=False):
        t = self.tmp()
        self.emit(f'uint32_t {t} = {cexpr};')
        self.temps.append([t, False])
        return D('block', c=t, type='pointer', name=t, var=None, temp=True, tempkind=kind, constview=const)

    def is_const_block(self, d):
        return bool((d.var and d.var.get('constparam')) or getattr(d, 'constview', False))

    def need_ref(self, blk, what, line):
        """Specyfikacja, sekcja 3: wpis bloku w menedżerze zmienia tylko funkcja z REF."""
        v = blk.var
        if v and v.get('param') in ('PLAIN', 'CONST'):
            self.err('BML-E0420', f'{what} zmienia wpis bloku „{blk.name}” w menedżerze, a parametr nie ma REF', line,
                     detail='bez REF funkcja może zmieniać dane bloku, ale nie jego rozmiar, adres ani istnienie',
                     help=f'dodaj REF w deklaracji funkcji ({blk.name} → REF {blk.name}) i przy wywołaniu')

    def segment(self, d, name, idx, line):
        self.line = line
        ln = line
        if d.kind == 'block':
            if name == 'size':
                self.noidx(idx, name)
                return D('num', c=f'bm_size({d.c}, {ln})', type='longint')
            if name == 'shares':
                self.noidx(idx, name)
                return D('num', c=f'(int64_t)bm_shares({d.c}, {ln})', type='longint')
            if name == 'length':
                if d.type != 'text':
                    self.err('BML-E0210', '.length jest tylko dla tekstów', ln, help='rozmiar bloku w bajtach to .size')
                return D('num', c=f'(int64_t)bm_text_len({d.c}, {ln})', type='longint')
            if name == 'capacity':
                self.err('BML-E0211', '.capacity nie istnieje', ln, help='pojemność tekstu to .size')
            if name == 'viewPortion':
                self.argc(idx, 2, name)
                a, b = (self.num(x, 'longint') for x in idx)
                return self.new_temp_block(f'bm_view_portion({d.c}, {a}, {b}, {ln})', 'view', self.is_const_block(d))
            if name == 'viewRectangle':
                self.argc(idx, 5, name)
                xs = [self.num(x, 'longint') for x in idx]
                return self.new_temp_block(f'bm_view_rect({d.c}, {", ".join(xs)}, {ln})', 'view', self.is_const_block(d))
            if name == 'copyPortion':
                self.argc(idx, 2, name)
                a, b = (self.num(x, 'longint') for x in idx)
                return self.new_temp_block(f'bm_copy_portion({d.c}, {a}, {b}, {ln})', 'new')
            if name == 'copyRectangle':
                self.argc(idx, 5, name)
                xs = [self.num(x, 'longint') for x in idx]
                return self.new_temp_block(f'bm_copy_rect({d.c}, {", ".join(xs)}, {ln})', 'new')
            if name == 'copy':
                self.noidx(idx, name)
                return self.new_temp_block(f'bm_copy_all({d.c}, {ln})', 'new')
            if name in BLOCK_METHODS or name == 'rangeError':
                return D('method', block=d, name=name, idx=idx, lenstype=None, line=ln)
            if name == 'value':
                unsupported('soczewka .value', ln)
            if name in TYPES or name in self.structs:
                constblock = self.is_const_block(d)
                if idx is None:
                    return D('lens', id=d.c, type=name, off=None, indexed=False, constblock=constblock)
                self.argc(idx, 1, name)
                i = self.num(idx[0], 'longint')
                if name == 'bit':
                    return D('lens', id=d.c, type=name, off=f'({i})', indexed=True, constblock=constblock)
                return D('lens', id=d.c, type=name, off=f'(({i}) * {self.size_of(name)})', indexed=True, constblock=constblock)
            self.err('BML-E0310', f'nieznana operacja lub soczewka „.{name}”', ln,
                     help='soczewki to nazwy typów (.byte, .float, .Color...), operacje np. .size, .viewPortion')
        if d.kind == 'input':
            if name != 'read':
                self.err('BML-E0317', f'INPUT nie ma operacji „.{name}”', ln, help='odczyt wejścia: n = INPUT.read[bufor]')
            self.argc(idx, 1, name)
            b = self.resolve(idx[0]) if idx[0].kind in ('Name', 'Chain') else None
            if not b or b.kind != 'block':
                self.err('BML-E0318', 'INPUT.read wczytuje do bloku', ln, help='bufor as pointer; bufor.new[65536]; n = INPUT.read[bufor]')
            return D('num', c=f'bm_input_read({b.c}, {ln})', type='longint')
        if d.kind == 'lens':
            if name == 'at':
                # Z4: dowolny typ od dowolnego bajtu
                if d.indexed:
                    self.err('BML-E0319', '.at stoi zaraz po nazwie typu, bez [ ]', ln,
                             help='np. ptr.doublefloat.at[1009]')
                self.argc(idx, 1, name)
                i = self.num(idx[0], 'longint')
                off = f'(({i}) * 8)' if d.type == 'bit' else f'({i})'
                return D('lens', id=d.id, type=d.type, off=off, indexed=True, constblock=d.constblock)
            st = self.structs.get(d.type)
            if st and name in st['fields']:
                if not d.indexed:
                    unsupported('operacja blokowa na polu struktury', ln)
                ftype, foff = st['fields'][name]
                return D('lens', id=d.id, type=ftype, off=f'({d.off} + {foff})', indexed=True, constblock=d.constblock)
            if name == 'count' and not d.indexed:
                return D('num', c=f'(int64_t)(bm_size({d.id}, {ln}) / {self.size_of(d.type)})', type='longint')
            if name == 'fill' and not d.indexed:
                return D('method', block=D('block', c=d.id, type='pointer', var=None, temp=False, name='',
                                           constview=d.constblock),
                         name='fill', idx=idx, lenstype=d.type, line=ln)
            self.err('BML-E0311', f'„.{name}” nie pasuje do soczewki .{d.type}', ln)
        if d.kind == 'sstruct':
            st = self.structs[d.type]
            if name in st['fields']:
                ftype, foff = st['fields'][name]
                return D('sfield', base=d.c, off=foff, type=ftype)
            self.err('BML-E0312', f'struktura {d.type} nie ma pola „{name}”', ln)
        if d.kind in ('svar', 'num'):
            self.err('BML-E0313', f'zmienna nie ma pola „.{name}”', ln,
                     help='pola i soczewki mają tylko bloki (pointer, text) i struktury')
        self.err('BML-E0314', f'„.{name}” nie jest tu dozwolone', ln)

    def noidx(self, idx, name):
        if idx is not None:
            self.err('BML-E0315', f'.{name} nie przyjmuje nawiasu [ ]')

    def argc(self, idx, n, name):
        if idx is None or len(idx) != n:
            self.err('BML-E0316', f'.{name} wymaga {n} wartości w nawiasie [ ]')

    # ---- soczewki: odczyt --------------------------------------------
    def lens_off(self, d):
        if d.indexed:
            return d.off
        if self.blockidx is None:
            self.err('BML-E0320', f'soczewka .{d.type} bez indeksu oznacza cały blok',
                     help='tu potrzebny jest jeden element: dodaj indeks, np. .byte[0]')
        if d.type == 'bit':
            return self.blockidx
        return f'({self.blockidx} * {self.size_of(d.type)})'

    def lens_read(self, d, width=None):
        """Z3: soczewka czyta zawsze swoją szerokość."""
        off = self.lens_off(d)
        if d.type == 'bit':
            return f'(uint8_t)bm_read_bits({d.id}, {off}, 1, {self.line})', 'bit'
        if d.type in self.structs:
            self.err('BML-E0321', f'element typu {d.type} nie jest liczbą', help='odczytaj konkretne pole, np. .Color[0].G')
        return f'bm_rd_{self.suf(d.type)}({d.id}, {off}, {self.line})', d.type

    # ---- wyrażenia ----------------------------------------------------
    def num(self, node, want='longint'):
        saved, self.fctx = self.fctx, None
        try:
            c, t = self.expr(node, want)
        finally:
            self.fctx = saved
        if not self.is_num(t):
            self.err('BML-E0330', 'oczekiwano liczby', node.line)
        return c

    def static_width(self, node):
        """Typ zmiennej lub stałej, jeśli węzeł to sama nazwa takiej (reguła 1 szerokości)."""
        if node.kind == 'As':
            return node.type
        if node.kind != 'Name':
            return None
        try:
            d = self.resolve_name(node.name, node.line)
        except BemolError:
            return None
        if d.kind == 'svar':
            return d.type
        return None

    def cast(self, c, frm, to):
        if to is None or frm == to:
            return c
        return f'(({self.ctype(to)})({c}))'

    def expr(self, node, want=None):
        self.line = node.line
        self.col = getattr(node, 'col', 0)
        k = node.kind
        if k == 'Num':
            if node.v >= 2**63:
                return f'{node.v}ULL', 'unsigned_64'
            return f'{node.v}LL', 'int_lit'
        if k == 'Flt':
            return f'((double){node.v!r})', 'float_lit'
        if k == 'Lit':
            t = self.lit_type(node.bits)
            return f'(({self.ctype(t)}){node.v}ULL)', t
        if k in ('Str', 'StrCopy'):
            self.err('BML-E0340', 'tekst w cudzysłowie nie jest tu dozwolony', node.line,
                     help='teksty w wersji 0: zmienne text, print, porównanie ==')
        if k in ('Name', 'Chain'):
            d = self.resolve(node)
            return self.dvalue(d, want, node)
        if k == 'Call':
            return self.call(node)
        if k == 'Sat':
            return self.saturate(node, want)
        if k == 'Un':
            if node.op == '-':
                c, t = self.expr(node.e)
                if t == 'bit':
                    t = 'byte'
                return f'(-({self.tct(t)})({c}))', t
            saved, self.fctx = self.fctx, None
            c, t = self.expr(node.e)
            self.fctx = saved
            if t == 'bit':
                return f'(!({c}))', 'bit'
            if self.is_float(t):
                self.err('BML-E0335', 'not działa na liczbach całkowitych i bitach', node.line)
            return f'(~(int64_t)({c}))', t
        if k == 'Bin':
            return self.binop(node, want)
        if k == 'As':
            return self.as_conv(node)
        self.err('BML-E0341', 'nieobsługiwane wyrażenie', node.line)

    def as_conv(self, node):
        typ = node.type
        if typ not in TYPES or typ == 'pointer':
            self.err('BML-E0240', f'„as {typ}” zamienia tylko liczby', node.line,
                     help='np. wartosc as byte, licznik as float')
        saved, self.fctx = self.fctx, None
        try:
            c, t = self.expr(node.e)
        finally:
            self.fctx = saved
        if not self.is_num(t):
            self.err('BML-E0241', 'as zamienia liczbę, a tu jej nie ma', node.line)
        ct = self.ctype(typ)
        if typ == 'bit':
            if self.is_float(t):
                c = f'((int64_t)({c}))'
            return f'((uint8_t)(({c}) & 1))', 'bit'
        if self.is_float(t) and not self.is_float(typ):
            # ułamek odcięty, potem najmłodsza część
            return f'(({ct})(int64_t)({c}))', typ
        return f'(({ct})({c}))', typ

    def dvalue(self, d, want, node):
        if d.kind == 'num':
            return d.c, d.type
        if d.kind == 'svar':
            return d.c, d.type
        if d.kind == 'sfield':
            return f'bm_ld_{self.suf(d.type)}({d.base} + {d.off})', d.type
        if d.kind == 'lens':
            return self.lens_read(d)
        if d.kind == 'block':
            return d.c, 'pointer' if d.type != 'text' else 'text'
        if d.kind == 'sstruct':
            self.err('BML-E0342', 'cała struktura nie jest liczbą', node.line)
        if d.kind == 'method':
            self.err('BML-E0343', f'.{d.name} to operacja, nie wartość', node.line)
        self.err('BML-E0344', 'nieobsługiwana wartość', node.line)

    def saturate(self, node, want):
        target = want
        if target is None or target not in TYPES:
            _, t0 = self.dry_type(node.e)
            t0 = self.norm(t0)
            target = t0 if t0 in TYPES else 'longint'
        if target == 'bit':
            target = 'byte'
        c, t = self.expr(node.e)
        if self.is_float(target):
            return f'bm_sat_{self.suf(target)}((long double)({c}))', target
        if self.is_float(t):
            return f'bm_sat_{self.suf(target)}((bm_wide)(long double)({c}))', target
        return f'bm_sat_{self.suf(target)}((bm_wide)({c}))', target

    def norm(self, t):
        if isinstance(t, tuple):
            return self.lit_type(t[1])
        if t == 'int_lit':
            return 'longint'
        if t == 'float_lit':
            return 'doublefloat'
        return t

    def tct(self, *types):
        """Z1: typ stołu w C: double, gdy działanie jest zmiennoprzecinkowe, inaczej 64 bity."""
        if self.fctx or any(self.is_float(t) for t in types):
            return 'double'
        if 'unsigned_64' in types:
            return 'uint64_t'
        return 'int64_t'

    def has_float(self, node):
        """Czy w działaniu (bez wchodzenia w nawiasy kwadratowe, wywołania i as) jest liczba zmiennoprzecinkowa."""
        k = node.kind
        if k == 'Flt':
            return True
        if k in ('Num', 'Lit', 'Str'):
            return False
        if k == 'As':
            return self.is_float(node.type)
        if k == 'Un':
            return self.has_float(node.e)
        if k == 'Sat':
            return self.has_float(node.e)
        if k == 'Bin':
            if node.op in ('==', '!=', '<', '>', '<=', '>=', 'and', 'or'):
                return False
            if node.op in ('shl', 'shr', 'rol', 'ror'):
                return self.has_float(node.l)
            return self.has_float(node.l) or self.has_float(node.r)
        try:
            _, t = self.dry_type(node)
        except BemolError:
            return False
        return self.is_float(t)

    def dry_type(self, node):
        """Typ wyrażenia bez emitowania kodu (dla saturate bez celu)."""
        saved = (len(self.out), self.tmpn, list(self.temps), self.fctx)
        try:
            return self.expr(node)
        finally:
            del self.out[saved[0]:]
            self.tmpn, self.temps, self.fctx = saved[1], saved[2], saved[3]

    def binop(self, node, want):
        op = node.op
        if op in ('==', '!=', '<', '>', '<=', '>='):
            return self.compare(node)
        if op in ('and', 'or'):
            saved, self.fctx = self.fctx, None
            lc, lt = self.expr(node.l)
            rc, rt = self.expr(node.r)
            self.fctx = saved
            if lt == 'bit' and rt == 'bit':
                return f'({lc} {"&&" if op == "and" else "||"} {rc})', 'bit'
            if self.is_float(lt) or self.is_float(rt):
                self.err('BML-E0335', f'{op} działa na liczbach całkowitych i bitach', node.line)
            ct = self.tct(lt, rt)
            return f'(({ct})({lc}) {"&" if op == "and" else "|"} ({ct})({rc}))', self.join(lt, rt)
        # Z1: początek działania ustala, czy całe działanie jest zmiennoprzecinkowe
        outer = self.fctx is None
        if outer:
            self.fctx = self.has_float(node)
        try:
            if op == 'xor':
                lc, lt = self.expr(node.l)
                rc, rt = self.expr(node.r)
                if self.is_float(lt) or self.is_float(rt):
                    self.err('BML-E0335', 'xor działa na liczbach całkowitych i bitach', node.line)
                ct = 'uint64_t' if 'unsigned_64' in (lt, rt) else 'int64_t'
                return f'(({ct})({lc}) ^ ({ct})({rc}))', self.join(lt, rt)
            if op in ('shl', 'shr', 'rol', 'ror'):
                saved, self.fctx = self.fctx, None
                lc, lt = self.expr(node.l)
                rc, _ = self.num(node.r, 'int'), None
                self.fctx = saved
                if self.is_float(lt):
                    self.err('BML-E0336', f'{op} działa na liczbach całkowitych', node.line)
                if op == 'shl':
                    ct = 'uint64_t' if lt == 'unsigned_64' else 'int64_t'
                    return f'(({ct})((uint64_t)({lc}) << ({rc})))', lt
                if op == 'shr':
                    ct = 'uint64_t' if lt == 'unsigned_64' else 'int64_t'
                    return f'(({ct})({lc}) >> ({rc}))', lt
                # rotacja w szerokości lewego składnika (Z3: w ramach soczewki)
                nt = self.norm(lt)
                if nt == 'bit':
                    nt = 'byte'
                ut = {1: 'u8', 2: 'u16', 4: 'u32', 8: 'u64'}[self.size_of(nt)]
                return f'((int64_t)bm_{op}_{ut}(({self.ctype(nt)})({lc}), {rc}))', nt
            lc, lt = self.expr(node.l)
            rc, rt = self.expr(node.r)
            t = self.join(lt, rt)
            if t == 'bit':
                t = 'byte'
            ct = self.tct(lt, rt)
            if ct == 'double' and not self.is_float(t):
                t = 'doublefloat'
            cop = {'%': '%'}.get(op, op)
            if op == '%' and ct == 'double':
                return f'fmod((double)({lc}), (double)({rc}))', t
            return f'(({ct})({lc}) {cop} ({ct})({rc}))', t
        finally:
            if outer:
                self.fctx = None

    def compare(self, node):
        op = node.op
        l, r = node.l, node.r
        # teksty
        for a, b in ((l, r), (r, l)):
            if b.kind == 'Str' and a.kind in ('Name', 'Chain'):
                d = self.resolve(a)
                if d.kind == 'block' and d.type == 'text' and op in ('==', '!='):
                    s, n = c_string(b.v)
                    neg = '!' if op == '!=' else ''
                    return f'({neg}bm_text_eq({d.c}, {s}, {n}, {node.line}))', 'bit'
        saved, self.fctx = self.fctx, None
        try:
            lc, lt = self.expr(l)
            self.fctx = None
            rc, rt = self.expr(r)
        finally:
            self.fctx = saved
        if lt in BLOCK_TYPES or rt in BLOCK_TYPES:
            if lt == 'text' and rt == 'text' and op in ('==', '!='):
                neg = '!' if op == '!=' else ''
                return (f'({neg}bm_text_eq({lc}, (const char *)(uintptr_t)bm_T[{rc}].addr, '
                        f'bm_text_len({rc}, {node.line}), {node.line}))'), 'bit'
            return f'({lc} {op} {rc})', 'bit'
        if lt == 'bit' and rt == 'bit':
            return f'({lc} {op} {rc})', 'bit'
        # Z1: porównanie na stole
        ct = self.tct(lt, rt)
        return f'(({ct})({lc}) {op} ({ct})({rc}))', 'bit'

    def call(self, node):
        f = self.funcs.get(node.name)
        if not f:
            if node.name in ('print', 'println'):
                self.err('BML-E0350', f'{node.name} to instrukcja, nie wartość', node.line)
            self.err('BML-E0351', f'nieznana funkcja „{node.name}”', node.line)
        if len(node.args) != len(f['params']):
            self.err('BML-E0352', f'{node.name} przyjmuje {len(f["params"])} parametry, podano {len(node.args)}', node.line)
        cargs = []
        seen = {}
        for (arg, ref), (pname, ptype, mod) in zip(node.args, f['params']):
            if mod == 'REF' and not ref:
                self.err('BML-E0353', f'parametr „{pname}” jest REF: napisz REF także przy wywołaniu', arg.line,
                         help=f'{node.name}(..., REF {pname} ...)')
            if ref and mod != 'REF':
                self.err('BML-E0355', f'parametr „{pname}” nie jest REF', arg.line)
            if ptype in BLOCK_TYPES:
                d = self.resolve(arg) if arg.kind in ('Name', 'Chain') else None
                if not d or d.kind != 'block':
                    self.err('BML-E0356', f'parametr „{pname}” wymaga bloku', arg.line)
                if self.is_const_block(d) and mod != 'CONST':
                    self.err('BML-E0422', f'blok „{d.name}” jest tu CONST, a parametr „{pname}” pozwala go zmieniać', arg.line,
                             detail='CONST obowiązuje do końca funkcji, także w funkcjach, które ona wywołuje',
                             help=f'oznacz parametr jako CONST {pname} albo przekaż kopię: {d.name}.copy')
                if mod == 'REF':
                    if d.temp:
                        self.err('BML-E0354', 'REF wymaga zmiennej, a nie widoku ani kopii', arg.line)
                    if d.var and d.var.get('param') in ('PLAIN', 'CONST'):
                        self.need_ref(d, 'przekazanie przez REF', arg.line)
                key = d.c
                if not d.temp:
                    if key in seen and (seen[key] != 'CONST' or mod != 'CONST'):
                        self.err('BML-E0423', f'blok „{d.name}” trafia do dwóch parametrów naraz', arg.line,
                                 detail='zapis przez jeden parametr zmieniałby drugi, a .release zwalniałoby go w trakcie funkcji',
                                 help='przekaż kopię (.copy) albo zmień funkcję tak, by dostała blok raz')
                    seen[key] = mod or 'PLAIN'
                cargs.append(f'&{d.c}' if mod == 'REF' else d.c)
                continue
            if mod == 'REF':
                d = self.resolve(arg) if arg.kind == 'Name' else None
                if not d or d.kind != 'svar' or d.const:
                    self.err('BML-E0354', 'REF wymaga zmiennej', arg.line)
                cargs.append(f'&{d.c}')
                continue
            cargs.append(self.value_for(ptype, arg))
        return f'{cident(node.name, "f_")}({", ".join(cargs)})', f['ret']

    # ---- instrukcje ----------------------------------------------------
    def stmts(self, body):
        for s in body:
            self.stmt(s)

    def stmt(self, s):
        self.line = s.line
        self.col = getattr(s, 'col', 0)
        outer = self.temps
        self.temps = []
        getattr(self, 'st_' + s.kind)(s)
        # tymczasowe widoki i kopie żyją do końca instrukcji
        for t, passed in self.temps:
            if not passed:
                self.emit(f'bm_drop({t});')
        self.temps = outer

    def st_Decl(self, s):
        typ = s.type
        if typ in ('pointer', 'text'):
            c = cident(s.name, 'v_')
            info = {'kind': 'block', 'type': typ, 'c': c}
            self.declare(s.name, info, s.line)
            self.emit(f'uint32_t {c} = 0;')
            self.scopes[-1]['drops'].append(c)
            if getattr(s, 'newsize', None) is not None:
                self.method(D('method', block=D('block', c=c, type=typ, var=info, temp=False, name=s.name),
                              name='new', idx=[s.newsize], lenstype=None, line=s.line), s.line)
            if s.init is not None:
                self.assign_block(D('block', c=c, type=typ, var=info, temp=False, name=s.name), s.init, s.line)
            return
        if typ in self.structs:
            c = cident(s.name, 'v_')
            self.declare(s.name, {'kind': 'struct', 'type': typ, 'c': c}, s.line)
            self.emit(f'uint8_t {c}[{self.structs[typ]["size"]}] = {{0}};')
            if s.init is not None:
                unsupported('inicjalizacja struktury przy deklaracji', s.line)
            return
        if typ not in TYPES:
            if typ == 'halffloat':
                unsupported('halffloat', s.line)
            if typ.startswith('unsigned_') or typ.startswith('signed_'):
                unsupported(f'typ {typ} (nietypowa szerokość)', s.line)
            self.err('BML-E0030', f'nieznany typ „{typ}”', s.line)
        c = cident(s.name, 'v_')
        init = '0'
        if s.init is not None:
            init = self.value_for(typ, s.init)
        self.declare(s.name, {'kind': 'static', 'type': typ, 'c': c}, s.line)
        self.emit(f'{self.ctype(typ)} {c} = {init};')

    def value_for(self, typ, node):
        """Z2: wartość wyrażenia dopasowana do worka typu typ dopiero przy zapisie."""
        saved, self.fctx = self.fctx, None
        try:
            c, t = self.expr(node, typ)
        finally:
            self.fctx = saved
        return self.fit(c, t, typ)

    def fit(self, c, t, typ):
        if t in BLOCK_TYPES or t in self.structs:
            self.err('BML-E0330', 'oczekiwano liczby')
        if typ == 'bit':
            if self.is_float(t):
                c = f'((int64_t)({c}))'
            return f'((uint8_t)(({c}) & 1))'
        ct = self.ctype(typ)
        if self.is_float(t) and not self.is_float(typ):
            if typ == 'unsigned_64':
                return f'(({ct})(long double)({c}))'
            return f'(({ct})(int64_t)({c}))'
        return f'(({ct})({c}))'

    def bitfix(self, typ, c):
        return f'((uint8_t)(({c}) & 1))' if typ == 'bit' else c

    def assign_block(self, tgt, value, line):
        if value.kind in ('Str', 'StrCopy'):
            if tgt.type != 'text':
                self.err('BML-E0360', 'tekst można przypisać tylko do zmiennej typu text', line)
            s, n = c_string(value.v)
            self.emit(f'bm_text_set(&{tgt.c}, {s}, {n}, {line});')
            return
        if value.kind == 'Call':
            c, t = self.call(value)
            if t not in BLOCK_TYPES:
                self.err('BML-E0361', 'funkcja nie zwraca bloku', line)
            self.emit(f'bm_assign_new(&{tgt.c}, {c});')
            return
        d = self.resolve(value) if value.kind in ('Name', 'Chain') else None
        if not d or d.kind != 'block':
            self.err('BML-E0362', 'zmiennej pointer można przypisać tylko blok, widok albo kopię', line)
        # CONST obowiązuje do końca funkcji: zmienna wskazująca blok CONST też jest tylko do odczytu
        if self.is_const_block(d) and tgt.var is not None:
            tgt.var['constparam'] = True
        if d.temp:
            for t in self.temps:
                if t[0] == d.c:
                    t[1] = True
            self.emit(f'bm_assign_new(&{tgt.c}, {d.c});')
        else:
            self.emit(f'bm_assign(&{tgt.c}, {d.c});')

    def check_writable(self, d, line):
        if getattr(d, 'constblock', False):
            self.err('BML-E0305', 'zapis do bloku przekazanego jako CONST', line,
                     help='parametr CONST jest tylko do odczytu')

    def st_Assign(self, s):
        op = s.op
        tgt = s.target
        if tgt.kind not in ('Name', 'Chain'):
            self.err('BML-E0370', 'lewa strona przypisania musi być zmienną albo fragmentem bloku', s.line)
        d = self.resolve(tgt)
        if d.kind == 'method' and d.name == 'rangeError':
            c = self.num(s.value, 'int')
            self.emit(f'bm_set_range({d.block.c}, (int)({c}), {s.line});')
            return
        if d.kind == 'svar':
            if d.const:
                self.err('BML-E0371', f'„{d.name}” to stała CONST', s.line)
            if op == '=':
                self.emit(f'{d.c} = {self.value_for(d.type, s.value)};')
            else:
                self.emit(f'{d.c} = {self.compound(d.c, d.type, op, s.value)};')
            return
        if d.kind == 'sfield':
            if op == '=':
                v = self.value_for(d.type, s.value)
            else:
                v = self.compound(f'bm_ld_{self.suf(d.type)}({d.base} + {d.off})', d.type, op, s.value)
            self.emit(f'bm_st_{self.suf(d.type)}({d.base} + {d.off}, {v});')
            return
        if d.kind == 'block':
            if d.temp and d.tempkind == 'view':
                if op != '=':
                    self.err('BML-E0372', 'na widoku dozwolone jest tylko przypisanie =', s.line)
                src = self.resolve(s.value) if s.value.kind in ('Name', 'Chain') else None
                if not src or src.kind != 'block':
                    self.err('BML-E0373', 'widokowi można przypisać tylko inny widok lub blok (kopia danych)', s.line)
                if self.is_const_block(d):
                    self.check_writable(D('lens', constblock=True), s.line)
                self.emit(f'bm_copy_view({d.c}, {src.c}, {s.line});')
                return
            if op != '=':
                if d.type == 'text' and op == '+=':
                    self.err('BML-E0374', 'dopisywanie do tekstu to .append[...]', s.line)
                self.err('BML-E0375', f'{op} nie działa na bloku', s.line, help='operacje na danych: użyj soczewki, np. ptr.byte += 1')
            self.need_ref(d, 'przypisanie innego bloku', s.line)
            self.assign_block(d, s.value, s.line)
            return
        if d.kind == 'lens':
            self.check_writable(d, s.line)
            if d.indexed:
                self.assign_lens(d, op, s.value, s.line)
            else:
                self.block_op(d, op, s.value, s.line)
            return
        self.err('BML-E0376', 'tego nie można przypisać', s.line)

    def compound(self, cur, typ, op, value):
        """x op= v: działanie na stole (Z1), dopasowanie do worka przy zapisie (Z2)."""
        base = op[:-1]
        cop = {'+': '+', '-': '-', '*': '*', '/': '/', '%': '%', 'xor': '^', 'and': '&', 'or': '|',
               'shl': '<<', 'shr': '>>'}.get(base)
        if base in ('rol', 'ror'):
            rc = self.num(value, 'int')
            nt = 'byte' if typ == 'bit' else typ
            ut = {1: 'u8', 2: 'u16', 4: 'u32', 8: 'u64'}[self.size_of(nt)]
            return f'(({self.ctype(typ)})bm_{base}_{ut}(({self.ctype(nt)})({cur}), {rc}))'
        if cop is None:
            self.err('BML-E0377', f'nieznany operator {op}')
        if base in ('shl', 'shr'):
            if self.is_float(typ):
                self.err('BML-E0336', f'{base} działa na liczbach całkowitych')
            rc = self.num(value, 'int')
            ct = 'uint64_t' if typ == 'unsigned_64' else 'int64_t'
            if base == 'shl':
                return self.fit(f'(({ct})((uint64_t)({cur}) << ({rc})))', typ, typ)
            return self.fit(f'(({ct})({cur}) >> ({rc}))', typ, typ)
        saved, self.fctx = self.fctx, None
        try:
            self.fctx = self.is_float(typ) or self.has_float(value)
            rc, rt = self.expr(value)
        finally:
            self.fctx = saved
        if base in ('xor', 'and', 'or'):
            if self.is_float(typ) or self.is_float(rt):
                self.err('BML-E0335', f'{base} działa na liczbach całkowitych i bitach')
            ct = 'uint64_t' if 'unsigned_64' in (typ, rt) else 'int64_t'
        else:
            ct = 'double' if (self.is_float(typ) or self.has_float(value)) else self.tct(typ, rt)
        if base == '%' and ct == 'double':
            return self.fit(f'fmod((double)({cur}), (double)({rc}))', 'doublefloat', typ)
        res = f'(({ct})({cur}) {cop} ({ct})({rc}))'
        return self.fit(res, 'doublefloat' if ct == 'double' else 'longint', typ)

    def assign_lens(self, d, op, value, line):
        off = self.lens_off(d)
        if op != '=':
            cur, _ = self.lens_read(d)
            v = self.compound(cur, d.type, op, value)
            self.write_lens(d, off, d.type, v, line)
            return
        if value.kind == 'Lit':
            bitoff = off if d.type == 'bit' else f'(({off}) * 8)'
            self.emit(f'bm_write_bits({d.id}, {bitoff}, {value.bits}, {value.v}ULL, {line});')
            return
        if value.kind == 'Chain':
            src = self.resolve(value)
            if src.kind == 'lens' and (d.type in self.structs or src.type in self.structs):
                n = self.size_of(d.type)
                b = self.tmp('_b')
                self.emit(f'{{ uint8_t {b}[{n}]; bm_read({src.id}, {self.lens_off(src)}, {b}, {n}, {line}); '
                          f'bm_write({d.id}, {off}, {b}, {n}, {line}); }}')
                return
        if d.type in self.structs:
            self.err('BML-E0378', f'element .{d.type} można przypisać tylko z innego elementu', line)
        v = self.value_for(d.type, value)
        self.write_lens(d, off, d.type, v, line)

    def write_lens(self, d, off, typ, v, line):
        if d.type == 'bit':
            self.emit(f'bm_write_bits({d.id}, {off}, 1, (({v}) & 1), {line});')
            return
        self.emit(f'bm_wr_{self.suf(typ)}({d.id}, {off}, {v}, {line});')

    def block_op(self, d, op, value, line):
        if d.type in self.structs:
            unsupported('operacja blokowa na strukturach', line)
        size = 1 if d.type == 'bit' else self.size_of(d.type)
        i = self.tmp('_i')
        b = self.tmp('_blk')
        n = self.tmp('_n')
        count = f'bm_size({b}, {line}) * 8' if d.type == 'bit' else f'(bm_size({b}, {line}) + {size - 1}) / {size}'
        self.emit(f'{{ uint32_t {b} = {d.id};')
        self.emit(f'  uint64_t {n} = {count};')
        self.emit(f'  for (uint64_t {i} = 0; {i} < {n}; {i}++) {{')
        saved = self.blockidx
        self.blockidx = i
        self.ind += 1
        el = D('lens', id=b, type=d.type, off=None, indexed=False, constblock=False)
        off = self.lens_off(el)
        if op == '=':
            v = self.value_for(d.type, value)
        else:
            cur, _ = self.lens_read(el)
            v = self.compound(cur, d.type, op, value)
        self.write_lens(el, off, d.type, v, line)
        self.ind -= 1
        self.blockidx = saved
        self.emit('  }')
        self.emit('}')

    def st_ExprStmt(self, s):
        e = s.expr
        if e.kind == 'Call':
            c, _ = self.call(e)
            self.emit(f'{c};')
            return
        if e.kind == 'Chain':
            d = self.resolve(e)
            if d.kind == 'method':
                return self.method(d, s.line)
        self.err('BML-E0380', 'ta instrukcja nic nie robi', s.line,
                 help='może brakuje przypisania albo operacji, np. ptr.new[1024]')

    def method(self, d, line):
        blk = d.block
        name, idx = d.name, d.idx
        if name in ('new', 'update', 'release', 'append'):
            self.need_ref(blk, f'.{name}', line)
        if name in ('clear', 'fill', 'append') and self.is_const_block(blk):
            self.check_writable(D('lens', constblock=True), line)
        if name == 'new':
            if blk.temp or blk.var is None:
                self.err('BML-E0381', '.new dotyczy zmiennej, nie widoku ani kopii', line)
            if blk.type == 'text':
                self.argc(idx, 1, name)
                n = self.num(idx[0], 'longint')
                self.emit(f'bm_new(&{blk.c}, {n}, {line}); bm_T[{blk.c}].flags |= BM_TEXT; bm_T[{blk.c}].kind = 0;')
                return
            self.argc(idx, 1, name)
            self.emit(f'bm_new(&{blk.c}, {self.num(idx[0], "longint")}, {line});')
            return
        if name == 'update':
            self.argc(idx, 1, name)
            self.emit(f'bm_update({blk.c}, {self.num(idx[0], "longint")}, {line});')
            return
        if name == 'release':
            self.noidx(idx, name)
            self.emit(f'bm_release({blk.c}, {line});')
            return
        if name == 'clear':
            self.noidx(idx, name)
            self.emit(f'{{ uint8_t _z = 0; bm_fill({blk.c}, &_z, 1, {line}); }}')
            return
        if name == 'append':
            if blk.type != 'text':
                self.err('BML-E0382', '.append działa na tekstach', line)
            self.argc(idx, 1, name)
            v = idx[0]
            if v.kind == 'Str':
                s, n = c_string(v.v)
                self.emit(f'bm_text_append(&{blk.c}, {s}, {n}, {line});')
                return
            src = self.resolve(v) if v.kind in ('Name', 'Chain') else None
            if src and src.kind == 'block' and src.type == 'text':
                self.emit(f'bm_text_append(&{blk.c}, (const char *)(uintptr_t)bm_T[{src.c}].addr, bm_text_len({src.c}, {line}), {line});')
                return
            self.err('BML-E0383', '.append przyjmuje tekst', line)
        if name == 'fill':
            self.argc(idx, 1, name)
            v = idx[0]
            p = self.tmp('_p')
            if d.lenstype:
                lt = d.lenstype
                if lt in self.structs:
                    src = self.resolve(v) if v.kind == 'Chain' else None
                    if not src or src.kind != 'lens':
                        self.err('BML-E0384', f'wzór dla .{lt}.fill musi być elementem .{lt}', line)
                    n = self.size_of(lt)
                    self.emit(f'{{ uint8_t {p}[{n}]; bm_read({src.id}, {self.lens_off(src)}, {p}, {n}, {line}); '
                              f'bm_fill({blk.c}, {p}, {n}, {line}); }}')
                    return
                if lt == 'bit':
                    unsupported('.bit.fill', line)
                c = self.value_for(lt, v)
                self.emit(f'{{ {self.ctype(lt)} {p} = {c}; bm_fill({blk.c}, &{p}, sizeof {p}, {line}); }}')
                return
            if v.kind == 'Lit':
                if v.bits % 8:
                    unsupported('wzór .fill o długości niebędącej wielokrotnością bajtu', line)
                nb = v.bits // 8
                bs = ', '.join(str((v.v >> (8 * k)) & 0xFF) for k in range(nb))
                self.emit(f'{{ uint8_t {p}[{nb}] = {{{bs}}}; bm_fill({blk.c}, {p}, {nb}, {line}); }}')
                return
            if v.kind in ('Num', 'Flt') or (v.kind == 'Un' and v.e.kind in ('Num', 'Flt')):
                self.err('BML-E0387', 'liczba dziesiętna nie ma szerokości, więc nie wiadomo, jak długi jest wzór', line,
                         detail='szerokość wzoru wyznacza soczewka, typ zmiennej albo literał szesnastkowy / binarny (sekcja 6)',
                         help='np. blok.byte.fill[5], blok.float.fill[1.5] albo blok.fill[&05h]')
            w = self.static_width(v)
            if w:
                c, _ = self.expr(v)
                self.emit(f'{{ {self.ctype(w)} {p} = {c}; bm_fill({blk.c}, &{p}, sizeof {p}, {line}); }}')
                return
            if v.kind == 'Name':
                sd = self.resolve(v)
                if sd.kind == 'sstruct':
                    self.emit(f'bm_fill({blk.c}, {sd.c}, {self.size_of(sd.type)}, {line});')
                    return
            self.err('BML-E0385', 'nie wiadomo, jaką szerokość ma wzór dla .fill', line,
                     help='użyj zmiennej, literału albo soczewki, np. ptr.float.fill[1.5]')
        self.err('BML-E0386', f'.{name} nie jest tu dozwolone', line)

    def cond(self, node):
        c, t = self.expr(node)
        if t != 'bit':
            self.err('BML-E0220', 'warunek musi mieć typ bit', node.line,
                     help='porównaj jawnie, np. `if licznik != 0 then`')
        return c

    def st_If(self, s):
        first = True
        for cond, body in s.branches:
            c = self.cond(cond)
            self.emit(f'{"if" if first else "} else if"} ({c}) {{')
            first = False
            self.ind += 1; self.push(); self.stmts(body); self.pop(); self.ind -= 1
        if s.els is not None:
            self.emit('} else {')
            self.ind += 1; self.push(); self.stmts(s.els); self.pop(); self.ind -= 1
        self.emit('}')

    def int_only(self, node, what):
        if node is None:
            return
        _, t = self.dry_type(node)
        if self.is_float(t):
            self.err('BML-E0207', f'pętla for przyjmuje tylko liczby całkowite ({what})', node.line,
                     col=getattr(node, 'col', 0),
                     help='licz licznik całkowity, a wartość ułamkową w środku: for i as int = 0 to 100 do ... x = i * 0.01')

    INT_RANGE = {'byte': (0, 255), 'unsigned_8': (0, 255), 'unsigned_16': (0, 65535),
                 'unsigned_32': (0, 2**32 - 1), 'unsigned_64': (0, 2**63 - 1),
                 'signed_8': (-128, 127), 'shortint': (-32768, 32767),
                 'int': (-2**31, 2**31 - 1), 'longint': (-2**63, 2**63 - 1)}

    def lit_value(self, node):
        if node is None:
            return None
        if node.kind == 'Num':
            return node.v
        if node.kind == 'Un' and node.op == '-' and node.e.kind == 'Num':
            return -node.e.v
        return None

    def st_For(self, s):
        for n, w in ((s.a, 'początek'), (s.b, 'koniec'), (s.step, 'krok')):
            self.int_only(n, w)
        if s.vtype is not None:
            typ = s.vtype
            if typ not in self.INT_RANGE:
                self.err('BML-E0204', f'licznik pętli for musi być liczbą całkowitą, a {typ} nią nie jest', s.line, col=s.col,
                         help=f'for {s.var} as int = ...')
            existing = None
        else:
            existing = self.lookup(s.var)
            if existing is None and s.var not in self.consts:
                self.err('BML-E0208', f'licznik pętli „{s.var}” nie ma typu', s.line, col=s.col,
                         detail='licznik może być nową zmienną pętli albo zmienną zadeklarowaną wcześniej',
                         help=f'for {s.var} as int = ...   albo   {s.var} as int przed pętlą, a potem for {s.var} = ...')
            if existing is None or existing['kind'] != 'static':
                self.err('BML-E0203', f'„{s.var}” nie może być licznikiem pętli', s.line, col=s.col,
                         help='licznik to zmienna liczbowa całkowita (nie stała, nie blok)')
            typ = existing['type']
            if typ not in self.INT_RANGE:
                self.err('BML-E0204', f'licznik pętli for musi być liczbą całkowitą, a „{s.var}” ma typ {typ}', s.line)
        lo, hi = self.INT_RANGE[typ]
        # zakres znany już przy kompilacji
        for n in (s.a, s.b):
            v = self.lit_value(n)
            if v is not None and not lo <= v <= hi:
                self.err('BML-E0206', f'{v} nie mieści się w liczniku typu {typ}', n.line, col=getattr(n, 'col', 0),
                         detail=f'{typ} mieści {lo}...{hi}', help=f'wybierz szerszy typ licznika, np. for {s.var} as int = ...')
        sv = self.lit_value(s.step)
        if sv == 0:
            self.err('BML-E0205', 'krok pętli for wynosi 0', s.step.line, col=getattr(s.step, 'col', 0),
                     help='podaj krok różny od 0')
        a = self.num(s.a, 'longint')
        b = self.num(s.b, 'longint')
        st_c = self.num(s.step, 'longint') if s.step is not None else '1'
        k, bt, st = self.tmp('_k'), self.tmp('_end'), self.tmp('_st')
        self.emit(f'{{ int64_t {k} = {a}; int64_t {bt} = {b}; int64_t {st} = {st_c};')
        self.emit(f'  bm_for_check({k}, {bt}, {st}, {cnum(lo)}, {cnum(hi)}, "{s.var}", "{typ}", {s.line});')
        self.emit(f'for (; {st} > 0 ? {k} <= {bt} : {k} >= {bt}; {k} += {st}) {{')
        self.ind += 1
        self.push(loop=True)
        if existing is None:
            c = cident(s.var, 'v_')
            self.declare(s.var, {'kind': 'static', 'type': typ, 'c': c}, s.line)
            self.emit(f'{self.ctype(typ)} {c} = ({self.ctype(typ)}){k};')
        else:
            self.emit(f'{existing["c"]} = ({self.ctype(typ)}){k};')
        self.push()
        self.stmts(s.body)
        self.pop()
        self.pop()
        self.ind -= 1
        self.emit('}}')
        if existing is None:
            self.gone[s.var] = s.line

    def st_While(self, s):
        self.temps = []
        c = self.cond(s.cond)
        if self.temps:
            self.err('BML-E0901', 'widok lub kopia w warunku pętli', s.line, help='utwórz widok przed pętlą')
        self.emit(f'while ({c}) {{')
        self.ind += 1; self.push(loop=True); self.stmts(s.body); self.pop(); self.ind -= 1
        self.emit('}')

    def st_Repeat(self, s):
        self.emit('do {')
        self.ind += 1; self.push(loop=True); self.stmts(s.body); self.pop(); self.ind -= 1
        self.temps = []
        c = self.cond(s.cond)
        if self.temps:
            self.err('BML-E0901', 'widok lub kopia w warunku pętli', s.line)
        self.emit(f'}} while (!({c}));')

    def st_Foreach(self, s):
        d = self.resolve(s.src) if s.src.kind == 'Chain' else None
        if not d or d.kind != 'lens' or d.indexed:
            self.err('BML-E0390', 'foreach przechodzi po soczewce bloku, np. foreach px in obraz.Color', s.line)
        size = 1 if d.type == 'bit' else self.size_of(d.type)
        b, n, i = self.tmp('_fb'), self.tmp('_fn'), self.tmp('_fi')
        count = f'bm_size({b}, {s.line}) * 8' if d.type == 'bit' else f'bm_size({b}, {s.line}) / {size}'
        self.emit(f'{{ uint32_t {b} = {d.id}; uint64_t {n} = {count};')
        self.emit(f'for (uint64_t {i} = 0; {i} < {n}; {i}++) {{')
        self.ind += 1
        self.push(loop=True)
        off = i if d.type == 'bit' else f'({i} * {size})'
        self.declare(s.var, {'kind': 'lensalias', 'id': b, 'type': d.type, 'off': off,
                             'constblock': d.constblock}, s.line)
        if s.idx:
            it = s.idxtype
            if it not in self.INT_RANGE:
                self.err('BML-E0204', f'numer elementu w foreach musi być liczbą całkowitą, a {it} nią nie jest', s.line)
            lo, hi = self.INT_RANGE[it]
            self.emit(f'if ({i} == 0) bm_for_check(0, (int64_t){n} - 1, 1, {cnum(lo)}, {cnum(hi)}, "{s.idx}", "{it}", {s.line});')
            ci = cident(s.idx, 'v_')
            self.declare(s.idx, {'kind': 'static', 'type': it, 'c': ci}, s.line)
            self.emit(f'{self.ctype(it)} {ci} = ({self.ctype(it)}){i};')
        saved_temps = self.temps
        self.stmts(s.body)
        self.temps = saved_temps
        self.pop()
        self.ind -= 1
        self.emit('}}')

    def loop_drops(self):
        for sc in reversed(self.scopes):
            for c in reversed(sc['drops']):
                self.emit(f'bm_drop({c});')
            if sc['loop']:
                return

    def st_Break(self, s):
        if not any(sc['loop'] for sc in self.scopes):
            self.err('BML-E0391', 'break poza pętlą', s.line)
        self.loop_drops()
        self.emit('break;')

    def st_Continue(self, s):
        if not any(sc['loop'] for sc in self.scopes):
            self.err('BML-E0392', 'continue poza pętlą', s.line)
        self.loop_drops()
        self.emit('continue;')

    def all_drops(self):
        for sc in reversed(self.scopes):
            for c in reversed(sc['drops']):
                self.emit(f'bm_drop({c});')

    def st_Return(self, s):
        ret = self.func['ret']
        if self.func['name'] == 'MAIN':
            v = self.num(s.value, 'int') if s.value is not None else '0'
            self.emit(f'{{ int _rc = (int)({v});')
            self.all_drops()
            self.emit('return _rc; }')
            return
        if ret == 'void':
            if s.value is not None:
                self.err('BML-E0393', 'funkcja bez wyniku (void) nie zwraca wartości', s.line)
            self.all_drops()
            self.emit('return;')
            return
        if s.value is None:
            self.err('BML-E0394', f'funkcja musi zwrócić wartość typu {ret}', s.line)
        if ret in BLOCK_TYPES:
            d = self.resolve(s.value) if s.value.kind in ('Name', 'Chain') else None
            if not d or d.kind != 'block':
                self.err('BML-E0395', 'funkcja zwraca blok: podaj zmienną pointer, widok albo kopię', s.line)
            if d.temp:
                for t in self.temps:
                    if t[0] == d.c:
                        t[1] = True
            else:
                self.emit(f'bm_retain({d.c});')
            self.emit(f'{{ uint32_t _rv = {d.c};')
            self.all_drops()
            self.emit('return _rv; }')
            return
        v = self.value_for(ret, s.value)
        self.emit(f'{{ {self.ctype(ret)} _rv = {v};')
        self.all_drops()
        self.emit('return _rv; }')

    def st_KeyInput(self, s):
        prompts = []
        def flush():
            for p in prompts:
                cs, _ = c_string(p)
                self.emit(f'bm_print_str({cs});')
            prompts.clear()
        any_ref = False
        for kind, v in s.args:
            if kind == 'str':
                prompts.append(v)
                continue
            any_ref = True
            d = self.resolve(v) if v.kind in ('Name', 'Chain') else None
            if d and d.kind == 'block':
                self.need_ref(d, 'keyInput do tekstu', s.line)
            pr = list(prompts)
            prompts.clear()
            self.emit('for (;;) {')
            self.ind += 1
            for p in pr:
                cs, _ = c_string(p)
                self.emit(f'bm_print_str({cs});')
            self.emit(f'uint64_t _kn = bm_keyline({s.line});')
            if d and d.kind == 'block' and d.type == 'text':
                self.emit(f'bm_text_set(&{d.c}, bm_keyline_buf, _kn, {s.line}); break;')
            elif d and d.kind == 'svar' and not d.const:
                t = d.type
                if t in self.INT_RANGE and TYPES[t][2] == 's':
                    lo, hi = self.INT_RANGE[t]
                    self.emit(f'int64_t _kv; if (bm_key_int(_kn, {cnum(lo)}, {cnum(hi)}, &_kv)) {{ {d.c} = ({self.ctype(t)})_kv; break; }}')
                    self.emit(f'bm_key_bad("liczba typu {t} ({lo}...{hi})");')
                elif t in self.INT_RANGE or t == 'bit':
                    hi = 1 if t == 'bit' else self.INT_RANGE[t][1]
                    if t == 'unsigned_64':
                        hi = 2**64 - 1
                    self.emit(f'uint64_t _kv; if (bm_key_uint(_kn, {hi}ULL, &_kv)) {{ {d.c} = ({self.ctype(t)})_kv; break; }}')
                    self.emit(f'bm_key_bad("liczba typu {t} (0...{hi})");')
                elif self.is_float(t):
                    self.emit(f'double _kv; if (bm_key_float(_kn, &_kv)) {{ {d.c} = ({self.ctype(t)})_kv; break; }}')
                    self.emit(f'bm_key_bad("liczba typu {t}");')
                else:
                    self.err('BML-E0131', f'keyInput nie wczyta typu {t}', s.line)
            else:
                self.err('BML-E0132', 'keyInput wczytuje do zmiennej liczbowej albo tekstu', v.line,
                         help='keyInput("Ile? ", REF ile)')
            self.ind -= 1
            self.emit('}')
        flush()
        if not any_ref:
            self.emit(f'bm_keyline({s.line});')

    def st_Print(self, s):
        for e, fmt in s.args:
            self.print_one(e, fmt, s.line)
        if s.newline:
            self.emit('bm_print_str("\\n");')

    def print_one(self, e, fmt, line):
        if e.kind == 'Str':
            cs, _ = c_string(e.v)
            self.emit(f'bm_print_str({cs});')
            return
        if e.kind in ('Name', 'Chain'):
            d = self.resolve(e)
            if d.kind == 'block':
                if d.type == 'text' and fmt is None:
                    self.emit(f'bm_print_text({d.c}, {line});')
                elif fmt == 'hex':
                    self.emit(f'bm_dump({d.c}, {line});')
                else:
                    self.emit(f'bm_describe({d.c}, {line});')
                return
            if d.kind == 'lens' and d.type in self.structs:
                unsupported('wypisywanie całej struktury', line)
            c, t = self.dvalue(d, None, e)
        else:
            c, t = self.expr(e)
        if isinstance(t, tuple):
            t = self.lit_type(t[1])
        if t == 'int_lit':
            t = 'longint'
        if t == 'float_lit':
            t = 'doublefloat'
        if fmt == 'hex':
            if self.is_float(t):
                self.err('BML-E0396', ':hex dla liczby zmiennoprzecinkowej', line)
            self.emit(f'bm_print_hex((unsigned long long)({c}), {TYPES[t][1]});')
        elif fmt == 'bin':
            if self.is_float(t):
                self.err('BML-E0397', ':bin dla liczby zmiennoprzecinkowej', line)
            self.emit(f'bm_print_bin((unsigned long long)({c}), {TYPES[t][1] * 8 if t != "bit" else 1});')
        elif isinstance(fmt, int) or (fmt is None and self.is_float(t)):
            self.emit(f'bm_print_f((double)({c}), {fmt if isinstance(fmt, int) else -1});')
        elif fmt is None:
            if TYPES[t][2] == 's':
                self.emit(f'bm_print_i((long long)({c}));')
            else:
                self.emit(f'bm_print_u((unsigned long long)({c}));')
        else:
            self.err('BML-E0398', f'nieznany format „{fmt}”', line, help='formaty: hex, bin, liczba miejsc po przecinku')

    # ---- całość ---------------------------------------------------------
    def generate(self):
        main = None
        # przebieg 1: deklaracje
        for it in self.items:
            if it.kind == 'Struct':
                fields, off = {}, 0
                for fname, ftype in it.fields:
                    if ftype not in TYPES or ftype == 'bit':
                        if ftype == 'bit' or ftype.startswith('unsigned_') or ftype.startswith('signed_'):
                            unsupported(f'pole bitowe {ftype} w strukturze', it.line)
                        self.err('BML-E0030', f'nieznany typ pola „{ftype}”', it.line)
                    fields[fname] = (ftype, off)
                    off += TYPES[ftype][1]
                self.structs[it.name] = {'fields': fields, 'size': off}
            elif it.kind == 'Alias':
                self.aliases[it.name] = it.value
            elif it.kind == 'Function':
                if it.name in self.funcs:
                    self.err('BML-E0400', f'funkcja „{it.name}” zdefiniowana dwa razy', it.line)
                self.funcs[it.name] = {'params': it.params, 'ret': it.ret, 'node': it}
            elif it.kind == 'Main':
                if main:
                    self.err('BML-E0401', 'drugi MAIN', it.line)
                main = it
        if not main:
            raise BemolError('BML-E0402', 'brak programu głównego MAIN BEGIN ... MAIN END', 1)

        head = ['/* Wygenerowane przez bemolc (prototyp, wersja 0) — nie edytować ręcznie */',
                f'#define BEMOL_BUILD_MODE {1 if self.finalbake else 0}',
                '#include "bemol_rt.h"', '']
        self.out = []
        self.ind = 0
        self.push()                       # zasięg globalny dla stałych
        for it in self.items:
            if it.kind == 'Const':
                self.line = it.line
                if it.type not in TYPES:
                    self.err('BML-E0403', 'stała CONST musi mieć typ liczbowy', it.line)
                c = cident(it.name, 'c_')
                v = self.value_for(it.type, it.value)
                self.emit(f'static const {self.ctype(it.type)} {c} = {v};')
                self.consts[it.name] = {'c': c, 'type': it.type}
        ginits = []
        for it in self.items:
            if it.kind == 'Decl':
                self.line = it.line
                c = cident(it.name, 'g_')
                if it.type in BLOCK_TYPES:
                    self.globals[it.name] = {'kind': 'block', 'type': it.type, 'c': c}
                    self.emit(f'static uint32_t {c} = 0;')
                    if getattr(it, 'newsize', None) is not None or it.init is not None:
                        ginits.append((it, self.globals[it.name]))
                elif it.type in self.structs:
                    self.globals[it.name] = {'kind': 'struct', 'type': it.type, 'c': c}
                    self.emit(f'static uint8_t {c}[{self.structs[it.type]["size"]}];')
                elif it.type in TYPES:
                    init = self.value_for(it.type, it.init) if it.init is not None else '0'
                    self.globals[it.name] = {'kind': 'static', 'type': it.type, 'c': c}
                    self.emit(f'static {self.ctype(it.type)} {c} = {init};')
                else:
                    self.err('BML-E0030', f'nieznany typ „{it.type}”', it.line)
        decls = list(self.out)
        self.out = []
        protos = []
        for name, f in self.funcs.items():
            protos.append(self.signature(name, f) + ';')
        bodies = []
        for name, f in self.funcs.items():
            self.out = []
            self.func_body(name, f)
            bodies.extend(self.out)
        self.out = []
        self.func = {'name': 'MAIN', 'ret': 'int'}
        self.ind = 0
        self.emit('int main(int argc, char **argv)')
        self.emit('{')
        self.ind = 1
        self.emit('(void)argc; (void)argv;')
        self.emit('bm_start();')
        self.emit(f'bm_srcfile = "{os.path.basename(self.srcname)}";')
        self.push()
        for it, info in ginits:                 # zmienne GLOBAL gotowe przed startem MAIN
            self.line = it.line
            blk = D('block', c=info['c'], type=it.type, var=info, temp=False, name=it.name)
            if getattr(it, 'newsize', None) is not None:
                self.method(D('method', block=blk, name='new', idx=[it.newsize], lenstype=None, line=it.line), it.line)
            else:
                self.assign_block(blk, it.init, it.line)
        self.stmts(main.body)
        self.pop()
        self.emit('return 0;')
        self.ind = 0
        self.emit('}')
        return '\n'.join(head + decls + [''] + protos + [''] + bodies + [''] + self.out) + '\n'

    def signature(self, name, f):
        ps = []
        for pname, ptype, mod in f['params']:
            ct = self.ctype(ptype) if (ptype in TYPES or ptype in BLOCK_TYPES) else None
            if ct is None:
                self.err('BML-E0404', f'nieobsługiwany typ parametru „{ptype}”', f['node'].line)
            if mod == 'REF':
                ps.append(f'{ct} *{cident(pname, "v_")}')
            else:
                ps.append(f'{ct} {cident(pname, "v_")}')
        ret = self.ctype(f['ret'])
        return f'static {ret} {cident(name, "f_")}({", ".join(ps) or "void"})'

    def func_body(self, name, f):
        node = f['node']
        self.func = {'name': name, 'ret': f['ret']}
        self.ind = 0
        self.emit(self.signature(name, f))
        self.emit('{')
        self.ind = 1
        saved_scopes = self.scopes
        self.scopes = [saved_scopes[0]]
        self.push()
        for pname, ptype, mod in f['params']:
            c = cident(pname, 'v_')
            if ptype in BLOCK_TYPES:
                self.declare(pname, {'kind': 'block', 'type': ptype, 'c': f'(*{c})' if mod == 'REF' else c,
                                     'constparam': mod == 'CONST', 'param': mod or 'PLAIN'}, node.line)
            elif mod == 'REF':
                self.declare(pname, {'kind': 'static', 'type': ptype, 'c': f'(*{c})'}, node.line)
            else:
                self.declare(pname, {'kind': 'static', 'type': ptype, 'c': c}, node.line)
        self.stmts(node.body)
        self.pop()
        if f['ret'] != 'void':
            self.emit(f'return ({self.ctype(f["ret"])})0;')
        self.ind = 0
        self.emit('}')
        self.emit('')
        self.scopes = saved_scopes


# --------------------------------------------------------------------------
# Komunikaty i uruchomienie
# --------------------------------------------------------------------------

LINE_STARS = '*' * 65
LINE_EQ = '=' * 65
LINE_DASH = '-' * 65
LINE_FOOT = '_' * 65


def show(kind, code, msg, src_lines, path, line, col=0, detail='', help=''):
    """Komunikat w formacie BEMOL (sekcja 20 specyfikacji)."""
    err = kind == 'błąd'
    out = [LINE_STARS if err else LINE_EQ,
           f'{"ERROR" if err else "WARNING"}: {code}']
    if path:
        out.append(os.path.basename(path))
    if line:
        out.append(f'at line {line}' + (f', column {col}' if col else ''))
    out.append(LINE_DASH)
    if src_lines and 1 <= line <= len(src_lines):
        text = src_lines[line - 1].rstrip('\n').replace('\t', '    ')
        pad = ' ' * len(str(line))
        out.append(f'{line} | {text}')
        if col:
            out.append(f'{pad} | {" " * (col - 1)}^')
        out.append(LINE_DASH)
    out.append(f'  [ ! ] {msg[:1].upper() + msg[1:]}')
    if detail:
        out.append(f'  [ i ] {detail}')
    if help:
        out.append(f'[ tip ] {help}')
    out.append(LINE_FOOT)
    print('\n'.join(out), file=sys.stderr)


INSTALL_HELP = ('zainstaluj GCC. Windows: w terminalu wpisz '
                '`winget install BrechtSanders.WinLibs.POSIX.UCRT`, potem zamknij i otwórz terminal na nowo. '
                'Linux: `sudo apt install gcc`. macOS: `xcode-select --install`')


def find_c_compiler():
    import shutil
    for name in ('gcc', 'clang', 'cc'):
        path = shutil.which(name)
        if path:
            return path
    return None


def show_plain(kind, code, msg, detail='', help=''):
    show(kind, code, msg, None, None, 0, 0, detail, help)


def main(argv):
    finalbake = '-finalbake' in argv
    emit_c = '--emit-c' in argv
    files = [a for a in argv[1:] if not a.startswith('-')]
    if len(files) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path = files[0]
    with open(path, encoding='utf-8') as fh:
        src = fh.read()
    lines = src.split('\n')
    try:
        items = Parser(lex(src)).program()
        gen = Gen(items, path, finalbake)
        csrc = gen.generate()
    except BemolError as e:
        show('błąd', e.code, e.msg, lines, path, e.line, e.col, e.detail, e.help)
        return 1
    for code, msg, line, detail, hlp in gen.warnings:
        show('ostrzeżenie', code, msg, lines, path, line, 0, detail, hlp)
    base = os.path.splitext(path)[0]
    cpath = base + '.c'
    with open(cpath, 'w', encoding='utf-8') as fh:
        fh.write(csrc)
    if emit_c:
        print(cpath)
        return 0
    compiler = find_c_compiler()
    if compiler is None:
        show_plain('błąd', 'BML-E0998', 'nie znaleziono kompilatora C (gcc albo clang)',
                   detail=f'kod C został wygenerowany: {os.path.basename(cpath)}, ale nie ma czym go skompilować',
                   help=INSTALL_HELP)
        return 1
    opt = '-O3' if finalbake else '-O1'
    exe = base + ('.exe' if os.name == 'nt' else '')
    cmd = [compiler, '-std=gnu11', opt, '-fwrapv', '-fno-strict-aliasing', '-w', '-I', HERE, cpath, '-o', exe, '-lm']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        show_plain('błąd', 'BML-E0998', f'nie udało się uruchomić kompilatora C ({compiler})', detail=str(e), help=INSTALL_HELP)
        return 1
    if r.returncode != 0:
        show_plain('błąd', 'BML-E0999', 'kompilator C zgłosił błąd w wygenerowanym kodzie',
                   detail='to błąd prototypu tłumacza, nie Twojego programu; komunikat kompilatora C poniżej',
                   help='zgłoś go razem z plikiem .bmol')
        print(r.stderr.strip(), file=sys.stderr)
        return 1
    run = os.path.basename(exe) if os.name == 'nt' else './' + os.path.basename(exe)
    print(f'{"finalbake" if finalbake else "kompilacja testowa"}: {os.path.basename(exe)}')
    print(f'uruchom: {run}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except FileNotFoundError as e:
        show_plain('błąd', 'BML-E0997', f'nie znaleziono pliku: {e.filename}',
                   help='sprawdź nazwę pliku i folder, w którym jesteś (polecenie `dir` albo `ls`)')
        sys.exit(1)
    except Exception as e:                       # błąd w samym prototypie
        if '--debug' in sys.argv:
            raise
        show_plain('błąd', 'BML-E0996', f'błąd wewnętrzny prototypu tłumacza ({type(e).__name__}: {e})',
                   detail='to błąd tłumacza, nie Twojego programu',
                   help='uruchom ponownie z opcją --debug i zgłoś wynik razem z plikiem .bmol')
        sys.exit(1)
