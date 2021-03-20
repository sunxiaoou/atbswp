#! /usr/bin/python3
# cp -p ~/Desktop/"`ls -lrt ~/Desktop/*.png | tail -1 | awk -F/ '{print $NF}'`" $name.png
# tesseract $name.png $name -l eng+chi_sim --psm 6; cat $name.txt
# mystocks.py --date=210312 yh yh_2323.88.png 2323.88
# mystocks.py --currency=hkd --exchange_rate=0.8384 --date=210312 hs hs_83088.38.png 83088.38
# mystocks.py --currency=usd --exchange_rate=6.5081 --date=210312 hs hs_17379.64.png 17379.64


import csv
import getopt
import re
import sys
from datetime import datetime
from pprint import pprint
from typing import List

import tesserocr
from PIL import Image

from save_to import save_to_spreadsheet, save_to_mongo


Stocks = {
    # A stocks
    '000858': ('五粮液', 3),
    '501046': ('财通福鑫', 3),
    '512170': ('医疗ETF', 2),
    '515170': ('食品饮料', 2),
    '600009': ('上海机场', 3),
    '600036': ('招商银行', 3),
    '600309': ('万华化学', 3),
    # HK stocks
    '00388': ('香港交易所', 3),
    '00700': ('腾讯控股', 3),
    '02840': ('SPDR金ETF', 2),
    '03033': ('南方恒生科技', 2),
    '03690': ('美团-W', 3),
    '07200': ('FL二南方恒指', 2),
    '09988': ('阿里巴巴-SW', 3),
    # US stocks
    'AAPL': ('苹果', 3),
    'AMZN': ('亚马逊', 3),
    'ARKG': ('ARK Genomic ETF', 3),
    'ARKK': ('ARK Innovation ETF', 3),
    'ARKW': ('ARK Web x.0 ETF', 3),
    'BABA': ('阿里巴巴', 3),
    'BILI': ('哔哩哔哩', 3),
    'GS':  ('高盛', 3),
    'MSFT': ('微软', 3),
    'PDD': ('拼多多', 3),
    'SPY': ('标普500指数ETF', 2)}


def usage_exit():
    print('Usage: {} --currency="rmb||hkd|usd" --exchange_rate=float --date=%y%m%d '
          '"yh||hs|ft" png|csv balance'.format(sys.argv[0]))
    sys.exit(1)


def get_options() -> dict:
    opts = args = []
    try:
        opts, args = getopt.getopt(sys.argv[1:], '', ['currency=', 'exchange_rate=', 'date='])
    except getopt.GetoptError as err:
        print(err)
        usage_exit()
    if len(args) < 3:
        usage_exit()

    if args[0] not in ['yh', 'hs', 'ft']:
        usage_exit()
    dic = {'platform': args[0],
           'datafile': args[1],
           'cash': float(args[2]),
           'currency': 'rmb',
           'exchange_rate': 1,
           'date': datetime.now().strftime('%y%m%d')}
    for opt, var in opts:
        if opt == '--currency' and var in ['rmb', 'hkd', 'usd']:
            dic['currency'] = var
        elif opt == '--exchange_rate':
            dic['exchange_rate'] = float(var)
        elif opt == '--date':
            dic['date'] = var
    return dic


def recognize_image(image_name: str) -> str:
    image = Image.open(image_name)
    """
    image = image.convert('L')
    new_size = tuple(2 * x for x in image.size)             # enlarge the image size
    image = image.resize(new_size, Image.ANTIALIAS)
    """
    # image.show()
    return tesserocr.image_to_text(image, lang='eng+chi_sim', psm=tesserocr.PSM.SINGLE_BLOCK)


def my_float(s: str, a: int) -> float:
    s = re.sub(',', '', s)
    if '.' not in s:
        s = s[: a] + '.' + s[a:]
    return float(s)


def print_grid(word1: str, word2: str, grid: List[List[int]]):
    row0 = ['\\', '\'\''] + [ch for ch in word1]
    print(', '.join(row0))
    w2 = ['\'\''] + list(word2)
    for i in range(len(w2)):
        print("{},  {}".format(w2[i], ', '.join([str(j) for j in grid[i]])))


def get_distance(source: str, target: str) -> int:
    n1, n2 = len(source), len(target)
    grid = [[0] * (n1 + 1) for _ in range(n2 + 1)]
    i = j = 0
    for i in range(1, n2 + 1):
        for j in range(1, n1 + 1):
            if target[i - 1] != source[j - 1]:
                grid[i][j] = max(grid[i - 1][j], grid[i][j - 1])
            else:
                grid[i][j] = grid[i - 1][j - 1] + 1
    # print_grid(source, target, grid)
    return grid[i][j]


def get_closest_code(code: str) -> str:
    return max(Stocks.keys(), key=lambda x: get_distance(code, x))


def verify(result: list):
    for i in result:
        if i['code'] != 'cash':
            if i['nav'] * i['volume'] != i['market_value']:
                print('market_value failed {} {}'.format(i, i['nav'] * i['volume']))
            if round((i['nav'] - i['cost']) * i['volume']) != round(i['hold_gain']):
                print('hold_gain failed {} {}'.format(i, (i['nav'] - i['cost']) * i['volume']))


