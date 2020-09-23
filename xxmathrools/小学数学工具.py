#解决递归错误
#import sys
#sys.setrecursionlimit(6000)

import sys
from sympy import *
from sympy.abc import x,y,z,a,b,c
from PyQt5.QtWidgets import QWidget,QApplication
from UI_Widget import Ui_Widget

class my_Widget(QWidget):
    def __init__(self):
        super().__init__()
        self.ui=Ui_Widget()
        self.ui.setupUi(self)
    def on_pushButton_9_clicked(self):
        one=float(self.ui.lineEdit.text())
        anther=float(self.ui.lineEdit_2.text())
        answer=str(one+anther)
        self.ui.lineEdit_3.setText(answer)
    def on_pushButton_2_clicked(self):
        jianone=float(self.ui.lineEdit_4.text())
        jiananther=float(self.ui.lineEdit_5.text())
        jiananswer=str(jianone-jiananther)
        self.ui.lineEdit_6.setText(jiananswer)
    def on_pushButton_3_clicked(self):
        xone=float(self.ui.lineEdit_7.text())
        xanther=float(self.ui.lineEdit_8.text())
        xanswer=str(xone*xanther)
        self.ui.lineEdit_9.setText(xanswer)
    def on_pushButton_4_clicked(self):
        chuone=float(self.ui.lineEdit_10.text())
        chuanther=float(self.ui.lineEdit_11.text())
        chuanswer=str(chuone/chuanther)
        self.ui.lineEdit_12.setText(chuanswer)
    def on_pushButton_5_clicked(self):
        danjia=self.ui.spinBox.value()
        zhongliang=self.ui.spinBox_2.value()
        zongjia=danjia*zhongliang
        self.ui.spinBox_5.setValue(zongjia)
    def on_pushButton_6_clicked(self):
        huashidu1=self.ui.spinBox_3.value()
        sheshidu1=(huashidu1-32)/1.8
        self.ui.spinBox_4.setValue(sheshidu1)
    def on_pushButton_7_clicked(self):
        sheshidu2=self.ui.spinBox_6.value()
        huashidu2=sheshidu2*1.8+32
        self.ui.spinBox_7.setValue(huashidu2)
    def on_pushButton_8_clicked(self):
        fangcheng=self.ui.lineEdit_13.text()
        like=[fangcheng]
        aa=solve(like,[x])
        bb='x='+str(aa[x])
        self.ui.lineEdit_14.setText(bb)
if __name__ == "__main__":
    app=QApplication(sys.argv)
    try:
        simple=my_Widget()
    except TypeError:
        pass
    simple.show()
    simple.move(300,140)
    sys.exit(app.exec_())
    
