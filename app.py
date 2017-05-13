# -*- coding: utf-8 -*-
"""
Created on Fri May 12 15:22:50 2017

@author: showshow
"""
import os
import sys
import csv
import requests
import re
import random
import redis
from bs4 import BeautifulSoup
from collections import defaultdict
from collections import namedtuple
from flask import Flask, request, abort, g
###import for google drive___>>>
import gspread
from oauth2client.service_account import ServiceAccountCredentials
'''
import psycopg2
from urllib.parse import urlparse
from flask import *
from datetime import datetime
from dbModel import *
'''
###import for google drive___<<<

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

###global init___>>>
app = Flask(__name__)
db = redis.from_url(os.getenv('REDIS_URL', None), decode_responses=True)

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
handler = WebhookHandler(channel_secret)
line_bot_api = LineBotApi(channel_access_token)

###conn to google drive___>>>
def auth_gss_client(path, scopes):
    creds = ServiceAccountCredentials.from_json_keyfile_name(path, scopes)
    return gspread.authorize(creds)


auth_json_path = 'client_secret.json'
gss_scopes = ['https://spreadsheets.google.com/feeds']

gss_client = auth_gss_client(auth_json_path, gss_scopes)
###conn to google drive___<<<

#sheet = gss_client.open("Copy of Legislators 2017").sheet1
sh = gss_client.open_by_key('1nJHriicxQAZj5i_c8bWAY8OShp7OMLErsz6QKIOs36M')

#wks = sh.get_worksheet(0)
#db.set('pdt', [])#pdt = []
wksList = sh.worksheets()
shopList = [x.title for x in wksList[1:]]
#db.set('wks', None)#wks = None
#db.set('shopSel', None)#shopSel = None 
#db.set('tRow', None)#tRow = None
#BASE_DIR = os.path.dirname(os.path.dirname(__file__))
#PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

picture = ["https://i.imgur.com/qKkE2bj.jpg",
           "https://i.imgur.com/QjMLPmx.jpg",
           "https://i.imgur.com/HefBo5o.jpg",
           "https://i.imgur.com/AjxWcuY.jpg"
           ]
###global init___<<<

def get_tRow(wks):
    return int(wks.acell('A1').value)
   
def get_sts():
    content = 'Now: \n\n'
    content+= 'wksList: {}\n'.format(wksList)
    #content+= 'wks: {}\n'.format(db.get('wks'))
    content+= 'shopSel: {}\n'.format(db.get('shopSel'))
    content+= 'status: {}\n'.format(db.get('status'))
    return content
        
def get_shops():
    content = '店家名單:'
    for s in shopList:
        content += '\n'+s 
    return content

def get_menu(wks):
    tRow = get_tRow(wks)
    all_cells = wks.range('A1:B{}'.format(tRow+1))

    pdt = []
    for c in all_cells:
        if c.col == 1:
            pdt.append([c.value])
        elif c.col == 2:
            pdt[c.row-1].append(c.value)
    return pdt

def set_shop(dbdShop):
    shop = dbdShop[3:].strip()

    if shop in shopList:
        content = '訂購店家: {}\n'.format(shop)
        db.set('shopSel', shop)
        wks = sh.worksheet("{}".format(db.get('shopSel')))
        pdt = get_menu(wks)
        for i in pdt:
            content += '{}: {}\n'.format(i[0], i[1])
        db.set('status', 'o')#open
    else:
        content = '找不到店家: \"{}\"'.format(shop)
        content+= '\n請輸入店家名稱:'
    return content

def get_user(uid):
    profile = line_bot_api.get_profile(uid)
    content = ''

    content+= str(profile.display_name)+'\n'
    content+= str(profile.user_id)+'\n'
    content+= str(profile.picture_url)+'\n'
    content+= str(profile.status_message)

    print(profile.display_name)
    print(profile.user_id)
    print(profile.picture_url)
    print(profile.status_message)

    return content

def add_1Row(event):
    wks = sh.worksheet("{}".format(db.get('shopSel')))
    tRow = get_tRow(wks)
    rowData = [tRow+1, 'aaa', 'bbb', 'ccc']
    for i in range(len(rowData)):
        db.get('wks').update_cell(tRow+2, i+1, rowData[i])


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    # print("body:",body)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

def default_factory():
    return 'not command'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # cmd = defaultdict(default_factory, command)
    event.message.text = event.message.text.strip()
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)
    if event.message.text == "add1":
        add_1Row(event)
        content = "add_1Row ok"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif event.message.text.lower() == "getu":
        print(event)
        content = get_user(event.source.user_id)#
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif event.message.text.lower() == "sts":
        content = get_sts()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif event.message.text.lower() == "dbd":
        content = get_shops()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif re.match("dbd", event.message.text, flags=re.IGNORECASE):
        content = set_shop(event.message.text)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif event.message.text == "收單":
        db.set('status', 'c')#closed
        content = '收單 done'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))  
    else:
        buttons_template = TemplateSendMessage(
            alt_text='Buttons template',
            template=ButtonsTemplate(
                title='選擇服務',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/qKkE2bj.jpg',
                actions=[
                    MessageTemplateAction(
                        label='PTT 表特版 近期大於 10 推的文章',
                        text='PTT 表特版 近期大於 10 推的文章'
                    ),
                    MessageTemplateAction(
                        label='安安妳好',
                        text='ananUgood'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
    return 0


if __name__ == '__main__':
    app.run()
