#!/bin/bash

# 保存原始的 LD_LIBRARY_PATH
ORIGINAL_LD_LIBRARY_PATH=$LD_LIBRARY_PATH

# 清除 Anaconda 相关的路径
unset CONDA_PREFIX
unset CONDA_DEFAULT_ENV
PATH=$(echo $PATH | tr ':' '\n' | grep -v "anaconda" | tr '\n' ':')
LD_LIBRARY_PATH=$(echo $LD_LIBRARY_PATH | tr ':' '\n' | grep -v "anaconda" | tr '\n' ':')

# 添加系统库路径
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

# 运行程序
./yolo_code

# 恢复环境
export LD_LIBRARY_PATH=$ORIGINAL_LD_LIBRARY_PATH