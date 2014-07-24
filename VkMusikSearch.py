#!/usr/bin/env python

# Copyright (c) 2014 Oleg Melnik
# This software is licensed by the MIT License.

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial
# portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import re
import httplib
import urllib
import json
from datetime import datetime, timedelta

lp_server_re = re.compile("^.+\.vk\.com")
lp_url_re = re.compile("im\d+$")
search_re = re.compile('^[Ss]\s+(.+)$')
help_re = re.compile("^[Hh]\s*")
token = ""
searchers = []
update_time = datetime.now() + timedelta(minutes=5)

def get_response(connection, url):
    #print url
    connection.request("GET", url)
    response = connection.getresponse()
    result = response.read()
    return result


def call_method(access_token, method, **kwargs):
    #print kwargs
    connection = httplib.HTTPSConnection("api.vk.com")
    url = "/method/" + method + "?"
    #print kwargs
    for key in kwargs:
        url += key + "=" + urllib.quote(kwargs[key]) + "&"
    url += "access_token=" + access_token
    result = get_response(connection, url)
    j_result = json.loads(result)
    if "error" in j_result.keys():
        raise Exception("Error: " + result)
    #print result
    return j_result


def get_long_poll(server, key, ts):
    #print "server: " + server
    serv = lp_server_re.findall(server)[0]
    im_url = lp_url_re.findall(server)[0]
    connection = httplib.HTTPConnection(serv)
    request_string = "/"+im_url+"?act=a_check&key="+key+"&ts="+str(ts)+"&wait=25&mode=2"
    result = get_response(connection, request_string)
    j_result = json.loads(result)
    if "failed" in j_result.keys():
        raise IOError("Failed to connect to long poll server")
    new_ts = j_result["ts"]
    updates = j_result["updates"]
    return new_ts, updates

def music_search(u_id, search_string):
    number = 0
    try:
        search_j_result = call_method(token, "audio.search", q=search_string, auto_complete=str(1), count=str(10))
        attachments_str = ""
        response = search_j_result["response"]
        for audio in response:
            if type(audio) is int:
                number = audio
            else:
                attachment = "audio"+str(audio["owner_id"])+"_"+str(audio["aid"])
                if response.index(audio) != len(response) - 1:
                    attachment += ","
                attachments_str += attachment
        try:
            call_method(token, "messages.send", user_id=str(u_id), message="Found "+str(number)+" tracks:", attachment=attachments_str)
        except Exception as e:
            print e.message
    except Exception as e:
        print e.message


if __name__ == "__main__":
    token = rec_id = message = ""
    if len(sys.argv) >= 2:
        token = sys.argv[1]

        lp_response = call_method(access_token=token, method="messages.getLongPollServer")
        k = lp_response["response"]["key"]
        serv = lp_response["response"]["server"]
        tss = lp_response["response"]["ts"]
        first_response = True
        while 1:
            if datetime.now() >= update_time:
                searchers = []
                update_time = datetime.now() + timedelta(minutes=5)
            try:
                ts_new, upds = get_long_poll(server=serv, key=k, ts=tss)
                #print upds
                for u in upds:
                    if u[0] == 61:
                        print "id" + str(u[1]) + " types a message"
                    elif u[0] == 4 and (u[2] >> 1) % 2 == 0:
                        user_id = u[3]
                        in_msg = u[6]
                        in_msg.replace("<br>", "")
                        print "id" + str(user_id) + " sent a message: " + in_msg
                        ans_msg = ""
                        if search_re.match(in_msg):
                            #ans_msg = "Search: "+search_re.findall(in_msg)[0].encode('utf-8')
                            music_search(user_id, search_re.findall(in_msg)[0].encode('utf-8'))
                        elif help_re.match(in_msg):
                            ans_msg = "Type: s SEARCH_WORDS to search."
                        else:
                            ans_msg = "Unknown command: "+in_msg.encode('utf-8')
                        try:
                            if ans_msg != "":
                                call_method(token, "messages.send", user_id=str(user_id), message=ans_msg)
                        except Exception as e:
                            print e.message
                tss = ts_new
            except IOError:
                lp_response = call_method(access_token=token, method="messages.getLongPollServer")
                k = lp_response["response"]["key"]
                serv = lp_response["response"]["server"]
                tss = lp_response["response"]["ts"]



    else:
        print "Format: VkMusikSearch.py token"