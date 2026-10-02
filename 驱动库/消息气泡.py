# -*- coding: utf-8 -*-
"""消息气泡模块：绘制左右分布的聊天气泡、头像与附件按钮。

默认视角（也就是“我”）的消息靠右显示、使用绿色气泡；
其它发言人的消息靠左显示、使用白色气泡，效果接近常用聊天软件。
气泡里的文字保持原样，不做任何替换、截断或转义。
"""

import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets


# 配色：自己用绿色气泡，其它发言人用白色气泡
颜色_己方气泡 = "#95EC69"
颜色_对方气泡 = "#FFFFFF"
颜色_正文 = "#1A1A1A"
颜色_名称 = "#8C8C8C"
颜色_占位头像背景 = "#BDBDBD"
# 头像边长与气泡宽度约束
头像边长 = 38
气泡最小宽度 = 280
气泡最大宽度 = 760
# 气泡左右内边距，用来把“正文自然宽度”换算成“气泡需要的宽度”
气泡左右内边距 = 12
# 量正文宽度时的起点余量与试排参数：emoji 这类字符会换成彩色字体渲染，
# 只按字体度量估算可能偏窄，所以要按步长往上试到“确实不换行”为止
换行余量 = 2
宽度试探步长 = 2
宽度试探上限 = 48
# 附件按钮样式（在绿色与白色气泡上都清晰可辨）
附件按钮样式 = """
QPushButton { background-color: rgba(255, 255, 255, 0.86); color: #1A1A1A;
	border: 1px solid #D5D5D5; border-radius: 8px; padding: 5px 10px; font-size: 13px; }
QPushButton:hover { background-color: #FFFFFF; border-color: #9E9E9E; }
QPushButton:pressed { background-color: #EDEDED; }
"""


