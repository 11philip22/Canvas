# Copyright (c) 2003-2006 CORE Security Technologies
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# $Id: ImpactPacket.py,v 1.9 2006/05/23 22:25:34 gera Exp $
#
# Description:
#  Network packet codecs basic building blocks.
#  Low-level packet codecs for various Internet protocols.
#
# Author:
#  Javier Burroni (javier)
#  Bruce Leidl (brl)
#  Javier Kohen (jkohen)

import array
import struct
import socket
import string
import sys
from binascii import hexlify

"""Classes to build network packets programmatically.

Each protocol layer is represented by an object, and these objects are
hierarchically structured to form a packet. This list is traversable
in both directions: from parent to child and vice versa.

All objects can be turned back into a raw buffer ready to be sent over
the wire (see method get_packet).
"""

class ImpactPacketException:
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return `self.value`

class PacketBuffer:
    """Implement the basic operations utilized to operate on a
    packet's raw buffer. All the packet classes derive from this one.

    The byte, word, long and ip_address getters and setters accept
    negative indeces, having these the a similar effect as in a
    regular Python sequence slice.
    """

    def __init__(self, length = None):
        "If 'length' is specified the buffer is created with an initial size"
        if length:
            self.__bytes = array.array('B', '\0' * length)
        else:
            self.__bytes = array.array('B')

    def set_bytes_from_string(self, data):
        "Sets the value of the packet buffer from the string 'data'"
        self.__bytes = array.array('B', data)

    def get_buffer_as_string(self):
        "Returns the packet buffer as a string object"
        return self.__bytes.tostring()

    def get_bytes(self):
        "Returns the packet buffer as an array"
        return self.__bytes

    def set_bytes(self, bytes):
        "Set the packet buffer from an array"
        # Make a copy to be safe
        self.__bytes = array.array('B', bytes.tolist())

    def set_byte(self, index, value):
        "Set byte at 'index' to 'value'"
        index = self.__validate_index(index, 1)
        self.__bytes[index] = value

    def get_byte(self, index):
        "Return byte at 'index'"
        index = self.__validate_index(index, 1)
        return self.__bytes[index]

    def set_word(self, index, value, order = '!'):
        "Set 2-byte word at 'index' to 'value'. See struct module's documentation to understand the meaning of 'order'."
        index = self.__validate_index(index, 2)
        ary = array.array("B", struct.pack(order + 'H', value))
        if -2 == index:
            self.__bytes[index:] = ary
        else:
            self.__bytes[index:index+2] = ary

    def get_word(self, index, order = '!'):
        "Return 2-byte word at 'index'. See struct module's documentation to understand the meaning of 'order'."
        index = self.__validate_index(index, 2)
        if -2 == index:
            bytes = self.__bytes[index:]
        else:
            bytes = self.__bytes[index:index+2]
        (value,) = struct.unpack(order + 'H', bytes.tostring())
        return value

    def set_long(self, index, value, order = '!'):
        "Set 4-byte 'value' at 'index'. See struct module's documentation to understand the meaning of 'order'."
        index = self.__validate_index(index, 4)
        ary = array.array("B", struct.pack(order + 'L', value))
        if -4 == index:
            self.__bytes[index:] = ary
        else:
            self.__bytes[index:index+4] = ary

    def get_long(self, index, order = '!'):
        "Return 4-byte value at 'index'. See struct module's documentation to understand the meaning of 'order'."
        index = self.__validate_index(index, 4)
        if -4 == index:
            bytes = self.__bytes[index:]
        else:
            bytes = self.__bytes[index:index+4]
        (value,) = struct.unpack(order + 'L', bytes.tostring())
        return value

    def get_ip_address(self, index):
        "Return 4-byte value at 'index' as an IP string"
        index = self.__validate_index(index, 4)
        if -4 == index:
            bytes = self.__bytes[index:]
        else:
            bytes = self.__bytes[index:index+4]
        return socket.inet_ntoa(bytes.tostring())

    def set_ip_address(self, index, ip_string):
        "Set 4-byte value at 'index' from 'ip_string'"
        index = self.__validate_index(index, 4)
        raw = socket.inet_aton(ip_string)
        (b1,b2,b3,b4) = struct.unpack("BBBB", raw)
        self.set_byte(index, b1)
        self.set_byte(index + 1, b2)
        self.set_byte(index + 2, b3)
        self.set_byte(index + 3, b4)

    def set_checksum_from_data(self, index, data):
        "Set 16-bit checksum at 'index' by calculating checksum of 'data'"
        self.set_word(index, self.compute_checksum(data))

    def compute_checksum(self, anArray):
        "Return the one's complement of the one's complement sum of all the 16-bit words in 'anArray'"
        nleft = len(anArray)
        sum = 0
        pos = 0
        while nleft > 1:
            sum = anArray[pos] * 256 + (anArray[pos + 1] + sum)
            pos = pos + 2
            nleft = nleft - 2
        if nleft == 1:
            sum = sum + anArray[pos] * 256
        return self.normalize_checksum(sum)

    def normalize_checksum(self, aValue):
        sum = aValue
        sum = (sum >> 16) + (sum & 0xFFFF)
        sum += (sum >> 16)
        sum = (~sum & 0xFFFF)
        return sum

    def __validate_index(self, index, size):
        """This method performs two tasks: to allocate enough space to
        fit the elements at positions index through index+size, and to
        adjust negative indeces to their absolute equivalent.
        """

        orig_index = index

        curlen = len(self.__bytes)
        if index < 0:
            index = curlen + index

        diff = index + size - curlen
        if diff > 0:
            self.__bytes.fromstring('\0' * diff)
            if orig_index < 0:
                orig_index -= diff

        return orig_index


