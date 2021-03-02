import struct
from TftpShared import *

class TftpPacketWithOptions(object):
    """This class exists to permit some TftpPacket subclasses to share code
    regarding options handling. It does not inherit from TftpPacket, as the
    goal is just to share code here, and not cause diamond inheritance."""
    def __init__(self):
        self.options = None

    def setoptions(self, options):
        myoptions = {}
        for key in options:
            newkey = str(key)
            myoptions[newkey] = str(options[key])

        self.__options = myoptions

    def getoptions(self):
        return self.__options

    # Set up getter and setter on options to ensure that they are the proper
    # type. They should always be strings, but we don't need to force the
    # client to necessarily enter strings if we can avoid it.
    options = property(getoptions, setoptions)

    def decode_options(self, buffer):
        """This method decodes the section of the buffer that contains an
        unknown number of options. It returns a dictionary of option names and
        values."""
        nulls = 0
        format = "!"
        options = {}

        if len(buffer) == 0:
            return {}

        # Count the nulls in the buffer. Each one terminates a string.
        length = 0
        for c in buffer:
            if ord(c) == 0:
                if length > 0:
                    format += "%dsx" % length
                    length = -1
                else:
                    raise TftpException, "Invalid options in buffer"
            length += 1
        try:
            mystruct = struct.unpack(format, buffer)
        except struct.error, message:
            print "Decode Error: %s"%message
            return options
        
        
        for i in range(0, len(mystruct), 2):
            options[mystruct[i]] = mystruct[i+1]

        return options

class TftpPacket(object):
    """This class is the parent class of all tftp packet classes. It is an
    abstract class, providing an interface, and should not be instantiated
    directly."""
    def __init__(self):
        self.opcode = 0
        self.buffer = None

    def encode(self):
        """The encode method of a TftpPacket takes keyword arguments specific
        to the type of packet, and packs an appropriate buffer in network-byte
        order suitable for sending over the wire.
        
        This is an abstract method."""
        raise NotImplementedError, "Abstract method"

    def decode(self):
        """The decode method of a TftpPacket takes a buffer off of the wire in
        network-byte order, and decodes it, populating internal properties as
        appropriate. This can only be done once the first 2-byte opcode has
        already been decoded, but the data section does include the entire
        datagram.
        
        This is an abstract method."""
        raise NotImplementedError, "Abstract method"

class TftpPacketInitial(TftpPacket, TftpPacketWithOptions):
    """This class is a common parent class for the RRQ and WRQ packets, as 
    they share quite a bit of code."""
    def __init__(self):
        TftpPacket.__init__(self)
        self.filename = None
        self.mode = None
        
    def encode(self):
        """Encode the packet's buffer from the instance variables."""

        ptype = None
        if self.opcode == 1: ptype = "RRQ"
        else:                ptype = "WRQ"
        
        format = "!H"
        format += "%dsx" % len(self.filename)
        if self.mode == "octet":
            format += "5sx"
        else:
            raise AssertionError, "Unsupported mode: %s" % mode
        # Add options.
        options_list = []
        if self.options.keys() > 0:
            for key in self.options:
                format += "%dsx" % len(key)
                format += "%dsx" % len(str(self.options[key]))
                options_list.append(key)
                options_list.append(str(self.options[key]))


        self.buffer = struct.pack(format,
                                  self.opcode,
                                  self.filename,
                                  self.mode,
                                  *options_list)

        return self
    
    def decode(self):

        # FIXME - this shares a lot of code with decode_options
        nulls = 0
        format = ""
        nulls = length = tlength = 0
        subbuf = self.buffer[2:]
        for c in subbuf:
            if ord(c) == 0:
                nulls += 1
                format += "%dsx" % length
                length = -1
                # At 2 nulls, we want to mark that position for decoding.
                if nulls == 2:
                    break
            length += 1
            tlength += 1

        # length should now be the end of the mode.
        shortbuf = subbuf[:tlength+1]
        try:
            mystruct = struct.unpack(format, shortbuf)
        except struct.error, message:
            print "packet error: %s"%message
            return self 
            

        self.filename = mystruct[0]
        self.mode = mystruct[1]

        self.options = self.decode_options(subbuf[tlength+1:])
        return self

class TftpPacketRRQ(TftpPacketInitial):
    """
        2 bytes    string   1 byte     string   1 byte
        -----------------------------------------------
RRQ/  | 01/02 |  Filename  |   0  |    Mode    |   0  |
WRQ    -----------------------------------------------
    """
    def __init__(self):
        TftpPacketInitial.__init__(self)
        self.opcode = 1

class TftpPacketWRQ(TftpPacketInitial):
    """
        2 bytes    string   1 byte     string   1 byte
        -----------------------------------------------
RRQ/  | 01/02 |  Filename  |   0  |    Mode    |   0  |
WRQ    -----------------------------------------------
    """
    def __init__(self):
        TftpPacketInitial.__init__(self)
        self.opcode = 2

