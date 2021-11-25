import wave
import os
import cv2
import sys
import numpy as np
import getopt


class ExcepHandler(Exception):
    pass


class Image_stegano():
    def __init__(self, pic):
        self.image = pic
        self.h, self.w, self.nbdim = pic.shape
        self.size = self.w * self.h

        self.val_o_mask = [1, 2, 4, 8, 16, 32, 64, 128]

        self.one_m = self.val_o_mask.pop(0)

        self.val_z_mask = [254, 253, 251, 247, 239, 223, 191, 127]

        self.zero_m = self.val_z_mask.pop(0)

        self.wid = 0
        self.hei = 0
        self.dim = 0

    def ins_bin(self, bits):
        for z in bits:

            val = list(self.image[self.hei, self.wid])
            if int(z) == 1:
                val[self.dim] = int(
                    val[self.dim]) | self.one_m
            else:
                val[self.dim] = int(
                    val[self.dim]) & self.zero_m

            self.image[self.hei, self.wid] = tuple(val)
            self.following_open()

    def following_open(self):
        if self.dim == self.nbdim-1:
            self.dim = 0
            if self.wid == self.w-1:
                self.wid = 0
                if self.hei == self.h-1:
                    self.hei = 0
                    if self.one_m == 128:
                        raise ExcepHandler("Image is full")
                    else:
                        self.one_m = self.val_o_mask.pop(0)
                        self.zero_m = self.val_z_mask.pop(0)
                else:
                    self.hei += 1
            else:
                self.wid += 1
        else:
            self.dim += 1

    def processbit(self):
        val = self.image[self.hei, self.wid][self.dim]
        val = int(val) & self.one_m
        self.following_open()
        if val > 0:
            return "1"
        else:
            return "0"

    def processbytes(self):
        return self.processbits(8)

    def processbits(self, nb):
        bits = ""
        for i in range(nb):
            bits += self.processbit()
        return bits

    def byteValue(self, val):
        return self.binval(val, 8)

    def binval(self, val, bitsize):
        binval = bin(val)[2:]
        if len(binval) > bitsize:
            raise ExcepHandler(
                "The size of bin is large")
        while len(binval) < bitsize:
            binval = "0"+binval
        return binval

    def textenc(self, txt):
        l = len(txt)

        binl = self.binval(l, 16)
        self.ins_bin(binl)
        for char in txt:
            c = ord(char)
            self.ins_bin(self.byteValue(c))
        return self.image

    def textdec(self):
        ls = self.processbits(16)
        l = int(ls, 2)
        i = 0
        tx = ""
        while i < l:
            t = self.processbytes()
            i += 1
            tx += chr(int(t, 2))
        return tx

    def imgenc(self, imag):
        w = imag.w
        h = imag.h
        if self.w*self.h*self.nbdim < w*h*imag.channels:
            raise ExcepHandler(
                "Picture is not compatible with size")

        iw = self.binval(w, 16)
        ih = self.binval(h, 16)
        self.ins_bin(iw)
        self.ins_bin(ih)
        for h in range(imag.h):
            for w in range(imag.w):
                for chan in range(imag.channels):
                    val = imag[h, w][chan]
                    self.ins_bin(self.byteValue(int(val)))
        return self.image

    def imgdec(self):
        w = int(self.processbits(16), 2)
        h = int(self.processbits(16), 2)

        imag = np.zeros((w, h, 3), np.uint8)
        for h in range(h):
            for w in range(w):
                for chan in range(imag.channels):
                    val = list(imag[h, w])
                    val[chan] = int(self.processbytes(), 2)
                    imag[h, w] = tuple(val)
        return imag

    def binenc(self, data):
        l = len(data)
        if self.w*self.h*self.nbdim < l+64:
            raise ExcepHandler(
                "Image not huge enought to handle")
        self.ins_bin(self.binval(l, 64))
        for byte in data:
            byte = byte if isinstance(byte, int) else ord(
                byte)
            self.ins_bin(self.byteValue(byte))
        return self.image

    def bindb(self):
        l = int(self.processbits(64), 2)
        output = b""
        for i in range(l):
            output += bytearray([int(self.processbytes(), 2)])
        return output


