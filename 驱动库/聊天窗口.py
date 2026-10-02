# -*- coding: utf-8 -*-
"""主窗口模块：把会话列表、聊天气泡区与右侧附件栏组装成一个窗口。

窗口只做“浏览”，不提供任何编辑或发送入口，
因此第一代不会、也没有办法改动任何一条聊天记录原文。
"""

import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets

from . import 基础工具
from . import 数据结构
from . import 会话列表
from . import 附件面板
from . import 消息气泡


# 界面配色
颜色_窗口背景 = "#EDEDED"
颜色_面板背景 = "#FFFFFF"
颜色_正文 = "#1A1A1A"
颜色_次要文字 = "#8C8C8C"
颜色_分隔线 = "#E3E3E3"
# 会话列表宽度、窗口初始尺寸、气泡占聊天区宽度的比例
会话列表宽度 = 190
窗口初始宽 = 1120
窗口初始高 = 740
右栏宽度 = 400
# 气泡宽度上限占聊天区可视宽度的比例（0.5 就是“聊天面板宽度的一半”）
气泡宽度比例 = 0.5


class 消息滚动区(PyQt5.QtWidgets.QScrollArea):
	"""能感知自身可视宽度变化的滚动区：可视宽度一变就发信号。

	无论是缩放窗口、拖动分隔条，还是打开右侧附件栏把聊天面板挤窄，
	最终都会让这个滚动区的可视宽度发生变化，因此这里上报最可靠。
	"""

	# 注意：pyqtSignal 的名称会被 Qt 按 ASCII 编码，因此这里只能用英文名
	viewportWidthChanged = PyQt5.QtCore.pyqtSignal(int)

	def __init__(self, 父控件=None):
		super().__init__(父控件)
		self.上次宽度 = -1
		# 竖向滚动条出现或消失时，可视宽度也会变，所以连视口的事件一起监听
		self.viewport().installEventFilter(self)

	def resizeEvent(self, 事件):
		"""滚动区自身尺寸变化时上报可视宽度。"""
		super().resizeEvent(事件)
		self.广播宽度()

	def eventFilter(self, 监听对象, 事件):
		"""视口尺寸变化时上报可视宽度。"""
		if 监听对象 is self.viewport() and 事件.type() == PyQt5.QtCore.QEvent.Resize:
			self.广播宽度()
		return super().eventFilter(监听对象, 事件)

	def 广播宽度(self):
		"""只在宽度真的变化时发信号，避免重复刷新气泡。"""
		当前宽度 = self.viewport().width()
		if 当前宽度 > 0 and 当前宽度 != self.上次宽度:
			self.上次宽度 = 当前宽度
			self.viewportWidthChanged.emit(当前宽度)