class Header(PacketBuffer):
    "This is the base class from which all protocol definitions extend."

    packet_printable = filter(lambda c: c not in string.whitespace, string.printable) + ' '

    ethertype = None
    protocol = None
    def __init__(self, length = None):
        PacketBuffer.__init__(self, length)
        self.__child = None
        self.__parent = None
        self.auto_checksum = 1

    def contains(self, aHeader):
        "Set 'aHeader' as the child of this header"
        self.__child = aHeader
        aHeader.set_parent(self)

    def set_parent(self, my_parent):
        "Set the header 'my_parent' as the parent of this header"
        self.__parent = my_parent

    def child(self):
        "Return the child of this header"
        return self.__child

    def parent(self):
        "Return the parent of this header"
        return self.__parent

    def get_data_as_string(self):
        "Returns all data from children of this header as string"

        if self.__child:
            return self.__child.get_packet()
        else:
            return None

    def get_packet(self):
        """Returns the raw representation of this packet and its
        children as a string. The output from this method is a packet
        ready to be transmited over the wire.
        """
        self.calculate_checksum()

        data = self.get_data_as_string()
        if data:
            return self.get_buffer_as_string() + data
        else:
            return self.get_buffer_as_string()

    def get_size(self):
        "Return the size of this header and all of it's children"
        tmp_value = self.get_header_size()
        if self.child():
            tmp_value = tmp_value + self.child().get_size()
        return tmp_value

    def calculate_checksum(self):
        "Calculate and set the checksum for this header"
        pass

    def get_pseudo_header(self):
        "Pseudo headers can be used to limit over what content will the checksums be calculated."
        # default implementation returns empty array
        return array.array('B')

    def load_header(self, aBuffer):
        "Properly set the state of this instance to reflect that of the raw packet passed as argument."
        self.set_bytes_from_string(aBuffer)
        hdr_len = self.get_header_size()
        if(len(aBuffer) < hdr_len):         #we must do something like this
            diff = hdr_len - len(aBuffer)
            for i in range(0, diff):
                aBuffer += '\x00'
        self.set_bytes_from_string(aBuffer[:hdr_len])

    def get_header_size(self):
        "Return the size of this header, that is, not counting neither the size of the children nor of the parents."
        raise RuntimeError("Method %s.get_header_size must be overriden." % self.__class__)

    def list_as_hex(self, aList):
        if len(aList):
            ltmp = []
            line = []
            count = 0
            for byte in aList:
                if not (count % 2):
                    if (count % 16):
                        ltmp.append(' ')
                    else:
                        ltmp.append(' '*4)
                        ltmp.append(string.join(line, ''))
                        ltmp.append('\n')
                        line = []
                if chr(byte) in Header.packet_printable:
                    line.append(chr(byte))
                else:
                    line.append('.')
                ltmp.append('%.2x' % byte)
                count += 1
            if (count%16):
                left = 16 - (count%16)
                ltmp.append(' ' * (4+(left / 2) + (left*2)))
                ltmp.append(string.join(line, ''))
                ltmp.append('\n')
            return ltmp
        else:
            return []

    def __str__(self):
        ltmp = self.list_as_hex(self.get_bytes().tolist())

        if self.__child:
            ltmp.append(['\n', self.__child.__str__()])

        if len(ltmp)>0:
            return string.join(ltmp, '')
        else:
            return ''



class Data(Header):
    """This packet type can hold raw data. It's normally employed to
    hold a packet's innermost layer's contents in those cases for
    which the protocol details are unknown, and there's a copy of a
    valid packet available.

    For instance, if all that's known about a certain protocol is that
    a UDP packet with its contents set to "HELLO" initiate a new
    session, creating such packet is as simple as in the following code
    fragment:
    packet = UDP()
    packet.contains('HELLO')
    """

    def __init__(self, aBuffer = None):
        Header.__init__(self)
        if aBuffer:
           self.set_data(aBuffer)

    def set_data(self, data):
        self.set_bytes_from_string(data)

    def get_size(self):
        return len(self.get_bytes())



class Ethernet(Header):
    def __init__(self, aBuffer = None):
        Header.__init__(self, 14)
        if(aBuffer):
            self.load_header(aBuffer)

    def set_ether_type(self, aValue):
        "Set ethernet data type field to 'aValue'"
        self.set_word(12, aValue)

    def get_ether_type(self):
        "Return ethernet data type field"
        return self.get_word(12)

    def get_header_size(self):
        "Return size of Ethernet header"
        return 14

    def get_packet(self):

        if self.child():
            self.set_ether_type(self.child().ethertype)
        return Header.get_packet(self)

    def get_ether_dhost(self):
        "Return 48 bit destination ethernet address as a 6 byte array"
        return self.get_bytes()[0:6]

    def set_ether_dhost(self, aValue):
        "Set destination ethernet address from 6 byte array 'aValue'"
        for i in range(0, 6):
            self.set_byte(i, aValue[i])

    def get_ether_shost(self):
        "Return 48 bit source ethernet address as a 6 byte array"
        return self.get_bytes()[6:12]

    def set_ether_shost(self, aValue):
        "Set source ethernet address from 6 byte array 'aValue'"
        for i in range(0, 6):
            self.set_byte(i + 6, aValue[i])

    def as_eth_addr(self, anArray):
        tmp_list = anArray.tolist()
        if not tmp_list:
            return ''
        tmp_str = '%x' % tmp_list[0]
        for i in range(1, len(tmp_list)):
            tmp_str += ':%x' % tmp_list[i]
        return tmp_str

    def __str__(self):
        tmp_str = 'Ether: ' + self.as_eth_addr(self.get_ether_shost()) + ' -> '
        tmp_str += self.as_eth_addr(self.get_ether_dhost())
        if self.child():
            tmp_str += '\n' + self.child().__str__()
        return tmp_str


# Linux "cooked" capture encapsulation.
# Used, for instance, for packets returned by the "any" interface.
class LinuxSLL(Header):
    type_descriptions = [
        "sent to us by somebody else",
        "broadcast by somebody else",
        "multicast by somebody else",
        "sent to somebody else to somebody else",
        "sent by us",
        ]

    def __init__(self, aBuffer = None):
        Header.__init__(self, 16)
        if (aBuffer):
            self.load_header(aBuffer)

    def set_type(self, type):
        "Sets the packet type field to type"
        self.set_word(0, type)

    def get_type(self):
        "Returns the packet type field"
        return self.get_word(0)

    def set_arphdr(self, value):
        "Sets the ARPHDR value for the link layer device type"
        self.set_word(2, type)

    def get_arphdr(self):
        "Returns the ARPHDR value for the link layer device type"
        return self.get_word(2)

    def set_addr_len(self, len):
        "Sets the length of the sender's address field to len"
        self.set_word(4, len)

    def get_addr_len(self):
        "Returns the length of the sender's address field"
        return self.get_word(4)

    def set_addr(self, addr):
        "Sets the sender's address field to addr. Addr must be at most 8-byte long."
        if (len(addr) < 8):
            addr += '\0' * (8 - len(addr))
        self.get_bytes()[6:14] = addr

    def get_addr(self):
        "Returns the sender's address field"
        return self.get_bytes()[6:14].tostring()

    def set_ether_type(self, aValue):
        "Set ethernet data type field to 'aValue'"
        self.set_word(14, aValue)

    def get_ether_type(self):
        "Return ethernet data type field"
        return self.get_word(14)

    def get_header_size(self):
        "Return size of packet header"
        return 16

    def get_packet(self):
        if self.child():
            self.set_ether_type(self.child().ethertype)
        return Header.get_packet(self)

    def get_type_desc(self):
        type = self.get_type()
        if type < len(LinuxSLL.type_descriptions):
            return LinuxSLL.type_descriptions[type]
        else:
            return "Unknown"

    def __str__(self):
        ss = []
        alen = self.get_addr_len()
        addr = hexlify(self.get_addr()[0:alen])
        ss.append("Linux SLL: addr=%s type=`%s'" % (addr, self.get_type_desc()))
        if self.child():
            ss.append(self.child().__str__())

        return '\n'.join(ss)


