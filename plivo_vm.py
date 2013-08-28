#!/usr/bin/env python

# @file plivo_vm.py
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
import time
from flask import Flask, request, make_response
import plivo

SERVER_PORT = 5000
SERVER_NAME = '127.0.0.1:%s' % SERVER_PORT
MAILBOX_ROOT = '/home/ubuntu/plivo-vm/mailboxes'
RECORD_FORMAT = 'mp3'

app = Flask(__name__)

class Message(object):
    @staticmethod
    def load(msg_file, directory):
        msg_key = os.path.splitext(msg_file)[0]
        return Message(msg_key, directory)

    def __init__(self, msg_key, directory):
        self.msg_key = msg_key
        self.directory = directory
        self.received = int(msg_key.split('_')[0])
        self.from_number = msg_key.split('_')[1]

    def deposit(self, rec_file):
        try:
            os.rename(rec_file, self.file())
        except OSError as e:
            print 'Move failed'
            raise e

    def file(self):
        return os.path.join(self.directory, '%s.%s' % (self.msg_key, RECORD_FORMAT))

    #def __str__(self):
    #    return self.msg_key

    #def __repr__(self):
    #    return self.msg_key

    osuffix = {'1':"st",'2':"nd",'3':"rd"}

    def ordinalize(number):
        s = str(number)
        if len(s) == 1 or s[-2] != '1':
            return s + osuffix.get(s[-1],"th")
        else:
            return s + "th"

    def description(self):
        # Create a textual description of the message based on the file name
        received = time.localtime(self.received)
        time_received = time.strftime("%I,%M,%p", received)
        now = time.localtime()
        if received.tm_year == now.tm_year and received.tm_yday == now.tm_yday:
            date_received = "today"
        else:
            date_received = "on %s %s" % (time.strftime("%A,%B", received), Message.ordinalize(received.tm_mday))
        return "Message received at %s %s from %s" % (time_received, date_received, ",".join(self.from_number))

class Mailbox(object):
    def __init__(self, mailbox_id):
        self.mailbox_id = mailbox_id
        self.root = os.path.join(MAILBOX_ROOT, self.mailbox_id)
        if not os.path.isdir(self.root):
            # Mailbox doesn't exist, so create it
            os.makedirs(self.root)

        # Mailbox exists, make sure subdirectories are in place
        self.new_msg_directory = os.path.join(self.root, 'new')
        self.saved_msg_directory = os.path.join(self.root, 'saved')
        if not os.path.isdir(self.new_msg_directory):
            os.mkdir(self.new_msg_directory)
        if not os.path.isdir(self.saved_msg_directory):
            os.mkdir(self.saved_msg_directory)

        # Populate message lists, sorted oldest first.
        self.new_msgs = [Message.load(x, self.new_msg_directory) for x in os.listdir(self.new_msg_directory)]
        self.saved_msgs = [Message.load(x, self.saved_msg_directory) for x in os.listdir(self.saved_msg_directory)]
        self.new_msgs.sort(key = lambda x: x.received)
        self.saved_msgs.sort(key = lambda x: x.received)
        print "Retrieved mailbox %s, %d new messages, %d saved messages" % (mailbox_id, len(self.new_msgs), len(self.saved_msgs))

    def id(self):
        return self.mailbox_id

    def deposit_message(self, received, from_num, rec_file):
        msg = Message(received + '_' + from_num, self.new_msg_directory)
        msg.deposit(rec_file)
        self.new_msgs.append(msg)

    def delete_message(self, msg):
        # Normally deletion happens from saved messages, so test that first.
        if msg in self.saved_msgs:
            os.remove(msg.file())
            self.saved_msgs.remove(msg)
        elif msg in self.new_msgs:
            os.remove(msg.file())
            self.new_msgs.remove(msg)

    def message_read(self, msg):
        if msg in self.new_msgs:
            new_msg_file = msg.file()
            msg.directory = self.saved_msg_directory
            os.rename(new_msg_file, msg.file())
            self.new_msgs.remove(msg)
            self.saved_msgs.append(msg)
            self.saved_msgs.sort(key=lambda x: x.received)

    def message_unread(self, msg):
        if msg in self.saved_msgs:
            saved_msg_file = msg.file()
            msg.directory = self.new_msg_directory
            os.rename(saved_msg_file, msg.file())
            self.saved_msgs.remove(msg)
            self.new_msgs.append(msg)
            self.new_msgs.sort(key=lambda x: x.received)

    def set_greeting(self, rec_file):
        greeting = os.path.join(self.root, "greeting.%s" % RECORD_FORMAT)
        try:
            os.rename(rec_file, greeting)
        except OSError as e:
            print "Move failed"
            raise e

    def get_greeting(self):
        greeting = os.path.join(self.root, "greeting.%s" % RECORD_FORMAT)
        if os.path.exists(greeting):
            return greeting
        else:
            return ''

