# Copyright (c) 2003-2006 CORE Security Technologies
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# $Id: transport.py,v 1.5 2006/05/23 21:19:26 gera Exp $
#
# Description:
#   Transport implementations for the DCE/RPC protocol.
#

import re
import socket

from impacket import smb
from impacket import nmb
from impacket.structure import pack
from impacket.dcerpc import dcerpc, dcerpc_v4

class DCERPCStringBinding:
    parser = re.compile(r'(?:([a-fA-F0-9-]{8}(?:-[a-fA-F0-9-]{4}){3}-[a-fA-F0-9-]{12})@)?' # UUID (opt.)
                        +'([_a-zA-Z0-9]*):' # Protocol Sequence
                        +'([^\[]*)' # Network Address (opt.)
                        +'(?:\[([^\]]*)\])?') # Endpoint and options (opt.)

    def __init__(self, stringbinding):
        match = DCERPCStringBinding.parser.match(stringbinding)
        self.__uuid = match.group(1)
        self.__ps = match.group(2)
        self.__na = match.group(3)
        options = match.group(4)
        if options:
            options = options.split(',')
            self.__endpoint = options[0]
            try:
                self.__endpoint.index('endpoint=')
                self.__endpoint = self.__endpoint[len('endpoint='):]
            except:
                pass
            self.__options = options[1:]
        else:
            self.__endpoint = ''
            self.__options = []

    def get_uuid(self):
        return self.__uuid

    def get_protocol_sequence(self):
        return self.__ps

    def get_network_address(self):
        return self.__na

    def get_endpoint(self):
        return self.__endpoint

    def get_options(self):
        return self.__options

    def __str__(self):
        return DCERPCStringBindingCompose(self.__uuid, self.__ps, self.__na, self.__endpoint, self.__options)

def DCERPCStringBindingCompose(uuid=None, protocol_sequence='', network_address='', endpoint='', options=[]):
    s = ''
    if uuid: s += uuid + '@'
    s += protocol_sequence + ':'
    if network_address: s += network_address
    if endpoint or options:
        s += '[' + endpoint
        if options: s += ',' + ','.join(options)
        s += ']'

    return s

def DCERPCTransportFactory(stringbinding):
    sb = DCERPCStringBinding(stringbinding)

    na = sb.get_network_address()
    ps = sb.get_protocol_sequence()
    if 'ncadg_ip_udp' == ps:
        port = sb.get_endpoint()
        if port:
            return UDPTransport(na, int(port))
        else:
            return UDPTransport(na)
    elif 'ncacn_ip_tcp' == ps:
        port = sb.get_endpoint()
        if port:
            return TCPTransport(na, int(port))
        else:
            return TCPTransport(na)
    elif 'ncacn_http' == ps:
        port = sb.get_endpoint()
        if port:
            return HTTPTransport(na, int(port))
        else:
            return HTTPTransport(na)
    elif 'ncacn_np' == ps:
        named_pipe = sb.get_endpoint()
        if named_pipe:
            named_pipe = named_pipe[len(r'\pipe'):]
            return SMBTransport(na, filename = named_pipe)
        else:
            return SMBTransport(na)
    else:
        raise Exception, "Unknown protocol sequence."


class DCERPCTransport:

    DCERPC_class = dcerpc.DCERPC_v5

    def __init__(self, dstip, dstport):
        self.__dstip = dstip
        self.__dstport = dstport
        self._max_send_frag = None
        self._max_recv_frag = None
        self.set_credentials('','','','')

    def connect(self):
        raise RuntimeError, 'virtual function'
    def send(self,data=0, forceWriteAndx = 0, forceRecv = 0):
        raise RuntimeError, 'virtual function'
    def recv(self):
        raise RuntimeError, 'virtual function'
    def disconnect(self):
        raise RuntimeError, 'virtual function'
    def get_socket(self):
        raise RuntimeError, 'virtual function'

    def get_dip(self):
        return self.__dstip
    def set_dip(self, dip):
        "This method only makes sense before connection for most protocols."
        self.__dstip = dip

    def get_dport(self):
        return self.__dstport
    def set_dport(self, dport):
        "This method only makes sense before connection for most protocols."
        self.__dstport = dport

    def get_addr(self):
        return (self.get_dip(), self.get_dport())
    def set_addr(self, addr):
        "This method only makes sense before connection for most protocols."
        self.set_dip(addr[0])
        self.set_dport(addr[1])

    def set_max_fragment_size(self, send_fragment_size):
        # -1 is default fragment size: 0 (don't fragment)
        #  0 is don't fragment
        #    other values are max fragment size
        if send_fragment_size == -1:
            self.set_default_max_fragment_size()
        else:
            self._max_send_frag = send_fragment_size

    def set_default_max_fragment_size(self):
        # default is 0: don'fragment. 
        # subclasses may override this method
        self._max_send_frag = 0
     
    def get_credentials(self):
        return (
            self._username,
            self._password,
            self._nt_hash,
            self._lm_hash)

    def set_credentials(self, username, password, lm_hash='', nt_hash=''):
        self._username = username
        self._password = password
        self._nt_hash = nt_hash
        self._lm_hash = lm_hash