class 聊天记录可视化窗口(PyQt5.QtWidgets.QMainWindow):
	"""聊天记录可视化主窗口。"""

	def __init__(self, 聊天元数据=None, 数据目录=None, 父窗口=None):
		super().__init__(父窗口)
		self.元数据 = self.规范化元数据(聊天元数据)
		self.仓库 = 数据结构.数据仓库(self.元数据, 数据目录)
		self.当前会话 = None
		self.消息部件列表 = []
		self.setWindowTitle("聊天记录可视化")
		self.resize(窗口初始宽, 窗口初始高)
		self.构建界面()
		self.绑定快捷键()
		self.加载会话列表()

	def 规范化元数据(self, 聊天元数据):
		"""元数据允许直接传字典，也允许传元数据 JSON 的路径。"""
		if isinstance(聊天元数据, dict):
			return 聊天元数据
		elif isinstance(聊天元数据, str):
			数据 = 基础工具.读取JSON(聊天元数据)
			if isinstance(数据, dict):
				return 数据
			else:
				return {}
		else:
			return 基础工具.读取聊天记录元数据()

	def 构建界面(self):
		"""搭建“会话列表 + 聊天区 + 附件栏”三分栏结构。"""
		self.分栏 = PyQt5.QtWidgets.QSplitter(PyQt5.QtCore.Qt.Horizontal)
		self.分栏.setHandleWidth(1)
		self.分栏.setStyleSheet("QSplitter::handle { background-color: %s; }" % 颜色_分隔线)
		self.分栏.addWidget(self.创建会话列表控件())
		self.分栏.addWidget(self.创建聊天面板())
		self.附件侧栏 = 附件面板.附件侧栏()
		# 说明：PyQt 连接信号时不接受中文名的方法，这里一律用 lambda 做一层薄封装
		self.附件侧栏.closeRequested.connect(lambda: self.关闭附件栏())
		self.分栏.addWidget(self.附件侧栏)
		self.分栏.setSizes([会话列表宽度, 窗口初始宽 - 会话列表宽度, 0])
		self.setCentralWidget(self.分栏)
		self.附件侧栏.hide()

	def 创建会话列表控件(self):
		"""左侧会话列表：普通对话在上，被折叠的对话收进可展开的分组。"""
		self.会话列表控件 = 会话列表.会话列表侧栏(self.仓库.会话列表, self.切换会话)
		self.会话列表控件.setMinimumWidth(140)
		self.会话列表控件.setToolTip("点击切换要浏览的聊天记录；“折叠对话”可展开或收起")
		return self.会话列表控件

	def 创建聊天面板(self):
		"""中间聊天区：标题栏 + 气泡滚动区 + 底部只读提示。"""
		面板 = PyQt5.QtWidgets.QWidget()
		面板.setObjectName("chatPanel")
		面板.setStyleSheet("#chatPanel { background-color: %s; }" % 颜色_窗口背景)
		面板布局 = PyQt5.QtWidgets.QVBoxLayout(面板)
		面板布局.setContentsMargins(0, 0, 0, 0)
		面板布局.setSpacing(0)
		面板布局.addWidget(self.创建标题栏())
		面板布局.addWidget(self.创建消息滚动区(), 1)
		面板布局.addWidget(self.创建底部提示栏())
		return 面板

	def 创建标题栏(self):
		"""聊天区顶部的标题与信息条。"""
		标题栏 = PyQt5.QtWidgets.QWidget()
		标题栏.setObjectName("chatHeader")
		标题栏.setStyleSheet("#chatHeader { background-color: %s; border-bottom: 1px solid %s; }"
			% (颜色_面板背景, 颜色_分隔线))
		布局 = PyQt5.QtWidgets.QVBoxLayout(标题栏)
		布局.setContentsMargins(18, 10, 18, 10)
		布局.setSpacing(2)
		self.标题标签 = PyQt5.QtWidgets.QLabel("聊天记录")
		self.标题标签.setStyleSheet("font-size: 16px; font-weight: bold; color: %s;" % 颜色_正文)
		self.信息标签 = PyQt5.QtWidgets.QLabel("")
		self.信息标签.setStyleSheet("font-size: 12px; color: %s;" % 颜色_次要文字)
		布局.addWidget(self.标题标签)
		布局.addWidget(self.信息标签)
		return 标题栏

	def 创建消息滚动区(self):
		"""气泡所在的可滚动区域。"""
		self.滚动区 = 消息滚动区()
		self.滚动区.setWidgetResizable(True)
		self.滚动区.setFrameShape(PyQt5.QtWidgets.QFrame.NoFrame)
		self.滚动区.setHorizontalScrollBarPolicy(PyQt5.QtCore.Qt.ScrollBarAlwaysOff)
		# 聊天面板宽度一变（缩放窗口、拖分隔条、开附件栏），就重算每条气泡的宽度
		# 说明：PyQt 连接信号时不接受中文名的方法，这里一律用 lambda 做一层薄封装
		self.滚动区.viewportWidthChanged.connect(lambda 宽度: self.更新气泡宽度(宽度))
		self.消息容器 = PyQt5.QtWidgets.QWidget()
		self.消息容器.setObjectName("msgContainer")
		self.消息容器.setStyleSheet("#msgContainer { background-color: %s; }" % 颜色_窗口背景)
		self.消息布局 = PyQt5.QtWidgets.QVBoxLayout(self.消息容器)
		self.消息布局.setContentsMargins(0, 10, 0, 10)
		self.消息布局.setSpacing(0)
		self.消息布局.addStretch(1)
		self.滚动区.setWidget(self.消息容器)
		return self.滚动区

	def 创建底部提示栏(self):
		"""底部只读提示，说明本代不会修改聊天内容。"""
		提示标签 = PyQt5.QtWidgets.QLabel("只读浏览：内容与附件均按原样显示，点击气泡中的附件按钮可在右侧栏查看附件。")
		提示标签.setStyleSheet("background-color: %s; border-top: 1px solid %s; color: %s;"
			"font-size: 12px; padding: 8px 18px;" % (颜色_面板背景, 颜色_分隔线, 颜色_次要文字))
		return 提示标签

	def 绑定快捷键(self):
		"""Esc 用于收起右侧附件栏。"""
		self.关闭快捷键 = PyQt5.QtWidgets.QShortcut(PyQt5.QtGui.QKeySequence(PyQt5.QtCore.Qt.Key_Escape), self)
		self.关闭快捷键.activated.connect(lambda: self.关闭附件栏())

	def 加载会话列表(self):
		"""默认选中第一条会话；一条记录都没有时给出提示。"""
		if len(self.仓库.会话列表) > 0:
			self.会话列表控件.选中会话(0, True)
		else:
			self.标题标签.setText("没有可显示的聊天记录")
			self.信息标签.setText("请检查“数据文件/%s”是否存在且格式正确。"
				% 基础工具.元数据文件名)

	def 切换会话(self, 行号):
		"""切换到左侧列表选中的会话。"""
		if 行号 < 0 or 行号 >= len(self.仓库.会话列表):
			return
		会话对象 = self.仓库.会话列表[行号]
		self.当前会话 = 会话对象
		self.标题标签.setText(会话对象.标题)
		self.信息标签.setText("默认视角：%s ｜ 共 %d 条消息 ｜ 记录文件：%s.json"
			% (会话对象.默认视角 or "未指定", len(会话对象.消息列表), 会话对象.键名))
		self.重建消息区(会话对象)

	def 清空消息区(self):
		"""移除全部消息部件，为重新生成做准备。"""
		while self.消息布局.count() > 0:
			项目 = self.消息布局.takeAt(0)
			部件 = 项目.widget()
			if 部件 is not None:
				部件.setParent(None)
				部件.deleteLater()
		self.消息部件列表 = []

	def 重建消息区(self, 会话对象):
		"""根据会话记录重新生成左右分布的气泡列表。"""
		self.清空消息区()
		if 会话对象 is None:
			self.消息布局.addStretch(1)
			return
		显示名称 = 会话对象.是否多人()
		for 序号, 消息对象 in enumerate(会话对象.消息列表):
			是否己方 = 消息对象.发言者 == 会话对象.默认视角
			用户对象 = self.仓库.取得用户(消息对象.发言者)
			部件 = 消息气泡.气泡部件(消息对象, 用户对象, 是否己方, True,
				显示名称 and not 是否己方)
			部件.attachmentClicked.connect(lambda 对象: self.打开附件(对象))
			self.消息布局.addWidget(部件)
			self.消息部件列表.append(部件)
		self.消息布局.addStretch(1)
		self.更新气泡宽度()
		self.滚动到底部()

	def 打开附件(self, 附件对象):
		"""在右侧栏浏览附件；重复点击同一个附件则收起右栏。"""
		if self.附件侧栏.isVisible() and self.附件侧栏.当前附件 is 附件对象:
			self.关闭附件栏()
			return
		self.附件侧栏.显示附件(附件对象)
		self.附件侧栏.show()
		总宽度 = max(self.分栏.width(), 窗口初始宽)
		目标右栏宽度 = min(右栏宽度, max(280, int(总宽度 * 0.34)))
		self.分栏.setSizes([会话列表宽度, max(320, 总宽度 - 会话列表宽度 - 目标右栏宽度), 目标右栏宽度])

	def 关闭附件栏(self):
		"""收起右侧附件栏。"""
		self.附件侧栏.hide()

	def 更新气泡宽度(self, 可视宽度=None):
		"""按聊天区可视宽度重算每条气泡的宽度上限。"""
		if not hasattr(self, "滚动区"):
			return
		if 可视宽度 is None:
			可视宽度 = self.滚动区.viewport().width()
		目标宽度 = int(max(240, 可视宽度) * 气泡宽度比例)
		for 部件 in self.消息部件列表:
			部件.设置气泡宽度(目标宽度)

	def 滚动到底部(self):
		"""切换会话后把视图滚到最新一条消息。"""
		滚动条 = self.滚动区.verticalScrollBar()
		PyQt5.QtCore.QTimer.singleShot(0, lambda: 滚动条.setValue(滚动条.maximum()))
