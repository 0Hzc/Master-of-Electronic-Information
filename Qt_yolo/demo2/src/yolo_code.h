#ifndef YOLO_CODE_H
#define YOLO_CODE_H

#include <QMainWindow>
#include <qtermwidget.h>
#include <QTimer>
#include <QDir>

class yolo_code : public QMainWindow
{
    Q_OBJECT

public:
    yolo_code(QWidget* parent = nullptr);
    ~yolo_code();

private slots:
    void handleFinished();

private:
    QTermWidget* terminal;
};

#endif // YOLO_CODE_H