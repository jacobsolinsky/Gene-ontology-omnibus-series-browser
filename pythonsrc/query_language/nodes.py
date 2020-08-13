from ..environment import environment as sample_environment
from . import query_language_builtins
from functools import partial
import operator, builtins, importlib, copy
import copy
from collections import OrderedDict


class Context:
    def __init__(self, lets = {},  parent = None):
        self.stack = []
        self.lets = lets
        self.consts = {}
        self.parent = parent

    def push(self, val, multiple = False):
        if not multiple:
            self.stack.append(val)
        else:
            self.stack += val

    def pop(self, number = None):
        if number is  None:
            return self.stack.pop()
        elif number == 0:
            return []
        else:
            retval = self.stack[-number:]
            self.stack = self.stack[:-number]
            return retval

    def get(self, key):
        try:
            try:
                return self.consts[key]
            except:
                return self.lets[key]
        except KeyError:
            if self.parent is None:
                raise NameError(f'{key} is not defined')
            else:
                return self.parent.get(key)

    def set(self, key, val):
        if key in self.consts:
            raise NameError(f'{key} is a constant')
        elif key in self.lets:
            self.lets[key] = val
        else:
            try:
                self.parent.set(key, val)
            except AttributeError:
                raise NameError(f'{key} is undeclared in this scope')

    def delete(self, key):
        if key in self.consts:
            self.consts.pop(key)
        elif key in self.lets:
            self.lets.pop(key)
        else:
            pass

    def add_const(self, key, a):
        self.consts[key] = a

    def add_let(self, key, a):
        self.lets[key] = a


class BASE_CONTEXT:
    @staticmethod
    def get(key):
        try:
            return sample_environment.samples[key]
        except KeyError:
            try:
                return getattr(sample_environment, key)
            except AttributeError:
                try:
                    return getattr(query_language_builtins, key)
                except AttributeError:
                    try:
                        return getattr(builtins, key)
                    except AttributeError:
                        raise NameError(f'{key} is not defined')

CONTEXT = Context({}, BASE_CONTEXT)

def split_into_lines(lexemes):
    current_line = []
    for lexeme in lexemes:
        if lexeme.type_ in ('endline', '$'):
            if current_line:
                yield Line(current_line)
            current_line = []
            continue
        else:
            current_line.append(lexeme)
    if current_line:
        yield Line(current_line)

def link_suite(lexemes):
    current_suite = None
    inner_line = []
    for lexeme in lexemes:
        if lexeme.type_ == 'keyword' and lexeme.word in SUITE_KEYWORDS:
            current_suite = lexeme.word
        elif current_suite:
            if type(lexeme) == BraceGrouping:
                il = Subline(inner_line)
                bg = BraceNode(lexeme, None)
                yield SUITE_KEYWORDS[current_suite](il, bg)
                current_suite = None
                inner_line = []
            else:
                inner_line.append(lexeme)
        else:
            yield lexeme


