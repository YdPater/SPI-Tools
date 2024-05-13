from pyftdi.spi import SpiController
from math import floor
from argparse import ArgumentParser


def int_to_three_bytes(num):
    if not (0 <= num <= 0xFFFFFF):
        raise ValueError("Number must be between 0 and 16777215 (0xFFFFFF)")
    
    byte1 = (num >> 16) & 0xFF  # Extract the third (most significant) byte
    byte2 = (num >> 8) & 0xFF   # Extract the second byte
    byte3 = num & 0xFF          # Extract the first (least significant) byte

    return byte1, byte2, byte3



class Handler():
    def __init__(self, ftdi_device: str = 'ftdi://:/1'):
        _spi = SpiController()
        _spi.configure(ftdi_device)
        self.slave = _spi.get_port(cs=0, freq=12E6, mode=0)
    
    def dump_head(self):
        ascii_string = ""
        print()
        _data = self.slave.exchange([0x03, 0x00, 0x00, 0x00], 100)
        _addr = 0
        amount_per_row = 20
        counter = 0
        for d in _data:
            if d < 128:
                ascii_string += chr(d)
            else: 
                ascii_string += "."

            if counter == 0:
                print(f"{_addr:#0{6}x}| ", end="")
            if counter < amount_per_row -1:
                print(f"{format(d, '02x')}", end=" ")
                counter += 1
            else:
                print(f"{format(d, '02x')}", end=" | ")
                print(ascii_string, end=" |\n")
                ascii_string = ""
                counter = 0
            _addr += 1
                
        print()
    
    def page_write(self):
        pass


class Winbond25QXX(Handler):

    def __init__(self, ftdi_device: str = 'ftdi://:/1', size=100):
        super().__init__(ftdi_device)
        self.size = size

    def dump_full(self, outputfile: str = "mem.out"):
        start = 0
        msb, mmb, lsb = int_to_three_bytes(start)
        with open(outputfile, 'wb') as outfile:
            while True:
                if start + 255 > self.size:
                    chunk = self.size % 255
                    _data = self.slave.exchange([0x03, msb, mmb, lsb], chunk)
                    outfile.write(bytes(_data))
                    return
                else:
                    _data = self.slave.exchange([0x03, msb, mmb, lsb], 255)
                    outfile.write(bytes(_data))
                    start += 256


class Winbond25Q64(Winbond25QXX):
    SIZE = 0x800000
    
    def __init__(self, ftdi_device: str = 'ftdi://:/1', size=SIZE):
        super().__init__(ftdi_device)
        self.size = size


class Winbond25Q128(Handler):
    SIZE = 0x1000000
    
    def __init__(self, ftdi_device: str = 'ftdi://:/1'):
        super().__init__(ftdi_device)
    
    def dump_full(self, outputfile: str = "mem.out"):
        chunk_size = 256
        high = 0
        mid = 0
        with open(outputfile, "ab") as outfile:
            while True:
                if high == 0xff:
                    if mid == 0xff:
                        _data = self.slave.exchange([0x03, high, mid, 0x00], chunk_size)
                        outfile.write(bytes(_data))
                        print("Done!")
                        return
                _data = self.slave.exchange([0x03, high, mid, 0x00], chunk_size)
                outfile.write(bytes(_data))
                if mid == 0xff: 
                    high += 1
                    mid = 0
                else:
                    mid += 1


if __name__ == "__main__":
    parser = ArgumentParser(description="SPI toolkit")
    parser.add_argument("--ftdi-device", help="Specify FTDI device.", default="ftdi://:/1")
    parser.add_argument("--spi-device", choices=["winbond_25q64", "winbond_25q128"], help="Specify SPI flash device to dump",required=True)
    parser.add_argument("-o", "--output", help="Output file", default="mem.out", type=str)
    parser.add_argument("-a", "--address", help="Read from or write to this address", type=int)
    subparsers = parser.add_subparsers(dest="Mode command")
    subparsers.required = True
    mode_parser = subparsers.add_parser("mode")
    mode_parser.add_argument("mode", choices=['dump_head', 'dump_full_content','read_from', "write_to"], help="Select the desired operation")
    args = parser.parse_args()

    if args.spi_device == "winbond_25q64":
        spi = Winbond25Q64(ftdi_device=args.ftdi_device)
    elif args.spi_device == "winbond_25q128":
        spi = Winbond25Q128(ftdi_device=args.ftdi_device)
    else:
        print("[!] Unsupported device.")

    if args.mode == "dump_head":
        spi.dump_head()
    
    if args.mode == "dump_full_content":
        spi.dump_full(args.output)