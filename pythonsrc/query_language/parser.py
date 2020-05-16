import re
from collections import deque
from .nodes import Line, ParenthesesGrouping, BracketGrouping, BraceGrouping, split_into_lines, Program

lex_dict = {
        "bin": r"0[bB][01_]+",
        "oct": r"0[oO][0-7_]+",
        "hex": r"0[xX][\da-fA-F_]+",
        "dec": r"[\d]+(\.[\d+]*)?([eE][\d]+)?[jJ]?",
        "dq": r'"([^"\n]|(\\"))*"',
        "sq": r"'([^'\n]|(\\'))*'",
        "tdq": r'""".*"""',
        "tsq": r"'''.*'''",
        "open": r"[\(\[\{]",
        "close": r"[\)\]\}]",
        "op": (
            r"([~.:,])|"
            r"([%*-+&^|@]=?)|"
            r"(//?=?)|"
            r"(<<?=?)|"
            r"(>>?=?)|"
            r"(==?)|"
            r"(!=)"
        ),
        "var": r"[a-zA-Z_][a-zA-Z\d_]*",
        "whitespace": r"[ \t]+",
        "endline": r"[;\n]+",
        }

lex_regex = "|".join([f"(?P<{k}>{v})" for k, v in lex_dict.items()])



def match_filter(m):
    for k, v in m.groupdict().items():
        if v:
            return k, v

class Lexeme:
    LITERALS = ["bin", "oct", "hex", "dec", "dq", "sq", "tdq", "tsq"]
    KEYWORDS = ['False','None','True','and','as','assert','async','await','break',
     'class','continue','def','del','elif','else','except','finally','for','from',
     'global','if','import','in','is','lambda','nonlocal','not','or','pass',
     'raise','return','try','while','with','yield', 'let', 'const']
    def __init__(self, type_, word):
        self.type_, self.word = type_, word
        if self.type_ in self.LITERALS:
            self.type_ = "literal"
            self.value = eval(self.word)
        elif self.word in self.KEYWORDS:
            if self.word in ('True', 'False', 'None'):
                self.type_ = "literal"
                self.value = eval(self.word)
            else:
                self.type_ = "keyword"

    def __repr__(self):
        return f'{self.type_}: {self.word}'

    def link(self, lexemes, output):
        try:
            lexeme = next(lexemes)
        except StopIteration:
            lexeme = None
        output.append(self)
        if lexeme:
            lexeme.link(lexemes, output)






def lex(s):
    m_iter = re.finditer(lex_regex, s)
    start_pos = 0
    for m in m_iter:
        start_pos = m.end()
        k, v = match_filter(m)
        if k != "whitespace":
            yield Lexeme(k, v)

def grouping_symbols(lexemes):
    symbol_stack = []
    inner_stack = []
    matches = {'(':')', '[':']', '{':'}'}
    group_types = {
            '(':ParenthesesGrouping,
            '[':BracketGrouping,
            '{':BraceGrouping,
    }
    for lexeme in lexemes:
        if lexeme.type_ == "open":
            symbol_stack.append(lexeme.word)
            inner_stack.append([])
            continue
        elif lexeme.type_ == "close":
            assert matches[symbol_stack[-1]] == lexeme.word, f"unmatched {lexeme.word} at {lexeme.line_no}:{lexeme.col_no}"
            lexeme =  group_types[symbol_stack.pop()](inner_stack.pop())
        if inner_stack:
            inner_stack[-1].append(lexeme)
        else:
            yield lexeme



def chain(s, * funcs):
    for f in funcs:
        s = f(s)
    return s

def parse(s):
    program = Program(list(chain(s,  lex, grouping_symbols, split_into_lines)))
    return program.eval()
