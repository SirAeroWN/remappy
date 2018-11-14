# 3 different action modes: short, macro, cmd
# short mode:
#   uses '+' to seperate keys
# macro mode:
#   no delimeters
#   modifier keys are represented as escapes
# cmd mode:
#   strings are run in a shell


import re


names = {'uinput': 'ui', 'ecodes': 'e'}
mod_converter = {
    'ctrl': 'LEFTCTRL',
    'lctrl': 'LEFTCTRL',
    'rctrl': 'RIGHTCTRL',
    'alt': 'LEFTALT',
    'lalt': 'LEFTALT',
    'ralt': 'RIGHTALT',
    'meta': 'LEFTMETA',
    'lmeta': 'LEFTMETA',
    'rmeta': 'RIGHTMETA',
    'super': 'LEFTMETA',
    'shift': 'LEFTSHIFT',
    'lshift': 'LEFTSHIFT',
    'rshift': 'RIGHTSHIFT'
}
mod_keys = list(mod_converter.keys())

special_converter = {
    'enter': 'ENTER',
    'return': 'ENTER',
    'up': 'UP',
    'right': 'RIGHT',
    'down': 'DOWN',
    'left': 'LEFT',
    'tab': 'TAB'
}
special_keys = list(special_converter.keys())


class Lexer():
    def __init__(self):
        self.tokens = []

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i < len(self.tokens):
            result = self.tokens[self.i]
            self.i += 1
            return result
        else:
            raise StopIteration

    def __repr__(self):
        return str(self.tokens)


class Short_Lexer(Lexer):
    def __init__(self, in_str):
        super().__init__()
        self.tokens = self.digest(in_str)

    def digest(self, in_str):
        token_strs = in_str.split('+')
        return token_strs


class Macro_Lexer(Lexer):
    def __init__(self, in_str):
        super().__init__()
        self.tokens = self.digest(in_str)

    def digest(self, in_str):
        token_strs = []
        c = re.compile(r'(?P<ctrl>\\C)|(?P<shift>\\S)|(?P<alt>\\A)|(?P<meta>\\M)')
        i = 0
        while i < len(in_str):
            mo = c.match(in_str[i:])
            if mo is None:
                # no matches, must be regular
                token_strs.append(in_str[i])
                i += 1
            else:
                for k, v in mo.groupdict().items():
                    if v is None:
                        continue
                    else:
                        token_strs.append(k)
                        break
                i += mo.end()
        return token_strs


class Layer_Lexer(Lexer):
    def __init__(self, in_str):
        super().__init__()
        self.tokens = self.digest(in_str)

    def digest(self, in_str):
        token_strs = in_str.split(' ')
        return token_strs


class Map_Builder():
    def __init__(self, lexer, mod_keys=mod_keys):
        self.lexer = lexer
        self.commands = []
        self.mod_keys = mod_keys

    def __repr__(self):
        return str(self.commands)

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i < len(self.commands):
            result = self.commands[self.i]
            self.i += 1
            return result
        else:
            raise StopIteration

    def build(self):
        mods = []
        self.mod_keys
        for token in self.lexer:
            if token in mod_keys:
                self.commands.append((token, 'down'))
                mods.append((token, 'up'))
            else:
                self.commands.append((token, 'down'))
                self.commands.append((token, 'up'))
                while len(mods) > 0:
                    self.commands.append(mods.pop())
        while len(mods) > 0:
            self.commands.append(mods.pop())


class Layer_Builder():
    def __init__(self, lexer):
        self.lexer = lexer
        self.commands = []

    def __repr__(self):
        return str(self.commands)

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i < len(self.commands):
            result = self.commands[self.i]
            self.i += 1
            return result
        else:
            raise StopIteration

    def build(self):
        tokens = list(self.lexer)
        cmd = tokens[0]
        self.commands.append('global current_layer')
        if cmd == 'inc':
            self.commands.append('current_layer.inc(%s)' % tokens[1])
        elif cmd == 'dec':
            self.commands.append('current_layer.dec(%s)' % tokens[1])
        elif cmd == 'set':
            self.commands.append('current_layer.set(%s)' % tokens[1])
        elif cmd == 'alt' or cmd == 'rot':
            self.commands.append('layers = %s' % ('[' + ', '.join(tokens[1:]) + ']'))
            self.commands.append('current_layer.rotate(layers)')
        else:
            self.commands.append('pass')


class Converter():
    def __init__(self, builder, names=names, mod_keys=mod_keys, mod_converter=mod_converter):
        self.builder = builder
        self.commands = []
        self.uinput_name = names.get('uinput', 'ui')
        self.ecodes_name = names.get('ecodes', 'e')
        self.mod_keys = mod_keys
        self.mod_converter = mod_converter

    def __repr__(self):
        return '\n'.join(self.commands)

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i < len(self.commands):
            result = self.commands[self.i]
            self.i += 1
            return result
        else:
            raise StopIteration

    def convert(self):
        self.builder.build()
        for c in self.builder:
            cmd_string = self.uinput_name + '.write(' + self.ecodes_name + '.EV_KEY, ' + self.ecodes_name + '.KEY_'
            if c[0].lower() in mod_keys:
                cmd_string += mod_converter.get(c[0].lower())
            elif c[0].lower() in special_keys:
                cmd_string += special_converter.get(c[0].lower())
            else:
                cmd_string += c[0].upper()
            cmd_string += ', '
            if c[1] == 'down':
                cmd_string += '1'
            elif c[1] == 'up':
                cmd_string += '0'
            cmd_string += ')'
            self.commands.append(cmd_string)


# ml = Macro_Lexer('al\\A\\Cpha\\Sbet\\Ma')
# ml = Macro_Lexer('\\Cc')
# ml = Short_Lexer('ctrl+rshift+c')
# mb = Map_Builder(ml, mod_keys)
# c = Converter(mb, names, mod_keys, mod_converter)
# c.convert()
# print(c)
# with open('test.txt', 'r') as f:
#   for line in f:
#       for c in line:
#           if bytes('\\\\', "utf-8").decode("unicode_escape") == c:
#               print('good', c)
#           else:
#               print('bad', c)
