# Remappy
Remappy is a utility for remapping scancodes from devices in software. This primarily means that you can remap a specific keyboard or mouse without effecting all keyboards or mice that you have plugged in.

## Advantages over similar tools
Existing tools such as [xmodmap](https://www.x.org/releases/current/doc/man/man1/xmodmap.1.xhtml) let you remap your keyboard keys and mouse buttons. However, they only allow for one-to-one mappings (e.g. 'L_ctrl' -> 'L_alt'), apply to all keyboards/mice, and cannot handle mice with more than 5 buttons. Remappy lets you remap an individual key to an arbitrary length macro. If you wanted to, you could remap your 's' key such that it prints the works of Shakespeare. Why would you want to do that? I dunno, but you could. Remappy also lets you remap devices individually, so if you have an external keyboard plugged in to your laptop, it can be mapped differently than your laptop's builtin keyboard. Lastly, because Remappy uses scancode input to trigger key presses, your MMO mouse (like the [razer naga](https://en.wikipedia.org/wiki/Razer_Naga) can do more than just be a numpad.


Many devices come with their own, proprietary remapping software (corsair and razer devices, for example). Unfortunately, the companies providing this software don't seem to care about linux users. While disappointing, this isn't particularly surprising. They're gaming companies and linux is *not* the place to go for hardcore gaming. Remappy is aimed at letting you use these devices to their full potential on linux.


Many mechanical keyboards support custom firmware based on [QMK](https://github.com/qmk/qmk_firmware). However, plenty of keyboards do not support custom firmware and use proprietary firmware that the end user can only change at their own peril. Remappy helps these users take full advantage of their keyboards.

## Disadvantages
Remappy is not a mature tool, mostly because I've only been adding features as I need them. Thus, if you want to remap a key to something that needs to be held down, (e.g. caps lock to control) it won't work properly. Additionally, many keys which aren't allowed as part of a python variable name (such as the grave '\`') need special handling. Lastly, there is only a command line interface and it is, well, not good at all. The good news is that I'm planning to fix these things in the future! Also, the code base is currently small enough that anyone familiar with python should be able to read it and figure out what's going on behind the curtains.


## Installation
Make sure you have a recent version of Python 3 installed.


Run `pip install -r requirements.txt` with the version appropriate pip to install required libraries.


## Usage
Since it is unlikely that you have the same keyboard and mouse as I do, nor desire the same mappings, you'll need to build a new config. Delete the file at `mappings/mappings.json` so you can start fresh (or just rename it). Now run `sudo config_builder.py` you need to use sudo so that the program has access to the device scancodes. It is recommended that you use a different device to type in the macros from the device that you are remapping. This is to work around a bug that is on the list to fix.

You will first be prompted to choose your device from a listing of devices. Each device will have a number displayed to the left, enter this number to begin remapping that device.


You will be prompted to hit a key on your device that you are remapping, do that. The program will report what scancode was read and then prompt you to choose a layer to map the key in. The default layer is 0, if you choose to map in a different layer, make sure you also map a key to changing layers

You will then be prompted to choose the remap type: short (s), macro (m), or layer (l).

Short remaps have the names of the keys separated by '+'

Example: `ctrl+shift+c`


Macro remaps use escapes to represent modification keys

Example: `\C\Sc`

Example 2: `\Shello, \Sworld!` will cause `Hello, World!` to be entered


Layer remaps allow switching between layers, there are 4 different commands: `alt`, `rotate`, `inc`, and `dec`.

`alt` takes two layer numbers and switches between the two, e.g. `alt 0 1` will switch between layer 0 and layer 1

`rotate` takes an arbitrary number of layers and rotates between them in the order given. For example, `rotate 1 4 3 5` will go from layer 1 to 4 to 3 to 5 and back to 1.

`inc` simply increments the layer number. For example layer 0 will go to layer 1 which will go to layer 2, ad infinitum

`dec` works the opposite way of `inc`


When you have entered all the remaps you want to create, simply kill the program with a ctrl-c or `kill` command from another terminal.


Now that you have created the mapping, you can run `sudo python3 parser.py` to run remappy. You will be prompted to choose a device like you were when setting up the config. Once you have chosen your device, remappy will echo whatever you have typed to this console. You can now switch to some other program and use your newly remapped device!


## Tips
- You can't run remappy in the background like you might other programs. To avoid always needing to have a terminal window open, run remappy in a tmux session, detach from the session, and close the terminal. Remappy will still work because tmux is still running. If you need to kill remappy for some reason, reattach to the tmux session and use ctrl-c
- You don't have to use the config builder if you know the scan codes that you want to remap. Just edit the mappings.json file directly, if you look at the examples provided in this repo it should be clear how the json file is formatted.
- You need to run this as root because the default users in most linux environments don't have access to the raw input and aren't allowed to intercept device scancodes. However, if you add your user to the `input` group then you can run remappy without superuser privileges
