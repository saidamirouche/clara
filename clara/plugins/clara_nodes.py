#!/usr/bin/env python
#-*- coding: utf-8 -*-
##############################################################################
#  Copyright (C) 2014 EDF SA                                                 #
#                                                                            #
#  This file is part of Clara                                                #
#                                                                            #
#  This software is governed by the CeCILL-C license under French law and    #
#  abiding by the rules of distribution of free software. You can use,       #
#  modify and/ or redistribute the software under the terms of the CeCILL-C  #
#  license as circulated by CEA, CNRS and INRIA at the following URL         #
#  "http://www.cecill.info".                                                 #
#                                                                            #
#  As a counterpart to the access to the source code and rights to copy,     #
#  modify and redistribute granted by the license, users are provided only   #
#  with a limited warranty and the software's author, the holder of the      #
#  economic rights, and the successive licensors have only limited           #
#  liability.                                                                #
#                                                                            #
#  In this respect, the user's attention is drawn to the risks associated    #
#  with loading, using, modifying and/or developing or reproducing the       #
#  software by the user in light of its specific status of free software,    #
#  that may mean that it is complicated to manipulate, and that also         #
#  therefore means that it is reserved for developers and experienced        #
#  professionals having in-depth computer knowledge. Users are therefore     #
#  encouraged to load and test the software's suitability as regards their   #
#  requirements in conditions enabling the security of their systems and/or  #
#  data to be ensured and, more generally, to use and operate it in the      #
#  same conditions as regards security.                                      #
#                                                                            #
#  The fact that you are presently reading this means that you have had      #
#  knowledge of the CeCILL-C license and that you accept its terms.          #
#                                                                            #
##############################################################################
"""
Manages and get the status from the nodes of a cluster.

Usage:
    clara nodes connect <hotlist>
    clara nodes (on|off|reboot) <hotlist>
    clara nodes status <hotlist>
    clara nodes setpwd <hotlist>
    clara nodes getmac <hotlist>
    clara nodes pxe <hotlist>
    clara nodes disk <hotlist>
    clara nodes ping <hotlist>
    clara nodes blink <hotlist>
    clara nodes immdhcp <hotlist>
    clara nodes bios <hotlist>
    clara nodes p2p (status|restart)
    clara nodes -h | --help

"""
import os
import subprocess
import sys
import time

import ClusterShell
import docopt
from clara.utils import clush, run, getconfig, value_from_file


def install_cfg():
    cfile = getconfig().get("nodes", "cfile")
    if not os.path.isfile(cfile) and os.path.isfile(cfile + ".enc"):
        password = value_from_file(getconfig().get("nodes", "master_passwd_file"), "PASSPHRASE")

        if len(password) > 20:
            cmd = ['openssl', 'aes-256-cbc', '-d', '-in', cfile + ".enc",
                    '-out', cfile, '-k', password]
            run(cmd)
            os.chmod(cfile, 0o400)
        else:
            sys.exit('There was some problem reading the PASSPHRASE')


def ipmi_do(hosts, cmd):
    install_cfg()
    imm_user = value_from_file(getconfig().get("nodes", "cfile"), "IMMUSER")
    os.environ["IPMI_PASSWORD"] = value_from_file(getconfig().get("nodes", "cfile"), "PASSWD")
    nodeset = ClusterShell.NodeSet.NodeSet(hosts)
    for host in nodeset:
        print "%s: " % host
        run(["ipmitool", "-I", "lanplus", "-H", "imm" + host,
             "-U", imm_user, "-E", cmd])


