import json
import macro_parser
from macro_parser import Converter, Map_Builder, Short_Lexer, Macro_Lexer


fname = 'config.json'
out_fname = 'compiled.py'


def make_func_name(in_key):
    return 'keymap_for_input_' + in_key


def get_ecode(inp):
    if inp in macro_parser.mod_keys:
        return 'KEY_' + macro_parser.mod_converter[inp]
    else:
        return 'KEY_' + inp.upper()


def create_function(keymap):
    # first we'll make the function signature
    func_sig = 'def ' + make_func_name(keymap.get('input', 'default')) + '(' + macro_parser.names.get('uinput', 'ui') + '):'
    # next, we'll make the body of the function
    body = []
    for k,v in keymap.items():
        if k == 'short':
            c = Converter(Map_Builder(Short_Lexer(v)))
            c.convert()
            body = c.commands
            break
        elif k == 'macro':
            c = Converter(Map_Builder(Macro_Lexer(v)))
            c.convert()
            body = c.commands
            break
    body.append(macro_parser.names.get('uinput', 'ui') + '.syn()')
    # now combine them into a function
    func_str = func_sig
    bld_str = ''.join(['\n\t' + s for s in body])
    return func_str + bld_str

with open(fname, 'r') as f:
    data = json.load(f)

maps = data.get('maps', [])
funcs = []
func_dict = {}
for m in maps:
    funcs.append(create_function(m))
    inp = m.get('input', 'default')
    fnc = make_func_name(inp)
    key = get_ecode(inp)
    func_dict[key] = fnc

# the template
template ="""
from evdev import ecodes as e


%s


def default(%s):
    print('default')


def callback(event, ui):
    # event should already be categorized
    if event.keystate == 1:
        print(event.keycode)
        {%s}[event.keycode](%s)
"""

func_block = '\n\n'.join(funcs)
dict_block = ', '.join(['\'' + k + '\': ' + v for k,v in func_dict.items()])
result = template % (func_block, macro_parser.names.get('uinput', 'ui'), dict_block, macro_parser.names.get('uinput', 'ui'))
print(result)

with open(out_fname, 'w') as f:
    f.write(result)

# now load that file
module = __import__(out_fname[:-3])
my_class = getattr(module, 'callback')


import asyncio
import evdev
from evdev import UInput, ecodes as e

dev = evdev.InputDevice('/dev/input/event3')
dev.grab()
ui = UInput()

async def print_events(device):
    async for event in device.async_read_loop():
        if event.type == e.EV_KEY:
            print(evdev.categorize(event).keycode)
            ke = evdev.categorize(event)
            my_class(ke, ui)


asyncio.ensure_future(print_events(dev))

loop = asyncio.get_event_loop()
loop.run_forever()

ui.close()
