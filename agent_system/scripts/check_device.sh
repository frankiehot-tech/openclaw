#!/bin/bash
# check_device.sh - 设备状态检查脚本

echo "========================================"
echo "       ADB 设备状态检查"
echo "========================================"
echo ""

# 检查 adb 是否可用
echo "[1] 检查 ADB..."
if command -v adb &> /dev/null; then
    ADB_VERSION=$(adb version | head -n 1)
    echo "✓ ADB 已安装: $ADB_VERSION"
else
    echo "✗ ADB 未安装或不在 PATH 中"
    exit 1
fi

echo ""
echo "[2] 设备列表..."
adb devices -l

echo ""
echo "[3] 在线设备详情..."

# 获取设备列表
DEVICES=$(adb devices | grep "device$" | cut -f1)

if [ -z "$DEVICES" ]; then
    echo "✗ 没有在线设备"
    exit 1
fi

for DEVICE in $DEVICES; do
    echo "----------------------------------------"
    echo "设备: $DEVICE"
    echo "----------------------------------------"
    
    # 设备型号
    MODEL=$(adb -s $DEVICE shell getprop ro.product.model 2>/dev/null)
    echo "型号: $MODEL"
    
    # Android 版本
    ANDROID_VERSION=$(adb -s $DEVICE shell getprop ro.build.version.release 2>/dev/null)
    echo "Android: $ANDROID_VERSION"
    
    # 屏幕分辨率
    SCREEN_SIZE=$(adb -s $DEVICE shell wm size 2>/dev/null)
    echo "屏幕: $SCREEN_SIZE"
    
    # 电池状态
    BATTERY=$(adb -s $DEVICE shell dumpsys battery | grep level | cut -d: -f2)
    echo "电量: $BATTERY%"
    
    # 屏幕状态
    SCREEN_STATE=$(adb -s $DEVICE shell dumpsys power | grep "Display Power" | cut -d: -f2 | tr -d ' ')
    echo "屏幕: $SCREEN_STATE"
    
    echo ""
done

echo "========================================"
echo "         检查完成"
echo "========================================"