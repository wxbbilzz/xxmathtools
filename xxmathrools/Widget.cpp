#include "Widget.h"
#include "ui_Widget.h"

Widget::Widget(QWidget *parent)
    : QWidget(parent)
    , ui(new Ui::Widget)
{
    ui->setupUi(this);
}

Widget::~Widget()
{
    delete ui;
}


void Widget::on_pushButton_2_clicked()
{

}

void Widget::on_pushButton_3_clicked()
{

}

void Widget::on_pushButton_4_clicked()
{

}

void Widget::on_pushButton_5_clicked()
{

}

void Widget::on_pushButton_6_clicked()
{

}

void Widget::on_pushButton_7_clicked()
{

}
