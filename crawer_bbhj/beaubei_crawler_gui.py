# -*- coding: utf-8 -*-
import sys
import os
import sqlite3
import json
import time
from datetime import datetime
import requests

from PySide6.QtWidgets import QApplication, QWidget, QTableWidgetItem
from PySide6.QtGui import QIcon
from PySide6.QtCore import *

# 原有 UI 文件（基于 PySide2 生成，通常兼容）
from mainwin import *
from sqlwin import *

# 新数据库文件名
NEW_DB_FILE = "bbhj_under18.sql"
conn = None
c = None

class sqlshow(QWidget, Ui_Widget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        sql = 'SELECT id,姓名,性别,生日,失踪时间,失踪类型,失踪地址,注册时间,missing_age FROM 宝贝回家未成年'
        data = c.execute(sql)
        n = 0
        self.tableWidget.setColumnCount(9)
        self.tableWidget.setHorizontalHeaderLabels(["ID","姓名","性别","生日","失踪时间","失踪类型","失踪地址","注册时间","失踪时年龄"])
        for i in data:
            self.tableWidget.insertRow(n)
            m = 0
            for j in i:
                item = QTableWidgetItem()
                item.setText(str(j))
                item.setTextAlignment(Qt.AlignCenter)
                self.tableWidget.setItem(n, m, item)
                item.setFlags(Qt.ItemIsEnabled)
                m += 1
            n += 1

class Mainwindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.pushButton_2.clicked.connect(self.runing)
        self.ui.progressBar.setValue(0)
        self.ui.pushButton.clicked.connect(self.sqllite)

    def sqllite(self):
        self.sqll = sqlshow()
        self.sqll.showMaximized()

    def runing(self):
        self.thread_1 = Worker()
        self.thread_1.begin = int(self.ui.lineEdit_2.text())
        # 如果结束页为空或无效，设为一个较大的数（爬取直到无数据）
        try:
            end_val = int(self.ui.lineEdit_3.text())
        except:
            end_val = 9999
        self.thread_1.end = end_val
        x = self.ui.comboBox.currentText()
        self.thread_1.index = self.indexs(x)
        self.thread_1.t = self.ui.lineEdit_4.text()
        self.ui.progressBar.setRange(0, self.thread_1.end - self.thread_1.begin)
        self.ui.textBrowser.append(f'开始爬取 {x}，从第 {self.thread_1.begin} 页开始，间隔 {self.thread_1.t} 秒')
        self.thread_1.text.connect(self.uptextBrowser)
        self.thread_1.Value.connect(self.upprogressBar)
        self.thread_1.start()

    def indexs(self, s):
        if s == '全部':
            return 0
        elif s == '家寻宝贝':
            return 1
        elif s == '宝贝寻家':
            return 2
        elif s == '其他寻人':
            return 4
        elif s == '海外寻亲':
            return 5
        elif s == '烈士寻根':
            return 6
        else:
            return 0

    def upprogressBar(self, i):
        self.ui.progressBar.setValue(i)

    def uptextBrowser(self, i):
        self.ui.textBrowser.append(i)

class Worker(QThread):
    Value = Signal(int)
    text = Signal(str)
    begin = 0
    end = 0
    index = 0
    t = 0

    def __init__(self):
        super(Worker, self).__init__()

    def run(self):
        start_time = time.time()
        wins.ui.pushButton.setEnabled(False)
        wins.ui.pushButton_2.setEnabled(False)

        url = 'https://so.baobeihuijia.com/api/search/contents/actions/list'
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        page = self.begin
        total_inserted = 0
        while page < self.end:
            self.text.emit(f'正在爬取第 {page} 页')
            payload = {
                "siteId": 1,
                "channelId": 1,
                "page": page,
                "searchType": self.index,
                "searchText": "",
                "isAdvanced": False,
                "checkedStates": [],
                "sex": "9",
                "isPhotos": False,
                "isSample": False,
                "isReport": False,
                "isDna": False,
                "birthdayRange": None,
                "lostdayRange": None,
                "adddayRange": None,
                "lostAddressCode": None,
                "liveAddressCode": None,
                "lostAddress": None,
                "liveAddress": None,
                "lowerHeight": 0,
                "higherHeight": 0
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                data_json = resp.json()
                page_contents = data_json.get('pageContents', [])
            except Exception as e:
                self.text.emit(f'请求失败: {e}')
                break

            if not page_contents:
                self.text.emit(f'第 {page} 页无数据，爬取完成')
                break

            for item in page_contents:
                sex = '男' if item.get('sex') else '女'
                lost_type = item.get('lostPass', '')
                lost_addr = item.get('lostAddress', '')
                add_date = item.get('addDate', '')
                birth = item.get('birthDay', '')
                lost_day = item.get('lostDay', '')

                # 计算失踪时周岁年龄
                missing_age = None
                if birth and lost_day and '-' in birth and '-' in lost_day:
                    try:
                        b_date = datetime.strptime(birth.split()[0], '%Y-%m-%d')
                        l_date = datetime.strptime(lost_day.split()[0], '%Y-%m-%d')
                        age = l_date.year - b_date.year
                        if (l_date.month, l_date.day) < (b_date.month, b_date.day):
                            age -= 1
                        if age >= 0:
                            missing_age = age
                    except:
                        pass

                # 只保留失踪时未成年的记录
                if missing_age is not None and missing_age < 18:
                    sql = '''
                        INSERT OR REPLACE INTO 宝贝回家未成年 
                        (id, 姓名, 性别, 生日, 失踪类型, 失踪地址, 失踪时间, 注册时间, missing_age)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    '''
                    c.execute(sql, (
                        item['publishId'],
                        item['name'],
                        sex,
                        birth,
                        lost_type,
                        lost_addr,
                        lost_day,
                        add_date,
                        missing_age
                    ))
                    total_inserted += 1

            conn.commit()
            self.text.emit(f'第 {page} 页完成，已累计插入未成年记录 {total_inserted} 条')
            self.Value.emit(page - self.begin + 1)

            # 间隔
            try:
                time.sleep(float(self.t))
            except:
                time.sleep(1)

            page += 1

        self.text.emit(f'爬取结束，共插入 {total_inserted} 条未成年记录，耗时 {time.time() - start_time:.2f} 秒')
        wins.ui.pushButton.setEnabled(True)
        wins.ui.pushButton_2.setEnabled(True)

def init_new_database():
    global conn, c
    # 如果新数据库文件已存在，删除后重建（确保全新）
    if os.path.exists(NEW_DB_FILE):
        os.remove(NEW_DB_FILE)
    conn = sqlite3.connect(NEW_DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE 宝贝回家未成年 (
            id INTEGER PRIMARY KEY,
            姓名 TEXT,
            性别 TEXT,
            生日 TEXT,
            失踪类型 TEXT,
            失踪地址 TEXT,
            失踪时间 TEXT,
            注册时间 TEXT,
            missing_age INTEGER
        )
    ''')
    conn.commit()
    print(f"新数据库 {NEW_DB_FILE} 创建成功")

if __name__ == '__main__':
    app = QApplication([])
    app.setWindowIcon(QIcon("./img/hj.ico"))
    init_new_database()
    wins = Mainwindow()
    wins.show()
    wins.ui.textBrowser.append(f'新建数据库 {NEW_DB_FILE} 成功，开始爬取未成年数据')
    sys.exit(app.exec())