class IP(Header):
    ethertype = 0x800
    def __init__(self, aBuffer = None):
        Header.__init__(self, 20)
        self.set_ip_v(4)
        self.set_ip_hl(5)
        self.set_ip_ttl(255)
        self.__option_list = []
        if(aBuffer):
            self.load_header(aBuffer)
        if sys.platform.count('bsd'):
            self.is_BSD = True
        else:
            self.is_BSD = False


    def get_packet(self):
        # set protocol
        if self.get_ip_p() == 0 and self.child():
            self.set_ip_p(self.child().protocol)

        # set total length
        if self.get_ip_len() == 0:
            self.set_ip_len(self.get_size())

        child_data = self.get_data_as_string();

        my_bytes = self.get_bytes()

        for op in self.__option_list:
            my_bytes.extend(op.get_bytes())

        # Pad to a multiple of 4 bytes
        num_pad = (4 - (len(my_bytes) % 4)) % 4
        if num_pad:
            my_bytes.fromstring("\0"* num_pad)

        # only change ip_hl value if options are present
        if len(self.__option_list):
            self.set_ip_hl(len(my_bytes) / 4)


        # set the checksum if the user hasn't modified it
        if self.auto_checksum:
            self.set_ip_sum(self.compute_checksum(my_bytes))

        if child_data == None:
            return my_bytes.tostring()
        else:
            return my_bytes.tostring() + child_data



  #  def calculate_checksum(self, buffer = None):
  #      tmp_value = self.get_ip_sum()
  #      if self.auto_checksum and (not tmp_value):
  #          if buffer:
  #              tmp_bytes = buffer
  #          else:
  #              tmp_bytes = self.bytes[0:self.get_header_size()]
  #
  #          self.set_ip_sum(self.compute_checksum(tmp_bytes))


    def get_pseudo_header(self):
        pseudo_buf = array.array("B")
        pseudo_buf.extend(self.get_bytes()[12:20])
        pseudo_buf.fromlist([0])
        pseudo_buf.extend(self.get_bytes()[9:10])
        tmp_size = self.child().get_size()

        size_str = struct.pack("!H", tmp_size)

        pseudo_buf.fromstring(size_str)
        return pseudo_buf

    def add_option(self, option):
        self.__option_list.append(option)
        sum = 0
        for op in self.__option_list:
            sum += op.get_len()
        if sum > 40:
            raise ImpactPacketException, "Options overflowed in IP packet with length: %d" % sum


    def get_ip_v(self):
        n = self.get_byte(0)
        return (n >> 4)

    def set_ip_v(self, value):
        n = self.get_byte(0)
        version = value & 0xF
        n = n & 0xF
        n = n | (version << 4)
        self.set_byte(0, n)

    def get_ip_hl(self):
        n = self.get_byte(0)
        return (n & 0xF)

    def set_ip_hl(self, value):
        n = self.get_byte(0)
        len = value & 0xF
        n = n & 0xF0
        n = (n | len)
        self.set_byte(0, n)

    def get_ip_tos(self):
        return self.get_byte(1)

    def set_ip_tos(self,value):
        self.set_byte(1, value)

    def get_ip_len(self):
        if self.is_BSD:
            return self.get_word(2, order = '=')
        else:
            return self.get_word(2)

    def set_ip_len(self, value):
        if self.is_BSD:
            self.set_word(2, value, order = '=')
        else:
            self.set_word(2, value)

    def get_ip_id(self):
        return self.get_word(4)
    def set_ip_id(self, value):
        return self.set_word(4, value)

    def get_ip_off(self):
        if self.is_BSD:
            return self.get_word(6, order = '=')
        else:
            return self.get_word(6)

    def set_ip_off(self, aValue):
        if self.is_BSD:
            self.set_word(6, aValue, order = '=')
        else:
            self.set_word(6, aValue)

    def get_ip_offmask(self):
        return self.get_ip_off() & 0x1FFF

    def set_ip_offmask(self, aValue):
        tmp_value = self.get_ip_off() & 0xD000
        tmp_value |= aValue
        self.set_ip_off(tmp_value)

    def get_ip_rf(self):
        return self.get_ip_off() & 0x8000

    def set_ip_rf(self, aValue):
        tmp_value = self.get_ip_off()
        if aValue:
            tmp_value |= 0x8000
        else:
            my_not = 0xFFFF ^ 0x8000
            tmp_value &= my_not
        self.set_ip_off(tmp_value)

    def get_ip_df(self):
        return self.get_ip_off() & 0x4000

    def set_ip_df(self, aValue):
        tmp_value = self.get_ip_off()
        if aValue:
            tmp_value |= 0x4000
        else:
            my_not = 0xFFFF ^ 0x4000
            tmp_value &= my_not
        self.set_ip_off(tmp_value)

    def get_ip_mf(self):
        return self.get_ip_off() & 0x2000

    def set_ip_mf(self, aValue):
        tmp_value = self.get_ip_off()
        if aValue:
            tmp_value |= 0x2000
        else:
            my_not = 0xFFFF ^ 0x2000
            tmp_value &= my_not
        self.set_ip_off(tmp_value)


    def fragment_by_list(self, aList):
        if self.child():
            proto = self.child().protocol
        else:
            proto = 0

        child_data = self.get_data_as_string()
        if not child_data:
            return [self]

        ip_header_bytes = self.get_bytes()
        current_offset = 0
        fragment_list = []

        for frag_size in aList:
            ip = IP()
            ip.set_bytes(ip_header_bytes) # copy of original header
            ip.set_ip_p(proto)


            if frag_size % 8:   # round this fragment size up to next multiple of 8
                frag_size += 8 - (frag_size % 8)


            ip.set_ip_offmask(current_offset / 8)
            current_offset += frag_size

            data = Data(child_data[:frag_size])
            child_data = child_data[frag_size:]

            ip.set_ip_len(20 + data.get_size())
            ip.contains(data)


            if child_data:

                ip.set_ip_mf(1)

                fragment_list.append(ip)
            else: # no more data bytes left to add to fragments

                ip.set_ip_mf(0)

                fragment_list.append(ip)
                return fragment_list

        if child_data: # any remaining data?
            # create a fragment containing all of the remaining child_data
            ip = IP()
            ip.set_bytes(ip_header_bytes)
            ip.set_ip_offmask(current_offset)
            ip.set_ip_len(20 + len(child_data))
            data = Data(child_data)
            ip.contains(data)
            fragment_list.append(ip)

        return fragment_list


    def fragment_by_size(self, aSize):
        data_len = len(self.get_data_as_string())
        num_frags = data_len / aSize

        if data_len % aSize:
            num_frags += 1

        size_list = []
        for i in range(0, num_frags):
            size_list.append(aSize)
        return self.fragment_by_list(size_list)


    def get_ip_ttl(self):
        return self.get_byte(8)
    def set_ip_ttl(self, value):
        self.set_byte(8, value)

    def get_ip_p(self):
        return self.get_byte(9)

    def set_ip_p(self, value):
        self.set_byte(9, value)

    def get_ip_sum(self):
        return self.get_word(10)
    def set_ip_sum(self, value):
        self.auto_checksum = 0
        self.set_word(10, value)

    def get_ip_src(self):
        return self.get_ip_address(12)
    def set_ip_src(self, value):
        self.set_ip_address(12, value)

    def get_ip_dst(self):
        return self.get_ip_address(16)

    def set_ip_dst(self, value):
        self.set_ip_address(16, value)

    def get_header_size(self):
        op_len = 0
        for op in self.__option_list:
            op_len += op.get_len()

        num_pad = (4 - (op_len % 4)) % 4

        return 20 + op_len + num_pad

    def load_header(self, aBuffer):
        self.set_bytes_from_string(aBuffer[:20])
        opt_left = (self.get_ip_hl() - 5) * 4
        opt_bytes = array.array('B', aBuffer[20:(20 + opt_left)])
        if len(opt_bytes) != opt_left:
            raise ImpactPacketException, "Cannot load options from truncated packet"


        while opt_left:
            op_type = opt_bytes[0]
            if op_type == IPOption.IPOPT_EOL or op_type == IPOption.IPOPT_NOP:
                new_option = IPOption(op_type)
                op_len = 1
            else:
                op_len = opt_bytes[1]
                if op_len > len(opt_bytes):
                    raise ImpactPacketException, "IP Option length is too high"

                new_option = IPOption(op_type, op_len)
                new_option.set_bytes(opt_bytes[:op_len])

            opt_bytes = opt_bytes[op_len:]
            opt_left -= op_len
            self.add_option(new_option)
            if op_type == IPOption.IPOPT_EOL:
                break


    def __str__(self):
        tmp_str = 'IP ' + self.get_ip_src() + ' -> ' + self.get_ip_dst()
        for op in self.__option_list:
            tmp_str += '\n' + op.__str__()
        if self.child():
            tmp_str += '\n' + self.child().__str__()
        return tmp_str