class PrecedenceNode:
    associativity = "left"
    precedence_levels = {
    'end': -8,
    'modifier': -7,
    'assign': -6,
    'from': -5,
    'comma': -4,
    'type_colon': -3,
    'dict_key': -3,
    'keyword_arg': -2,
    'star': -1,
    'lambda': 0,
    'boolean_or': 1,
    'boolean_and': 2,
    'boolean_not': 3,
    'comparison': 4,
    'bitwise_or': 5,
    'bitwise_xor': 6,
    'bitwise_and': 7,
    'shifts': 8,
    'sums': 9,
    'products': 10,
    'signs': 11,
    'bitwise_not': 12,
    'power': 13,
    'subscript': 14,
    'call': 15,
    'attribute': 16,

    }

    def __init__(self, lexeme, l):
        self.lexeme = lexeme
        self._l = l
        self._r = None
        self.lc = None
        self.rc = None

    def validity_check(self):
        scl = type(self)
        lcl = type(self.l)
        rcl = type(self.r)
        if issubclass(scl, SimpleNode):
            assert not issubclass(lcl, (SimpleNode, RightUnaryNode)), (self, self.l, self.r)
        elif issubclass(scl, BinaryNode):
            assert issubclass(lcl, (SimpleNode, RightUnaryNode)), self
            if issubclass(scl, DividerNode):
                assert  issubclass(rcl, (SimpleNode, LeftUnaryNode, EndNode)), self.r
            else:
                assert  issubclass(rcl, (SimpleNode, LeftUnaryNode)), self
        elif issubclass(scl, LeftUnaryNode):
            assert  issubclass(rcl, (SimpleNode, LeftUnaryNode)), self
        elif issubclass(scl, RightUnaryNode):
            assert issubclass(lcl, (SimpleNode, RightUnaryNode)), self

    def children_check(self):
        pass

    def __repr__(self):
        return f"{self.lexeme}:{self.__class__.__name__}"
    def judge(self, go_right = True):
        if self.complete:
            self.postprocess()
            if type(self.l) == EndNode and type(self.r) == EndNode:
                self.children_check()
                if type(self) == ExprNode:
                    return self.children[0]
                else:
                    return self
            lprec , rprec = self.precedence_levels[self.l.precedence], self.precedence_levels[self.r.precedence]
            if lprec > rprec or lprec == rprec and self.l.associativity == "left":
                if type(self) == ExprNode:
                    self.l.rc = self.children[0]
                    self.l.override_r = self.r
                else:
                    self.l.rc = self
                return self.l.judge(go_right)
            else:
                if type(self) == ExprNode:
                    self.r.lc = self.children[0]
                    self.r.override_l = self.l
                else:
                    self.r.lc = self
                return self.r.judge(go_right)
        else:
            if type(self.l) == EndNode:
                return self.r.judge(True)
            elif type(self.r) == EndNode:
                if issubclass(type(self), DividerNode):
                    self.rc = None
                    self._complete = True
                    self.judge(go_right)
                return self.l.judge(False)
            elif go_right:
                return self.r.judge(go_right)
            else:
                return self.l.judge(go_right)
    @property
    def l(self):
        return self._l

    @property
    def r(self):
        return self._r

    @staticmethod
    def create(lexeme, l, grammar = 'line'):
        if issubclass(type(lexeme), SuiteExpression):
            lexeme._l = l
            return lexeme
        node_map = {
                'line': line_node_map,
                }[grammar]
        (lexeme, l)
        if lexeme.type_ in ("op", "keyword"):
            intermediary =  node_map[lexeme.word]
        elif lexeme.type_ in ("var", "parentheses_grouping", "bracket_grouping", "brace_grouping", "literal"):
            intermediary = node_map[lexeme.type_]
        if issubclass(intermediary, AmbiguousNode):
            return intermediary.disambiguate(lexeme, l)
        else:
            return intermediary(lexeme, l)

    @classmethod
    def parse(cls, elements, grammar="line"):
        if elements:
            l = EndNode()
            parsenv = []
            for e in elements:
                parsenv.append(cls.create(e, l, grammar))
                l._r = parsenv[-1]
                l.validity_check()
                l = parsenv[-1]
            l._r = EndNode()
            l.validity_check()
            return [parsenv[0].judge()]
        else:
            return []
    def postprocess(self):
        pass




class SimpleNode(PrecedenceNode):
    complete = True

class LeftUnaryNode(PrecedenceNode):
    @property
    def complete(self):
        return self.rc

    @property
    def r(self):
        if hasattr(self, 'override_r'):
            return self.override_r
        else:
            return self.rc.r if self.rc else self._r

    def __repr__(self):
        return f"{self.__class__.__name__}:{self.lexeme}<ul><li>{self.rc}</li></ul>"
    @property
    def children(self):
        return [self.rc]

    def eval(self, context):
        self.rc.eval(context)
        context.push(self.operation(context.pop()))

class RightUnaryNode(PrecedenceNode):
    @property
    def complete(self):
        return self.lc

    @property
    def l(self):
        if hasattr(self, 'override_l'):
            return self.override_l
        else:
            return self.lc.l if self.lc else self._l


    def __repr__(self):
        return f"{self.__class__.__name__}:{self.lexeme}<ul><li>{self.lc}</li></ul>"

    @property
    def children(self):
        return [self.lc]

class BinaryNode(PrecedenceNode):
    @property
    def complete(self):
        return self.lc and self.rc

    @property
    def l(self):
        if hasattr(self, 'override_l'):
            return self.override_l
        else:
            return self.lc.l if self.lc else self._l

    @property
    def r(self):
        if hasattr(self, 'override_r'):
            return self.override_r
        else:
            return self.rc.r if self.rc else self._r

    def __repr__(self):
        return f"{self.__class__.__name__}:{self.lexeme}<ul><li>{self.lc}</li><li>{self.rc}</li></ul>"

    @property
    def children(self):
        return [self.lc, self.rc]

    def eval(self, context):
        self.lc.eval(context)
        self.rc.eval(context)
        r = context.pop()
        l = context.pop()
        context.push(self.operation(l, r))