def main():
    def help():
        print("                                              Usage of this tool")
        print("")
        print("")
        print("     For audio ")
        print("")
        print("python stegauim.py -m audio -p encode -i <input message> -o <file to be encoded> -f <name of the file to be saved>")
        print("python stegauim.py -m audio -p decode -i <input file to be decoded>")
        print("")
        print("     For images")
        print("")
        print("python stegauim.py -m image -p encode -i <this file is viewed as end result(cover image)> -o <name of the file to be saved> -f <file to be encoded>")
        print("python stegauim.py -m image -p decode -i <input file> -o <output file>")
    if not len(sys.argv[1:]):
        help()
        exit()
    argo = sys.argv[1:]
    try:
        opts, args = getopt.getopt(
            argo, "m:p:i:o:f:h", ['mode=', 'operation=', 'input=', 'output=', 'file=', 'help='])
        mode = opts[0][1].lower()
        operation = opts[1][1].lower()

        if operation == "decode":
            if mode == "image":
                inp = opts[2][1].lower()
                out = opts[3][1].lower()
                imag = cv2.imread(inp)
                steg = Image_stegano(imag)
                raw = steg.bindb()
                with open(out, "wb") as f:
                    f.write(raw)
            if mode == "audio":
                inp = opts[2][1].lower()
                aud = inp
                check = False
                if aud:
                    check = True

                def ex_msg(aud):
                    if not check:
                        help()
                    else:
                        waveaudio = wave.open(aud, mode='rb')
                        frame_bytes = bytearray(
                            list(waveaudio.readframes(waveaudio.getnframes())))
                        extracted = [frame_bytes[i] &
                                     1 for i in range(len(frame_bytes))]
                        string = "".join(chr(
                            int("".join(map(str, extracted[i:i+8])), 2)) for i in range(0, len(extracted), 8))
                        msg = string.split("###")[0]
                        print(
                            "The Hidden Message is: "+msg)
                        waveaudio.close()

                try:
                    ex_msg(aud)
                except:
                    print("Try again")
                    quit('')
        if operation == "encode":
            if mode == "image":
                inp = opts[2][1].lower()
                out = opts[3][1].lower()
                file = opts[4][1]
                data = open(file, "rb").read()
                imag = cv2.imread(inp)
                steg = Image_stegano(imag)
                res = steg.binenc(data)
                print(out)
                cv2.imwrite(os.getcwd()+'/'+out, res)
            if mode == "audio":
                inp = opts[2][1].lower()
                out = opts[3][1].lower()
                file = opts[4][1]
                aud = out
                string = inp
                output = file
                check = False
                if aud and string and output:
                    check = True

                def em_audio(aud, string, output):
                    if not check:
                        help()
                    else:
                        waveaudio = wave.open(aud, mode='rb')
                        frame_bytes = bytearray(
                            list(waveaudio.readframes(waveaudio.getnframes())))
                        string = string + \
                            int((len(frame_bytes)-(len(string)*8*8))/8) * '#'
                        bits = list(
                            map(int, ''.join([bin(ord(i)).lstrip('0b').rjust(8, '0') for i in string])))
                        for i, bit in enumerate(bits):
                            frame_bytes[i] = (frame_bytes[i] & 254) | bit
                        frame_modified = bytes(frame_bytes)
                        with wave.open(output, 'wb') as fd:
                            fd.setparams(waveaudio.getparams())
                            fd.writeframes(frame_modified)
                        waveaudio.close()
                try:
                    em_audio(aud, string, output)
                except:
                    print("Try again")
                    quit('')

    except getopt.GetoptError:
        help()


if __name__ == "__main__":
    main()
