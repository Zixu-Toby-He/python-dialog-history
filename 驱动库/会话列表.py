# -*- coding: utf-8 -*-
"""会话列表模块：左侧会话列表、菜单分隔符与可展开的“折叠对话”分组。

“折叠”只影响会话列表本身：被标记为折叠的对话默认收进一个分组里，
点击分组标题即可展开或收起，让首屏只保留需要关注的少数对话，
从而降低挑选对话时的注意力成本。展开后的折叠对话与普通对话完全一样。
"""

import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets


# 行高与配色（与会话列表整体的浅灰风格保持一致）
行高 = 44
颜色_列表背景 = "#F4F4F4"
颜色_悬停背景 = "#EAEAEA"
颜色_选中背景 = "#DCDCDC"
颜色_选中强调 = "#07C160"
颜色_正文 = "#1A1A1A"
颜色_次要文字 = "#8C8C8C"
颜色_分隔线 = "#D9D9D9"
# 分组标题上的箭头：收起时朝下（表示可向下展开），展开时朝上（表示可收起）
箭头_收起 = "▼"
箭头_展开 = "▲"
# 分组标题文字
折叠分组标题 = "折叠对话"


class 会话行部件(PyQt5.QtWidgets.QWidget):
	"""会话列表中的一行，自带悬停效果、选中高亮与左侧强调条。"""

	def __init__(self, 文本, 点击回调=None, 是否分组标题=False, 提示文本="", 父控件=None):
		super().__init__(父控件)
		self.点击回调 = 点击回调
		self.是否分组标题 = 是否分组标题
		self.悬停 = False
		self.选中 = False
		self.setFixedHeight(行高)
		self.setCursor(PyQt5.QtCore.Qt.PointingHandCursor)
		if 提示文本:
			self.setToolTip(提示文本)
		行布局 = PyQt5.QtWidgets.QHBoxLayout(self)
		行布局.setContentsMargins(16, 0, 12, 0)
		行布局.setSpacing(6)
		if 是否分组标题:
			文字颜色 = 颜色_次要文字
		else:
			文字颜色 = 颜色_正文
		self.文本标签 = PyQt5.QtWidgets.QLabel(文本)
		self.文本标签.setStyleSheet("background: transparent; color: %s; font-size: 14px;" % 文字颜色)
		行布局.addWidget(self.文本标签)
		if 是否分组标题:
			self.箭头标签 = PyQt5.QtWidgets.QLabel(箭头_收起)
			self.箭头标签.setStyleSheet("background: transparent; color: %s; font-size: 11px;" % 颜色_次要文字)
			行布局.addWidget(self.箭头标签)
		else:
			self.箭头标签 = None
		行布局.addStretch(1)

	def 设置选中(self, 是否选中):
		"""更新选中状态并触发重绘。"""
		self.选中 = bool(是否选中)
		self.update()

	def 设置箭头(self, 是否展开):
		"""分组标题专用：按展开状态切换箭头方向。"""
		if self.箭头标签 is None:
			return
		if 是否展开:
			self.箭头标签.setText(箭头_展开)
		else:
			self.箭头标签.setText(箭头_收起)

	def enterEvent(self, 事件):
		"""鼠标进入时高亮整行。"""
		self.悬停 = True
		self.update()
		super().enterEvent(事件)

	def leaveEvent(self, 事件):
		"""鼠标离开时取消高亮。"""
		self.悬停 = False
		self.update()
		super().leaveEvent(事件)

	def mouseReleaseEvent(self, 事件):
		"""左键释放时触发点击回调（回调由本模块内部传入，不经过 Qt 信号）。"""
		if 事件.button() == PyQt5.QtCore.Qt.LeftButton and self.点击回调 is not None:
			self.点击回调()
		super().mouseReleaseEvent(事件)

	def paintEvent(self, 事件):
		"""自行绘制背景：选中优先于悬停，选中时左侧再画一条绿色强调条。"""
		绘制器 = PyQt5.QtGui.QPainter(self)
		if self.选中:
			背景颜色 = 颜色_选中背景
		elif self.悬停:
			背景颜色 = 颜色_悬停背景
		else:
			背景颜色 = ""
		if 背景颜色:
			绘制器.fillRect(self.rect(), PyQt5.QtGui.QColor(背景颜色))
		if self.选中:
			绘制器.fillRect(0, 0, 3, self.height(), PyQt5.QtGui.QColor(颜色_选中强调))
		绘制器.end()


