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
from bs4 import BeautifulSoup as bs
from collections import defaultdict
from collections import namedtuple
from flask import Flask, request, abort
from requests.packages.urllib3.exceptions import InsecureRequestWarning
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
from selenium import webdriver

phantomjs_path = os.getenv('PHANTOMJS_PATH', None)
phantomjs_path+="/phantomjs"


# 禁用安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

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

def gen_url(c, s):
    if c == 0:
        url = 'http://www.vscinemas.com.tw/visPrintShowTimes.aspx?cid={}&visLang=2'.format(s)
    elif c==1:
        url = 'https://tw.movies.yahoo.com/theater_result.html/id={}'.format(s)
    else:
        url = 'http://www.vscinemas.com.tw/visPrintShowTimes.aspx?cid={}&visLang=2'.format(s)
    return url

def get_cinema(soup):
    cinema = []
    for item in soup.select('option'):
        if re.search('新竹', item.text):
            if not re.search('gold', item.text, flags=re.IGNORECASE):
                print(item['value'])
                print(item.text)
                cinema.append([item['value'], item.text])
    return cinema

def vieshow():
    rs = requests.session()
    res = rs.get(gen_url(0, ''), verify=False)
    soup = bs(res.text, 'html.parser')
    cinema = get_cinema(soup)
    content = ''
    
    for c in cinema:
        content+=c[1]+'\n'
        res = rs.get(gen_url(0, c[0]), verify=False)
        soup = bs(res.text, 'html.parser')
        for item in soup.select('.PrintShowTimesFilm'):
            content+=item.text+'\n'
            #print(item.text)
        content+='--\n'
        #print('--')
    return content

def vieshow_time(m):
    m = m[2:].strip()#'冠軍'#input('想看哪一部:')
    if (not m) or m.isdigit():
        return '請加上電影關鍵字\n'
    
    rs = requests.session()
    res = rs.get(gen_url(0, ''), verify=False)
    soup = bs(res.text, 'html.parser')
    cinema = get_cinema(soup)
    print (cinema)
    content = ''
    
    for c in cinema:
        res = rs.get(gen_url(0, c[0]), verify=False)
        soup = bs(res.text, 'html.parser')
        found = 0
        for item in soup.select('table'):#[1:]:
            for _ in item.select('.PrintShowTimesFilm'):
                #print(_.text)
                if re.search(m, _.text):
                    if found==0:
                        content+=c[1]+'\n'
                    found = 1
                    content+=_.text+'\n'
                    for i,x in enumerate(item.select('.PrintShowTimesDay')):
                        content+=item.select('.PrintShowTimesDay')[i].text+' '
                        content+=item.select('.PrintShowTimesSession')[i].text+'\n'
    if found:
        content+='--\n'
    else:
        content+=c[1]+'找不到: \"{}\"\n--\n'.format(m)
    return content

def hhst():
    content = ''
    content+='欣欣秀泰影城'+'\n'
    rs = requests.session()
    res = rs.get(gen_url(1, 30), verify=False)
    soup = bs(res.text, 'html.parser')

    for item in soup.select('.item.clearfix'):#[1:]:
        for _ in item.select('h4'):
            if re.search('電話|地址', _.text):
                continue
            else:
                content+=_.text+'\n'
    return content

def hhst_time(m):
    m = m[2:].strip()#'冠軍'#input('想看哪一部:')
    if (not m) or m.isdigit():
        return '請加上電影關鍵字\n'
    content = ''
    cinema = '欣欣秀泰影城'
    rs = requests.session()
    res = rs.get(gen_url(1, 30), verify=False)
    soup = bs(res.text, 'html.parser')
    found = 0
    for item in soup.select('.item.clearfix'):#[1:]:
        if re.search(m, item.text):
            if found==0:
                content+=cinema+'\n'
            found = 1
            for _ in item.select('h4'):
                content+=_.text+'\n'
            for _ in item.select('.mtcontainer'):
                for __ in _.select('.tmt'):
                    content+=__.text+'\n'
    if found:
        content+='--\n'
    else:
        content+=cinema+'找不到: \"{}\"\n--\n'.format(m)
    return content

def get_js(url):
    driver = webdriver.PhantomJS(executable_path=phantomjs_path)  # PhantomJs
    driver.get(url)  # 輸入範例網址，交給瀏覽器 
    pageSource = driver.page_source  # 取得網頁原始碼
    print(pageSource)
    driver.close()  # 關閉瀏覽器
    return pageSource

def taipei_bus(wayIn):
    print(phantomjs_path)
    way=0 if wayIn=="回家" else 1

    url = 'http://www.e-bus.taipei.gov.tw/newmap/Tw/Map?rid=10842&sec={}'.format(way)
    pageSource = get_js(url)
    soup = bs(pageSource, 'html.parser')

    stopName=[]
    eta=[]
    for c in soup.select('.stopName'):
        stopName.append(c.text)
    for c in soup.select('.eta'):
        eta.append(c.text)
    
    content = ''
    for i,x in enumerate(stopName):
        print (stopName[i],eta[i])
        content+=stopName[i]+':'+eta[i]+'\n'
    return content

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
    if event.message.text.lower() == "vs":
        content = vieshow()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif re.match("vs", event.message.text, flags=re.IGNORECASE):
        content = vieshow_time(event.message.text)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif event.message.text.lower() == "st":
        content = hhst()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif re.match("st", event.message.text, flags=re.IGNORECASE):
        content = hhst_time(event.message.text)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    elif event.message.text == "上班" or event.message.text == "回家":
        content = taipei_bus(event.message.text)
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
        pass
        '''
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
        '''
    return 0


if __name__ == '__main__':
    app.run()