def play_message(response, mailbox, list, time, msg):
    mailbox.message_read(msg);
    getdigits = response.addGetDigits(
        action="http://" + SERVER_NAME + "/vmmsgoption/" + mailbox.id() + "/" + list + "/" + time + "/" + msg.msg_key,
        timeout='60',
        numDigits='1',
        method='GET'
    )
    getdigits.addSpeak(body=msg.description())
    getdigits.addPlay(msg.file())
    getdigits.addSpeak(body="Press 2 to repeat, 3 to delete, 6 to skip, 7 to save")

def play_menu(response, mailbox):
    response.addSpeak(body="Main menu")
    getdigits = response.addGetDigits(
        action="http://" + SERVER_NAME + "/vmmenu/" + mailbox.id(),
        timeout='15',
        numDigits='1',
        method='GET'
    )
    getdigits.addSpeak(body="Press 2 for your messages, 3 to record a personal greeting")
    response.addSpeak(body="No option selected")

@app.route("/answered/", methods=['GET'])
def vm():
    forward_num = request.args.get('ForwardedFrom', '')
    from_num = request.args.get('From', '')

    response = plivo.Response()
    response.addWait(length='1')

    if forward_num != '':
        # Call is forwarded to a mailbox, so play the greeting and record the message.
        mailbox = Mailbox(forward_num)
        greeting = mailbox.get_greeting()
        if greeting != '':
            response.addPlay(body=greeting)
        else:
            response.addSpeak(body="You have reached the voicemail of %s.  Please leave a message after the beep." % ",".join(mailbox.id()))
        response.addRecord(
              action="http://" + SERVER_NAME + "/vmdeposit/" + mailbox.id() + "/" + from_num + "/" + str(int(time.time())),
              fileFormat=RECORD_FORMAT,
              finishOnKey='#',
              method='GET')
        response.addSpeak(body="Message not received")
    elif from_num != '':
        # Call is to a mailbox, so play the message status and any messages.
        mailbox = Mailbox(from_num)
        response.addSpeak(body="%d new messages and %d saved messages" % (len(mailbox.new_msgs), len(mailbox.saved_msgs)))
        if len(mailbox.new_msgs) > 0:
            msg = mailbox.new_msgs[0]
            play_message(response, mailbox, 'new', str(msg.received), msg)
        else:
            play_menu(response, mailbox)
    else:
        response.addSpeak(body="Cannot find mailbox")

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

@app.route("/vmdeposit/<id>/<from_num>/<received>", methods=['GET'])
def vmdeposit(id, from_num, received):
    rec_file = request.args.get('RecordFile', '')

    mailbox = Mailbox(id)
    response = plivo.Response()

    if rec_file != '':
        # Message deposited, so copy it into the mailbox.
        mailbox.deposit_message(received, from_num, rec_file)
        response.addSpeak(body='Thank you')
    else:
        # No message received
        response.addSpeak(body='No message received')

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