class IPOption(PacketBuffer):
    IPOPT_EOL = 0
    IPOPT_NOP = 1
    IPOPT_RR = 7
    IPOPT_TS = 68
    IPOPT_LSRR = 131
    IPOPT_SSRR = 137

    def __init__(self, opcode = 0, size = None):
        if size and (size < 3 or size > 39):
            raise ImpactPacketException, "IP Options must have a size between 3 and 39 bytes"

        if(opcode == IPOption.IPOPT_EOL):
            PacketBuffer.__init__(self, 1)
            self.set_code(IPOption.IPOPT_EOL)
        elif(opcode == IPOption.IPOPT_NOP):
            PacketBuffer.__init__(self, 1)
            self.set_code(IPOption.IPOPT_NOP)
        elif(opcode == IPOption.IPOPT_RR):
            if not size:
                size = 39
            PacketBuffer.__init__(self, size)
            self.set_code(IPOption.IPOPT_RR)
            self.set_len(size)
            self.set_ptr(4)

        elif(opcode == IPOption.IPOPT_LSRR):
            if not size:
                size = 39
            PacketBuffer.__init__(self, size)
            self.set_code(IPOption.IPOPT_LSRR)
            self.set_len(size)
            self.set_ptr(4)

        elif(opcode == IPOption.IPOPT_SSRR):
            if not size:
                size = 39
            PacketBuffer.__init__(self, size)
            self.set_code(IPOption.IPOPT_SSRR)
            self.set_len(size)
            self.set_ptr(4)

        elif(opcode == IPOption.IPOPT_TS):
            if not size:
                size = 40
            PacketBuffer.__init__(self, size)
            self.set_code(IPOption.IPOPT_TS)
            self.set_len(size)
            self.set_ptr(5)
            self.set_flags(0)
        else:
            if not size:
                raise ImpactPacketError, "Size required for this type"
            PacketBuffer.__init__(self,size)
            self.set_code(opcode)
            self.set_len(size)


    def append_ip(self, ip):
        op = self.get_code()
        if not (op == IPOption.IPOPT_RR or op == IPOption.IPOPT_LSRR or op == IPOption.IPOPT_SSRR or op == IPOption.IPOPT_TS):
            raise ImpactPacketException, "append_ip() not support for option type %d" % self.opt_type

        p = self.get_ptr()
        if not p:
            raise ImpactPacketException, "append_ip() failed, option ptr uninitialized"

        if (p + 4) > self.get_len():
            raise ImpactPacketException, "append_ip() would overflow option"

        self.set_ip_address(p - 1, ip)
        p += 4
        self.set_ptr(p)


    def set_code(self, value):
        self.set_byte(0, value)

    def get_code(self):
        return self.get_byte(0)


    def set_flags(self, flags):
        if not (self.get_code() == IPOption.IPOPT_TS):
            raise ImpactPacketException, "Operation only supported on Timestamp option"
        self.set_byte(3, flags)

    def get_flags(self, flags):
        if not (self.get_code() == IPOption.IPOPT_TS):
            raise ImpactPacketException, "Operation only supported on Timestamp option"
        return self.get_byte(3)


    def set_len(self, len):
        self.set_byte(1, len)


    def set_ptr(self, ptr):
        self.set_byte(2, ptr)

    def get_ptr(self):
        return self.get_byte(2)

    def get_len(self):
        return len(self.get_bytes())


    def __str__(self):
        map = {IPOption.IPOPT_EOL : "End of List ",
               IPOption.IPOPT_NOP : "No Operation ",
               IPOption.IPOPT_RR  : "Record Route ",
               IPOption.IPOPT_TS  : "Timestamp ",
               IPOption.IPOPT_LSRR : "Loose Source Route ",
               IPOption.IPOPT_SSRR : "Strict Source Route "}

        tmp_str = "\tIP Option: "
        op = self.get_code()
        if map.has_key(op):
            tmp_str += map[op]
        else:
            tmp_str += "Code: %d " % op

        if op == IPOption.IPOPT_RR or op == IPOption.IPOPT_LSRR or op ==IPOption.IPOPT_SSRR:
            tmp_str += self.print_addresses()


        return tmp_str


    def print_addresses(self):
        p = 3
        tmp_str = "["
        if self.get_len() >= 7: # at least one complete IP address
            while 1:
                if p + 1 == self.get_ptr():
                    tmp_str += "#"
                tmp_str += self.get_ip_address(p)
                p += 4
                if p >= self.get_len():
                    break
                else:
                    tmp_str += ", "
        tmp_str += "] "
        if self.get_ptr() % 4: # ptr field should be a multiple of 4
            tmp_str += "nonsense ptr field: %d " % self.get_ptr()
        return tmp_str


class UDP(Header):
    protocol = 17
    def __init__(self, aBuffer = None):
        Header.__init__(self, 8)
        if(aBuffer):
            self.load_header(aBuffer)

    def get_uh_sport(self):
        return self.get_word(0)
    def set_uh_sport(self, value):
        self.set_word(0, value)

    def get_uh_dport(self):
        return self.get_word(2)
    def set_uh_dport(self, value):
        self.set_word(2, value)

    def get_uh_ulen(self):
        return self.get_word(4)

    def set_uh_ulen(self, value):
        self.set_word(4, value)

    def get_uh_sum(self):
        return self.get_word(6)

    def set_uh_sum(self, value):
        self.set_word(6, value)
        self.auto_checksum = 0

    def calculate_checksum(self):
        if self.auto_checksum and (not self.get_uh_sum()):
            # if there isn't a parent to grab a pseudo-header from we'll assume the user knows what they're doing
            # and won't meddle with the checksum or throw an exception
            if not self.parent:
                return

            buffer = self.parent().get_pseudo_header()

            buffer += self.get_bytes()
            data = self.get_data_as_string()
            if(data):
                buffer.fromstring(data)
            self.set_uh_sum(self.compute_checksum(buffer))

    def get_header_size(self):
        return 8

    def __str__(self):
        tmp_str = 'UDP %d -> %d' % (self.get_uh_sport(), self.get_uh_dport())
        if self.child():
            tmp_str += '\n' + self.child().__str__()
        return tmp_str

    def get_packet(self):
        # set total length
        if(self.get_uh_ulen() == 0):
            self.set_uh_ulen(self.get_size())
        return Header.get_packet(self)

