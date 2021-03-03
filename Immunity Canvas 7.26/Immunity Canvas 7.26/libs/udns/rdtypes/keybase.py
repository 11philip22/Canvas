# Copyright (C) 2004-2007, 2009 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import udns.exception
import udns.dnssec
import udns.rdata

_flags_from_text = {
    'NOCONF': (0x4000, 0xC000),
    'NOAUTH': (0x8000, 0xC000),
    'NOKEY': (0xC000, 0xC000),
    'FLAG2': (0x2000, 0x2000),
    'EXTEND': (0x1000, 0x1000),
    'FLAG4': (0x0800, 0x0800),
    'FLAG5': (0x0400, 0x0400),
    'USER': (0x0000, 0x0300),
    'ZONE': (0x0100, 0x0300),
    'HOST': (0x0200, 0x0300),
    'NTYP3': (0x0300, 0x0300),
    'FLAG8': (0x0080, 0x0080),
    'FLAG9': (0x0040, 0x0040),
    'FLAG10': (0x0020, 0x0020),
    'FLAG11': (0x0010, 0x0010),
    'SIG0': (0x0000, 0x000f),
    'SIG1': (0x0001, 0x000f),
    'SIG2': (0x0002, 0x000f),
    'SIG3': (0x0003, 0x000f),
    'SIG4': (0x0004, 0x000f),
    'SIG5': (0x0005, 0x000f),
    'SIG6': (0x0006, 0x000f),
    'SIG7': (0x0007, 0x000f),
    'SIG8': (0x0008, 0x000f),
    'SIG9': (0x0009, 0x000f),
    'SIG10': (0x000a, 0x000f),
    'SIG11': (0x000b, 0x000f),
    'SIG12': (0x000c, 0x000f),
    'SIG13': (0x000d, 0x000f),
    'SIG14': (0x000e, 0x000f),
    'SIG15': (0x000f, 0x000f),
    }

_protocol_from_text = {
    'NONE' : 0,
    'TLS' : 1,
    'EMAIL' : 2,
    'DNSSEC' : 3,
    'IPSEC' : 4,
    'ALL' : 255,
    }
    
class KEYBase(udns.rdata.Rdata):
    """KEY-like record base

    @ivar flags: the key flags
    @type flags: int
    @ivar protocol: the protocol for which this key may be used
    @type protocol: int
    @ivar algorithm: the algorithm used for the key
    @type algorithm: int
    @ivar key: the public key
    @type key: string"""

    __slots__ = ['flags', 'protocol', 'algorithm', 'key']
    
    def __init__(self, rdclass, rdtype, flags, protocol, algorithm, key):
        super(KEYBase, self).__init__(rdclass, rdtype)
        self.flags = flags
        self.protocol = protocol
        self.algorithm = algorithm
        self.key = key

    def to_text(self, origin=None, relativize=True, **kw):
        return '%d %d %d %s' % (self.flags, self.protocol, self.algorithm,
                                udns.rdata._base64ify(self.key))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        flags = tok.get_string()
        if flags.isdigit():
            flags = int(flags)
        else:
            flag_names = flags.split('|')
            flags = 0
            for flag in flag_names:
                v = _flags_from_text.get(flag)
                if v is None:
                    raise udns.exception.SyntaxError, 'unknown flag %s' % flag
                flags &= ~v[1]
                flags |= v[0]
        protocol = tok.get_string()
        if protocol.isdigit():
            protocol = int(protocol)
        else:
            protocol = _protocol_from_text.get(protocol)
            if protocol is None:
                raise udns.exception.SyntaxError, \
                      'unknown protocol %s' % protocol
            
        algorithm = udns.dnssec.algorithm_from_text(tok.get_string())
        chunks = []
        while 1:
            t = tok.get()
            if t[0] == udns.tokenizer.EOL or t[0] == udns.tokenizer.EOF:
                break
            if t[0] != udns.tokenizer.IDENTIFIER:
                raise udns.exception.SyntaxError
            chunks.append(t[1])
        b64 = ''.join(chunks)
        key = b64.decode('base64_codec')
        return cls(rdclass, rdtype, flags, protocol, algorithm, key)
    
    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        header = struct.pack("!HBB", self.flags, self.protocol, self.algorithm)
        file.write(header)
        file.write(self.key)
        
    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        if rdlen < 4:
            raise udns.exception.FormError
        header = struct.unpack('!HBB', wire[current : current + 4])
        current += 4
        rdlen -= 4
        key = wire[current : current + rdlen]
        return cls(rdclass, rdtype, header[0], header[1], header[2],
                   key)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        hs = struct.pack("!HBB", self.flags, self.protocol, self.algorithm)
        ho = struct.pack("!HBB", other.flags, other.protocol, other.algorithm)
        v = cmp(hs, ho)
        if v == 0:
            v = cmp(self.key, other.key)
        return v
