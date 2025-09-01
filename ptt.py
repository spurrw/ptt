""" Handles PTT for my radio. Watches log files of Digital mode programs and opens/closes
the relay when transmit and stop transmit is detected. Opening relay connects
2 pins that activates PTT on radio. 

https://www.youtube.com/watch?v=26XHb_cpiAA&t=577s
https://robojax.com/RJT86
Relay: Ch340 usb relay. This one is from Jessinie on Amazon
https://docs.python.org/3/library/argparse.html
https://python-sounddevice.readthedocs.io/en/latest/index.html
https://stackoverflow.com/questions/44056846/how-to-read-and-write-from-a-com-port-using-pyserial
https://stackoverflow.com/questions/32018993/how-can-i-send-a-byte-array-to-a-serial-port-using-python
https://python-sounddevice.readthedocs.io/en/0.3.15/api/streams.html


"""

import sounddevice as sd
import numpy as np
import serial
from datetime import datetime as date
import argparse


# makes sure relay is closed, COM port is closed
def cleanup():
    global args
    global relay
    ptt_disable()
    if (args.no_relay):
        relay.close()


def ptt_enable ():
    global ptt
    global relay

    # write to serial port
    if (args.no_relay):
        relay.write(bytearray([0xA0, 0x01, 0x01, 0xA2]))

    print("PTT ON")
    ptt = True


def ptt_disable ():
    global ptt
    global relay

    # write to serial port
    if (args.no_relay):
        relay.write(bytearray([0xA0, 0x01, 0x00, 0xA1]))

    print("PTT off")
    ptt = False


# called repeatedly to monitor sound levels.
def monitor_sound_level (indata, outdata, frames, time, status):
    outdata[:] = indata # pass input audio to output
    volume = np.linalg.norm(indata)*10
    #print ((int(volume_norm)))
    #print ("|" * int(volume_norm))
    # significant sound detected and we're Rx
    
    global nosound_time
    global nosound_waiting
    global args

    # sound risen above level?
    if (volume > args.audio_level):
        # Tx if not already
        if (not ptt):
            #print(int(volume))
            ptt_enable()

        # stop tracking no sound time in case ware, we just heard sound!
        nosound_waiting = False

    # sound dropped below level during Tx?
    elif (volume <= args.audio_level and ptt):
        # cooldown set to 0? stop ptt
        if (args.cooldown_ms == 0):
            ptt_disable()

        # reset the time sound stopped
        elif (not nosound_waiting):
            nosound_waiting = True
            nosound_time = date.now()
            
        # sound stopped for longer than args.cooldown_ms? stop PTT
        elif ((date.now() - nosound_time).total_seconds() * 1000 >= args.cooldown_ms):
            ptt_disable()
            nosound_waiting = False
            print("nosound_time:" + str((date.now() - nosound_time).total_seconds() * 1000) + " ms")


## ==== CLI Arguments ====
parser = argparse.ArgumentParser()

parser.add_argument(
    '-t', '--cooldown_ms', type=int, default=0,
    help='miliseconds to wait below audio level threshold before disabling PTT')

parser.add_argument(
    '-a', '--audio_level', type=int, default=5,
    help='audio level that must be reached to activate PTT')

parser.add_argument(
    '-i', '--inputdevice', type=int,
    help='input audio device (numeric ID or substring)')

parser.add_argument(
    '-o', '--outputdevice', type=int,
    help='output audio device (numeric ID or substring)')

parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')

parser.add_argument(
    '-c', '--channels',  type=int, default=1,
    help='number of audio channels to transmit')

parser.add_argument(
    '--no-relay', action='store_false',
    help='do nothing with relays if set. Used for testing')

parser.add_argument(
    '-r', '--relay', type=str,
    help='relay COM port name. ex \'COM3\' or \'COM4\'')

parser.add_argument(
    '--baud-rate',  type=int, default=9600,
    help='baud rate of COM port')

parser.add_argument(
    '--byte-size',  type=int, default=8,
    help='byte size of COM port')

parser.add_argument(
    '--com-timeout',  type=int, default=None,
    help='timeout of COM port')

parser.add_argument(
    '--stop-bits',  type=int, default=1,
    help='stop bits of COM port')

args = parser.parse_args()

if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)


## ==== Global variables ====
nosound_time = None # time no sound was last detected
nosound_waiting = False # are we currently waiting for no sound cooldown_ms to disable PTT?
ptt = False # is PTT activated now?

# get relay COM object
relay = None
if (args.no_relay):
    try:
        relay = serial.Serial(port=args.relay, baudrate=args.baud_rate, bytesize=args.byte_size, timeout=args.com_timeout, stopbits=args.stop_bits)
    except Exception as e:
        print("Failed to open COM port")
        parser.exit(type(e).__name__ + ': ' + str(e))

## ==== Main Loop ====
try:
    with sd.Stream(callback=monitor_sound_level, device=(args.inputdevice, args.outputdevice), channels=args.channels):
        print("#" * 20)
        print("press Return to quit")
        print("#" * 20)
        print()
        input()
        #while (True):    
        #    sd.sleep(10000)
except KeyboardInterrupt:
    cleanup()
    parser.exit("")
except Exception as e:
    cleanup()
    parser.exit(type(e).__name__ + ': ' + str(e))

print("Exiting...")
cleanup()
parser.exit("")
