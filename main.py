# -*- coding: utf-8 -*-
import requests
import pickle
import base64
import random
import time
import re
import logging
import sys
import os
from aip import AipOcr
from PIL import Image
from config import user_id,user_psw,APP_ID,API_KEY,SECRET_KEY

if sys.getdefaultencoding() != 'utf-8':
    reload(sys)
    sys.setdefaultencoding('utf-8')

# 日志配置
FILE = os.path.abspath(os.path.dirname(__file__))
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename=os.path.join(FILE,'log.txt'),level=logging.INFO, format=LOG_FORMAT)

# 初始化AipFace对象
client = AipOcr(APP_ID, API_KEY, SECRET_KEY)

# 定义session
session = requests.session()

# session信息本地保存路径
path = os.path.join(FILE,"session",user_id)

flag = False

def str_time(pattern='%Y-%m-%d %H:%M:%S'):
    return time.strftime(pattern, time.localtime(time.time()))

def encrypt(str1):
    key = 'tPhCyUsKpXlHsEgSyHoEkLdQpLkOsLcYhErFkWxJsFeVhLiQrHqFbYbNyEvClEwUfQmEgUnEfJiHfPtLuEdDbIiIqUqLoTzOmYqA'
    key_login = '95a1446a7120e4af5c0c8878abb7e6d2'
    string = base64.b64encode(str1.encode("utf-8"))
    key_len = len(key)
    code = ''
    newcode = ''
    for i in range(0,len(string)):
        k = i % key_len
        code += chr(string[i]^ord(key[k]))
    code = str(base64.b64encode(code.encode("utf-8")), encoding = "utf8")
    for j in range(0,len(code)):
        t1 = code[j]
        t2 = key[j]
        newcode += t1+t2
    newcode = newcode.replace('/',"6666cd76f96956469e7be39d750cc7d9")
    newcode = newcode.replace('=', "43ec3e5dee6e706af7766fffea512721")
    newcode = newcode.replace('+', "26b17225b626fb9238849fd60eabdf60")
    newcode = key_login + newcode
    return newcode

def get_code():
    code_url = "http://yun.zjer.cn/index.php?r=portal/Vcode/GetNewCode"
    # 获取并保存验证码图片
    response = requests.get(url=code_url)
    if response.content:
        passCode = response.json()['passCode']
        image_data = response.json()['imageinfo']
    else:
        return None,None
    data = image_data.split(',')[1]
    image_data = base64.b64decode(data)
    img_path = os.path.join(FILE, "img", "1.png")
    img_1_path = os.path.join(FILE, "img", "split_num_1.png")
    img_operator_path = os.path.join(FILE, "img", "split_operator.png")
    img_2_path = os.path.join(FILE, "img", "split_num_2.png")
    with open(img_path, 'wb') as f:
        f.write(image_data)

    im = Image.open(img_path)
    # 图片的宽度和高度
    img_size = im.size

    # 第1块
    h = img_size[1]
    x = 0
    y = 0
    region = im.crop((x, y, x + 26, y + h))
    region.save(img_1_path)

    # 第2块
    x = 27
    region = im.crop((x, y, x + 14, y + h))
    region.save(img_operator_path)

    # 第3块
    x = 41
    region = im.crop((x, y, x + 26, y + h))
    region.save(img_2_path)

    # 读取图片
    def get_file_content(filePath):
        with open(filePath, 'rb') as fp:
            return fp.read()
    image_first = get_file_content(img_1_path)
    image_second = get_file_content(img_2_path)
    # 调用高精度版文字识别, 图片为本地图片
    options = {}
    options["language_type"] = "ENG"

    res = client.basicAccurate(image_first,options)  #识别4个数字，即原图的4个数字
    extract_data_first = res['words_result'][0]['words']

    res = client.basicAccurate(image_second,options)  #识别4个数字，即原图的4个数字
    extract_data_second = res['words_result'][0]['words']

    num_one = int(re.sub(r'[^0-9]+', '', extract_data_first))
    num_two = int(re.sub(r'[^0-9]+', '', extract_data_second))
    answer = num_one+num_two
    return passCode,answer