class UDPTransport(DCERPCTransport):
    "Implementation of ncadg_ip_udp protocol sequence"

    DCERPC_class = dcerpc_v4.DCERPC_v4

    def __init__(self,dstip, dstport = 135):
        DCERPCTransport.__init__(self, dstip, dstport)
        self.__socket = 0

    def connect(self):
        try:
            self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.__socket.settimeout(30)
        except socket.error, msg:
            self.__socket = None
            raise Exception, "Could not connect: %s" % msg

        return 1

    def disconnect(self):
        try:
            self.__socket.close()
        except socket.error, msg:
            self.__socket = None
            return 0
        return 1

    def send(self,data, forceWriteAndx = 0, forceRecv = 0):
        self.__socket.sendto(data,(self.get_dip(),self.get_dport()))

    def recv(self):
        buffer, self.__recv_addr = self.__socket.recvfrom(8192)
        return buffer

    def get_recv_addr(self):
        return self.__recv_addr

    def get_socket(self):
        return self.__socket

class TCPTransport(DCERPCTransport):
    "Implementation of ncacn_ip_tcp protocol sequence"

    def __init__(self, dstip, dstport = 135):
        DCERPCTransport.__init__(self, dstip, dstport)
        self.__socket = 0

    def connect(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.__socket.settimeout(300)
            self.__socket.connect((self.get_dip(), self.get_dport()))
        except socket.error, msg:
            self.__socket.close()
            raise Exception, "Could not connect: %s" % msg

        return 1

    def disconnect(self):
        try:
            self.__socket.close()
        except socket.error, msg:
            self.__socket = None
            return 0
        return 1

    def send(self,data, forceWriteAndx = 0, forceRecv = 0):
        if self._max_send_frag:
            offset = 0
            while 1:
                toSend = data[offset:offset+self._max_send_frag]
                if not toSend:
                    break
                self.__socket.send(toSend)
                offset += len(toSend)
        else:
            self.__socket.send(data)

    def recv(self):
        buffer = self.__socket.recv(8192)
        return buffer

    def get_socket(self):
        return self.__socket

class HTTPTransport(TCPTransport):
    "Implementation of ncacn_http protocol sequence"

    def connect(self):
        TCPTransport.connect(self)

        self.__socket.send('RPC_CONNECT ' + self.get_dip() + ':593 HTTP/1.0\r\n\r\n')
        data = self.__socket.recv(8192)
        if data[10:13] != '200':
            raise Exception("Service not supported.")

class SMBTransport(DCERPCTransport):
    "Implementation of ncacn_np protocol sequence"

    def __init__(self, dstip, dstport = 445, filename = '', username='', password='', lm_hash='', nt_hash=''):
        DCERPCTransport.__init__(self, dstip, dstport)
        self.__socket = None
        self.__smb_server = 0
        self.__tid = 0
        self.__filename = filename
        self.__handle = 0
        self.__pending_recv = 0
        self.set_credentials(username, password, lm_hash, nt_hash)


    def setup_smb_server(self):
        if not self.__smb_server:
            self.__smb_server = smb.SMB('*SMBSERVER',self.get_dip(), sess_port = self.get_dport())

    def connect(self):
        self.setup_smb_server()
        if self.__smb_server.is_login_required():
            if self._password != '' or (self._password == '' and self._nt_hash == '' and self._lm_hash == ''):
                self.__smb_server.login(self._username, self._password)
            elif self._nt_hash != '' or self._lm_hash != '':
                self.__smb_server.login(self._username, '', '', self._lm_hash, self._nt_hash)
        self.__tid = self.__smb_server.tree_connect_andx('\\\\*SMBSERVER\\IPC$')
        self.__handle = self.__smb_server.nt_create_andx(self.__tid, self.__filename)
        # self.__handle = self.__smb_server.open_file_andx(self.__tid, r"\\PIPE\%s" % self.__filename, smb.SMB_O_CREAT, smb.SMB_ACCESS_READ)[0]
        # self.__handle = self.__smb_server.open_file(self.__tid, r"\\PIPE\%s" % self.__filename, smb.SMB_O_CREAT, smb.SMB_ACCESS_READ)[0]
        self.__socket = self.__smb_server.get_socket()
        return 1
    
    def disconnect(self):
        self.__smb_server.disconnect_tree(self.__tid)
        self.__smb_server.logoff()

    def send(self,data, noAnswer = 0, forceWriteAndx = 0, forceRecv = 0):
        if self._max_send_frag:
            offset = 0
            while 1:
                toSend = data[offset:offset+self._max_send_frag]
                if not toSend:
                    break
                self.__smb_server.write_andx(self.__tid, self.__handle, toSend, offset = offset)
                offset += len(toSend)
        else:
            if forceWriteAndx:
                self.__smb_server.write_andx(self.__tid, self.__handle, data)
            else:
                self.__smb_server.TransactNamedPipe(self.__tid,self.__handle,data, noAnswer = noAnswer, waitAnswer = 0)
        if forceRecv:
            self.__pending_recv += 1
        
    def recv(self):
        if self._max_send_frag or self.__pending_recv:
            # _max_send_frag is checked because it's the same condition we checked
            # to decide whether to use write_andx() or send_trans() in send() above.
            if self.__pending_recv:
                self.__pending_recv -= 1
            return self.__smb_server.read_andx(self.__tid, self.__handle, max_size = self._max_recv_frag)
        else:
            s = self.__smb_server.recv_packet()
            if self.__smb_server.isValidAnswer(s,smb.SMB.SMB_COM_TRANSACTION):
                trans = smb.TRANSHeader(s.get_parameter_words(), s.get_buffer())
                data = trans.get_data()
                return data
            return None

    def get_smb_server(self):
        return self.__smb_server

    def get_socket(self):
        return self.__socket

