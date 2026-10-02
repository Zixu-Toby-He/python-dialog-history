# -*- coding: utf-8 -*-
"""附件浏览模块：提供右侧附件栏与独立附件弹窗两种浏览方式。

文本附件按纯文本显示，Markdown 附件渲染成富文本（含表格），
图片附件按窗口宽度自动缩放。所有内容都是只读的，不会改动源文件。
"""

import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets

from . import 基础工具


# Markdown 是可选依赖，缺少时自动退化为纯文本显示，不影响程序启动
try:
	import markdown
	支持Markdown = True
except ImportError:
	支持Markdown = False


# 文本浏览器使用的默认样式（通过 QTextDocument.setDefaultStyleSheet 生效）
文本样式表 = """
body { font-family: 'Microsoft YaHei', '微软雅黑', sans-serif; font-size: 14px; color: #1A1A1A; }
h1 { font-size: 19px; }
h2 { font-size: 17px; }
h3 { font-size: 15px; }
th, td { padding: 4px 10px; }
th { background-color: #F2F2F2; }
code { background-color: #F2F2F2; }
"""
# 渲染 Markdown 时启用的扩展
Markdown扩展列表 = ["tables", "fenced_code", "nl2br", "sane_lists"]
# 允许按 Markdown 渲染的扩展名
Markdown扩展名集合 = (".md", ".markdown", ".mdown", ".mkd")


def 是否Markdown文件(文件名称):
	"""按扩展名判断该文本是否应当按 Markdown 渲染。"""
	名称 = str(文件名称 or "").strip().lower()
	for 扩展名 in Markdown扩展名集合:
		if 名称.endswith(扩展名):
			return True
	return False


def 渲染Markdown(文本):
	"""把 Markdown 文本渲染成 Qt 能显示的 HTML，失败时返回 None。"""
	if not 支持Markdown:
		return None
	try:
		HTML主体 = markdown.markdown(文本, extensions=Markdown扩展列表)
	except Exception:
		return None
	# Qt 的富文本表格默认没有边框，这里给表格补上边框属性
	HTML主体 = HTML主体.replace("<table>", "<table border='1' cellspacing='0' cellpadding='4'>")
	return HTML主体


class 图片浏览区(PyQt5.QtWidgets.QScrollArea):
	"""按窗口宽度自动缩放显示图片的滚动区域。"""

	def __init__(self, 父控件=None):
		super().__init__(父控件)
		self.原始图片 = PyQt5.QtGui.QPixmap()
		self.图片标签 = PyQt5.QtWidgets.QLabel("尚未选择附件")
		self.图片标签.setAlignment(PyQt5.QtCore.Qt.AlignCenter)
		self.setWidget(self.图片标签)
		self.setWidgetResizable(True)
		self.setAlignment(PyQt5.QtCore.Qt.AlignCenter)
		self.setFrameShape(PyQt5.QtWidgets.QFrame.NoFrame)

	def 设置图片(self, 图片路径):
		"""加载图片文件，加载失败时提示无法显示。"""
		if 图片路径:
			self.原始图片 = PyQt5.QtGui.QPixmap(图片路径)
		else:
			self.原始图片 = PyQt5.QtGui.QPixmap()
		self.适应宽度()

	def 适应宽度(self):
		"""按当前视口宽度重新缩放，过大时缩小、过小时保持原始尺寸。"""
		if self.原始图片.isNull():
			self.图片标签.setPixmap(PyQt5.QtGui.QPixmap())
			self.图片标签.setText("图片无法显示")
			return
		可用宽度 = max(120, self.viewport().width() - 16)
		if self.原始图片.width() > 可用宽度:
			显示图片 = self.原始图片.scaledToWidth(可用宽度, PyQt5.QtCore.Qt.SmoothTransformation)
		else:
			显示图片 = self.原始图片
		self.图片标签.setText("")
		self.图片标签.setPixmap(显示图片)

	def resizeEvent(self, 事件):
		"""窗口尺寸变化时重新适应宽度。"""
		super().resizeEvent(事件)
		self.适应宽度()