class 会话列表侧栏(PyQt5.QtWidgets.QWidget):
	"""左侧会话列表：普通对话在上，被折叠的对话收进可展开的分组。"""

	def __init__(self, 会话列表=None, 点击回调=None, 父控件=None):
		super().__init__(父控件)
		self.会话列表 = 会话列表 if 会话列表 else []
		self.点击回调 = 点击回调
		self.选中行号 = -1
		self.行部件表 = {}
		self.折叠容器 = None
		self.折叠标题行 = None
		self.折叠是否展开 = False
		self.setObjectName("sessionList")
		self.setStyleSheet("#sessionList { background-color: %s; }" % 颜色_列表背景)
		self.构建界面()

	def 构建界面(self):
		"""搭出“普通对话 / 分隔符 / 折叠对话分组”的纵向结构。"""
		外层布局 = PyQt5.QtWidgets.QVBoxLayout(self)
		外层布局.setContentsMargins(0, 6, 0, 6)
		外层布局.setSpacing(0)
		滚动区 = PyQt5.QtWidgets.QScrollArea()
		滚动区.setWidgetResizable(True)
		滚动区.setFrameShape(PyQt5.QtWidgets.QFrame.NoFrame)
		滚动区.setHorizontalScrollBarPolicy(PyQt5.QtCore.Qt.ScrollBarAlwaysOff)
		内容容器 = PyQt5.QtWidgets.QWidget()
		内容容器.setObjectName("sessionListContent")
		内容容器.setStyleSheet("#sessionListContent { background-color: %s; }" % 颜色_列表背景)
		self.内容布局 = PyQt5.QtWidgets.QVBoxLayout(内容容器)
		self.内容布局.setContentsMargins(0, 0, 0, 0)
		self.内容布局.setSpacing(0)
		滚动区.setWidget(内容容器)
		外层布局.addWidget(滚动区)
		self.填充会话行()

	def 填充会话行(self):
		"""按“普通对话在前、折叠对话在后”的顺序生成全部行。"""
		普通行列表 = []
		折叠行列表 = []
		for 行号, 会话对象 in enumerate(self.会话列表):
			行部件 = self.创建会话行(行号, 会话对象)
			if 会话对象.是否折叠:
				折叠行列表.append(行部件)
			else:
				普通行列表.append(行部件)
		for 行部件 in 普通行列表:
			self.内容布局.addWidget(行部件)
		if 普通行列表 and 折叠行列表:
			self.内容布局.addWidget(self.创建分隔线())
		if 折叠行列表:
			self.内容布局.addWidget(self.创建折叠标题行(len(折叠行列表)))
			self.折叠容器 = self.创建折叠容器(折叠行列表)
			self.内容布局.addWidget(self.折叠容器)
		self.内容布局.addStretch(1)
		# 一条普通对话都没有时，默认把折叠分组展开，避免首屏空空荡荡
		if 折叠行列表 and not 普通行列表:
			self.设置折叠展开(True)
		else:
			self.设置折叠展开(False)

	def 创建会话行(self, 行号, 会话对象):
		"""创建一个会话行，点击后回到主窗口切换会话。"""
		提示文本 = "记录文件：%s.json" % 会话对象.键名
		行部件 = 会话行部件(会话对象.标题, lambda 号码=行号: self.处理行点击(号码), False, 提示文本)
		self.行部件表[行号] = 行部件
		return 行部件

	def 创建分隔线(self):
		"""创建菜单分隔符风格的水平细线，用来隔开普通对话与折叠分组。"""
		容器 = PyQt5.QtWidgets.QWidget()
		布局 = PyQt5.QtWidgets.QHBoxLayout(容器)
		布局.setContentsMargins(12, 4, 12, 4)
		布局.setSpacing(0)
		细线 = PyQt5.QtWidgets.QFrame()
		细线.setFixedHeight(1)
		细线.setStyleSheet("background-color: %s;" % 颜色_分隔线)
		布局.addWidget(细线)
		return 容器

	def 创建折叠标题行(self, 数量):
		"""创建“折叠对话”分组标题行，点击即可展开或收起。"""
		提示文本 = "点击展开或收起被折叠的对话，共 %d 条" % 数量
		self.折叠标题行 = 会话行部件(折叠分组标题, self.切换折叠, True, 提示文本)
		return self.折叠标题行

	def 创建折叠容器(self, 折叠行列表):
		"""创建承载折叠对话行的容器。"""
		容器 = PyQt5.QtWidgets.QWidget()
		布局 = PyQt5.QtWidgets.QVBoxLayout(容器)
		布局.setContentsMargins(0, 0, 0, 0)
		布局.setSpacing(0)
		for 行部件 in 折叠行列表:
			布局.addWidget(行部件)
		return 容器

	def 处理行点击(self, 行号):
		"""用户点中某条会话：更新高亮并通知主窗口。"""
		self.选中会话(行号, True)

	def 选中会话(self, 行号, 是否通知=False):
		"""设置当前选中的会话行号，必要时回调主窗口。"""
		if 行号 < 0 or 行号 >= len(self.会话列表):
			return
		self.选中行号 = 行号
		for 号码, 行部件 in self.行部件表.items():
			行部件.设置选中(号码 == 行号)
		if 是否通知 and self.点击回调 is not None:
			self.点击回调(行号)

	def 切换折叠(self):
		"""分组标题被点击：在展开与收起之间切换。"""
		self.设置折叠展开(not self.折叠是否展开)

	def 设置折叠展开(self, 是否展开):
		"""显示或隐藏折叠分组里的会话行，并同步箭头方向。"""
		self.折叠是否展开 = bool(是否展开)
		if self.折叠容器 is not None:
			self.折叠容器.setVisible(self.折叠是否展开)
		if self.折叠标题行 is not None:
			self.折叠标题行.设置箭头(self.折叠是否展开)

	def 取得选中行号(self):
		"""返回当前选中的行号，未选中时返回 -1。"""
		return self.选中行号