class TCP(Header):
    protocol = 6
    def __init__(self, aBuffer = None):
        Header.__init__(self, 20)
        self.set_th_off(5)
        self.__option_list = []
        if aBuffer:
            self.load_header(aBuffer)

    def add_option(self, option):
        self.__option_list.append(option)

        sum = 0
        for op in self.__option_list:
            sum += op.get_size()

        if sum > 40:
            raise ImpactPacketException, "Cannot add TCP option, would overflow option space"

    def get_options(self):
        return self.__option_list

    def swapSourceAndDestination(self):
        oldSource = self.get_th_sport()
        self.set_th_sport(self.get_th_dport())
        self.set_th_dport(oldSource)

    #
    # Header field accessors
    #

    def set_th_sport(self, aValue):
        self.set_word(0, aValue)

    def get_th_sport(self):
        return self.get_word(0)

    def get_th_dport(self):
        return self.get_word(2)

    def set_th_dport(self, aValue):
        self.set_word(2, aValue)

    def get_th_seq(self):
        return self.get_long(4)

    def set_th_seq(self, aValue):
        self.set_long(4, aValue)

    def get_th_ack(self):
        return self.get_long(8)

    def set_th_ack(self, aValue):
        self.set_long(8, aValue)

    def get_th_flags(self):
        return self.get_word(12)

    def set_th_flags(self, aValue):
        self.set_word(12, aValue)

    def get_th_win(self):
        return self.get_word(14)

    def set_th_win(self, aValue):
        self.set_word(14, aValue)

    def set_th_sum(self, aValue):
        self.set_word(16, aValue)
        self.auto_checksum = 0

    def get_th_sum(self):
        return self.get_long(16)

    def get_th_urp(self):
        return self.get_word(18)

    def set_th_urp(self, aValue):
        return self.set_word(18, aValue)

    # Flag accessors

    def get_th_off(self):
        tmp_value = self.get_th_flags() >> 12
        return tmp_value

    def set_th_off(self, aValue):
        self.reset_flags(0xF000)
        self.set_flags(aValue << 12)

    def get_CWR(self):
        return self.get_flag(128)
    def set_CWR(self):
        return self.set_flags(128)
    def reset_CWR(self):
        return self.reset_flags(128)

    def get_ECE(self):
        return self.get_flag(64)
    def set_ECE(self):
        return self.set_flags(64)
    def reset_ECE(self):
        return self.reset_flags(64)

    def get_URG(self):
        return self.get_flag(32)
    def set_URG(self):
        return self.set_flags(32)
    def reset_URG(self):
        return self.reset_flags(32)

    def get_ACK(self):
        return self.get_flag(16)
    def set_ACK(self):
        return self.set_flags(16)
    def reset_ACK(self):
        return self.reset_flags(16)

    def get_PSH(self):
        return self.get_flag(8)
    def set_PSH(self):
        return self.set_flags(8)
    def reset_PSH(self):
        return self.reset_flags(8)

    def get_RST(self):
        return self.get_flag(4)
    def set_RST(self):
        return self.set_flags(4)
    def reset_RST(self):
        return self.reset_flags(4)

    def get_SYN(self):
        return self.get_flag(2)
    def set_SYN(self):
        return self.set_flags(2)
    def reset_SYN(self):
        return self.reset_flags(2)

    def get_FIN(self):
        return self.get_flag(1)
    def set_FIN(self):
        return self.set_flags(1)
    def reset_FIN(self):
        return self.reset_flags(1)

    # Overriden Methods

    def get_header_size(self):

        return 20 + len(self.get_padded_options())


    def calculate_checksum(self):
        if not self.auto_checksum or not self.parent():
            return

        self.set_th_sum(0)
        buffer = self.parent().get_pseudo_header()
        buffer += self.get_bytes()
        buffer += self.get_padded_options()

        data = self.get_data_as_string()
        if(data):
            buffer.fromstring(data)

        res = self.compute_checksum(buffer)

        self.set_th_sum(self.compute_checksum(buffer))


    def get_packet(self):
        "Returns entire packet including child data as a string.  This is the function used to extract the final packet"

        # only change th_off value if options are present
        if len(self.__option_list):
            self.set_th_off(self.get_header_size() / 4)

        self.calculate_checksum()

        bytes = self.get_bytes() + self.get_padded_options()
        data = self.get_data_as_string()

        if data:
            return bytes.tostring() + data
        else:
            return bytes.tostring()


    def load_header(self, aBuffer):
        self.set_bytes_from_string(aBuffer[:20])
        opt_left = (self.get_th_off() - 5) * 4
        opt_bytes = array.array('B', aBuffer[20:(20 + opt_left)])
        if len(opt_bytes) != opt_left:
            raise ImpactPacketException, "Cannot load options from truncated packet"

        while opt_left:
            op_kind = opt_bytes[0]
            if op_kind == TCPOption.TCPOPT_EOL or op_kind == TCPOption.TCPOPT_NOP:
                new_option = TCPOption(op_kind)
                op_len = 1
            else:
                op_len = opt_bytes[1]
                if op_len > len(opt_bytes):
                    raise ImpactPacketException, "TCP Option length is too high"

                new_option = TCPOption(op_kind)
                new_option.set_bytes(opt_bytes[:op_len])

            opt_bytes = opt_bytes[op_len:]
            opt_left -= op_len
            self.add_option(new_option)
            if op_kind == TCPOption.TCPOPT_EOL:
                break




    #
    # Private
    #

    def get_flag(self, bit):
        if self.get_th_flags() & bit:
            return 1
        else:
            return 0

    def reset_flags(self, aValue):
        tmp_value = self.get_th_flags() & (~aValue)
        return self.set_word(12, tmp_value)


    def set_flags(self, aValue):
        tmp_value =  self.get_th_flags() | aValue
        return self.set_word(12, tmp_value)

    def get_padded_options(self):
        "Return an array containing all options padded to a 4 byte boundry"
        op_buf = array.array('B')
        for op in self.__option_list:
            op_buf += op.get_bytes()
        num_pad = (4 - (len(op_buf) % 4)) % 4
        if num_pad:
            op_buf.fromstring("\0" * num_pad)
        return op_buf

    def __str__(self):
        tmp_str = 'TCP '
        if self.get_ACK():
            tmp_str += 'ack '
        if self.get_FIN():
            tmp_str += 'fin '
        if self.get_PSH():
            tmp_str += 'push '
        if self.get_RST():
            tmp_str += 'rst '
        if self.get_SYN():
            tmp_str += 'syn '
        if self.get_URG():
            tmp_str += 'urg '
        tmp_str += '%d -> %d' % (self.get_th_sport(), self.get_th_dport())
        for op in self.__option_list:
            tmp_str += '\n' + op.__str__()

        if self.child():
            tmp_str += '\n' + self.child().__str__()
        return tmp_str