def getmac(hosts):
    install_cfg()
    imm_user = value_from_file(getconfig().get("nodes", "cfile"), "IMMUSER")
    os.environ["IPMI_PASSWORD"] = value_from_file(getconfig().get("nodes", "cfile"), "PASSWD")
    nodeset = ClusterShell.NodeSet.NodeSet(hosts)
    for host in nodeset:
        print "%s: " % host
        cmd = ["ipmitool", "-I", "lanplus", "-H", "imm" + host,
             "-U", imm_user, "-E", "fru", "print", "0"]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        # The data we want is in line 15
        line = proc.stdout.readlines()[14]
        full_mac = line.split(":")[1].strip().upper()
        mac_address1 = "{0}:{1}:{2}:{3}:{4}:{5}".format(full_mac[0:2],
                                                        full_mac[2:4],
                                                        full_mac[4:6],
                                                        full_mac[6:8],
                                                        full_mac[8:10],
                                                        full_mac[10:12])

        mac_address2 = "{0}:{1}:{2}:{3}:{4}:{5}".format(full_mac[12:14],
                                                        full_mac[14:16],
                                                        full_mac[16:18],
                                                        full_mac[18:20],
                                                        full_mac[20:22],
                                                        full_mac[22:24])

        print "ETH0's MAC address is {0}\n" \
              "ETH1's MAC address is {1}\n".format(mac_address1, mac_address2)


def do_connect(hosts):

    try:
        cmd = ["service", "conman", "status"]
        retcode = subprocess.call(cmd)
    except OSError, e:
        if (e.errno == errno.ENOENT):
            sys.exit("Binary not found, check your path and/or retry as root." \
                     "You were trying to run:\n {0}".format(" ".join(cmd)))

    if retcode == 0:  # if conman is running
        os.environ["CONMAN_ESCAPE"] = '!'
        conmand = value_from_file(getconfig().get("nodes", "conmand"))
        run(["conman", "-d", conmand, hosts])
    elif retcode == 1:  # if conman is NOT running
        ipmi_do(hosts, "-e! sol activate")
    else:
        sys.exit('E: ' + ' '.join(cmd))


def do_ping(hosts):
    nodes = ClusterShell.NodeSet.NodeSet(hosts)
    cmd = ["fping", "-r1", "-u", "-s"] + list(nodes)
    run(cmd)


def main():
    dargs = docopt.docopt(__doc__)

    if dargs['connect']:
        do_connect(dargs['<hotlist>'])
    elif dargs['status'] and not dargs['p2p']:
        ipmi_do(dargs['<hotlist>'], "power status")
    elif dargs['setpwd']:
        sys.exit("Not tested!")  # TODO
        ipmi_do(dargs['<hotlist>'], "user set name 2 IMMUSER")
        ipmi_do(dargs['<hotlist>'], "user set password 2 PASSWD")
    elif dargs['getmac']:
        getmac(dargs['<hotlist>'])
    elif dargs['on']:
        ipmi_do(dargs['<hotlist>'], "power on")
    elif dargs['off']:
        ipmi_do(dargs['<hotlist>'], "power off")
    elif dargs['reboot']:
        ipmi_do(dargs['<hotlist>'], "chassis power reset")
    elif dargs['blink']:
        ipmi_do(dargs['<hotlist>'], "chassis identify 1")
    elif dargs['bios']:
        ipmi_do(dargs['<hotlist>'],
                                   "chassis bootparam set bootflag force_bios")
    elif dargs['immdhcp']:
        ipmi_do(dargs['<hotlist>'], "lan set 1 ipsrc dhcp")
    elif dargs['pxe']:
        ipmi_do(dargs['<hotlist>'], "chassis bootdev pxe")
    elif dargs['disk']:
        ipmi_do(dargs['<hotlist>'], "chassis bootdev disk")
    elif dargs['p2p']:
        trackers = getconfig().get("nodes", "trackers")
        seeders = getconfig().get("nodes", "seeders")
        if dargs['status']:
            clush(trackers, "service mldonkey-server status")
            clush(seeders, "service ctorrent status")
        elif dargs['restart']:
            clush(seeders, "service ctorrent stop")
            clush(trackers, "service mldonkey-server stop")
            time.sleep(1)
            clush(trackers, "service mldonkey-server start")
            clush(seeders, "service ctorrent start")
    elif dargs['ping']:
        do_ping(dargs['<hotlist>'])


if __name__ == '__main__':
    main()