class 附件内容视图(PyQt5.QtWidgets.QWidget):
	"""附件内容视图：图片走图片浏览区，其余内容走文本浏览器。"""

	def __init__(self, 父控件=None):
		super().__init__(父控件)
		self.图片浏览 = 图片浏览区()
		self.文本浏览框 = PyQt5.QtWidgets.QTextBrowser()
		self.文本浏览框.setOpenExternalLinks(True)
		self.文本浏览框.setLineWrapMode(PyQt5.QtWidgets.QTextEdit.WidgetWidth)
		self.文本浏览框.document().setDefaultStyleSheet(文本样式表)
		self.堆叠容器 = PyQt5.QtWidgets.QStackedWidget()
		self.堆叠容器.addWidget(self.图片浏览)
		self.堆叠容器.addWidget(self.文本浏览框)
		布局 = PyQt5.QtWidgets.QVBoxLayout(self)
		布局.setContentsMargins(0, 0, 0, 0)
		布局.addWidget(self.堆叠容器)

	def 显示附件(self, 附件对象):
		"""显示一个附件对象；传入 None 时回到空白提示。"""
		if 附件对象 is None:
			self.堆叠容器.setCurrentIndex(1)
			self.文本浏览框.setPlainText("尚未选择附件")
			return
		if 附件对象.是否图片:
			self.堆叠容器.setCurrentIndex(0)
			self.图片浏览.设置图片(附件对象.文件路径)
		else:
			self.堆叠容器.setCurrentIndex(1)
			self.显示文本附件(附件对象)

	def 显示文本附件(self, 附件对象):
		"""读取文本内容并按需要渲染 Markdown。"""
		文本 = 基础工具.读取文本(附件对象.文件路径)
		if 文本 is None:
			self.文本浏览框.setPlainText("文本内容无法读取：%s" % (附件对象.文件名称 or 附件对象.名称))
			return
		HTML = None
		if 是否Markdown文件(附件对象.文件名称) or 是否Markdown文件(附件对象.名称):
			HTML = 渲染Markdown(文本)
		if HTML:
			self.文本浏览框.setHtml(HTML)
		else:
			self.文本浏览框.setPlainText(文本)


