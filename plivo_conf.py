#!/usr/bin/env python

# @file plivo_conf.py
#
# Project Clearwater - IMS in the Cloud
# Copyright (C) 2013  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version, along with the "Special Exception" for use of
# the program along with SSL, set forth below. This program is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details. You should have received a copy of the GNU General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by
# post at Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK
#
# Special Exception
# Metaswitch Networks Ltd  grants you permission to copy, modify,
# propagate, and distribute a work formed by combining OpenSSL with The
# Software, or a work derivative of such a combination, even if such
# copying, modification, propagation, or distribution would otherwise
# violate the terms of the GPL. You must comply with the GPL in all
# respects for all of the code used other than OpenSSL.
# "OpenSSL" means OpenSSL toolkit software distributed by the OpenSSL
# Project and licensed under the OpenSSL Licenses, or a work based on such
# software and licensed under the OpenSSL Licenses.
# "OpenSSL Licenses" means the OpenSSL License and Original SSLeay License
# under which the OpenSSL Project distributes the OpenSSL toolkit software,
# as those licenses appear in the file LICENSE-OPENSSL.

import os
from flask import Flask, request, make_response
import plivo

SERVER_PORT = 5000
SERVER_NAME = '127.0.0.1:%s' % SERVER_PORT

app = Flask(__name__)

@app.route('/answered/', methods=['GET', 'POST'])
def confselect():
    response = plivo.Response()
    getdigits = response.addGetDigits(
        action='http://%s/confroom/' % SERVER_NAME,
        timeout='15',
        finishOnKey='#',
        method='GET'
    )
    getdigits.addWait(length='1')
    getdigits.addSpeak("Please enter your conference i d, followed by the pound key.")
    response.addSpeak(body="Input not received. Thank you.")
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

@app.route('/confroom/', methods=['GET', 'POST'])
def confroom():
    if request.method == 'GET':
        conf = request.args.get('Digits', '')
    elif request.method == 'POST':
        conf = request.form.get('Digits', '')

    response = plivo.Response()
    response.addSpeak(body="Now entering conference " + ",".join(str(conf)))
    response.addConference(
        enterSound='beep:2',
        exitSound='beep:1',
        waitSound='http://%s/confwait/' % SERVER_NAME,
        body=conf
    )

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

@app.route('/confwait/', methods=['POST'])
def confwait():
    response = plivo.Response()
    response.addPlay(body='http://localhost/music.mp3')

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SERVER_PORT)
