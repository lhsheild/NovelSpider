#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2019/11/17 10:42 
# @Author : Ahrist 
# @Site :  
# @File : main.py 
# @Software: PyCharm

import os
import sys

from scrapy.cmdline import execute

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
execute(["scrapy", 'crawl', 'qidian'])