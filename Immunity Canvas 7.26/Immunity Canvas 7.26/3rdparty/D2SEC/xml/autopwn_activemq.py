#! /usr/bin/env python

#
# Proprietary D2 Exploitation Pack source code - use only under the license 
# agreement specified in LICENSE.txt in your D2 Exploitation Pack
#
# Copyright DSquare Security, LLC, 2007-2010
#

import autopwn
import appli.activemq
import xmlrpclib

class run(autopwn.run):

  def exploit(self, target, port):
    result = ''
    discovery = [
      appli.activemq.cve_2010_1587,
    ]
    self.result = ''
    self.log.info('Apache Activemq server scan %s:%s' % (target, port))
    try:
      for fct in discovery:
        infos = fct(target, port)
        if infos:
          for info in infos:
            result += '%s' % info
    except xmlrpclib.Fault, fault:
      print fault.faultString
      return
    self.db.db_unique_info(self.victim, self.service, 'Apache Activemq Scanner', 'autopwn_activemq', result)
    self.log.debug('%s' % result)
