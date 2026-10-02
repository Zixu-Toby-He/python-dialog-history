# -*- coding: utf-8 -*-
"""基础工具模块：负责定位数据目录、以 UTF-8（无 BOM）方式读写文本与 JSON。

本模块不包含任何界面逻辑，只做“找文件”和“读文件”两件事，
以便界面代码在数据缺失时统一走回退方案，而不会因为缺文件直接崩溃。
"""

import os
import json


# 驱动库目录本身的绝对路径
驱动库目录 = os.path.dirname(os.path.abspath(__file__))
# 项目根目录（即 main.py 所在目录）
项目根目录 = os.path.dirname(驱动库目录)
# 默认的数据根目录
默认数据目录 = os.path.join(项目根目录, "数据文件")
# 元数据文件的默认文件名
元数据文件名 = "聊天记录元数据.json"


def 取得数据目录(数据目录=None):
	"""返回本次实际使用的数据根目录。

	参数为 None 时使用项目自带的“数据文件”目录；
	参数为其它路径时以调用方给出的路径为准，方便把记录搬到别处。
	"""
	if 数据目录:
		return 数据目录
	else:
		return 默认数据目录


def 读取文本(路径):
	"""以 UTF-8（无 BOM）方式读取文本文件。

	读取失败时返回 None，由调用方决定回退内容；
	本函数不抛出异常、不打印错误，保证界面不会因缺文件而退出。
	"""
	if not 路径:
		return None
	if not os.path.isfile(路径):
		return None
	try:
		with open(路径, "r", encoding="utf-8") as 文件对象:
			内容 = 文件对象.read()
	except (OSError, UnicodeDecodeError):
		return None
	# 个别文件可能带了 BOM，这里手动去掉，避免 JSON 解析失败
	if 内容.startswith("\ufeff"):
		内容 = 内容[1:]
	return 内容


def 读取JSON(路径):
	"""以 UTF-8 方式读取 JSON 文件，失败时返回 None。"""
	文本 = 读取文本(路径)
	if 文本 is None:
		return None
	try:
		数据 = json.loads(文本)
	except (json.JSONDecodeError, ValueError):
		return None
	else:
		return 数据


def 读取聊天记录元数据(数据目录=None, 元数据路径=None):
	"""读取聊天记录元数据，失败时返回空字典。

	界面对空字典会显示“没有可显示的聊天记录”，不会弹出异常。
	"""
	路径 = 元数据路径
	if not 路径:
		路径 = os.path.join(取得数据目录(数据目录), 元数据文件名)
	数据 = 读取JSON(路径)
	if isinstance(数据, dict):
		return 数据
	else:
		return {}


def 查找目录内文件(目录, 文件名):
	"""在指定目录内查找文件，找不到时返回 None。"""
	if not 目录 or not 文件名:
		return None
	路径 = os.path.join(目录, str(文件名))
	if os.path.isfile(路径):
		return 路径
	else:
		return None
