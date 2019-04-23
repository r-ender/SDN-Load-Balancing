import os
import sys
from PyQt4 import QtCore, QtGui, Qt


from time import strftime


# create a MainWindow and set it as central widget
class MainWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.form_widget = FormWidget(self)
	self.GUIinit()
        _widget = QtGui.QWidget()
        _layout = QtGui.QVBoxLayout(_widget)
        _layout.addWidget(self.form_widget)
        self.setCentralWidget(_widget)

    # set the geometry and title of the main window 	
    def GUIinit(self):
	self.title = "SDN-Gui"
	self.top = 60	#set y-position
	self.left = 0	#set x-position
	self.width = 900
	self.height = 675
	self.setWindowIcon(QtGui.QIcon("web.png"))
	self.setWindowTitle(self.title)
	self.setGeometry(self.top, self.left, self.width, self.height)


#add widgets to the main window
class FormWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        super(FormWidget, self).__init__(parent)
	self.init_timer()
	self.arrived_packets()
	#self.slide()
	#self.loadbar()
	#self.loadbar2()

    def init_timer(self):
	#update the roles every 1000ms 
	self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update) 
        self.timer.start(1000)


    def paintEvent(self, event):
	#role is role of controllers in respect to switches
	# the roles are printed inside c1/c2_role.csv
	ctrl = open("c1_role.csv", "r")
	temp_ctrl1 = ctrl.read()
	ctrl1 = str(temp_ctrl1)
	ctrl.close()

	ctrl = open("c2_role.csv", "r")
	temp_ctrl2 = ctrl.read()
	ctrl2 = str(temp_ctrl2)
	ctrl.close()

	#open the networkX generated topology image and color the controller-switch links according to their roles
        painter = QtGui.QPainter(self)
        pixmap = QtGui.QPixmap("mult_ctrl_topo.png")
        painter.drawPixmap(self.rect(), pixmap)
	if ctrl1 == str(['MASTER', 'MASTER']):
		
        	pen = QtGui.QPen(QtCore.Qt.green, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,264,238,158)

        	pen = QtGui.QPen(QtCore.Qt.green, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,158,663,264)

		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,663,264)

		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,663,264)

	if ctrl1 == str(['MASTER', 'SLAVE']) and ctrl2 != str(['MASTER','SLAVE']):

		pen = QtGui.QPen(QtCore.Qt.green, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,264,238,158)

		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,158,663,264)

	if ctrl1 == str(['SLAVE', 'MASTER']) and ctrl2 != str(['SLAVE', 'MASTER']):

		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,264,238,158)

        	pen = QtGui.QPen(QtCore.Qt.green, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,158,663,264)
		

	if ctrl1 == str(['SLAVE','SLAVE']) and ctrl2 != str(['SLAVE','SLAVE']):
        	pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,264,238,158)

        	pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,158,663,264)

	if ctrl2 == str(['MASTER','MASTER']):
		pen = QtGui.QPen(QtCore.Qt.green, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,663,264)

		pen = QtGui.QPen(QtCore.Qt.green, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,238,264)

		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,264,238,158)

        	pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(238,158,663,264)

	if ctrl2 == str(['MASTER','SLAVE']) and ctrl1 != str(['MASTER','SLAVE']):

		pen = QtGui.QPen(QtCore.Qt.green, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,238,264)

		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,663,264) 


	if ctrl2 == str(['SLAVE','MASTER']) and ctrl1 != str(['SLAVE', 'MASTER']):
		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,238,264)

		pen = QtGui.QPen(QtCore.Qt.green, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,663,264)		

	if ctrl2 == str(['SLAVE', 'SLAVE']) and ctrl1 != str(['SLAVE','SLAVE']):

		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,663,264)

		pen = QtGui.QPen(QtCore.Qt.red, 10, QtCore.Qt.SolidLine)
		painter.setPen(pen)
        	painter.drawLine(663,158,663,264)

    #in newest version, slider to scale the max.threshold and load-bars to show current load relation skipped to not overload the GUI too much   
    def slide(self):
	sld = QtGui.QSlider(QtCore.Qt.Horizontal, self)
	sld.setMinimum(0)
	sld.setMaximum(50)
	sld.setTickInterval(10)
	lcd = QtGui.QLCDNumber(self)

	l1 = QtGui.QLabel('Controller-Load Threshold', self)
	l1.setFont(QtGui.QFont('SansSerif',10,QtGui.QFont.Bold))
	l1.setGeometry(QtCore.QRect(375,310,300,40))

	hbox = QtGui.QVBoxLayout()
	hbox.addWidget(sld)
	hbox.addWidget(lcd)
	hbox.setGeometry(QtCore.QRect(390,340,150,80))	
	sld.valueChanged.connect(lcd.display)

    def loadbar(self):
	pbar = QtGui.QProgressBar(self)
	pbar.setGeometry(170,110,30,150)
	pbar.setOrientation(QtCore.Qt.Vertical)
	pbar.setValue(30)
	l1 = QtGui.QLabel('Ctrl.-Load\n    in\n   pps', self)
	l1.setFont(QtGui.QFont('SansSerif',12,QtGui.QFont.Bold))
	l1.setGeometry(QtCore.QRect(60,60,100,250))
	l2 = QtGui.QLabel('0_',self)
	l2.setFont(QtGui.QFont('SansSerif',12))
	l2.setGeometry(QtCore.QRect(145,125,100,250))
	l3 = QtGui.QLabel('5_',self)
	l3.setFont(QtGui.QFont('SansSerif',12))
	l3.setGeometry(QtCore.QRect(145,-22,100,250))


    def loadbar2(self):
	pbar = QtGui.QProgressBar(self)
	pbar.setGeometry(700,110,30,150)
	pbar.setOrientation(QtCore.Qt.Vertical)
	pbar.setValue(30)
	l1 = QtGui.QLabel('Ctrl.-Load\n    in\n   pps', self)
	l1.setFont(QtGui.QFont('SansSerif',12,QtGui.QFont.Bold))
	l1.setGeometry(QtCore.QRect(750,60,100,250))
	l2 = QtGui.QLabel('_0',self)
	l2.setFont(QtGui.QFont('SansSerif',12))
	l2.setGeometry(QtCore.QRect(735,125,100,250))
	l3 = QtGui.QLabel('_5',self)
	l3.setFont(QtGui.QFont('SansSerif',12))
	l3.setGeometry(QtCore.QRect(735,-22,100,250))
	
    # counts the arrived packets for the controllers and shows them in LCD-displays
    def arrived_packets(self):
	lcd1 = QtGui.QLCDNumber(self)
	lcd2 = QtGui.QLCDNumber(self)
	packets = open("packet_in_counter_1.csv", "r")
	packets1 = packets.read()
	packets.close()

	packets = open("packet_in_counter_2.csv", "r")
	packets2 = packets.read()
	packets.close()

	lcd1.display(packets1)
	lcd2.display(packets2)

	hbox = QtGui.QVBoxLayout()
	hbox.addWidget(lcd1)
	hbox.setGeometry(QtCore.QRect(100,110,100,50))	


	hbox = QtGui.QVBoxLayout()
	hbox.addWidget(lcd2)
	hbox.setGeometry(QtCore.QRect(705,110,100,50))	

	l1 = QtGui.QLabel('packet-in\n  since\n  start', self)
	l1.setFont(QtGui.QFont('SansSerif',12,QtGui.QFont.Bold))
	l1.setGeometry(QtCore.QRect(109,65,100,250))

	l2 = QtGui.QLabel('packet-in\n  since\n  start', self)
	l2.setFont(QtGui.QFont('SansSerif',12,QtGui.QFont.Bold))
	l2.setGeometry(QtCore.QRect(714,65,100,250))

	#print "go through arrived_packets for " + str(h) + "th time"	


def main():
    app = QtGui.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec_()	#application enters main loop

if __name__ == '__main__':
    sys.exit(main())
