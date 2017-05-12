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
from bs4 import BeautifulSoup
from collections import defaultdict
from collections import namedtuple
from flask import Flask, request, abort
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

app = Flask(__name__)
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

def get_tRow():
    global tRow
    tRow = int(wks.acell('A1').value)
    return tRow

def add_1Row():
    global tRow
    tRow = get_tRow()
    rowData = [tRow+1, 'aaa', 'bbb', 'ccc']
    for i in range(len(rowData)):
        wks.update_cell(tRow+2, i+1, rowData[i])
        
def get_sts():
    global wksList, wks, shopSel, pdt
    content = 'Status Now: \n\n'
    content+= 'wksList: {}\n'.format(wksList)
    content+= 'wks: {}\n'.format(wks)
    content+= 'shopSel: {}\n'.format(shopSel)
    content+= 'pdt: {}\n'.format(pdt[:3])
    return content
        
def get_sh_tts():
    global shopList
    content = '店家名單:'
    for s in shopList:
        content += '\n'+s 
    return content

def get_menu():
    global wks, tRow, pdt
    tRow = int(wks.acell('A1').value)
    all_cells = wks.range('A1:B{}'.format(tRow+1))

    for c in all_cells:
        if c.col == 1:
            pdt.append([c.value])
        elif c.col == 2:
            pdt[c.row-1].append(c.value)
    return pdt

def set_shop(dbdShop):
    global wks, shopSel, pdt
    shop = dbdShop[3:].strip()
    if shop in shopList:
        content = '訂購店家: {}\n'.format(shop)
        shopSel = shop
        wks = sh.worksheet("{}".format(shopSel))
        get_menu()
        for i in pdt:
            content += '{}: {}\n'.format(i[0], i[1])
    else:
        content = '找不到店家: \"{}\"'.format(shop)
        content+= '\n請輸入店家名稱:'
    return content

###conn to google drive___<<<



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
    if event.message.text == "gtr":
        get_tRow()
        content = 'tRow = {}'.format(tRow)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    if event.message.text == "add1":
        add_1Row()
        content = "add_1Row ok"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    if event.message.text.lower() == "sts":
        content = get_sts()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    if event.message.text.lower() == "dbd":
        content = get_sh_tts()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif re.match("dbd", event.message.text, flags=re.IGNORECASE):
        content = set_shop(event.message.text)
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


"""
@code start
"""

###global init___>>>

auth_json_path = 'client_secret.json'
gss_scopes = ['https://spreadsheets.google.com/feeds']

gss_client = auth_gss_client(auth_json_path, gss_scopes)

#sheet = gss_client.open("Copy of Legislators 2017").sheet1
sh = gss_client.open_by_key('1nJHriicxQAZj5i_c8bWAY8OShp7OMLErsz6QKIOs36M')

#wks = sh.get_worksheet(0)
pdt = []
wksList = sh.worksheets()
shopList = [x.title for x in wksList[1:]]
wks = None
shopSel = None
tRow = None

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

picture = ["https://i.imgur.com/qKkE2bj.jpg",
           "https://i.imgur.com/QjMLPmx.jpg",
           "https://i.imgur.com/HefBo5o.jpg",
           "https://i.imgur.com/AjxWcuY.jpg"
           ]
###global init___<<<

if __name__ == '__main__':
    app.run()