class TCPOption(PacketBuffer):
    TCPOPT_EOL =             0
    TCPOPT_NOP  =            1
    TCPOPT_MAXSEG =          2
    TCPOPT_WINDOW  =         3
    TCPOPT_SACK_PERMITTED =  4
    TCPOPT_SACK         =    5
    TCPOPT_TIMESTAMP    =    8
    TCPOPT_SIGNATURE    =    19


    def __init__(self, kind, data = None):

        if kind == TCPOption.TCPOPT_EOL:
            PacketBuffer.__init__(self, 1)
            self.set_kind(TCPOption.TCPOPT_EOL)
        elif kind == TCPOption.TCPOPT_NOP:
            PacketBuffer.__init__(self, 1)
            self.set_kind(TCPOption.TCPOPT_NOP)
        elif kind == TCPOption.TCPOPT_MAXSEG:
            PacketBuffer.__init__(self, 4)
            self.set_kind(TCPOption.TCPOPT_MAXSEG)
            self.set_len(4)
            if data:
                self.set_mss(data)
            else:
                self.set_mss(512)
        elif kind == TCPOption.TCPOPT_WINDOW:
            PacketBuffer.__init__(self, 3)
            self.set_kind(TCPOption.TCPOPT_WINDOW)
            self.set_len(3)
            if data:
                self.set_shift_cnt(data)
            else:
                self.set_shift_cnt(0)
        elif kind == TCPOption.TCPOPT_TIMESTAMP:
            PacketBuffer.__init__(self, 10)
            self.set_kind(TCPOption.TCPOPT_TIMESTAMP)
            self.set_len(10)
            if data:
                self.set_ts(data)
            else:
                self.set_ts(0)
        elif kind == TCPOption.TCPOPT_SACK_PERMITTED:
            PacketBuffer.__init__(self, 2)
            self.set_kind(TCPOption.TCPOPT_SACK_PERMITTED)
            self.set_len(2)                

    def set_kind(self, kind):
        self.set_byte(0, kind)


    def get_kind(self):
        return self.get_byte(0)


    def set_len(self, len):
        if self.get_size() < 2:
            raise ImpactPacketException, "Cannot set length field on option of less than two bytes"
        self.set_byte(1, len)

    def get_len(self):
        if self.get_size() < 2:
            raise ImpactPacketException, "Cannot retrive length field from option of less that two bytes"
        return self.get_byte(1)

    def get_size(self):
        return len(self.get_bytes())


    def set_mss(self, len):
        if self.get_kind() != TCPOption.TCPOPT_MAXSEG:
            raise ImpactPacketException, "Can only set MSS on TCPOPT_MAXSEG option"
        self.set_word(2, len)

    def get_mss(self):
        if self.get_kind() != TCPOption.TCPOPT_MAXSEG:
            raise ImpactPacketException, "Can only retrieve MSS from TCPOPT_MAXSEG option"
        return self.get_word(2)

    def set_shift_cnt(self, cnt):
        if self.get_kind() != TCPOption.TCPOPT_WINDOW:
            raise ImpactPacketException, "Can only set Shift Count on TCPOPT_WINDOW option"
        self.set_byte(2, cnt)

    def get_shift_cnt(self):
        if self.get_kind() != TCPOption.TCPOPT_WINDOW:
            raise ImpactPacketException, "Can only retrieve Shift Count from TCPOPT_WINDOW option"
        return self.get_byte(2)

    def get_ts(self):
        if self.get_kind() != TCPOption.TCPOPT_TIMESTAMP:
            raise ImpactPacketException, "Can only retrieve timestamp from TCPOPT_TIMESTAMP option"
        return self.get_long(2)

    def set_ts(self, ts):
        if self.get_kind() != TCPOption.TCPOPT_TIMESTAMP:
            raise ImpactPacketException, "Can only set timestamp on TCPOPT_TIMESTAMP option"
        self.set_long(2, ts)

    def get_ts_echo(self):
        if self.get_kind() != TCPOption.TCPOPT_TIMESTAMP:
            raise ImpactPacketException, "Can only retrieve timestamp from TCPOPT_TIMESTAMP option"
        self.get_long(6)

    def set_ts_echo(self, ts):
        if self.get_kind() != TCPOption.TCPOPT_TIMESTAMP:
            raise ImpactPacketException, "Can only set timestamp on TCPOPT_TIMESTAMP option"



    def __str__(self):
        map = { TCPOption.TCPOPT_EOL : "End of List ",
                TCPOption.TCPOPT_NOP : "No Operation ",
                TCPOption.TCPOPT_MAXSEG : "Maximum Segment Size ",
                TCPOption.TCPOPT_WINDOW : "Window Scale ",
                TCPOption.TCPOPT_TIMESTAMP : "Timestamp " }

        tmp_str = "\tTCP Option: "
        op = self.get_kind()
        if map.has_key(op):
            tmp_str += map[op]
        else:
            tmp_str += " kind: %d " % op
        if op == TCPOption.TCPOPT_MAXSEG:
            tmp_str += " MSS : %d " % self.get_mss()
        elif op == TCPOption.TCPOPT_WINDOW:
            tmp_str += " Shift Count: %d " % self.get_shift_cnt()
        elif op == TCPOption.TCPOPT_TIMESTAMP:
            pass # TODO
        return tmp_str