class DividerNode(BinaryNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._complete = False
    @property
    def complete(self):
        return self.lc and self.rc or self._complete

class EndNode(PrecedenceNode):
    precedence = "end"
    lexeme = "$:$"
    def validity_check(self):
        pass
    def __init__(self):
        pass

class VarNode(SimpleNode):
    def eval(self, context):
        context.push(context.get(self.lexeme.word))

    def left_eval(self, context, a):
        context.set(self.lexeme.word, a)

    def let_eval(self, context, a):
        context.add_let(self.lexeme.word, a)

    def const_eval(self, context, a):
        context.add_const(self.lexeme.word, a)

    def delete(self, context):
        context.delete(self.lexeme.word)


class LiteralNode(SimpleNode):
    def eval(self, context):
        context.push(self.lexeme.value)

class AmbiguousNode(PrecedenceNode):
    @classmethod
    def disambiguate(cls, lexeme, l):
        if not issubclass(type(l),(SimpleNode, RightUnaryNode)):
            return cls.unary(lexeme, l)
        else:
            return cls.binary(lexeme, l)


class DotNode(BinaryNode):
    precedence = "attribute"
    def eval(self, context):
        self.lc.eval(context)
        context.push(getattr(context.pop(), self.rc.lexeme.word))

    def left_eval(self, context, a):
        self.lc.eval(context)
        setattr(context.pop(), self.rc.lexeme.word, a)

    def delete(self, context):
        self.lc.eval(context)
        delattr(context.pop(), self.rc.lexeme.word)


class AssignNode(BinaryNode):
    precedence = "assign"
    associativity = "right"
    def eval(self, context):
        self.rc.eval(context)
        a = context.pop()
        self.lc.left_eval(context, a)
        context.push(a)

    def let_eval(self, context):
        self.rc.eval(context)
        a = context.pop()
        self.lc.let_eval(context, a)
        context.push(a)

    def const_eval(self, context):
        self.rc.eval(context)
        a = context.pop()
        self.lc.const_eval(context, a)
        context.push(a)


class DictKeyNode(BinaryNode):
    precedence = "dict_key"
    def eval(self, context):
        self.lc.eval(context)
        self.rc.eval(context)
        v, k = context.pop(), context.pop()
        context.push({k:v})

class AssignModifyNode(BinaryNode):
    precedence = "assign"
    def eval(self, context):
        self.rc.eval(context)
        a = context.pop()
        b = context.get(self.lc.lexeme.word)
        context.set(self.lc.lexeme.word, self.operation(b, a))
        context.push(context.get(self.lc.lexeme.word))

class PowerAssignNode(AssignModifyNode):
    operation = operator.pow

class AddAssignNode(AssignModifyNode):
    operation = operator.add

class SubtractAssignNode(AssignModifyNode):
    operation = operator.sub

class MultiplyAssignNode(AssignModifyNode):
    operation = operator.mul

class MatrixMultiplyAssignNode(AssignModifyNode):
    operation = operator.matmul

class TrueDivideAssignNode(AssignModifyNode):
    operation = operator.truediv

class FloorDivideAssignNode(AssignModifyNode):
    operation = operator.floordiv

class ModuloAssignNode(AssignModifyNode):
    operation = operator.mod

class ShiftLeftAssignNode(AssignModifyNode):
    operation = operator.lshift

class ShiftRightAssignNode(AssignModifyNode):
    operation = operator.rshift

class BitwiseOrAssignNode(AssignModifyNode):
    operation = operator.or_

class BitwiseXorAssignNode(AssignModifyNode):
    operation = operator.xor

class BitwiseAndAssignNode(AssignModifyNode):
    operation = operator.and_

class CommaNode(DividerNode):
    def dict_process_comma(self):
        self.key_list = []
        self.value_list = []
        first = self
        while True:
            if type(first) == CommaNode:
                assert type(first.lc) == DictKeyNode, "not dict key node"
                self.key_list.append(first.lc.lc)
                self.value_list.append(first.lc.rc)
                first = first.rc
                continue
            elif first:
                assert type(first) == DictKeyNode, "not dict key node"
                self.key_list.append(first.lc)
                self.value_list.append(first.rc)
            break
        self.children_list = self.key_list + self.value_list
    @property
    def child(self):
        return [self]

    def dict_eval(self, context):
        self.process_comma()
        length = len(self.children_list)
        for child in self.children_list:
            child.eval(context)
        values = context.pop(length // 2)
        keys = context.pop(length // 2)
        context.push({k: v for k, v in zip(keys, values)})

    def dict_left_eval(self, context, a):
        self.process_comma()
        for k, v in zip(self.key_list, self.value_list):
            k.eval(context)
            v.left_eval(context, a[context.pop()])

    def dict_let_eval(self, context, a):
        self.process_comma()
        for k, v in zip(self.key_list, self.value_list):
            k.eval(context)
            v.let_eval(context, a[context.pop()])

    def dict_const_eval(self, context, a):
        self.process_comma()
        for k, v in zip(self.key_list, self.value_list):
            k.eval(context)
            v.const_eval(context, a[context.pop()])

    precedence = "comma"
    associativity = "right"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def process_comma(self):
        if type(self.lc) == DictKeyNode:
            self.dict_process_comma()
        else:
            self.children_list = []
            first = self
            while True:
                if type(first) == CommaNode:
                    self.children_list.append(first.lc)
                    first = first.rc
                    continue
                elif first:
                    self.children_list.append(first)
                break

    def eval(self, context):
        if type(self.lc) == DictKeyNode:
            self.dict_eval(context)
        else:
            self.process_comma()
            length = len(self.children_list)
            for child in self.children_list:
                child.eval(context)
            contents = context.pop(length)
            context.push((*contents,))

    def left_eval(self, context, a):
        if type(self.lc) == DictKeyNode:
            self.dict_left_eval(context, a)
        else:
            self.process_comma()
            length = len(self.children_list)
            for i, child in enumerate(self.children_list):
                child.left_eval(context, a[i])

    def let_eval(self, context, a):
        if type(self.lc) == DictKeyNode:
            self.dict_let_eval(context, a)
        else:
            self.process_comma()
            length = len(self.children_list)
            for i, child in enumerate(self.children_list):
                child.let_eval(context, a[i])

    def const_eval(self, context, a):
        if type(self.lc) == DictKeyNode:
            self.dict_const_eval(context, a)
        else:
            self.process_comma()
            length = len(self.children_list)
            for i, child in enumerate(self.children_list):
                child.const_eval(context, a[i])

class RegularParseNode(SimpleNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        elements = [e for e in self.lexeme.elements if e.type_ != "endline"]
        elements = link_suite(elements)
        children_list = []
        if elements:
            next(elements).link(elements, children_list)
        self.children = PrecedenceNode.parse(children_list, grammar = "line")

    def __repr__(self):
        return f'{self.__class__.__name__}<ul><li>{self.children}</li></ul>'

class ExprNode(RegularParseNode):
    pass

class ListNode(RegularParseNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process_comma()

    def process_comma(self):
        self.children_list = []
        if self.children:
            first = self.children[0]
            while True:
                if type(first) == CommaNode:
                    self.children_list.append(first.lc)
                    first = first.rc
                    continue
                elif first:
                    self.children_list.append(first)
                break

    def __repr__(self):
        return '[' + ','.join(str(c) for c in self.children_list) + ']'

    def eval(self, context):
        length = len(self.children_list)
        for child in self.children_list:
            child.eval(context)
        contents = context.pop(length)
        context.push([*contents])


class BraceNode(SimpleNode):
    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)
        self.lines = self.lexeme.lines

    def eval(self, context, subcontext = None):
        if subcontext is None:
            self.subcontext = Context({}, context)
        else:
            self.subcontext = subcontext
        retval = None
        for line in self.lines:
            retval = line.eval(self.subcontext)
        context.push(retval)


class IndexNode(RightUnaryNode):
    precedence = "call"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.child = PrecedenceNode.parse(self.lexeme.elements)

    def eval(self, context):
        child = self.child[0]
        self.lc.eval(context)
        if type(child) == DictKeyNode:
            child.lc.eval(context)
            child.rc.eval(context)
            stop = context.pop()
            start = context.pop()
            indexer = slice(start, stop)
        else:
            child.eval(context)
            indexer = context.pop()
        indexee = context.pop()
        context.push(indexee[indexer])

    def left_eval(self, context, a):
        self.lc.eval(context)
        indexee = context.pop()
        child = self.child[0]
        if type(child) == DictKeyNode:
            child.lc.eval(context)
            child.rc.eval(context)
            stop = context.pop()
            start = context.pop()
            indexer = slice(start, stop)
        else:
            child.eval(context)
            indexer = context.pop()
        indexee[indexer] = a



class CallNode(RightUnaryNode):
    precedence = "call"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        elements = [e for e in self.lexeme.elements if e.type_ != "endline"]
        elements = link_suite(elements)
        children_list = []
        try:
            if elements:
                next(elements).link(elements, children_list)
            self.child = PrecedenceNode.parse(children_list, grammar = "line")
        except StopIteration:
            self.child = None
        self.process_comma()

    def process_comma(self):
        self.positional_args = []
        self.keyword_args = []
        self.keywords = []
        if self.child:
            first = self.child[0]
            while True:
                if type(first) == CommaNode:
                    if type(first.lc) == DictKeyNode:
                        self.keyword_args.append(first.lc.rc)
                        self.keywords.append(first.lc.lc.lexeme.word)
                    else:
                        assert not self.keywords
                        self.positional_args.append(first.lc)
                    first = first.rc
                    continue
                elif first:
                    if type(first) == DictKeyNode:
                        self.keyword_args.append(first.rc)
                        self.keywords.append(first.lc.lexeme.word)
                    else:
                        assert not self.keywords
                        self.positional_args.append(first)
                break

    def __repr__(self):
        return f'{self.lc}(' + ','.join(str(c) for c in self.positional_args + self.keyword_args) + ')'

    def eval(self, context):
        self.lc.eval(context)
        posarglen = len(self.positional_args)
        for posarg in self.positional_args:
            posarg.eval(context)
        kwargs = {}
        if self.keyword_args:
            kwarglen = len(self.keyword_args)
            for kwarg in self.keyword_args:
                kwarg.eval(context)
            kwargs = {k:v for k, v in zip(self.keywords, context.pop(kwarglen))}
        posargs = context.pop(posarglen)
        func = context.pop()
        context.push(func(*posargs, **kwargs))






class ParenthesesNode(AmbiguousNode):
    unary = ExprNode
    binary = CallNode


class BracketNode(AmbiguousNode):
    unary = ListNode
    binary = IndexNode

class PositiveNode(LeftUnaryNode):
    precedence = "signs"
    operation = operator.pos

class NegativeNode(LeftUnaryNode):
    precedence = "signs"
    operation = operator.neg

class AddNode(BinaryNode):
    precedence = "sums"
    operation = operator.add

class SubtractNode(BinaryNode):
    precedence = "sums"
    operation = operator.sub

class PowerNode(BinaryNode):
    precedence = "power"
    associativity = "right"
    operation = operator.pow

class MultiplyNode(BinaryNode):
    precedence = "products"
    operation = operator.mul

class MatrixMultiplyNode(BinaryNode):
    precedence = "products"
    operation = operator.matmul

class TrueDivideNode(BinaryNode):
    precedence = "products"
    operation = operator.truediv

class FloorDivideNode(BinaryNode):
    precedence = "products"
    operation = operator.floordiv

class ModuloNode(BinaryNode):
    precedence = "products"
    operation = operator.mod

class PlusNode(AmbiguousNode):
    unary = PositiveNode
    binary = AddNode

class MinusNode(AmbiguousNode):
    unary = NegativeNode
    binary = SubtractNode


class BooleanOrNode(BinaryNode):
    precedence = "boolean_or"
    def eval(self, context):
        self.lc.eval(context)
        self.rc.eval(context)
        r = context.pop()
        l = context.pop()
        context.push(l or r)

class BooleanAndNode(BinaryNode):
    precedence = "boolean_and"
    def eval(self, context):
        self.lc.eval(context)
        self.rc.eval(context)
        r = context.pop()
        l = context.pop()
        context.push(l and r)

class BooleanNotNode(LeftUnaryNode):
    precedence = "boolean_not"
    def eval(self, context):
        self.rc.eval(context)
        context.push(not context.pop())

class ComparisonNode(BinaryNode):
    precedence = "comparison"
    def eval(self, context, ispassdown_r = False, passdown_r = None):
        if isinstance(self.lc, ComparisonNode):
            self.lc.rc.eval(context)
            l = context.pop()
            self.lc.eval(context, True, l)
            truth = context.pop()
            if ispassdown_r:
                r = passdown_r
            else:
                self.rc.eval(context)
                r = context.pop()
            context.push(self.operation(l, r) and truth)
        else:
            self.lc.eval(context)
            l = context.pop()
            self.rc.eval(context)
            r = context.pop()
            context.push(self.operation(l, r))


class IsNode(ComparisonNode):
    operation = operator.is_

class IsNotNode(ComparisonNode):
    operation = operator.is_not

class InNode(ComparisonNode):
    def eval(self, context, ispassdown_r = False, passdown_r = None):
        if isinstance(self.lc, ComparisonNode):
            self.lc.rc.eval(context)
            l = context.pop()
            self.lc.eval(context, True, l)
            truth = context.pop()
            if ispassdown_r:
                r = passdown_r
            else:
                self.rc.eval(context)
                r = context.pop()
            context.push((l in r) and truth)
        else:
            self.lc.eval(context)
            l = context.pop()
            self.rc.eval(context)
            r = context.pop()
            context.push(l in r)

class NotInNode(ComparisonNode):
    def eval(self, context, ispassdown_r = False, passdown_r = None):
        if isinstance(self.lc, ComparisonNode):
            self.lc.rc.eval(context)
            l = context.pop()
            self.lc.eval(context, True, l)
            truth = context.pop()
            if ispassdown_r:
                r = passdown_r
            else:
                self.rc.eval(context)
                r = context.pop()
            context.push((l not in r) and truth)
        else:
            self.lc.eval(context)
            l = context.pop()
            self.rc.eval(context)
            r = context.pop()
            context.push(l not in r)

class EqualsNode(ComparisonNode):
    operation = operator.eq

class NotEqualsNode(ComparisonNode):
    operation = operator.ne

class GtNode(ComparisonNode):
    operation = operator.gt

class GeNode(ComparisonNode):
    operation = operator.ge

class LtNode(ComparisonNode):
    operation = operator.lt

class LeNode(ComparisonNode):
    operation = operator.le

class BitwiseOrNode(BinaryNode):
    precedence = "bitwise_or"
    operation = operator.or_

class BitwiseXorNode(BinaryNode):
    precedence = "bitwise_xor"
    operation = operator.xor

class BitwiseAndNode(BinaryNode):
    precedence = "bitwise_and"
    operation = operator.and_

class BitwiseNotNode(LeftUnaryNode):
    precedence = "bitwise_not"
    operation = operator.not_

class ShiftLeftNode(BinaryNode):
    precedence = "shifts"
    operation = operator.lshift

class ShiftRightNode(BinaryNode):
    precedence = "shifts"
    operation = operator.rshift

class ImportNode(LeftUnaryNode):
    precedence = "from"
    def eval(self, context):
        if type(self.rc) == DotNode:
            opand = self.rc.lc
            name = '.' + self.rc.rc.lexeme.word
            while type(opand) == DotNode:
                name = '.' + opand.rc.lexeme.word + name
                opand = opand.lc
            name = opand.lexeme.word + name
        else:
            name = self.rc.lexeme.word
        context.push(importlib.import_module(name))
        context.add_const(name, context.stack[-1])

class RaiseNode(LeftUnaryNode):
    precedence = "from"
    def eval(self, context):
        self.rc.eval(context)
        raise context.pop()

class LetNode(LeftUnaryNode):
    precedence = "modifier"
    def eval(self, context):
        self.rc.let_eval(context)

class ConstNode(LeftUnaryNode):
    precedence = "modifier"
    def eval(self, context):
        self.rc.const_eval(context)

class ReturnValue(Exception):
    def __init__(self, retval):
        self.retval = retval


class ReturnNode(LeftUnaryNode):
    precedence = 'from'
    def eval(self, context):
        self.rc.eval(context)
        raise ReturnValue(context.pop())

class BreakIteration(Exception):
    pass

class BreakNode(SimpleNode):
    def eval(self, context):
        raise BreakIteration

class DelNode(LeftUnaryNode):
    precedence = "from"
    def eval(self, context):
        self.rc.delete(context)
        context.push(None)


class Grouping:
    def __init__(self, elements):
        self.elements = [e for e in elements if e.type_ !=  "endline"]

    def __repr__(self):
        inner = ''.join(f"<li>{e}</li>" for e in self.elements)
        return f"{self.type_}: <ul>{inner}</ul>"

    def link(self, lexemes, output):
        try:
            lexeme = next(lexemes)
        except StopIteration:
            lexeme = None
        output.append(self)
        if lexeme:
            lexeme.link(lexemes, output)

class ParenthesesGrouping(Grouping):
    type_ = "parentheses_grouping"
    word = "()"


class BracketGrouping(Grouping):
    type_ = "bracket_grouping"
    word = "[]"

class BraceGrouping(Grouping):
    type_ = "brace_grouping"
    word = "{}"
    def __init__(self, elements):
        self.lines = list(split_into_lines(elements))


    def __repr__(self):
        inner = ''.join(f"<li>{e}</li>" for e in self.lines)
        return f"{self.type_}: <ul>{inner}</ul>"

class StrandedBlockException(Exception):
    pass

class SuiteExpression(SimpleNode):
    def __init__(self, guard, block):
        self.guard = guard
        self.block = block
    def link(self, lexemes, output):
        try:
            lexeme = next(lexemes)
        except StopIteration:
            lexeme = None
        output.append(self)
        if lexeme:
            lexeme.link(lexemes, output)

class IfExpression(SuiteExpression):
    type_ = "if_expression"
    word = "if"


    def eval(self, context):
        self.guard.eval(context)
        if context.pop():

            self.block.eval(context)
        else:
            if self.next:
                self.next.eval(context)
            else:
                context.push(None)

    def link(self, lexemes, output):
        self.elifs = []
        self.else_ = None
        while True:
            try:
                lexeme = next(lexemes)
            except StopIteration:
                lexeme = None
                break
            if type(lexeme) == ElifExpression and not self.else_:
                self.elifs.append(lexeme)
                continue
            elif type(lexeme) == ElseExpression and not self.else_:
                self.else_ = lexeme
                continue
            break
        self.clauses = self.elifs + [self.else_] if [self.else_] else []
        for c1, c2 in zip(self.clauses[:-1], self.clauses[1:]):
            c1.next = c2
        self.next = self.clauses[0] if self.clauses else None
        output.append(self)
        if lexeme:
            lexeme.link(lexemes, output)

    def __repr__(self):
        elif_ss = ''
        else_s = ''
        if self.elifs:
            content = ''.join([f'<li>{ess}</li>' for ess in self.elifs])
            elif_ss = f'Elifs<ul>{content}</ul>'
        if self.else_:
            else_s = ''.join(f'Else<ul>{self.else_}</ul>')
        return f"{self.type_}: <ul><li>{self.guard}</li><li>{self.block}</li>{elif_ss}{else_s}</ul>"

class ElifExpression(IfExpression):
    type_ = "elif_expression"
    word = "elif"

    def link(self):
        raise StrandedBlockException

class ElseExpression(ElifExpression):
    type_ = "else_expression"
    word = "else"
    def eval(self, context):
        self.block.eval(context)

    def link(self, lexemes, output):
        raise StrandedBlockException

class ForExpression(SuiteExpression):
    def eval(self, context):
        subcontext = Context({}, context)
        guard = self.guard.elements[0]
        guard.rc.rc.eval(context)
        a = iter(context.pop())
        try:
            if type(guard) == LetNode:
                while True:
                    guard.rc.lc.let_eval(subcontext, next(a))
                    self.block.eval(context, subcontext)
            elif type(self.rc) == ConstNode:
                while True:
                    guard.rc.lc.const_eval(subcontext, next(a))
                    self.block.eval(context, subcontext)
        except StopIteration:
            if self.else_ is not None:
                self.else_.eval(context)
        except BreakIteration:
            pass

    def link(self, lexemes, output):
        self.else_ = None
        while True:
            try:
                lexeme = next(lexemes)
            except StopIteration:
                lexeme = None
                break
            if type(lexeme) == ElseExpression and not self.else_:
                self.else_ = lexeme
                continue
            break
        output.append(self)
        if lexeme is not None:
            lexeme.link(lexemes, output)

    def __repr__(self):
        return 'forexpr'

class WhileExpression(SuiteExpression):
    def eval(self, context):
        subcontext = Context({}, context)
        try:
            while True:
                self.guard.eval(context)
                if context.pop():
                    self.block.eval(context, subcontext)
                else:
                    raise StopIteration
        except StopIteration:
            if self.else_ is not None:
                self.else_.eval(context)
        except BreakIteration:
            pass

    def link(self, lexemes, output):
        self.else_ = None
        while True:
            try:
                lexeme = next(lexemes)
            except StopIteration:
                lexeme = None
                break
            if type(lexeme) == ElseExpression and not self.else_:
                self.else_ = lexeme
                continue
            break
        output.append(self)
        if lexeme is not None:
            lexeme.link(lexemes, output)


class TryExpression(SuiteExpression):
    def link(self, lexemes, output):
        self.excepts = []
        self.else_ = None
        self.finally_ = None
        while True:
            try:
                lexeme = next(lexemes)
            except StopIteration:
                lexeme = None
                break
            if type(lexeme) == ExceptExpression and not (self.else_ or self.finally_):
                self.excepts.append(lexeme)
                continue
            elif type(lexeme) == ElseExpression and not (self.else_ or self.finally_):
                self.else_ = lexeme
                continue
            elif type(lexeme) == FinallyExpression and not self.finally_:
                self.finally_ = lexeme
                continue
            break
        assert self.finally_ or self.excepts, "try block must have a finally statement or at least one except statement"
        output.append(self)
        if lexeme:
            lexeme.link(lexemes, output)

    def eval(self, context):
        except_dict = {}
        raise_me = None
        for except_ in self.excepts:
            subcontext = Context({}, context)
            except_.guard.elements[0].eval(subcontext)
            except_dict[subcontext.pop()] = except_
        try:
            subcontext = Context({}, context)
            self.block.eval(context, subcontext)
        except Exception as e:
            for k, v in except_dict.items():
                if isinstance(e, k):
                    v.eval(context, e)
                    break
            else:
                raise_me = e
        else:
            if self.else_ is not None:
                self.else_.eval(context)
        finally:
            if self.finally_ is not None:
                self.finally_.eval(context)
        if raise_me is not None:
            raise raise_me





class ExceptExpression(SuiteExpression):
    def eval(self, context, e):
        subcontext = Context({}, context)
        guard = self.guard.elements[0]
        if type(guard) == ConstNode:
            guard.rc.lc.const_eval(subcontext, e)
        elif type(guard) == LetNode:
            guard.rc.lc.let_eval(subcontext, e)
        self.block.eval(context, subcontext)

class FinallyExpression(SuiteExpression):
    def eval(self, context):
        self.block.eval(context)

class WithExpression(SuiteExpression):
    def eval(self, context):
        subcontext = Context({}, context)
        guard = self.guard.elements[0]
        guard.rc.eval(context)
        a = context.pop().__enter__()
        guard.lc.const_eval(subcontext, a)
        try:
            self.block.eval(context, subcontext)
        finally:
            a.__exit__()



class DefExpression(SuiteExpression):
    class Undefined: pass
    class Function:
        def __init__(self, argdict, context, block):
            self.argdict = argdict
            self.context = context
            self.block = block


        def __get__(self, instance, owner):
            if instance is not None:
                return partial(self.__call__, instance)
            else:
                return self.__call__


        def __call__(self, *args, **kwargs):
            argdict = copy.copy(self.argdict)
            for i, arg in enumerate(args):
                argdict[list(argdict.keys())[i]] = arg
            for k, v in kwargs.items():
                argdict[k] = v
            for v in argdict.values():
                if v is DefExpression.Undefined:
                    raise TypeError("Wrong number of arguments!")
            subcontext = Context(argdict, self.context)
            try:
                self.block.eval(subcontext)
            except ReturnValue as r:
                return r.retval
            else:
                return None



    def eval(self, context):
        guard = self.guard.elements[0]
        name = None
        if type(guard) == CallNode:
            name = guard.lc.lexeme.word
        elif type(guard) == CommaNode:
            CallNode.process_comma(guard)
        positional_args = []
        keyword_args = []
        keywords = []
        if type(guard) in (CallNode, CommaNode):
            positional_args = guard.positional_args
            keyword_args = guard.keyword_args
            keywords = guard.keywords
        elif type(guard) == DictKeyNode:
            keyword_args.append(guard.rc)
            keywords.append(guard.lc.lexeme.word)
        elif type(guard) == VarNode:
            positional_args.append(guard)
        argdict = {}
        for posarg in positional_args:
            argdict[posarg.lexeme.word] = self.Undefined
        for keyword, keyword_arg in zip(keywords, keyword_args):
            keyword_arg.eval(context)
            argdict[keyword] = context.pop()
        function = self.Function(argdict, context, self.block)
        if name is not None:
            context.add_const(name, function)
        context.push(function)






class ClassExpression(SuiteExpression):
    def eval(self, context):
        bases = ()
        guard = self.guard.elements[0]
        if type(guard) == CallNode:
            assert type(guard.lc) == VarNode, 'Syntax error'
            name = guard.lc.lexeme.word
            for posarg in guard.positional_args:
                posarg.eval(context)
            bases = tuple(context.pop(len(guard.positional_args)))
        elif type(guard) == VarNode:
            name = guard.lexeme.word
        self.block.eval(context)
        context.pop()
        dict = {**self.block.subcontext.consts, **self.block.subcontext.lets}
        context.push(type(name, bases, dict))
        context.add_const(name, context.stack[-1])



class Subline(Grouping):
    type_ = "line"
    def __init__(self, elements):
        elements = [e for e in elements if e.type_ != "endline"]
        self.elements = PrecedenceNode.parse(elements, grammar = "line")

    def eval(self, context):
        self.elements[0].eval(context)

    @property
    def empty(self):
        return not self.elements

class Line(Grouping):
    type_ = "line"
    def __init__(self, elements):
        elements = [e for e in elements if e.type_ != "endline"]
        elements = link_suite(elements)
        children_list = []
        if elements:
            next(elements).link(elements, children_list)
        self.elements = PrecedenceNode.parse(children_list, grammar = "line")

    def eval(self, context):
        self.elements[0].eval(context)
        return context.pop()

    @property
    def empty(self):
        return not self.elements


class Program(Grouping):
    type_ = "program"
    def __init__(self, lines):
        self.lines = lines
    def eval(self):
        context = CONTEXT
        retval = None
        for line in self.lines:
            retval = line.eval(context)
        return retval


line_node_map = {
            ".": DotNode,
            "=": AssignNode,
            ":": DictKeyNode,
            ",": CommaNode,
            "var": VarNode,
            "literal": LiteralNode,
            "**": PowerNode,
            "**=": PowerAssignNode ,
            "+": PlusNode,
            "+=": AddAssignNode,
            "-": MinusNode,
            "-=": SubtractAssignNode,
            "*": MultiplyNode,
            "*=": MultiplyAssignNode,
            "@": MatrixMultiplyNode,
            "@=": MatrixMultiplyAssignNode,
            "/": TrueDivideNode,
            "/=": TrueDivideAssignNode,
            "//": FloorDivideNode,
            "//=": FloorDivideAssignNode,
            "%": ModuloNode,
            "%=": ModuloAssignNode,
            "~": BitwiseNotNode,
            "&": BitwiseAndNode,
            "&=": BitwiseAndAssignNode,
            "|": BitwiseOrNode,
            "|=": BitwiseOrAssignNode,
            "^": BitwiseXorNode,
            "^=": BitwiseXorAssignNode,
            "<<": ShiftLeftNode,
            "<<=": ShiftLeftAssignNode,
            ">>": ShiftRightNode,
            ">>=": ShiftRightAssignNode,
            "<": LtNode,
            "<=": LeNode,
            ">": GtNode,
            ">=": GeNode,
            "==": EqualsNode,
            "!=": NotEqualsNode,
            "is": IsNode,
            "is not": IsNotNode,
            "in": InNode,
            "not in": NotInNode,
            "and": BooleanAndNode,
            "or": BooleanOrNode,
            "not": BooleanNotNode,
            "parentheses_grouping": ParenthesesNode,
            "bracket_grouping": BracketNode,
            "brace_grouping": BraceNode,
            "import": ImportNode,
            "raise": RaiseNode,
            "let": LetNode,
            "const": ConstNode,
            "return": ReturnNode,
            "break": BreakNode,
            "del": DelNode,
        }
SUITE_KEYWORDS = {'for': ForExpression,
              'while': WhileExpression,
              'try': TryExpression,
              'except': ExceptExpression,
              'finally': FinallyExpression,
              'if': IfExpression,
              'elif': ElifExpression,
              'else': ElseExpression,
              'with': WithExpression,
              'def': DefExpression,
              'class': ClassExpression,
}
