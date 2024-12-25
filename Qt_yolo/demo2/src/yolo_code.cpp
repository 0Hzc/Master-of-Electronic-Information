#include "yolo_code.h"
#include <QVBoxLayout>
#include <QApplication>
#include <QDebug>
#include <QProcessEnvironment>
#include <QFontDatabase>
#include <QFile>
#include <QTextStream>

yolo_code::yolo_code(QWidget* parent)
    : QMainWindow(parent)
{
    // 创建中心部件
    QWidget* centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);
    
    // 创建垂直布局
    QVBoxLayout* layout = new QVBoxLayout(centralWidget);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);
    
    // 创建终端部件
    terminal = new QTermWidget(0, this);
    
    // 设置终端属性
    terminal->setColorScheme("Linux");
    
    // 设置字体
    QFont font = QFontDatabase::systemFont(QFontDatabase::FixedFont);
    font.setPointSize(11);
    terminal->setTerminalFont(font);
    
    // 设置滚动条
    terminal->setScrollBarPosition(QTermWidget::ScrollBarRight);
    terminal->setTerminalOpacity(1.0);
    
    // 设置环境变量
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    QStringList envList = env.toStringList();
    
    // 添加 Conda 相关环境变量
    QString condaPath = QDir::homePath() + "/anaconda3";  // 根据实际路径调整
    if (QDir(condaPath).exists()) {
        envList << "PATH=" + condaPath + "/bin:" + env.value("PATH");
        envList << "CONDA_PREFIX=" + condaPath;
        envList << "CONDA_DEFAULT_ENV=base";
        envList << "CONDA_EXE=" + condaPath + "/bin/conda";
        envList << "CONDA_PYTHON_EXE=" + condaPath + "/bin/python";
    }
    
    envList << "TERM=xterm-256color";
    terminal->setEnvironment(envList);
    
    // 设置 shell 程序
    terminal->setShellProgram("/bin/bash");
    QStringList args;
    args << "--login";
    terminal->setArgs(args);
    
    // 设置终端大小
    terminal->setTerminalSizeHint(true);
    terminal->setMinimumSize(400, 300);
    
    // 添加到布局
    layout->addWidget(terminal);
    
    // 连接信号
    connect(terminal, &QTermWidget::finished, this, &yolo_code::handleFinished);
    connect(terminal, &QTermWidget::copyAvailable, terminal, &QTermWidget::copyClipboard);
    
    // 设置窗口属性
    setWindowTitle("终端");
    resize(800, 600);
    
    // 启动终端并初始化 Conda
    terminal->startShellProgram();
    
    // 延迟执行 Conda 初始化命令
    QTimer::singleShot(1000, this, [this]() {
        QString condaInit = QString(
            "source ~/anaconda3/etc/profile.d/conda.sh\n"  // 根据实际路径调整
            "conda activate base\n"
        );
        terminal->sendText(condaInit);
    });
}

void yolo_code::handleFinished()
{
    qDebug() << "Terminal session finished";
    terminal->startShellProgram();
}

yolo_code::~yolo_code()
{
}