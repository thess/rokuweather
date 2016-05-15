# Telnet comms to Roku Soundbridge

from telnetlib import Telnet as TN


# Font List for costumization:
#  1 - Fixed8
#  2 - Fixed16 (UFT8 font with japanese charachters)
#  3 - ZurichBold32
#  10 - ZurichBold16
#  11 - ZurichLite16
#  12 - Fixed16
#  14 - SansSerif16

class rokuSB:
    def __init__(self, dtype):
        self.sb = TN()
        self.dpytype = dtype

    def open(self, host):
        try:
            self.sb.open(host, 4444, 2)

            prompt = self.sb.expect([b'SoundBridge> ', b'sketch> '], 2)
            if (prompt[0] == -1):
                print("SB not responding")
                self.sb.close()
                return False
        except ConnectionError:
            print("SB not found or connect failure")
            return False

        return True

    def close(self):
        self.cmd("sketch -c clear")
        self.cmd("sketch -c exit")
        self.cmd("irman off")
        self.cmd("exit")
        self.sb.close()

    # Optional args to msg (soundbridge display)
    #
    # text          - default none - can be ommited to just set font and encoding
    # x,y  location - default 0,0
    # font          -
    # clear         - 0/1 force the display to clear first (default 0)
    #
    def msg(self, **kwargs):
        x = kwargs.get('x', 0)
        y = kwargs.get('y', 0)
        text = kwargs.get('text')
        clear = kwargs.get('clear', False)
        font = kwargs.get('font')
        encoding = kwargs.get('encoding')

        if (encoding is not None):
            self.cmd("sketch -c encoding " + str(encoding))

        if (font is not None):
            self.cmd("sketch -c font " + str(font))

        if (text is None):
            return

        if (clear):
            self.clear()

        self.cmd('sketch -c text {} {} "{}"'.format(x, y, text))
        return

    def cmd(self, text):
        self.sb.write(text.encode('utf-8') + b'\n')

    def clear(self):
        self.cmd("sketch -c clear")
