# -*- coding: utf-8 -*-
import time

import cv2
import scrapy
import requests
import numpy as np
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from scrapy.http.cookies import CookieJar


cookie_jar = CookieJar()


class QidianSpider(scrapy.Spider):
    name = 'qidian'
    allowed_domains = ['www.qidian.com', 'book.qidian.com']
    start_urls = ['https://www.qidian.com/']
    headers = {
        # 'HOST': 'www.qidian.com',
        # "Referer": "https://www.qidian.com/",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36'
    }

    custom_settings = {
        'ALLOW_REDIRECTS': False,
        'HTTPERROR_ALLOWED_CODES': [302,301],
        'DOWNLOADER_MIDDLEWARES ':{
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        }
    }

    chrome_driver = r"C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    browser = webdriver.Chrome(chrome_driver, options=options)
    wait = WebDriverWait(browser, 10)
    cookies = {}

    def parse(self, response):
        script = """
        function main(splash)
            splash:init_cookies(splash.args.cookies)
            assert(splash:go{
                splash.args.url,
                headers=splash.args.headers,
                http_method=splash.args.http_method,
                body=splash.args.body,
                })
            assert(splash:wait(0.5))

        local entries = splash:history()
        local last_response = entries[#entries].response
        return {
          url = splash:url(),
          headers = last_response.headers,
          http_status = last_response.status,
          cookies = splash:get_cookies(),
          html = splash:html(),
        }
        end
        """

        yield scrapy.Request('https://book.qidian.com/info/1015762599', callback=self.parse_detail, headers=self.headers, cookies=self.cookies)

    def parse_detail(self, response):
        yield scrapy.Request('https://my.qidian.com/bookcase', headers=self.headers, callback=self.check_login, dont_filter=True)

    def check_login(self, response):
        print(response.url)
        pass

    def parse_with_out_login(self, response):
        pass

    def start_requests(self):
        """
        破解入口
        :return:
        """
        self.open()
        if self.password_error():
            # self.browser.quit()
            return {
                'status': 2,
                'content': '用户名或密码错误'
            }
        # 如果不需要验证码直接登录成功
        if self.login_successfully():
            self.cookies = self.get_cookies()
            self.browser.quit()
            return [scrapy.Request('https://my.qidian.com', cookies=self.cookies, headers=self.headers)]
        self.crack()
        if self.login_successfully():
            self.cookies = self.get_cookies()
            self.browser.quit()
            return [scrapy.Request('https://my.qidian.com', cookies=self.cookies, headers=self.headers)]
        else:
            self.browser.quit()
            return [scrapy.Request(self.start_urls[0], callback=self.parse_with_out_login, headers=self.headers)]

    def open(self):
        """
        打开网页输入用户名密码并点击
        :return: None
        """
        login_url = 'https://passport.qidian.com/'
        self.browser.delete_all_cookies()
        self.browser.get(login_url)
        username_input = self.wait.until(
            EC.element_to_be_clickable((By.ID, 'username'))
        )
        password_input = self.wait.until(
            EC.element_to_be_clickable((By.ID, 'password'))
        )
        auto_login_checkbox = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, '//div[@class="auto-login-box cf"]/label'))
        )
        username_input.send_keys('18178007095')
        password_input.send_keys('Qidian911016')
        auto_login_checkbox.click()
        submit_btn = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, '//a[@class="red-btn go-login btnLogin login-button"]'))
        )
        submit_btn.click()

    def password_error(self):
        """
        判断是否密码错误
        :return:
        """
        try:
            return WebDriverWait(self.browser, 5).until(
                EC.text_to_be_present_in_element((By.XPATH, '//div[@class="error-tip"]'), '您输入的账号或密码不正确，请重新输入'))
        except TimeoutException:
            return False

    def login_successfully(self):
        """
        判断是否登录成功
        :return:
        """
        try:
            return bool(
                WebDriverWait(self.browser, 5).until(
                    EC.text_to_be_present_in_element((By.ID, 'exit-btn'), '退出')
                ))
        except TimeoutException:
            return False

    def get_distance(self):
        bkg, blk = self.get_image()
        block = cv2.imread(blk, 0)
        template = cv2.imread(bkg, 0)
        cv2.imwrite('template.jpg', template)
        cv2.imwrite('block.jpg', block)
        block = cv2.imread('block.jpg')
        block = cv2.cvtColor(block, cv2.COLOR_BGR2GRAY)
        block = abs(255 - block)
        cv2.imwrite('block.jpg', block)
        block = cv2.imread('block.jpg')
        template = cv2.imread('template.jpg')
        result = cv2.matchTemplate(block, template, cv2.TM_CCOEFF_NORMED)
        x, y = np.unravel_index(result.argmax(), result.shape)
        # 这里就是下图中的绿色框框
        cv2.rectangle(template, (y + 20, x + 20), (y + 136 - 25, x + 136 - 25), (7, 249, 151), 2)
        # 之所以加20的原因是滑块的四周存在白色填充
        print('x坐标为：%d' % (y + 20))
        try:
            if self.browser.find_element_by_id('tcaptcha_note').text == '请控制拼图块对齐缺口':
                elem = self.browser.find_element_by_xpath('//div[@id="reload"]/div')
                elem.click()
                time.sleep(1)
                bkg, blk = self.get_image()
                y, template = self.get_distance(bkg, blk)
            elif self.browser.find_element_by_id('tcaptcha_note').text == '这题有点难呢，已为您更换题目':
                bkg, blk = self.get_image()
                y, template = self.get_distance(bkg, blk)
        except TimeoutException:
            pass
        if y + 20 < 450:
            elem = self.browser.find_element_by_xpath('//div[@id="reload"]/div')
            elem.click()
            time.sleep(1)
            bkg, blk = self.get_image()
            y, template = self.get_distance(bkg, blk)
        return y, template

    def get_tracks(self, distance, dis):
        v = 0
        t = 0.3
        # 保存0.3内的位移
        tracks = []
        current = 0
        mid = distance * 4 / 5
        while current <= dis:
            if current < mid:
                a = 2
            else:
                a = -3
            v0 = v
            s = v0 * t + 0.5 * a * (t ** 2)
            current += s
            tracks.append(round(s))
            v = v0 + a * t
        return tracks

    def crack(self):
        distance, template = self.get_distance()
        double_distance = int((distance - 70 + 20) / 2)
        tracks = self.get_tracks(distance, double_distance)
        tracks.append(-(sum(tracks) - double_distance))
        print('tracks: ', tracks)
        slider_btn = self.browser.find_element_by_id('tcaptcha_drag_thumb')
        ActionChains(self.browser).click_and_hold(on_element=slider_btn).perform()
        for track in tracks:
            ActionChains(self.browser).move_by_offset(xoffset=track, yoffset=0).perform()
        time.sleep(0.5)
        ActionChains(self.browser).release(on_element=slider_btn).perform()
        try:
            print('需要输入手机验证码')
            temp = WebDriverWait(self.browser, 5).until(
                EC.element_to_be_clickable((By.ID, 'sendPhoneMsgByKey')))
            send_code_btn = self.browser.find_element_by_id('sendPhoneMsgByKey')
            send_code_btn.click()
            code = input('输入手机验证码')
            code_input = self.browser.find_element_by_xpath('//div[@class="risk-code phone-mode"]/dl/dd/input')
            code_input.send_keys(code)
            submit_btn = self.browser.find_element_by_id('riskSendPhoneMsgSubmit')
            submit_btn.click()
        except TimeoutException:
            return False

    def get_cookies(self):
        """
        获取Cookies
        :return:
        """
        return self.browser.get_cookies()

    def get_image(self):
        try:
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'}
            self.browser.switch_to.frame('tcaptcha_iframe')
            image1 = self.browser.find_element_by_id('slideBg').get_attribute('src')
            image2 = self.browser.find_element_by_id('slideBlock').get_attribute('src')
            html1 = requests.get(image1, headers=headers)
            with open('slide_bkg.png', 'wb') as file:
                file.write(html1.content)
            html2 = requests.get(image2, headers=headers)
            with open('slide_block.png', 'wb') as file:
                file.write(html2.content)
            return 'slide_bkg.png', 'slide_block.png'
        except TimeoutException:
            return False