class ICMP(Header):
    protocol = 1
    ICMP_ECHOREPLY              = 0
    ICMP_UNREACH                = 3
    ICMP_UNREACH_NET            = 0
    ICMP_UNREACH_HOST           = 1
    ICMP_UNREACH_PROTOCOL       = 2
    ICMP_UNREACH_PORT           = 3
    ICMP_UNREACH_NEEDFRAG       = 4
    ICMP_UNREACH_SRCFAIL        = 5
    ICMP_UNREACH_NET_UNKNOWN    = 6
    ICMP_UNREACH_HOST_UNKNOWN   = 7
    ICMP_UNREACH_ISOLATED       = 8
    ICMP_UNREACH_NET_PROHIB     = 9
    ICMP_UNREACH_HOST_PROHIB    = 10
    ICMP_UNREACH_TOSNET         = 11
    ICMP_UNREACH_TOSHOST        = 12
    ICMP_UNREACH_FILTERPROHIB   = 13
    ICMP_UNREACH_HOST_PRECEDENCE = 14
    ICMP_UNREACH_PRECEDENCE_CUTOFF = 15
    ICMP_SOURCEQUENCH               = 4
    ICMP_REDIRECT                   = 5
    ICMP_REDIRECT_NET           = 0
    ICMP_REDIRECT_HOST          = 1
    ICMP_REDIRECT_TOSNET        = 2
    ICMP_REDIRECT_TOSHOST       = 3
    ICMP_ALTHOSTADDR                = 6
    ICMP_ECHO                       = 8
    ICMP_ROUTERADVERT               = 9
    ICMP_ROUTERSOLICIT              = 10
    ICMP_TIMXCEED                   = 11
    ICMP_TIMXCEED_INTRANS       = 0
    ICMP_TIMXCEED_REASS         = 1
    ICMP_PARAMPROB                  = 12
    ICMP_PARAMPROB_ERRATPTR     = 0
    ICMP_PARAMPROB_OPTABSENT    = 1
    ICMP_PARAMPROB_LENGTH       = 2
    ICMP_TSTAMP                     = 13
    ICMP_TSTAMPREPLY                = 14
    ICMP_IREQ                       = 15
    ICMP_IREQREPLY                  = 16
    ICMP_MASKREQ                    = 17
    ICMP_MASKREPLY                  = 18

    def __init__(self, aBuffer = None):
        Header.__init__(self, 8)
        if aBuffer:
            self.load_header(aBuffer)

    def get_header_size(self):
        anamolies = { ICMP.ICMP_TSTAMP : 20, ICMP.ICMP_TSTAMPREPLY : 20, ICMP.ICMP_MASKREQ : 12, ICMP.ICMP_MASKREPLY : 12 }
        if anamolies.has_key(self.get_icmp_type()):
            return anamolies[self.get_icmp_type()]
        else:
            return 8

    def get_icmp_type(self):
        return self.get_byte(0)

    def set_icmp_type(self, aValue):
        self.set_byte(0, aValue)

    def get_icmp_code(self):
        return self.get_byte(1)

    def set_icmp_code(self, aValue):
        self.set_byte(1, aValue)

    def get_icmp_cksum(self):
        return self.get_word(2)

    def set_icmp_cksum(self, aValue):
        self.set_word(2, aValue)
        self.auto_checksum = 0

    def get_icmp_gwaddr(self):
        return self.get_ip_address(4)

    def set_icmp_gwaddr(self, ip):
        self.set_ip_adress(4, ip)

    def get_icmp_id(self):
        return self.get_word(4)

    def set_icmp_id(self, aValue):
        self.set_word(4, aValue)

    def get_icmp_seq(self):
        return self.get_word(6)

    def set_icmp_seq(self, aValue):
        self.set_word(6, aValue)

    def get_icmp_void(self):
        return self.get_long(4)

    def set_icmp_void(self, aValue):
        self.set_long(4, aValue)


    def get_icmp_nextmtu(self):
        return self.get_word(6)

    def set_icmp_nextmtu(self, aValue):
        self.set_word(6, aValue)

    def get_icmp_num_addrs(self):
        return self.get_byte(4)

    def set_icmp_num_addrs(self, aValue):
        self.set_byte(4, aValue)

    def get_icmp_wpa(self):
        return self.get_byte(5)

    def set_icmp_wpa(self, aValue):
        self.set_byte(5, aValue)

    def get_icmp_lifetime(self):
        return self.get_word(6)

    def set_icmp_lifetime(self, aValue):
        self.set_word(6, aValue)

    def get_icmp_otime(self):
        return self.get_long(8)

    def set_icmp_otime(self, aValue):
        self.set_long(8, aValue)

    def get_icmp_rtime(self):
        return self.get_long(12)

    def set_icmp_rtime(self, aValue):
        self.set_long(12, aValue)

    def get_icmp_ttime(self):
        return self.get_long(16)

    def set_icmp_ttime(self, aValue):
        self.set_long(16, aValue)

    def get_icmp_mask(self):
        return self.get_ip_address(8)

    def set_icmp_mask(self, mask):
        self.set_ip_address(8, mask)


    def calculate_checksum(self):
        if self.auto_checksum and (not self.get_icmp_cksum()):
            buffer = self.get_buffer_as_string()
            data = self.get_data_as_string()
            if data:
                buffer += data

            tmp_array = array.array('B', buffer)
            self.set_icmp_cksum(self.compute_checksum(tmp_array))

    def get_type_name(self, aType):
        tmp_type = {0:'ECHOREPLY', 3:'UNREACH', 4:'SOURCEQUENCH',5:'REDIRECT', 6:'ALTHOSTADDR', 8:'ECHO', 9:'ROUTERADVERT', 10:'ROUTERSOLICIT', 11:'TIMXCEED', 12:'PARAMPROB', 13:'TSTAMP', 14:'TSTAMPREPLY', 15:'IREQ', 16:'IREQREPLY', 17:'MASKREQ', 18:'MASKREPLY', 30:'TRACEROUTE', 31:'DATACONVERR', 32:'MOBILE REDIRECT', 33:'IPV6 WHEREAREYOU', 34:'IPV6 IAMHERE', 35:'MOBILE REGREQUEST', 36:'MOBILE REGREPLY', 39:'SKIP', 40:'PHOTURIS'}
        answer = tmp_type.get(aType, 'UNKNOWN')
        return answer

    def get_code_name(self, aType, aCode):
        tmp_code = {3:['UNREACH NET', 'UNREACH HOST', 'UNREACH PROTOCOL', 'UNREACH PORT', 'UNREACH NEEDFRAG', 'UNREACH SRCFAIL', 'UNREACH NET UNKNOWN', 'UNREACH HOST UNKNOWN', 'UNREACH ISOLATED', 'UNREACH NET PROHIB', 'UNREACH HOST PROHIB', 'UNREACH TOSNET', 'UNREACH TOSHOST', 'UNREACH FILTER PROHIB', 'UNREACH HOST PRECEDENCE', 'UNREACH PRECEDENCE CUTOFF', 'UNKNOWN ICMP UNREACH']}
        tmp_code[5] = ['REDIRECT NET', 'REDIRECT HOST', 'REDIRECT TOSNET', 'REDIRECT TOSHOST']
        tmp_code[9] = ['ROUTERADVERT NORMAL', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,'ROUTERADVERT NOROUTE COMMON']
        tmp_code[11] = ['TIMXCEED INTRANS ', 'TIMXCEED REASS']
        tmp_code[12] = ['PARAMPROB ERRATPTR ', 'PARAMPROB OPTABSENT', 'PARAMPROB LENGTH']
        tmp_code[40] = [None, 'PHOTURIS UNKNOWN INDEX', 'PHOTURIS AUTH FAILED', 'PHOTURIS DECRYPT FAILED']
        if tmp_code.has_key(aType):
            tmp_list = tmp_code[aType]
            if ((aCode + 1) > len(tmp_list)) or (not tmp_list[aCode]):
                return 'UNKNOWN'
            else:
                return tmp_list[aCode]
        else:
            return 'UNKNOWN'

    def __str__(self):
        tmp_type = self.get_icmp_type()
        tmp_code = self.get_icmp_code()
        tmp_str = 'ICMP type: ' + self.get_type_name(tmp_type)
        tmp_str+= ' code: ' + self.get_code_name(tmp_type, tmp_code)
        if self.child():
            tmp_str += '\n' + self.child().__str__()
        return tmp_str

    def isDestinationUnreachable(self):
        return self.get_icmp_type() == 3

    def isError(self):
        return not self.isQuery()

    def isHostUnreachable(self):
        return self.isDestinationUnreachable() and (self.get_icmp_code() == 1)

    def isNetUnreachable(self):
        return self.isDestinationUnreachable() and (self.get_icmp_code() == 0)

    def isPortUnreachable(self):
        return self.isDestinationUnreachable() and (self.get_icmp_code() == 3)

    def isProtocolUnreachable(self):
        return self.isDestinationUnreachable() and (self.get_icmp_code() == 2)

    def isQuery(self):
         tmp_dict = {8:'',  9:'',  10:'', 13:'', 14:'', 15:'', 16:'', 17:'', 18:''}
         return tmp_dict.has_key(self.get_icmp_type())

