# -*- coding: utf-8 -*-
"""数据结构模块：把 JSON 描述转换成界面可以直接使用的对象。

任何来源（不同账户、不同对象、不同驱动软件）的记录都允许缺字段，
缺字段时统一走“(default)”占位数据，保证界面始终能显示出内容。
本模块只读取数据、不做任何修改，因此生成的对象可以放心地反复渲染。
"""

import os

from . import 基础工具


# 无法从“类型”字段判断时，用来推断附件种类的扩展名集合
图片扩展名集合 = {
	".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
	".ico", ".svg", ".tif", ".tiff", ".heic",
}
文本扩展名集合 = {
	".txt", ".md", ".markdown", ".json", ".log", ".csv", ".html",
	".htm", ".xml", ".yaml", ".yml", ".ini", ".py", ".c", ".h",
}
# 附件在本库内部的两种种类名称
种类_图片 = "图片"
种类_文本 = "文本"
# 占位数据使用的固定名称
默认用户名称 = "(default)"
默认图片附件名称 = "(default_fig)"
默认文本附件名称 = "(default_txt)"
# 元数据中表示“折叠同一发言人消息”的取值
折叠标记 = "折叠"
# 附件名称在显示时允许去掉的类型前缀
类型前缀列表 = ("txt_", "png_", "fig_", "img_", "image_", "file_")


class 用户:
	"""一个发言者的显示信息（名称与头像）。"""

	def __init__(self, 名称, 头像路径=None, 是否占位=False):
		self.名称 = 名称
		self.头像路径 = 头像路径
		self.是否占位 = 是否占位

	def 取得头像图片路径(self):
		"""返回真实存在的头像图片路径，没有可用图片时返回 None。"""
		if self.头像路径 and os.path.isfile(self.头像路径):
			return self.头像路径
		else:
			return None


class 附件:
	"""一条聊天记录里引用到的附件。"""

	def __init__(self, 名称, 文件路径=None, 种类=种类_文本, 文件名称="", 是否占位=False, 是否缺失=False):
		self.名称 = 名称
		self.文件路径 = 文件路径
		self.种类 = 种类
		self.文件名称 = 文件名称 or (os.path.basename(文件路径) if 文件路径 else "")
		self.是否占位 = 是否占位
		# 是否缺失：引用的原文件没找到，内容由占位文件顶替
		self.是否缺失 = 是否缺失

	@property
	def 是否图片(self):
		"""该附件是否应当按图片方式浏览。"""
		return self.种类 == 种类_图片

	@property
	def 是否存在(self):
		"""附件对应的真实文件是否存在。"""
		return bool(self.文件路径) and os.path.isfile(self.文件路径)

	@property
	def 显示标题(self):
		"""按钮与标题栏上显示的文本，自动去掉“txt_ / png_”一类前缀。"""
		名称 = str(self.名称 or self.文件名称 or "未命名附件")
		for 前缀 in 类型前缀列表:
			if 名称.startswith(前缀):
				名称 = 名称[len(前缀):]
				break
		if not 名称:
			名称 = self.文件名称 or "未命名附件"
		return 名称


class 消息:
	"""一条聊天消息：一个发言人、一段原文、若干附件。"""

	def __init__(self, 发言者, 内容, 附件列表=None):
		self.发言者 = 发言者
		self.内容 = 内容
		self.附件列表 = 附件列表 if 附件列表 else []


class 会话:
	"""一段完整的聊天记录。"""

	def __init__(self, 标题, 键名, 默认视角, 消息列表, 是否折叠, 附件引用列表=None):
		self.标题 = 标题
		self.键名 = 键名
		self.默认视角 = 默认视角
		self.消息列表 = 消息列表 if 消息列表 else []
		self.是否折叠 = 是否折叠
		self.附件引用列表 = 附件引用列表 if 附件引用列表 else []

	def 发言者名称列表(self):
		"""按出现顺序返回去重后的发言人名称列表。"""
		结果 = []
		for 消息对象 in self.消息列表:
			if 消息对象.发言者 not in 结果:
				结果.append(消息对象.发言者)
		return 结果

	def 是否多人(self):
		"""发言者多于两人时，界面上需要显示每条消息的发言人名称。"""
		return len(self.发言者名称列表()) > 2


