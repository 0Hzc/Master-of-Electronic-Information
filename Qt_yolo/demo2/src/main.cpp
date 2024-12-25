#include "yolo_code.h"
#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    yolo_code w;
    w.show();
    return a.exec();
}