class IGMP(Header):
    protocol = 2
    def __init__(self, aBuffer = None):
        Header.__init__(self, 8)
        if aBuffer:
            self.load_header(aBuffer)

    def get_igmp_type(self):
        return self.get_byte(0)

    def set_igmp_type(self, aValue):
        self.set_byte(0, aValue)

    def get_igmp_code(self):
        return self.get_byte(1)

    def set_igmp_code(self, aValue):
        self.set_byte(1, aValue)

    def get_igmp_cksum(self):
        return self.get_word(2)

    def set_igmp_cksum(self, aValue):
        self.set_word(2, aValue)

    def get_igmp_group(self):
        return self.get_long(4)

    def set_igmp_group(self, aValue):
        self.set_long(4, aValue)

    def get_header_size(self):
        return 8

    def get_type_name(self, aType):
        tmp_dict = {0x11:'HOST MEMBERSHIP QUERY ', 0x12:'v1 HOST MEMBERSHIP REPORT ', 0x13:'IGMP DVMRP ', 0x14:' PIM ', 0x16:'v2 HOST MEMBERSHIP REPORT ', 0x17:'HOST LEAVE MESSAGE ', 0x1e:'MTRACE REPLY ', 0X1f:'MTRACE QUERY '}
        answer = tmp_type.get(aType, 'UNKNOWN TYPE OR VERSION ')
        return answer

    def calculate_checksum(self):
        if self.__auto_checksum and (not self.get_igmp_cksum()):
            self.set_igmp_cksum(self.compute_checksum(self.get_buffer_as_string()))

    def __str__(self):
        knowcode = 0
        tmp_str = 'IGMP: ' + self.get_type_name(self.get_igmp_type())
        tmp_str += 'Group: ' +  socket.inet_ntoa(pack('!L',self.get_igmp_group()))
        if self.child():
            tmp_str += '\n' + self.child().__str__()
        return tmp_str



class ARP(Header):
    ethertype = 0x806
    def __init__(self, aBuffer = None):
        Header.__init__(self, 7)
        if aBuffer:
            self.load_header(aBuffer)

    def get_ar_hrd(self):
        return self.get_word(0)

    def set_ar_hrd(self, aValue):
        self.set_word(0, aValue)

    def get_ar_pro(self):
        return self.get_word(2)

    def set_ar_pro(self, aValue):
        self.set_word(2, aValue)

    def get_ar_hln(self):
        return self.get_byte(4)

    def set_ar_hln(self, aValue):
        self.set_byte(4, aValue)

    def get_ar_pln(self):
        return self.get_byte(5)

    def set_ar_pln(self, aValue):
        self.set_byte(5, aValue)

    def get_ar_op(self):
        return self.get_word(6)

    def set_ar_op(self, aValue):
        self.set_word(6, aValue)

    def get_ar_sha(self):
        tmp_size = self.get_ar_hln()
        return self.get_bytes().tolist()[8: 8 + tmp_size]

    def set_ar_sha(self, aValue):
        for i in range(0, self.get_ar_hln()):
            self.set_byte(i + 8, aValue[i])

    def get_ar_spa(self):
        tmp_size = self.get_ar_pln()
        return self.get_bytes().tolist()[8 + self.get_ar_hln(): 8 + self.get_ar_hln() + tmp_size]

    def set_ar_spa(self, aValue):
        for i in range(0, self.get_ar_pln()):
            self.set_byte(i + 8 + self.get_ar_hln(), aValue[i])

    def get_ar_tha(self):
        tmp_size = self.get_ar_hln()
        tmp_from = 8 + self.get_ar_hln() + self.get_ar_pln()
        return self.get_bytes().tolist()[tmp_from: tmp_from + tmp_size]

    def set_ar_tha(self, aValue):
        tmp_from = 8 + self.get_ar_hln() + self.get_ar_pln()
        for i in range(0, self.get_ar_hln()):
            self.set_byte(i + tmp_from, aValue[i])

    def get_ar_tpa(self):
        tmp_size = self.get_ar_pln()
        tmp_from = 8 + ( 2 * self.get_ar_hln()) + self.get_ar_pln()
        return self.get_bytes().tolist()[tmp_from: tmp_from + tmp_size]

    def set_ar_tpa(self, aValue):
        tmp_from = 8 + (2 * self.get_ar_hln()) + self.get_ar_pln()
        for i in range(0, self.get_ar_pln()):
            self.set_byte(i + tmp_from, aValue[i])

    def get_header_size(self):
        return 8 + (2 * self.get_ar_hln()) + (2 * self.get_ar_pln())

    def get_op_name(self, ar_op):
        tmp_dict = {1:'REQUEST', 2:'REPLY', 3:'REVREQUEST', 4:'REVREPLY', 8:'INVREQUEST', 9:'INVREPLY'}
        answer = tmp_dict.get(ar_op, 'UNKNOWN')
        return answer

    def get_hrd_name(self, ar_hrd):
        tmp_dict = { 1:'ARPHRD ETHER', 6:'ARPHRD IEEE802', 15:'ARPHRD FRELAY'}
        answer = tmp_dict.get(ar_hrd, 'UNKNOWN')
        return answer


    def as_hrd(self, anArray):
        if not anArray:
            return ''
        tmp_str = '%x' % anArray[0]
        for i in range(1, len(anArray)):
            tmp_str += ':%x' % anArray[i]
        return tmp_str

    def as_pro(self, anArray):
        if not anArray:
            return ''
        tmp_str = '%d' % anArray[0]
        for i in range(1, len(anArray)):
            tmp_str += '.%d' % anArray[i]
        return tmp_str

    def __str__(self):
        tmp_op = self.get_ar_op()
        tmp_str = 'ARP format: ' + self.get_hrd_name(self.get_ar_hrd()) + ' '
        tmp_str += 'opcode: ' + self.get_op_name(tmp_op)
        tmp_str += '\n' + self.as_hrd(self.get_ar_sha()) + ' -> '
        tmp_str += self.as_hrd(self.get_ar_tha())
        tmp_str += '\n' + self.as_pro(self.get_ar_spa()) + ' -> '
        tmp_str += self.as_pro(self.get_ar_tpa())
        if self.child():
            tmp_str += '\n' + self.child().__str__()
        return tmp_str


def example(): #To execute an example, remove this line
    a = Ethernet()
    b = ARP()
    c = Data('Hola loco!!!')
    b.set_ar_hln(6)
    b.set_ar_pln(4)
    #a.set_ip_dst('192.168.22.6')
    #a.set_ip_src('1.1.1.2')
    a.contains(b)
    b.contains(c)
    b.set_ar_op(2)
    b.set_ar_hrd(1)
    b.set_ar_spa((192, 168, 22, 6))
    b.set_ar_tpa((192, 168, 66, 171))
    a.set_ether_shost((0x0, 0xe0, 0x7d, 0x8a, 0xef, 0x3d))
    a.set_ether_dhost((0x0, 0xc0, 0xdf, 0x6, 0x5, 0xe))
