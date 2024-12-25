cmake_minimum_required(VERSION 3.10)

project(yolo_code VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt5 COMPONENTS Widgets Core Network REQUIRED)

# 添加 QTermWidget 支持
find_package(PkgConfig REQUIRED)
pkg_check_modules(QTERMWIDGET5 REQUIRED qtermwidget5)

add_executable(yolo_code
    src/main.cpp
    src/yolo_code.cpp
    src/yolo_code.h
)

target_include_directories(yolo_code PRIVATE 
    src
    ${QTERMWIDGET5_INCLUDE_DIRS}
)

target_link_libraries(yolo_code PRIVATE
    Qt5::Widgets
    Qt5::Core
    Qt5::Network
    ${QTERMWIDGET5_LIBRARIES}
)