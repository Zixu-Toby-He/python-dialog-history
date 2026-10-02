import sys

import PyQt5.QtWidgets

import 驱动库

def main():
	应用实例 = PyQt5.QtWidgets.QApplication(sys.argv)
	聊天元数据   = 驱动库.读取聊天记录元数据()
	聊天显示窗口 = 驱动库.聊天记录可视化窗口(聊天元数据)
	聊天显示窗口.show()
	sys.exit(应用实例.exec_())

if __name__ == "__main__":
	main()
