#!/bin/bash

# Check for a valid parameter
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [check|update]"
    exit 1
fi

ACTION=$1

if [ "$ACTION" != "check" ] && [ "$ACTION" != "update" ]; then
    echo "Invalid parameter. Use either 'check' or 'update'."
    exit 1
fi

if [ "$ACTION" == "check" ]; then
    echo "----- Checking System Settings -----"

    # 1. Check CPU governor for each CPU
    echo "CPU Governors:"
    for cpu in /sys/devices/system/cpu/cpu[0-9]*; do
        if [ -f "$cpu/cpufreq/scaling_governor" ]; then
            governor=$(cat "$cpu/cpufreq/scaling_governor")
            echo "  $(basename $cpu): $governor"
        else
            echo "  $(basename $cpu): (no scaling governor file)"
        fi
    done
    echo

    # 2. Check process priority (nice value) for uvicorn and gstreamer
    echo "Process Niceness:"
    for proc in uvicorn gstreamer; do
        pids=$(pgrep -f "$proc")
        if [ -z "$pids" ]; then
            echo "  No process found for $proc"
        else
            for pid in $pids; do
                ps -p $pid -o pid,comm,nice --no-headers | awk '{print "  PID: "$1", Process: "$2", Nice: "$3}'
            done
        fi
    done
    echo

    # 3. Check network settings
    echo "Network Settings:"
    sysctl net.core.rmem_max
    sysctl net.core.wmem_max
    sysctl net.ipv4.tcp_rmem
    sysctl net.ipv4.tcp_wmem
    echo

    # 4. Check wireless power saving setting on wlan0
    echo "Wireless Power Management (wlan0):"
    iwconfig wlan0 2>/dev/null | grep "Power Management"
    echo

    # 5. Check process scheduling policy for uvicorn and gstreamer
    echo "Process Scheduling Policy:"
    for proc in uvicorn gstreamer; do
        pids=$(pgrep -f "$proc")
        if [ -z "$pids" ]; then
            echo "  No process found for $proc"
        else
            for pid in $pids; do
                echo "  Scheduling for PID $pid:"
                sudo chrt -p $pid
            done
        fi
    done

    echo "----- Check Complete -----"

elif [ "$ACTION" == "update" ]; then
    echo "----- Applying System Optimizations -----"

    # 1. Set CPU governor to performance mode
    echo "Setting CPU governors to performance mode..."
    for cpu in /sys/devices/system/cpu/cpu[0-9]*; do
        if [ -f "$cpu/cpufreq/scaling_governor" ]; then
            echo "  $(basename $cpu): setting to performance"
            sudo sh -c "echo performance > $cpu/cpufreq/scaling_governor"
        else
            echo "  $(basename $cpu): scaling governor file not found"
        fi
    done
    echo

    # 2. Increase process priority (set nice value to -20) for uvicorn and gstreamer
    echo "Updating process niceness for uvicorn and gstreamer..."
    for proc in uvicorn gstreamer; do
        pids=$(pgrep -f "$proc")
        if [ -z "$pids" ]; then
            echo "  No process found for $proc"
        else
            for pid in $pids; do
                echo "  Setting PID $pid to nice -20"
                sudo renice -20 $pid
            done
        fi
    done
    echo

    # 3. Optimize network settings
    echo "Updating network settings..."
    sudo sysctl -w net.core.rmem_max=26214400
    sudo sysctl -w net.core.wmem_max=26214400
    sudo sysctl -w net.ipv4.tcp_rmem='4096 87380 26214400'
    sudo sysctl -w net.ipv4.tcp_wmem='4096 87380 26214400'
    echo

    # 4. Disable wireless power saving on wlan0
    echo "Disabling power management on wlan0..."
    sudo iwconfig wlan0 power off
    echo

    # 5. Set process scheduling policy to FIFO with priority 99 for uvicorn and gstreamer
    echo "Setting real-time scheduling (FIFO) for uvicorn and gstreamer..."
    for proc in uvicorn gstreamer; do
        pids=$(pgrep -f "$proc")
        if [ -z "$pids" ]; then
            echo "  No process found for $proc"
        else
            for pid in $pids; do
                echo "  Setting FIFO scheduling for PID $pid with priority 99"
                sudo chrt -f -p 99 $pid
            done
        fi
    done

    echo "----- System Optimizations Applied -----"
fi
