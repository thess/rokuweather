# Telnet comms to Roku Soundbridge

import sys
import socket
from telnetlib import Telnet


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
        self.sb = Telnet()
        self.dpytype = dtype
        self.host = None

    def open(self, host):
        try:
            self.sb.open(host, 4444, 10)
            prompt = self.sb.expect([b'SoundBridge> ', b'sketch> '], 2)
            if (prompt[0] == -1):
                print("SB not responding")
                self.sb.close()
                return False

        except (ConnectionError, socket.error) as err:
            print("SoundBridge '{}', not found or connect failure = {}".format(host, err))
            return False

        # Save host for reopen()
        self.host = host
        # Set character encoding default
        self.msg(encoding='utf8')
        self.cmd("irman echo")
        return True

    def reopen(self):
        if (self.host is None):
            return False
        assert(self.sb.get_socket() is None)
        return self.open(self.host)

    def close(self):
        if (self.sb.get_socket() is None):
            return
        try:
            # self.cmd("sketch -c clear")
            self.cmd("sketch -c exit")
            self.cmd("irman off")
            self.cmd("exit")
        except socket.error:
            print("Socket error in close = {}", sys.exc_info())
        finally:
            if (self.sb.get_socket() is not None):
                self.sb.close()

    # Optional args to msg (soundbridge display)
    #
    # text          - default none - can be omitted to just set font and encoding
    # x,y  location - default 0,0
    # font          -
    # clear         - 0/1 force the display to clear first (default 0)
    # encoding      - set roku text encoding
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
        try:
            self.sb.write(text.encode('utf-8') + b'\n')
        except socket.error:
            print("Socket error in write = {}", sys.exc_info())
            if (self.sb.get_socket() is not None):
                self.sb.close()
            raise

    def clear(self):
        self.cmd("sketch -c clear")

    # Handle input and look for IR commands between panels
    def keyproc(self, timeout):
        self.cmd("irman intercept")
        try:
            msg = self.sb.expect([b'irman: (.*)$'], timeout)
        except EOFError:
            if (self.sb.get_socket() is not None):
                self.sb.close()
            raise

        # Got an IR code - pass it on to SB and exit app
        self.cmd("irman off")
        if (msg[0] == -1):
            return 'TIMEOUT'
        self.cmd("sketch -c exit")
        ir_cmd = msg[1].group(1)
        self.cmd("irman dispatch {}".format(ir_cmd))
        return ir_cmd