#!/bin/sh
cd modules

while sleep 3; do
    ps aux |grep garbage_collector.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "garbage_collector.py exited. Reboot..."
        ./garbage_collector.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start garbage_collector: $status"
        fi
    fi
    
    ps aux |grep exiftool.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "exiftool.py exited. Reboot..."
        ./exiftool.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start exiftool: $status"
        fi
    fi
    
    ps aux |grep strings.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "strings.py exited. Reboot..."
        ./strings.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start strings: $status"
        fi
    fi
    
    ps aux |grep foremost.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "foremost.py exited. Reboot..."
        ./foremost.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start foremost: $status"
        fi
    fi
    
    ps aux |grep binwalk.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "binwalk.py exited. Reboot..."
        ./binwalk.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start binwalk: $status"
        fi
    fi
    
    ps aux |grep view.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "view.py exited. Reboot..."
        ./view.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start view: $status"
        fi
    fi
    
    ps aux |grep outguess.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "outguess.py exited. Reboot..."
        ./outguess.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start outguess: $status"
        fi
    fi
    
    ps aux |grep steghide.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "steghide.py exited. Reboot..."
        ./steghide.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start steghide: $status"
        fi
    fi
    
    ps aux |grep zsteg.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "zsteg.py exited. Reboot..."
        ./zsteg.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start zsteg: $status"
        fi
    fi

    #ps aux |grep pcrt.py |grep -v grep
    #PROCESS_STATUS=$?
    #if [ $PROCESS_STATUS -ne 0 ]; then
    #    echo "pcrt.py exited. Reboot..."
    #    ./pcrt.py &
    #    status=$?
    #    if [ $status -ne 0 ]; then
    #        echo "Failed to start pcrt: $status"
    #    fi
    #fi

    ps aux |grep pngcheck.py |grep -v grep
    PROCESS_STATUS=$?
    if [ $PROCESS_STATUS -ne 0 ]; then
        echo "pngcheck.py exited. Reboot..."
        ./pngcheck.py &
        status=$?
        if [ $status -ne 0 ]; then
            echo "Failed to start pngcheck: $status"
        fi
    fi
    
done

