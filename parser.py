import re
import sys
import json
import asyncio
import evdev
from evdev import UInput, ecodes as e, list_devices, InputDevice

import macro_parser
from macro_parser import Converter, Map_Builder, Short_Lexer, Macro_Lexer


fname = 'mappings.json'
out_fname = 'compiled.py'


def select_device(device_dir='/dev/input'):
    '''
    Select a device from a list of accessible input devices.
    '''

    def devicenum(device_path):
        digits = re.findall(r'\d+$', device_path)
        return [int(i) for i in digits]

    devices = sorted(list_devices(device_dir), key=devicenum)
    devices = [InputDevice(path) for path in devices]
    if not devices:
        msg = 'error: no input devices found (do you have rw permission on %s/*?)'
        print(msg % device_dir, file=sys.stderr)
        sys.exit(1)

    dev_format = '{0:<3} {1.path:<20} {1.name:<35} {1.phys:<35} {1.uniq:<4}'
    dev_lines = [dev_format.format(num, dev) for num, dev in enumerate(devices)]

    print('ID  {:<20} {:<35} {:<35} {}'.format('Device', 'Name', 'Phys', 'Uniq'))
    print('-' * len(max(dev_lines, key=len)))
    print('\n'.join(dev_lines))
    print()

    choice = input('Select devices [0-%s]: ' % (len(dev_lines) - 1))

    try:
        choice = choice.strip().split()
        choice = [devices[int(num)] for num in choice]
    except ValueError:
        choice = None

    if not choice:
        msg = 'error: invalid input - please enter a number'
        print(msg, file=sys.stderr)
        sys.exit(1)

    return choice[0]


def make_func_name(in_key):
    return 'keymap_for_input_' + in_key


def get_ecode(inp):
    return inp


def create_function(keymap):
    # first we'll make the function signature
    func_sig = 'def ' + make_func_name(keymap.get('input', 'default')) + '(' + macro_parser.names.get('uinput', 'ui') + '):'
    # next, we'll make the body of the function
    body = []
    for k, v in keymap.items():
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
template = """
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
dict_block = ', '.join(['\'' + k + '\': ' + v for k, v in func_dict.items()])
result = template % (func_block, macro_parser.names.get('uinput', 'ui'), dict_block, macro_parser.names.get('uinput', 'ui'))
print(result)

with open(out_fname, 'w') as f:
    f.write(result)

# now load that file
module = __import__(out_fname[:-3])
my_class = getattr(module, 'callback')


# dev = evdev.InputDevice('/dev/input/event19')
dev = select_device()
dev.grab()
print(dev)
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