class 附件侧栏(PyQt5.QtWidgets.QWidget):
	"""主窗口右侧的附件浏览栏。"""

	# 注意：pyqtSignal 的名称会被 Qt 按 ASCII 编码，因此这里只能用英文名
	closeRequested = PyQt5.QtCore.pyqtSignal()

	def __init__(self, 父控件=None):
		super().__init__(父控件)
		self.当前附件 = None
		self.setObjectName("attachPanel")
		self.setMinimumWidth(260)
		self.setStyleSheet("#attachPanel { background-color: #FFFFFF; border-left: 1px solid #E3E3E3; }")
		self.构建界面()

	def 构建界面(self):
		"""搭建标题行、缺失提示、内容视图与来源路径。"""
		布局 = PyQt5.QtWidgets.QVBoxLayout(self)
		布局.setContentsMargins(12, 12, 12, 12)
		布局.setSpacing(8)
		标题行 = PyQt5.QtWidgets.QHBoxLayout()
		标题行.setSpacing(6)
		self.标题标签 = PyQt5.QtWidgets.QLabel("附件")
		self.标题标签.setStyleSheet("font-size: 15px; font-weight: bold; color: #1A1A1A;")
		新窗口按钮 = PyQt5.QtWidgets.QPushButton("独立窗口")
		新窗口按钮.setCursor(PyQt5.QtCore.Qt.PointingHandCursor)
		新窗口按钮.setToolTip("在单独的弹窗中打开当前附件")
		新窗口按钮.setStyleSheet("QPushButton { border: 1px solid #D0D0D0; border-radius: 6px; padding: 4px 10px; }"
			"QPushButton:hover { background-color: #F2F2F2; }")
		关闭按钮 = PyQt5.QtWidgets.QPushButton("关闭")
		关闭按钮.setCursor(PyQt5.QtCore.Qt.PointingHandCursor)
		关闭按钮.setToolTip("收起右侧附件栏")
		关闭按钮.setStyleSheet("QPushButton { border: 1px solid #D0D0D0; border-radius: 6px; padding: 4px 10px; }"
			"QPushButton:hover { background-color: #F2F2F2; }")
		标题行.addWidget(self.标题标签, 1)
		标题行.addWidget(新窗口按钮)
		标题行.addWidget(关闭按钮)
		self.提示标签 = PyQt5.QtWidgets.QLabel("")
		self.提示标签.setWordWrap(True)
		self.提示标签.setStyleSheet("color: #B26A00; font-size: 12px;")
		self.提示标签.hide()
		self.内容视图 = 附件内容视图()
		self.路径标签 = PyQt5.QtWidgets.QLabel("")
		self.路径标签.setWordWrap(True)
		self.路径标签.setTextInteractionFlags(PyQt5.QtCore.Qt.TextSelectableByMouse)
		self.路径标签.setStyleSheet("color: #8C8C8C; font-size: 11px;")
		布局.addLayout(标题行)
		布局.addWidget(self.提示标签)
		布局.addWidget(self.内容视图, 1)
		布局.addWidget(self.路径标签)
		# 说明：PyQt 连接信号时不接受中文名的方法，这里用 lambda 做一层薄封装
		关闭按钮.clicked.connect(lambda 选中=False: self.清空())
		新窗口按钮.clicked.connect(lambda 选中=False: self.在新窗口打开())
		关闭按钮.clicked.connect(self.closeRequested.emit)

	def 显示附件(self, 附件对象):
		"""在侧栏中显示一个附件。"""
		self.当前附件 = 附件对象
		if 附件对象 is None:
			self.标题标签.setText("附件")
			self.提示标签.hide()
			self.路径标签.setText("")
			self.内容视图.显示附件(None)
			return
		self.标题标签.setText(附件对象.显示标题)
		if 附件对象.是否缺失:
			self.提示标签.setText("未找到原文件，以下为占位内容：%s" % (附件对象.名称 or 附件对象.文件名称))
			self.提示标签.show()
		else:
			self.提示标签.hide()
		self.内容视图.显示附件(附件对象)
		self.路径标签.setText(附件对象.文件路径 or "（没有可用的文件路径）")

	def 清空(self):
		"""清掉当前附件，侧栏恢复空白状态。"""
		self.显示附件(None)

	def 在新窗口打开(self):
		"""把当前附件放到独立弹窗里浏览。"""
		if self.当前附件 is None:
			return
		弹窗 = 附件弹窗(self.当前附件, self)
		弹窗.exec_()


class 附件弹窗(PyQt5.QtWidgets.QDialog):
	"""独立的附件查看窗口，内容与右侧栏保持一致。"""

	def __init__(self, 附件对象, 父控件=None):
		super().__init__(父控件)
		self.setWindowTitle(附件对象.显示标题 if 附件对象 else "附件")
		self.resize(820, 640)
		布局 = PyQt5.QtWidgets.QVBoxLayout(self)
		布局.setContentsMargins(10, 10, 10, 10)
		布局.setSpacing(8)
		self.提示标签 = PyQt5.QtWidgets.QLabel("")
		self.提示标签.setWordWrap(True)
		self.提示标签.setStyleSheet("color: #B26A00; font-size: 12px;")
		self.提示标签.hide()
		self.内容视图 = 附件内容视图()
		self.路径标签 = PyQt5.QtWidgets.QLabel("")
		self.路径标签.setWordWrap(True)
		self.路径标签.setTextInteractionFlags(PyQt5.QtCore.Qt.TextSelectableByMouse)
		self.路径标签.setStyleSheet("color: #8C8C8C; font-size: 11px;")
		布局.addWidget(self.提示标签)
		布局.addWidget(self.内容视图, 1)
		布局.addWidget(self.路径标签)
		self.显示附件(附件对象)

	def 显示附件(self, 附件对象):
		"""显示指定附件，并在原文件缺失时给出提示。"""
		if 附件对象 is None:
			self.提示标签.hide()
			self.路径标签.setText("")
			self.内容视图.显示附件(None)
			return
		if 附件对象.是否缺失:
			self.提示标签.setText("未找到原文件，以下为占位内容：%s" % (附件对象.名称 or 附件对象.文件名称))
			self.提示标签.show()
		else:
			self.提示标签.hide()
		self.内容视图.显示附件(附件对象)
		self.路径标签.setText(附件对象.文件路径 or "（没有可用的文件路径）")