def login(user_id,user_psw,passCode,answer,session,path):
    # 登录信息
    login_url = 'http://yun.zjer.cn/index.php?r=portal/user/loginNew'

    userId = encrypt(user_id)
    userPsw = encrypt(user_psw)
    form_data = {
        'userId': userId,
        'userPsw': userPsw,
        'remember': '1',
        'vaildata': passCode,
        'valCode': answer,
        'service': ''
    }

    # 设置请求头
    req_header = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    }

    # 使用session发起请求
    response = session.post(url=login_url, headers=req_header, data=form_data)
    if response.content:
        statusCode = response.json()['code']
        if statusCode == "000000":
            mv_url = response.json()['url']
            session.get(url=mv_url)
            homepage_url = "http://yun.zjer.cn/index.php?r=center/person/index"
            response = session.get(url=homepage_url)
            if "登录" in response.text:
                statusCode = "-1"
                logging.info(str_time("%H%M") + user_id + "登录失败，请排查错误原因")
            else:
                logging.info(str_time("%H%M") + user_id + "获取session成功")
                with open(path, 'wb') as f:
                    pickle.dump(session.cookies, f)
        else:
            message = response.json()['message']
            logging.info(str_time("%H%M") + user_id + "登录失败，错误代码：" + statusCode + " 错误信息:" + message)
        return statusCode,session
    else:
        return "-1",session

def get_score(session):
    score_one_url = "http://ke.zjer.cn/index.php?r=curricula/syncourse/play&kcid=308270&ksid=1557196148"
    response = session.get(url=score_one_url, timeout=5)
    if "万物互联01" in response.text:
        logging.info(str_time("%H%M") + user_id + "任务一完成")

    delay_time = random.randint(0,3)
    time.sleep(delay_time)
    while (True):
        try:
            ret_code = ""
            sid = 31000 + random.randint(0, 999)
            score_two_url = "http://yun.zjer.cn/space/index.php?r=space/person/visitor/index&sid=" + str(sid)
            response = session.get(url=score_two_url, timeout=5)
            time.sleep(1)
            if response.content:
                ret_code = response.json()['re1']['code']
            if ret_code == "000000":
                logging.info(str_time("%H%M") + user_id + "任务二完成")
                break
        except:
            continue

    delay_time = random.randint(0, 3)
    time.sleep(delay_time)
    score_third_url = "http://jdx.zjer.cn/index.php?r=studio/courselive/Livelist&sid=600061&tid=9525&aid=4043&xs_id=1&on_sale=1"
    response = session.get(url=score_third_url, timeout=5)
    if "温州市第二外国语学校高中地理基地校" in response.text:
        logging.info(str_time("%H%M") + user_id + "任务三完成")

    delay_time = random.randint(0, 3)
    time.sleep(delay_time)
    score_four_url_1 = "http://ms.zjer.cn/index.php?r=studio/live/livebackdetail&sid=824&id=3159&live_type=1"
    score_four_url_2 = "http://ms.zjer.cn/index.php?r=studio/live/livebackdetail&sid=603&id=2617&live_type=3"
    response1 = session.get(url=score_four_url_1, timeout=5)
    response2 = session.get(url=score_four_url_2, timeout=5)
    if "名师工作室头部" in response1.text and "名师工作室头部" in response2.text:
        logging.info(str_time("%H%M") + user_id + "任务四完成")

if not os.path.exists(path):
    flag = True
else:
    with open(path, 'rb') as f:
        session.cookies.update(pickle.load(f))

# 如果session失效则重新获取session
test_url = "http://yun.zjer.cn/index.php?r=center/person/index"
response = session.get(url=test_url,timeout=5)
if "登录" in response.text:
    flag = True

if flag:
    passCode, answer = get_code()
    if passCode == None:
        logging.info(str_time("%H%M") + user_id + "获取验证码失败")
        exit(1)
    statusCode,session = login(user_id,user_psw,passCode,answer,session,path)
    if statusCode != "000000":
        exit(1)

get_score(session)