class 数据仓库:
	"""把元数据、用户表、附件表、会话表集中保存，供界面随时查询。"""

	def __init__(self, 元数据=None, 数据目录=None):
		self.元数据 = 元数据 if isinstance(元数据, dict) else {}
		self.数据目录 = 基础工具.取得数据目录(数据目录)
		self.用户目录 = os.path.join(self.数据目录, "发言者数据")
		self.附件目录 = os.path.join(self.数据目录, "聊天附件数据")
		self.聊天目录 = os.path.join(self.数据目录, "聊天信息数据")
		self.用户表 = {}
		self.附件表 = {}
		self.附件文件名表 = {}
		self.默认用户 = None
		self.默认图片附件 = None
		self.默认文本附件 = None
		self.会话列表 = []
		self.会话表 = {}
		self.加载全部()

	def 加载全部(self):
		"""按用户、附件、会话的顺序加载数据。"""
		self.加载用户表()
		self.加载附件表()
		self.加载会话表()

	def 加载用户表(self):
		"""读取“所有用户.json”，并准备默认占位用户。"""
		用户数据 = 基础工具.读取JSON(os.path.join(self.用户目录, "所有用户.json"))
		if not isinstance(用户数据, list):
			用户数据 = []
		for 条目 in 用户数据:
			if not isinstance(条目, dict):
				continue
			名称 = str(条目.get("名称", "") or "").strip()
			if not 名称:
				continue
			头像路径 = 基础工具.查找目录内文件(self.用户目录, 条目.get("头像", ""))
			用户对象 = 用户(名称, 头像路径, 名称 == 默认用户名称)
			self.用户表[名称] = 用户对象
			if 名称 == 默认用户名称:
				self.默认用户 = 用户对象
		# 元数据里列出的用户也要进表，避免“所有用户.json”缺失时全部变成占位头像
		for 名称 in (self.元数据.get("所有用户", []) or []):
			名称文本 = str(名称 or "").strip()
			if 名称文本 and 名称文本 not in self.用户表:
				self.用户表[名称文本] = 用户(名称文本, None)
		if self.默认用户 is None:
			默认头像 = 基础工具.查找目录内文件(self.用户目录, 默认用户名称 + ".png")
			self.默认用户 = 用户(默认用户名称, 默认头像, True)
			self.用户表.setdefault(默认用户名称, self.默认用户)

	def 寻找同名头像文件(self, 名称):
		"""在“发言者数据”目录里寻找与名称同名的图片文件。"""
		名称文本 = str(名称 or "").strip()
		if 名称文本:
			for 扩展名 in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
				路径 = 基础工具.查找目录内文件(self.用户目录, 名称文本 + 扩展名)
				if 路径:
					return 路径
		# 找不到同名图片时退回默认头像
		if self.默认用户:
			return self.默认用户.头像路径
		else:
			return None

	def 取得用户(self, 名称):
		"""按名称取用户；不在花名册中时先找同名图片，最后回退默认用户。"""
		名称文本 = str(名称 or "").strip()
		if 名称文本 and 名称文本 in self.用户表:
			用户对象 = self.用户表[名称文本]
			if not 用户对象.头像路径:
				用户对象.头像路径 = self.寻找同名头像文件(名称文本)
			return 用户对象
		else:
			用户对象 = 用户(名称文本 or "未知用户", self.寻找同名头像文件(名称文本))
			self.用户表[用户对象.名称] = 用户对象
			return 用户对象

	def 推断附件种类(self, 类型字段, 文件名="", 路径=None):
		"""根据“类型”字段或文件扩展名判断附件是图片还是文本。"""
		类型文本 = str(类型字段 or "").strip().lower()
		if 类型文本 in ("fig", "figure", "img", "image", "picture", "photo", "图片"):
			return 种类_图片
		elif 类型文本 in ("txt", "text", "md", "markdown", "doc", "document", "文本"):
			return 种类_文本
		else:
			扩展名 = os.path.splitext(str(文件名 or 路径 or ""))[1].lower()
			if 扩展名 in 图片扩展名集合:
				return 种类_图片
			elif 扩展名 in 文本扩展名集合:
				return 种类_文本
			else:
				return 种类_文本

	def 加载附件表(self):
		"""读取“所有附件.json”，建立“名称→附件”和“文件名→附件”两张索引。"""
		附件数据 = 基础工具.读取JSON(os.path.join(self.附件目录, "所有附件.json"))
		if not isinstance(附件数据, list):
			附件数据 = []
		for 条目 in 附件数据:
			if not isinstance(条目, dict):
				continue
			名称 = str(条目.get("名称", "") or "").strip()
			文件名 = str(条目.get("文件", "") or "").strip()
			if not 名称 and not 文件名:
				continue
			文件路径 = 基础工具.查找目录内文件(self.附件目录, 文件名)
			种类 = self.推断附件种类(条目.get("类型", ""), 文件名, 文件路径)
			附件对象 = 附件(名称 or 文件名, 文件路径, 种类, 文件名, 名称.startswith("(default"))
			if 名称:
				self.附件表[名称] = 附件对象
			if 文件名:
				self.附件文件名表[文件名] = 附件对象
		self.准备默认附件()

	def 准备默认附件(self):
		"""挑出占位附件，供原文件缺失时顶替显示。"""
		for 附件对象 in self.附件表.values():
			if not 附件对象.是否占位:
				continue
			if 附件对象.是否图片 and self.默认图片附件 is None:
				self.默认图片附件 = 附件对象
			elif 附件对象.种类 == 种类_文本 and self.默认文本附件 is None:
				self.默认文本附件 = 附件对象
		if self.默认图片附件 is None:
			路径 = 基础工具.查找目录内文件(self.附件目录, 默认图片附件名称 + ".png")
			self.默认图片附件 = 附件(默认图片附件名称, 路径, 种类_图片, 默认图片附件名称 + ".png", True)
		if self.默认文本附件 is None:
			路径 = 基础工具.查找目录内文件(self.附件目录, 默认文本附件名称 + ".txt")
			self.默认文本附件 = 附件(默认文本附件名称, 路径, 种类_文本, 默认文本附件名称 + ".txt", True)

	def 去掉类型前缀(self, 名称):
		"""去掉“txt_ / png_”一类前缀，便于二次匹配。"""
		名称文本 = str(名称 or "")
		for 前缀 in 类型前缀列表:
			if 名称文本.startswith(前缀):
				return 名称文本[len(前缀):]
		return 名称文本

	def 建立缺失附件(self, 引用名):
		"""引用名完全对不上时，构造一个用占位内容顶替的附件对象。"""
		种类 = self.推断附件种类("", 引用名)
		if 种类 == 种类_图片:
			占位对象 = self.默认图片附件
		else:
			占位对象 = self.默认文本附件
		文件路径 = 占位对象.文件路径 if 占位对象 else None
		文件名称 = 占位对象.文件名称 if 占位对象 else ""
		return 附件(str(引用名), 文件路径, 种类, 文件名称, True, True)

	def 取得附件(self, 引用名):
		"""按引用名取附件。

		引用名既可能是“所有附件.json”里的名称，也可能是真实文件名，
		两种写法都允许；完全找不到时返回 None，由调用方补占位附件。
		"""
		引用名文本 = str(引用名 or "").strip()
		if 引用名文本 in self.附件表:
			return self.附件表[引用名文本]
		elif 引用名文本 in self.附件文件名表:
			return self.附件文件名表[引用名文本]
		直接路径 = 基础工具.查找目录内文件(self.附件目录, 引用名文本)
		if 直接路径:
			种类 = self.推断附件种类("", 引用名文本, 直接路径)
			附件对象 = 附件(引用名文本, 直接路径, 种类, 引用名文本)
			self.附件表[引用名文本] = 附件对象
			return 附件对象
		去前缀名称 = self.去掉类型前缀(引用名文本)
		if 去前缀名称 and 去前缀名称 != 引用名文本:
			return self.取得附件(去前缀名称)
		else:
			return None

	def 收集消息附件(self, 附件引用, 引用名称列表):
		"""把一条消息里的附件引用全部解析成附件对象。"""
		附件列表 = []
		if not isinstance(附件引用, list):
			附件引用 = []
		for 引用名 in 附件引用:
			附件对象 = self.取得附件(引用名)
			if 附件对象 is None:
				附件对象 = self.建立缺失附件(引用名)
			附件列表.append(附件对象)
			引用名称列表.append(str(引用名))
		return 附件列表

	def 构建会话(self, 键名, 记录数据, 折叠字段, 元数据附件引用):
		"""把一个聊天记录 JSON 转换成会话对象。"""
		if not isinstance(记录数据, dict):
			记录数据 = {}
		标题 = str(记录数据.get("聊天标题", "") or 键名)
		默认视角 = str(记录数据.get("默认视角", "") or "").strip()
		消息列表 = []
		引用名称列表 = []
		内容列表 = 记录数据.get("聊天内容", [])
		if not isinstance(内容列表, list):
			内容列表 = []
		for 条目 in 内容列表:
			if not isinstance(条目, dict):
				continue
			发言者 = str(条目.get("发言者", "") or "未知用户").strip()
			内容 = 条目.get("发言内容", "")
			if 内容 is None:
				内容 = ""
			elif not isinstance(内容, str):
				# 只做类型安全转换，正文一个字都不改动
				内容 = str(内容)
			附件列表 = self.收集消息附件(条目.get("附件", []), 引用名称列表)
			消息列表.append(消息(发言者, 内容, 附件列表))
		if not 默认视角 and 消息列表:
			默认视角 = 消息列表[0].发言者
		if not 引用名称列表 and isinstance(元数据附件引用, list):
			引用名称列表 = [str(名称) for 名称 in 元数据附件引用]
		return 会话(标题, 键名, 默认视角, 消息列表, 折叠字段 == 折叠标记, 引用名称列表)

	def 加载会话表(self):
		"""按元数据“所有消息记录”的顺序逐个加载会话。"""
		记录表 = self.元数据.get("所有消息记录", {})
		if not isinstance(记录表, dict):
			记录表 = {}
		附件引用表 = self.元数据.get("附件引用", {})
		if not isinstance(附件引用表, dict):
			附件引用表 = {}
		for 键名, 折叠字段 in 记录表.items():
			路径 = os.path.join(self.聊天目录, str(键名) + ".json")
			记录数据 = 基础工具.读取JSON(路径)
			会话对象 = self.构建会话(str(键名), 记录数据, 折叠字段, 附件引用表.get(键名, []))
			self.会话列表.append(会话对象)
			self.会话表[会话对象.键名] = 会话对象
