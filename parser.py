#!/usr/bin/env python3

"""remappy

Usage:
  parser.py [<config_file>]

"""
# parser.py ship <name> move <x> <y> [--speed=<kn>]
# parser.py ship shoot <x> <y>
# parser.py mine (set|remove) <x> <y> [--moored | --drifting]
# parser.py (-h | --help)
# parser.py --version

# Options:
# -h --help     Show this screen.
# --version     Show version.
# --speed=<kn>  Speed in knots [default: 10].
# --moored      Moored (anchored) mine.
# --drifting    Drifting mine.

# """


import re
import sys
import json
import asyncio
import evdev
from docopt import docopt
from evdev import UInput, ecodes as e, list_devices, InputDevice

import libs.macro_parser as macro_parser
from libs.macro_parser import Converter, Map_Builder, Layer_Builder, Layer_Lexer, Short_Lexer, Macro_Lexer


fname = 'mappings/mappings.json'
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


def make_func_name(in_key, layer):
    return 'keymap_for_input_' + str(in_key) + '_' + str(layer)


def get_ecode(inp):
    return inp


def create_function(keymap):
    # first we'll make the function signature
    func_sig = 'def ' + make_func_name(keymap.get('input', 'default'), keymap.get('layer', 0)) + '(' + macro_parser.names.get('uinput', 'ui') + '):'
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
        elif k == 'set_layer':
            lb = Layer_Builder(Layer_Lexer(v))
            lb.build()
            body = list(lb)
            break
    body.append(macro_parser.names.get('uinput', 'ui') + '.syn()')
    # now combine them into a function
    func_str = func_sig
    bld_str = ''.join(['\n\t' + s for s in body])
    return func_str + bld_str


def get_device_by_name(name, device_dir='/dev/input'):
    devices = [InputDevice(path) for path in list_devices(device_dir)]
    dev = list(filter(lambda d: d.name == name, devices))
    if len(dev) == 0:
        return None
    elif len(dev) > 1:
        dev_format = '{0:<3} {1.path:<20} {1.name:<35} {1.phys:<35} {1.uniq:<4}'
        dev_lines = [dev_format.format(num, d) for num, d in enumerate(dev)]

        print('ID  {:<20} {:<35} {:<35} {}'.format('Device', 'Name', 'Phys', 'Uniq'))
        print('-' * len(max(dev_lines, key=len)))
        print('\n'.join(dev_lines))
        print()

        choices = input('Select device [0-%s]: ' % (len(dev_lines) - 1))

        try:
            choices = dev[int(choices.strip())]
        except ValueError:
            choices = None

        if not choices:
            msg = 'error: invalid input - please enter one or more numbers separated by spaces'
            print(msg, file=sys.stderr)
            sys.exit(1)

        return choices
    else:
        # dev has just one element
        return dev[0]


if __name__ == '__main__':
    arguments = docopt(__doc__, version='remappy 0.2')
    print(arguments)

    config_file = arguments.get('<config_file>', None)
    fname = 'mappings/mappings.json' if config_file is None else config_file

    # if len(sys.argv) > 2:
    #     fname = sys.argv[1]

    with open(fname, 'r') as f:
        data = json.load(f)

    maps = data.get('maps', [])
    funcs = []
    func_dict = {}
    num_layers = max(maps, key=lambda x: x.get('layer', 0)).get('layer', 0) + 1
    func_list = [{} for i in range(num_layers)]
    for m in maps:
        funcs.append(create_function(m))
        inp = m.get('input', 'default')
        fnc = make_func_name(inp, m.get('layer', 0))
        key = get_ecode(inp)
        func_list[m.get('layer', 0)][key] = fnc

    # the template
    template = """
from evdev import ecodes as e
from libs.layer import Layer


%s


def default(%s):
    print('default')


key_list = [%s]
key_dict_keys = [list(key_dict.keys()) for key_dict in key_list]


current_layer = Layer(0, len(key_list), 0)


def callback(event, ui):
    # event should already be categorized
    global key_dict
    global key_dict_keys
    if event.keystate == 1 and event.scancode in key_dict_keys[current_layer.layer]:
        # print(event.keycode, event.scancode)
        key_list[current_layer.layer][event.scancode](%s)
    else:
        ui.write_event(event)
        ui.syn()
"""

    func_block = '\n\n'.join(funcs)
    dict_block = ', '.join(['{' + (', '.join([str(k) + ': ' + str(v) for k, v in func_dict.items()])) + '}' for func_dict in func_list])
    result = template % (func_block, macro_parser.names.get('uinput', 'ui'), dict_block, macro_parser.names.get('uinput', 'ui'))
    # print(result)

    with open(out_fname, 'w') as f:
        f.write(result)

    # now load that file
    module = __import__(out_fname[:-3])
    my_class = getattr(module, 'callback')

    # dev = evdev.InputDevice('/dev/input/event19')
    name = data.get('name', None)
    if name is None:
        dev = select_device()
    else:
        dev = get_device_by_name(name)
        if dev is None:
            dev = select_device()
        else:
            print(f'Config uses {dev} is this ok [Y/N]?', end=' ')
            cont = input().strip().lower()
            if cont not in ['y', 'yes', '']:
                print(ord(cont))
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