@app.route("/vmmsgoption/<id>/<list>/<time>/<msg_key>", methods=['GET'])
def vmmsgoptions(id, list, time, msg_key):
    action = request.args.get('Digits', '')

    response = plivo.Response()
    mailbox = Mailbox(id)

    # Find the message that was playing.  It should always be in the saved
    # message lists since it has just been played.
    for saved_msg in mailbox.saved_msgs:
        if saved_msg.msg_key == msg_key:
            msg = saved_msg
            break

    if action == '2':
        # Just play this message again
        play_message(response, mailbox, list, time, msg)
    elif action == '3' or action == '6' or action == '7':
        if action == '3':
            mailbox.delete_message(msg)
            response.addSpeak(body="Message deleted")
        elif action == '6':
            response.addSpeak(body="Skip to next message")
        elif action == '7':
            response.addSpeak(body="Message saved")

        # Find the next message to play
        next_msg = None
        if list == 'new':
            # Reviewing new messages - are there any more?
            if len(mailbox.new_msgs) > 0:
                next_msg = mailbox.new_msgs[0]
            else:
                # No more new messages, so move to the saved messages.  Use the
                # time passed in the request to filter any messages that have
                # already been played as a new message.
                list = 'saved'
                unplayed_msgs = [x for x in mailbox.saved_msgs if x.received < int(time)]
                if len(unplayed_msgs) > 0:
                    # There are messages in the saved list that haven't been played yet
                    response.addSpeak(body="%d saved messages" % len(unplayed_msgs))
                    next_msg = unplayed_msgs[0]
        elif list == 'saved':
            # Reviewing saved messages, have we reached the end.  Use the time
            # passed in the request to filter any messages that have already
            # been played as a new message.
            unplayed_msgs = [x for x in mailbox.saved_msgs if x.received < int(time)]
            for unplayed_msg in unplayed_msgs:
                if unplayed_msg.msg_key > msg_key:
                    next_msg = unplayed_msg
                    break

        if next_msg is not None:
            play_message(response, mailbox, list, time, next_msg)
        else:
            response.addSpeak(body="No more messages")
            play_menu(response, mailbox)

    elif action == '1':
        play_menu(response, mailbox)

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

@app.route("/vmmenu/<id>", methods=['GET'])
def vmmenu(id):
    option = request.args.get('Digits', '')

    response = plivo.Response()
    mailbox = Mailbox(id)

    if option == '2':
        if len(mailbox.new_msgs) > 0:
            # Start playing new messages.  Pass the time of oldest new
            # message so we spot new messages when they get moved to the saved
            # list.
            response.addSpeak(body="%d new messages" % (len(mailbox.new_msgs)))
            msg = mailbox.new_msgs[0]
            play_message(response, mailbox, 'new', str(msg.received), msg)
        elif len(mailbox.saved_msgs) > 0:
            # Start playing saved messages.  Since there are no new messages
            # use the current time as the time of the first new message.
            response.addSpeak(body="%d saved messages" % len(mailbox.saved_msgs))
            msg = mailbox.saved_msgs[0]
            play_message(response, mailbox, 'saved', str(int(time.time())), msg)
        else:
            response.addSpeak(body="You have no messages.")
            play_menu(response, mailbox)
    elif option == '3':
        response.addSpeak(body="Record your personal greeting after the beep.  Press # to end recording.")
        response.addRecord(
          action="http://" + SERVER_NAME + "/vmgreeting/" + mailbox.id(),
          fileFormat=RECORD_FORMAT,
          finishOnKey='#',
          method='GET')
        response.addSpeak(body="Greeting not recorded")
        play_menu(response, mailbox)
    else:
        response.addSpeak(body="Unknown selection")
        play_menu(response, mailbox)

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

@app.route("/vmgreeting/<id>", methods=['GET'])
def vmgreeting(id):
    rec_file = request.args.get('RecordFile', '')

    response = plivo.Response()
    mailbox = Mailbox(id)

    if rec_file != '':
        # Copy the greeting to the mailbox directory.
        mailbox.set_greeting(rec_file)
        response.addSpeak(body="Your personal greeting has been updated. Thank you")
        play_menu(response, mailbox)
    else:
        response.addSpeak(body="Greeting not updated.")
        play_menu(response, mailbox)

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

if __name__ == '__main__':
    # Enable debug if DEBUG environment variable is set
    if os.environ.get('DEBUG', '') != '':
        app.debug = True
    app.run(host='0.0.0.0', port=5000)
