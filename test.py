from struct import unpack, pack
from time import sleep

from imax.b6mini import *

dev = B6Mini()

dev.print_charge_info()
dev.stop()

dev.discharge(BAT_LIPO, 2, 0.3, 3.2)
