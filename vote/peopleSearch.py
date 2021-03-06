#! /usr/local/bin/python3

import re
import sys
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def open_browser():
    return webdriver.Chrome()     # needs chromedriver in $PATH


# Prerequisites:
# A browser has opened in debug mode as, for example:
#   $ "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
#       --remote-debugging-port=9014 --user-data-dir=/tmp/chrome
# then login People Search from SSO, that is why we need attach mode


def attach_browser():
    options = webdriver.ChromeOptions()
    options.debugger_address = 'localhost:9014'
    driver = webdriver.Chrome(options=options)
    return driver


def people_search(name, driver):
    known = {
        "张黎钦-粥客": "liqin.zhang",
        "陈慧": "hui.x.chen",
        "申旭刚": "xugang.shen",
        "李向东": "xiangdong.li",
        "时培植": "pierce.shi",
        "张广权": "guang.quan.zhang",
        "张黎明": "liming.z.zhang",
        "李若霖": "ruolin.li",
        "张亮": "liang.z.zhang",
        "张雁飞": "yan.fei.zhang",
        "史玉龙": "yu.long.shi",
        "金永顺": "jim.jin",
        "曹长征": "charles.cao",
        "何冠群": "junger.he",
        "刘翔德": "steven.liu"
    }

    if name in known:
        name = known[name]
    else:
        # regex = re.compile(r'([a-zA-Z]+\.)?[a-zA-Z]+\.[a-zA-Z]+')
        regex = re.compile(r'([a-zA-Z]+(\.|-))?[a-zA-Z]+\.[a-zA-Z]{2,}')
        mo = regex.search(name)
        if mo is None:
            print('{}, Not a mail, ,'.format(name))
            return ()
        name = mo.group().lower()

    url = "https://people.oracle.com/apex/f?p=8000:1:101705649184588::::P1_SEARCH:"
    driver.get(url + name + "@oracle.com")
    delay = 5   # seconds
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'profile_main')))
        # print("Page is ready!")
    except TimeoutException:
        # print("{}, Retry, ,".format(name))
        links = driver.find_elements_by_tag_name('a')
        for link in links:
            href = link.get_attribute('href')
            if href.endswith(name.lower()):
                # print(href)
                driver.get(href)
                try:
                    WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'profile_main')))
                except TimeoutException:
                    print("{}, Timeout, ,".format(name))
                    return ()
                break

    soup = BeautifulSoup(driver.page_source, 'lxml')
    try:
        phone = ''
        l = -11
        li = soup.find('li', class_=re.compile('p-DetailList-item--mobilephone'))
        # if li is None:
        #    li = soup.find('li', class_=re.compile('p-DetailList-item--workphone'))
        #    l = -8

        if li is not None:
            phone = re.sub('\D', '', li.find('a').getText())[l:]
        # else:
            # phone = str(abs(hash(name)) % (10 ** 9))    # use name hash code instead of

        ul = soup.find('ul', class_='p-UserBlocks p-UserBlocks--horizontal p-UserBlocks--managers')
        manager = ul.find('span', class_='p-UserBlock-name').getText()
        dt = soup.find('dt', text=re.compile('Cost Center'))
        cost_center = ''
        if dt is not None:
            sibling = dt.find_next_sibling()
            while sibling is not None and sibling.name != 'dd':
                sibling = sibling.find_next_sibling()
            cost_center = sibling.getText().strip().replace(',', '/')
        ul = soup.find('ul', class_='p-DetailList p-DetailList--stacked')
        city = ul.find('a').getText()
    except (AttributeError, NoSuchElementException) as err:
        print("{}, {}, ,".format(name, err))
        return ()
    people = (name, phone, manager, cost_center, city)
    return people

    # with open(name + '.html', "w") as f:
    #    f.write(driver.page_source)


def main():
    # people_search("xiao.ou.sun", driver)
    # people_search("junger.he", driver)

    if len(sys.argv) < 2:
        print('Usage: {} file'.format(sys.argv[0]))
        sys.exit(1)

    driver = attach_browser()
    peoples = []
    file = open(sys.argv[1])
    try:
        for name in file.readlines():
            name = name.strip()
            if not name:
                continue
            people = people_search(name, driver)
            if people:
                peoples.append(people)
            # time.sleep(1)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')

    peoples.sort(key=lambda e: [e[3], e[2], e[4]])
    for people in peoples:
        print('{}, {}, {}, {}, {}'.format(people[0], people[1], people[3], people[4], people[2]))
    driver.quit()


if __name__ == "__main__":
    main()