class 气泡部件(PyQt5.QtWidgets.QWidget):
	"""单条消息的气泡控件。"""

	# 注意：pyqtSignal 的名称会被 Qt 按 ASCII 编码，因此这里只能用英文名
	attachmentClicked = PyQt5.QtCore.pyqtSignal(object)

	def __init__(self, 消息对象, 用户对象, 是否己方, 是否显示头像=True, 是否显示名称=False, 父控件=None):
		super().__init__(父控件)
		self.消息对象 = 消息对象
		self.用户对象 = 用户对象
		self.是否己方 = 是否己方
		self.是否显示头像 = 是否显示头像
		self.是否显示名称 = 是否显示名称
		self.附件按钮列表 = []
		# 正文自然宽度只和内容、字体有关，量一次缓存起来
		self.正文自然宽度 = None
		self.缓存字体 = None
		self.构建界面()

	def 构建界面(self):
		"""按“自己靠右、他人靠左”的规则组装一整行。"""
		行布局 = PyQt5.QtWidgets.QHBoxLayout(self)
		行布局.setContentsMargins(14, 5, 14, 5)
		行布局.setSpacing(10)
		self.头像标签 = self.创建头像标签()
		内容容器 = PyQt5.QtWidgets.QWidget()
		内容列 = PyQt5.QtWidgets.QVBoxLayout(内容容器)
		内容列.setContentsMargins(0, 0, 0, 0)
		内容列.setSpacing(3)
		if self.是否显示名称:
			名称标签 = PyQt5.QtWidgets.QLabel(self.用户对象.名称)
			名称标签.setStyleSheet("color: %s; font-size: 11px;" % 颜色_名称)
			if self.是否己方:
				名称标签.setAlignment(PyQt5.QtCore.Qt.AlignRight)
			else:
				名称标签.setAlignment(PyQt5.QtCore.Qt.AlignLeft)
			内容列.addWidget(名称标签)
		self.气泡容器 = self.创建气泡容器()
		if self.是否己方:
			内容列.setAlignment(PyQt5.QtCore.Qt.AlignRight)
		else:
			内容列.setAlignment(PyQt5.QtCore.Qt.AlignLeft)
		内容列.addWidget(self.气泡容器)
		if self.是否己方:
			行布局.addStretch(1)
			行布局.addWidget(内容容器, 0, PyQt5.QtCore.Qt.AlignTop)
			行布局.addWidget(self.头像标签, 0, PyQt5.QtCore.Qt.AlignTop)
		else:
			行布局.addWidget(self.头像标签, 0, PyQt5.QtCore.Qt.AlignTop)
			行布局.addWidget(内容容器, 0, PyQt5.QtCore.Qt.AlignTop)
			行布局.addStretch(1)
		self.设置气泡宽度(气泡最大宽度)

	def 创建头像标签(self):
		"""创建头像控件；没有图片时用圆形文字头像顶替。"""
		标签 = PyQt5.QtWidgets.QLabel()
		标签.setFixedSize(头像边长, 头像边长)
		if not self.是否显示头像:
			标签.setStyleSheet("background: transparent;")
			return 标签
		else:
			图片路径 = self.用户对象.取得头像图片路径()
		if 图片路径:
			图片 = PyQt5.QtGui.QPixmap(图片路径)
		else:
			图片 = PyQt5.QtGui.QPixmap()
		if not 图片.isNull():
			方形图片 = 图片.scaled(头像边长, 头像边长, PyQt5.QtCore.Qt.KeepAspectRatioByExpanding,
				PyQt5.QtCore.Qt.SmoothTransformation)
			标签.setPixmap(self.裁剪为圆形(方形图片))
		else:
			文字 = self.用户对象.名称[:1] if self.用户对象.名称 else "?"
			标签.setText(文字)
			标签.setAlignment(PyQt5.QtCore.Qt.AlignCenter)
			标签.setStyleSheet("background-color: %s; color: #FFFFFF; border-radius: %dpx; font-size: 16px;"
				% (颜色_占位头像背景, 头像边长 // 2))
		return 标签

	def 裁剪为圆形(self, 图片):
		"""把正方形头像裁剪成圆形。"""
		目标图片 = PyQt5.QtGui.QPixmap(头像边长, 头像边长)
		目标图片.fill(PyQt5.QtCore.Qt.transparent)
		绘制器 = PyQt5.QtGui.QPainter(目标图片)
		绘制器.setRenderHints(PyQt5.QtGui.QPainter.Antialiasing | PyQt5.QtGui.QPainter.SmoothPixmapTransform)
		圆形路径 = PyQt5.QtGui.QPainterPath()
		圆形路径.addEllipse(0, 0, 头像边长, 头像边长)
		绘制器.setClipPath(圆形路径)
		绘制器.drawPixmap(int((头像边长 - 图片.width()) / 2), int((头像边长 - 图片.height()) / 2), 图片)
		绘制器.end()
		return 目标图片

	def 创建气泡容器(self):
		"""创建气泡主体：正文在上，附件按钮在下。"""
		容器 = PyQt5.QtWidgets.QWidget()
		容器.setObjectName("bubble")
		if self.是否己方:
			气泡颜色 = 颜色_己方气泡
		else:
			气泡颜色 = 颜色_对方气泡
		容器.setStyleSheet("#bubble { background-color: %s; border-radius: 10px; }" % 气泡颜色)
		布局 = PyQt5.QtWidgets.QVBoxLayout(容器)
		布局.setContentsMargins(气泡左右内边距, 9, 气泡左右内边距, 9)
		布局.setSpacing(7)
		self.文本标签 = PyQt5.QtWidgets.QLabel(self.消息对象.内容)
		self.文本标签.setTextFormat(PyQt5.QtCore.Qt.PlainText)
		self.文本标签.setWordWrap(True)
		self.文本标签.setTextInteractionFlags(PyQt5.QtCore.Qt.TextSelectableByMouse)
		self.文本标签.setStyleSheet("background: transparent; color: %s; font-size: 14px;" % 颜色_正文)
		附件列表 = self.消息对象.附件列表 if self.消息对象.附件列表 else []
		if not self.消息对象.内容 and 附件列表:
			self.文本标签.hide()
		else:
			布局.addWidget(self.文本标签)
		if 附件列表:
			按钮行 = PyQt5.QtWidgets.QHBoxLayout()
			按钮行.setContentsMargins(0, 0, 0, 0)
			按钮行.setSpacing(6)
			for 附件对象 in 附件列表:
				按钮 = self.创建附件按钮(附件对象)
				按钮行.addWidget(按钮, 0, PyQt5.QtCore.Qt.AlignLeft)
				self.附件按钮列表.append(按钮)
			按钮行.addStretch(1)
			布局.addLayout(按钮行)
		return 容器

	def 创建附件按钮(self, 附件对象):
		"""附件按钮类似网页版聊天里的附件胶囊，点击后交给主窗口打开。"""
		if 附件对象.是否图片:
			前缀 = "🖼 "
		else:
			前缀 = "📄 "
		按钮 = PyQt5.QtWidgets.QPushButton(前缀 + 附件对象.显示标题)
		按钮.setCursor(PyQt5.QtCore.Qt.PointingHandCursor)
		按钮.setStyleSheet(附件按钮样式)
		if 附件对象.是否缺失:
			按钮.setToolTip("原文件缺失，点击查看占位内容：%s" % 附件对象.名称)
		else:
			按钮.setToolTip("点击查看附件：%s" % (附件对象.文件名称 or 附件对象.名称))
		按钮.clicked.connect(lambda 选中=False, 对象=附件对象: self.attachmentClicked.emit(对象))
		return 按钮

	def 估算正文宽度(self):
		"""用一个关掉自动换行的同字体标签估算正文宽度，多行文本取最长的一行。"""
		self.文本标签.ensurePolished()
		度量标签 = PyQt5.QtWidgets.QLabel()
		度量标签.setFont(self.文本标签.font())
		度量标签.setTextFormat(PyQt5.QtCore.Qt.PlainText)
		度量标签.setWordWrap(False)
		最宽 = 0
		for 行 in str(self.消息对象.内容).split("\n"):
			度量标签.setText(行)
			最宽 = max(最宽, 度量标签.sizeHint().width())
		return 最宽

	def 测量正文自然宽度(self):
		"""量出正文排成一行真正需要的宽度。

		先按排版引擎估一个起点，再按步长往上试：
		只要这个宽度下正文还会换行，就继续放宽，直到试出不换行为止。
		emoji 之类要换成回退字体渲染的字符，引擎估算往往偏小，
		只有实际试排一次才能保证最后一个字符不被挤到下一行。
		"""
		起点 = self.估算正文宽度() + 换行余量
		参考宽度 = 起点 + 宽度试探上限 + 400
		单行高度 = self.文本标签.heightForWidth(参考宽度)
		宽度 = 起点
		while 宽度 < 起点 + 宽度试探上限 and self.文本标签.heightForWidth(宽度) > 单行高度:
			宽度 += 宽度试探步长
		self.正文自然宽度 = 宽度

	def 取正文自然宽度(self):
		"""返回正文自然宽度；字体（例如换了缩放比例）变了就重新量一次。"""
		当前字体 = self.文本标签.font()
		if self.正文自然宽度 is None or 当前字体 != self.缓存字体:
			self.测量正文自然宽度()
			self.缓存字体 = 当前字体
		return self.正文自然宽度

	def 设置气泡宽度(self, 上限像素):
		"""按给定上限设置气泡宽度。

		上限决定长文本在哪里换行；下限取正文的自然宽度，
		这样短句保持紧凑、长句才会撑到上限后换行。
		"""
		上限 = max(气泡最小宽度, int(上限像素))
		自然宽度 = self.取正文自然宽度() + 气泡左右内边距 * 2
		self.气泡容器.setMaximumWidth(上限)
		self.气泡容器.setMinimumWidth(min(自然宽度, 上限))