class TftpPacketDAT(TftpPacket):
    """
        2 bytes    2 bytes       n bytes
        ---------------------------------
DATA  | 03    |   Block #  |    Data    |
        ---------------------------------
    """
    def __init__(self):
        TftpPacket.__init__(self)
        self.opcode = 3
        self.blocknumber = 0
        self.data = None

    def encode(self):
        """Encode the DAT packet. This method populates self.buffer, and
        returns self for easy method chaining."""
        format = "!HH%ds" % len(self.data)
        self.buffer = struct.pack(format, 
                                  self.opcode, 
                                  self.blocknumber, 
                                  self.data)
        return self

    def decode(self):
        """Decode self.buffer into instance variables. It returns self for
        easy method chaining."""
        # We know the first 2 bytes are the opcode. The second two are the
        # block number.
        (self.blocknumber,) = struct.unpack("!H", self.buffer[2:4])
        # Everything else is data.
        self.data = self.buffer[4:]
        return self

class TftpPacketACK(TftpPacket):
    """
        2 bytes    2 bytes
        -------------------
ACK   | 04    |   Block #  |
        --------------------
    """
    def __init__(self):
        TftpPacket.__init__(self)
        self.opcode = 4
        self.blocknumber = 0

    def encode(self):
        self.buffer = struct.pack("!HH", self.opcode, self.blocknumber)
        return self

    def decode(self):
        self.opcode, self.blocknumber = struct.unpack("!HH", self.buffer)
        return self

class TftpPacketERR(TftpPacket):
    """
        2 bytes  2 bytes        string    1 byte
        ----------------------------------------
ERROR | 05    |  ErrorCode |   ErrMsg   |   0  |
        ----------------------------------------
    Error Codes

    Value     Meaning

    0         Not defined, see error message (if any).
    1         File not found.
    2         Access violation.
    3         Disk full or allocation exceeded.
    4         Illegal TFTP operation.
    5         Unknown transfer ID.
    6         File already exists.
    7         No such user.
    8         Failed to negotiate options
    """
    def __init__(self):
        TftpPacket.__init__(self)
        self.opcode = 5
        self.errorcode = 0
        self.errmsg = None
        # FIXME - integrate in TftpErrors references?
        self.errmsgs = {
            1: "File not found",
            2: "Access violation",
            3: "Disk full or allocation exceeded",
            4: "Illegal TFTP operation",
            5: "Unknown transfer ID",
            6: "File already exists",
            7: "No such user",
            8: "Failed to negotiate options"
            }

    def encode(self):
        """Encode the DAT packet based on instance variables, populating
        self.buffer, returning self."""
        format = "!HH%dsx" % len(self.errmsgs[self.errorcode])
        self.buffer = struct.pack(format,
                                  self.opcode,
                                  self.errorcode,
                                  self.errmsgs[self.errorcode])
        return self

    def decode(self):
        "Decode self.buffer, populating instance variables and return self."
        format = "!HH%dsx" % (len(self.buffer) - 5)
        self.opcode, self.errorcode, self.errmsg = struct.unpack(format, 
                                                                 self.buffer)
        return self
    
class TftpPacketOACK(TftpPacket, TftpPacketWithOptions):
    """
    #  +-------+---~~---+---+---~~---+---+---~~---+---+---~~---+---+
    #  |  opc  |  opt1  | 0 | value1 | 0 |  optN  | 0 | valueN | 0 |
    #  +-------+---~~---+---+---~~---+---+---~~---+---+---~~---+---+
    """
    def __init__(self):
        TftpPacket.__init__(self)
        self.opcode = 6
        
    def encode(self):
        format = "!H" # opcode
        options_list = []
        for key in self.options:
            format += "%dsx" % len(key)
            format += "%dsx" % len(self.options[key])
            options_list.append(key)
            options_list.append(self.options[key])
        self.buffer = struct.pack(format, self.opcode, *options_list)
        return self
    
    def decode(self):
        self.options = self.decode_options(self.buffer[2:])
        return self
    
    def match_options(self, options):
        """This method takes a set of options, and tries to match them with
        its own. It can accept some changes in those options from the server as
        part of a negotiation. Changed or unchanged, it will return a dict of
        the options so that the session can update itself to the negotiated
        options."""
        for name in self.options:
            if options.has_key(name):
                if name == 'blksize':
                    # We can accept anything between the min and max values.
                    size = self.options[name]
                    if size >= MIN_BLKSIZE and size <= MAX_BLKSIZE:
                        options[blksize] = size
                else:
                    raise TftpException, "Unsupported option: %s" % name
        return True
