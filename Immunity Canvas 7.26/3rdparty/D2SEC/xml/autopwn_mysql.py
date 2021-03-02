#! /usr/bin/env python

#
# Proprietary D2 Exploitation Pack source code - use only under the license 
# agreement specified in LICENSE.txt in your D2 Exploitation Pack
#
# Copyright DSquare Security, LLC, 2007-2010
#

import autopwn
import net.banner
import proto.smtp
import xmlrpclib

class run(autopwn.run):

  def exploit(self, target, port):
    banner = ''
    try:
      banner = net.banner.bannergrab(target, port)
    except xmlrpclib.Fault, fault:
      print fault.faultString
      return
    if banner:
      self.db.db_unique_info(self.victim, self.service, 'MYSQL Banner', 'autopwn_mysql', banner)
      self.log.debug('%s' % banner)