def yinhe(image_file: str, cash: float, currency: str, exchange_rate: float, date: datetime) -> list:
    text = recognize_image(image_file)
    # print(text)
    dic = {
        'platform': '银河',
        'currency': currency,
        'exchange_rate': exchange_rate,
        'code': 'cash',
        'date': date,
        'name': '现金',
        'risk': 0,
        'market_value': cash,
        'hold_gain': 0,
        'mv_rmb': cash,
        'hg_rmb': 0,
        'nav': 1}
    result = [dic.copy()]
    for line in text.split('\n'):
        if line:
            line = re.sub('[,‘]', '', line)
            items = re.findall('[-+]?\d*\.?\d+', line)
            # print(items)
            if len(items) == 8:
                if items[0] not in Stocks:
                    items[0] = get_closest_code(items[0])
                dic = {
                    'platform': '银河',
                    'currency': currency,
                    'exchange_rate': exchange_rate,
                    'date': date,
                    'code': items[0],
                    'name': Stocks[items[0]][0],
                    'risk': Stocks[items[0]][1],
                    'volume': int(items[1]),
                    'market_value': my_float(items[5], -2),
                    'hold_gain': my_float(items[2], -2),
                    'mv_rmb': my_float(items[5], -2),
                    'hg_rmb': my_float(items[2], -2),
                    'nav': my_float(items[6], -3),
                    'cost': my_float(items[7], -3)}
                result.append(dic.copy())
    return result


def huasheng(image_file: str, cash: float, currency: str, exchange_rate: float, date: datetime) -> list:
    dic = {
        'platform': '华盛' + currency.upper(),
        'currency': currency,
        'exchange_rate': exchange_rate,
        'date': date,
        'code': 'cash',
        'name': '现金',
        'risk': 0,
        'hold_gain': 0,
        'market_value': cash,
        'mv_rmb': round(cash * exchange_rate, 2),
        'hg_rmb': 0,
        'nav': 1}
    result = [dic.copy()]

    text = recognize_image(image_file)
    # print(text)
    for line in text.split('\n'):
        if line:
            line = re.sub('[,‘]', '', line)
            items = re.findall('^[A-Za-z]{2,4}|[-+]?\d*\.?\d+', line)
            # print(items)
            if re.search(r'\w{2,4}', items[0]):
                items[0] = items[0].split()[0].upper()
                if items[0] in Stocks:
                    if len(items) == 9:         # remove digits in US stock's name
                        items.pop(1)
                    dic = {
                        'platform': '华盛' + currency.upper(),
                        'currency': currency,
                        'exchange_rate': exchange_rate,
                        'date': date,
                        'code': items[0],
                        'name': Stocks[items[0]][0],
                        'risk': Stocks[items[0]][1],
                        'volume': int(items[1]),
                        'market_value': float(items[7]),
                        'hold_gain': float(items[3]),
                        'mv_rmb': round(float(items[7]) * exchange_rate, 2),
                        'hg_rmb': round(float(items[3]) * exchange_rate, 2),
                        'cost': float(items[5]),
                        'nav': float(items[6])}
                    result.append(dic.copy())
    return result


def futu(csv_file: str, cash: float, currency: str, exchange_rate: float, date: datetime) -> list:
    dic = {
        'platform': '富途' + currency.upper(),
        'currency': currency,
        'exchange_rate': exchange_rate,
        'date': date,
        'code': 'cash',
        'name': '现金',
        'risk': 0,
        'hold_gain': 0,
        'market_value': cash,
        'mv_rmb': round(cash * exchange_rate, 2),
        'hg_rmb': 0,
        'nav': 1}
    result = [dic.copy()]
    try:
        with open(csv_file) as f:
            reader = csv.reader(f, delimiter='\t')
            rows = list(reader)
            rows.pop(0)
            for row in rows:
                dic = {
                    'platform': '富途' + currency.upper(),
                    'currency': currency,
                    'exchange_rate': exchange_rate,
                    'date': date,
                    'code': row[1],
                    'name': row[2],
                    'risk': 3,
                    'volume': int(row[3].split('@')[0]),
                    'market_value': my_float(row[5], -2),
                    'hold_gain': my_float(row[7], -2),
                    'mv_rmb': round(my_float(row[5], -2) * exchange_rate, 2),
                    'hg_rmb': round(my_float(row[7], -2) * exchange_rate, 2),
                    'cost': my_float(row[6], -4),
                    'nav': my_float(row[3].split('@')[1], -4)}
                result.append(dic.copy())
    except FileNotFoundError as e:
        print(e)

    return result


def main():
    platforms = {'yh': yinhe, 'hs': huasheng, 'ft': futu}
    options = get_options()

    result = platforms[options['platform']](options['datafile'],
                                            options['cash'],
                                            options['currency'],
                                            options['exchange_rate'],
                                            datetime.strptime(options['date'], '%y%m%d'))
    verify(result)
    # pprint(result)
    print(len(result))

    save_to_spreadsheet('finance.xlsx', options['date'], result)
    # save_to_mongo('mystocks', result)


if __name__ == "__main__":
    main()
