# Draw netpbm (P1) weather icon to Roku

import sys
import json


# Map OWM condition codes to icon
# 'altid' refers to yahoo/wu weather icons
class wi_icons(object):
    def __init__(self):
        try:
            icons = open('ow_icons.json')
            self.wi_map = json.load(icons)
            icons.close()
        except FileNotFoundError:
            print("Cannot find icons.json")
            exit()
        except json.JSONDecodeError:
            print("Error parsing icons file")
            exit()

    # Define generator for pbm tokens
    def tokenize(self, f):
        for line in f:
            # skip comments
            if line[0] != '#':
                for t in line.split():
                    # return single atom
                    yield t

    def drawItAt(self, sb, code, locx, locy):
        try:
            icon = self.wi_map[str(code)]['altid']
        except KeyError:
            icon = 3200
            pass

        # Open PBM file
        prefix = "s-" if (sb.dpytype == 1) else ""
        try:
            f = open("pbm/" + prefix + icon + ".pbm")
        except IOError:
            print("PBM file ({}.pbm) open failure".format(prefix + icon))
            exit()

        try:
            t = self.tokenize(f)
            nexttoken = lambda: next(t)
            assert ('P1' == nexttoken()), 'Not a P1 PBM file'
            # Get HxW dimensions
            sizex = int(nexttoken())
            sizey = int(nexttoken())
            # Set display invisible bounding box
            sb.cmd("sketch -c color 0")
            sb.cmd("sketch -c rect {} {} {} {}".format(locx, locy, sizex, sizey))
            sb.cmd("sketch -c color 1")

            # Now plot data
            for y in range(sizey):
                x = 0
                while (x < sizex):
                    cnt = 1
                    bit = int(nexttoken())
                    if (bit == 1):
                        xpos = locx + x
                        ypos = locy + y
                        # Optimize horiz lines
                        while ((bit == 1) and (x < (sizex - 1))):
                            bit = int(nexttoken())
                            x += 1
                            if (bit == 1):
                                cnt += 1

                        x2 = xpos + cnt
                        # Line or point
                        if (cnt == 1):
                            sb.cmd("sketch -c point {} {}".format(xpos, ypos))
                        else:
                            sb.cmd("sketch -c line {} {} {} {}".format(xpos, ypos, x2, ypos))
                    x += 1

            # Close tokenizer
            t.close()

        except Exception:
            print("Problem processing {}.pbm file. Err = {}".format(prefix + code, sys.exc_info()[0]))
            f.close()
            raise

        else:
            f.close()

        return
