# encoding: utf-8

'''
Usage: evtest [options] [<device>, ...]

Input device enumerator and event monitor.

Running evtest without any arguments will let you select
from a list of all readable input devices.

Options:
  -h, --help          Show this help message and exit.
  -c, --capabilities  List device capabilities and exit.
  -g, --grab          Other applications will not receive events from
                      the selected devices while evtest is running.

Examples:
  evtest /dev/input/event0 /dev/input/event1
'''


from __future__ import print_function

import re
import sys
import json
import select
import atexit
import termios
import optparse

try:
    input = raw_input
except NameError:
    pass

import evdev
from evdev import ecodes, list_devices, AbsInfo, InputDevice


def parseopt():
    parser = optparse.OptionParser(add_help_option=False)
    parser.add_option('-h', '--help', action='store_true')
    parser.add_option('-g', '--grab', action='store_true')
    parser.add_option('-c', '--capabilities', action='store_true')
    return parser.parse_args()


def main():
    opts, devices = parseopt()
    if opts.help:
        print(__doc__.strip())
        return 0

    if not devices:
        devices = select_devices()
    else:
        devices = [InputDevice(path) for path in devices]

    if opts.capabilities:
        for device in devices:
            print_capabilities(device)
        return 0

    if opts.grab:
        for device in devices:
            device.grab()

    # # Disable tty echoing if stdin is a tty.
    # if sys.stdin.isatty():
    #     toggle_tty_echo(sys.stdin, enable=False)
    #     atexit.register(toggle_tty_echo, sys.stdin, enable=False)

    try:
        with open('mappings/mappings.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {"maps": []}

    # save configs on exit
    atexit.register(save_config, config)
    print('Listening for events, changes saved automatically (press ctrl-c to exit) ...')
    fd_to_device = {dev.fd: dev for dev in devices}
    while True:
        r, w, e = select.select(fd_to_device, [], [])

        for fd in r:
            for event in fd_to_device[fd].read():
                # print_event(event)
                add_to_config(event, config)


def add_to_config(event, config):
    if event.type == ecodes.EV_KEY:
        event = evdev.categorize(event)
        if event.keystate != 1:
            return
        temp = {'input': event.scancode}
        layer_number = input('Layer to map scancode %s in? ' % event.scancode).lower().strip()
        if layer_number == '':
            layer_number = 0
        else:
            layer_number = int(layer_number)
        mode = input('Short, Macro, or Layer for keycode %s?[S/M/L]' % event.scancode).lower()
        if mode == 's':
            temp['short'] = input('Short: ')
        elif mode == 'm':
            temp['macro'] = input('Macro: ')
        elif mode == 'l':
            temp['set_layer'] = input('Layer: ')
        else:
            # didn't enter an option, so don't possibly overwrite something
            return
        temp['layer'] = layer_number
        maps = config.get('maps', [])
        for i, m in enumerate(maps):
            if m.get('input', '') == temp['input'] and m.get('layer', 0) == temp['layer']:
                maps[i] = temp
                break
        else:
            maps.append(temp)
        config['maps'] = maps


def save_config(config, fname='mappings/mappings.json'):
    with open(fname, 'w') as f:
        json.dump(config, f, sort_keys=True, indent=4)


def select_devices(device_dir='/dev/input'):
    '''
    Select one or more devices from a list of accessible input devices.
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

    choices = input('Select devices [0-%s]: ' % (len(dev_lines) - 1))

    try:
        choices = choices.split()
        choices = [devices[int(num)] for num in choices]
    except ValueError:
        choices = None

    if not choices:
        msg = 'error: invalid input - please enter one or more numbers separated by spaces'
        print(msg, file=sys.stderr)
        sys.exit(1)

    return choices


def print_capabilities(device):
    capabilities = device.capabilities(verbose=True)

    print('Device name: {.name}'.format(device))
    print('Device info: {.info}'.format(device))
    print('Repeat settings: {}\n'.format(device.repeat))

    if ('EV_LED', ecodes.EV_LED) in capabilities:
        leds = ','.join(i[0] for i in device.leds(True))
        print('Active LEDs: %s' % leds)

    active_keys = ','.join(k[0] for k in device.active_keys(True))
    print('Active keys: %s\n' % active_keys)

    print('Device capabilities:')
    for type, codes in capabilities.items():
        print('  Type {} {}:'.format(*type))
        for code in codes:
            # code <- ('BTN_RIGHT', 273) or (['BTN_LEFT', 'BTN_MOUSE'], 272)
            if isinstance(code[1], AbsInfo):
                print('    Code {:<4} {}:'.format(*code[0]))
                print('      {}'.format(code[1]))
            else:
                # Multiple names may resolve to one value.
                s = ', '.join(code[0]) if isinstance(code[0], list) else code[0]
                print('    Code {:<4} {}'.format(s, code[1]))
        print('')


def print_event(e):
    if e.type == ecodes.EV_SYN:
        if e.code == ecodes.SYN_MT_REPORT:
            msg = 'time {:<16} +++++++++ {} ++++++++'
        else:
            msg = 'time {:<16} --------- {} --------'
        print(msg.format(e.timestamp(), ecodes.SYN[e.code]))
    else:
        if e.type in ecodes.bytype:
            codename = ecodes.bytype[e.type][e.code]
        else:
            codename = '?'

        evfmt = 'time {:<16} type {} ({}), code {:<4} ({}), value {}'
        print(evfmt.format(e.timestamp(), e.type, ecodes.EV[e.type], e.code, codename, e.value))


def toggle_tty_echo(fh, enable=True):
    flags = termios.tcgetattr(fh.fileno())
    if enable:
        flags[3] |= termios.ECHO
    else:
        flags[3] &= ~termios.ECHO
    termios.tcsetattr(fh.fileno(), termios.TCSANOW, flags)


if __name__ == '__main__':
    try:
        ret = main()
    except (KeyboardInterrupt, EOFError):
        ret = 0
    sys.exit(ret)
