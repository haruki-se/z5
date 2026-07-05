#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import sys

# --- GPIO 設定（好きな番号に変更可） ---
PIN1 = 17   # ソレノイド1
PIN2 = 22   # ソレノイド2
PIN3 = 27   # ソレノイド3
# -----------------------------------------

PULSE_TIME = 1.0  # パルス時間(秒) 好きに変更可

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN1, GPIO.OUT)
GPIO.setup(PIN2, GPIO.OUT)
GPIO.setup(PIN3, GPIO.OUT)

def pulse(pin):
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(PULSE_TIME)
    GPIO.output(pin, GPIO.LOW)

if len(sys.argv) < 3:
    print("使い方: sol3.py [1|2|3] [on|off|pulse]")
    GPIO.cleanup()
    sys.exit(0)

target = sys.argv[1]     # 1,2,3 のどれ
command = sys.argv[2]    # on/off/pulse

# 対象ピンを選択
if target == "1":
    pin = PIN1
elif target == "2":
    pin = PIN2
elif target == "3":
    pin = PIN3
else:
    print("ソレノイド番号は 1 / 2 / 3 です")
    GPIO.cleanup()
    sys.exit(0)

# コマンド実行
if command == "on":
    GPIO.output(pin, GPIO.HIGH)
elif command == "off":
    GPIO.output(pin, GPIO.LOW)
elif command == "pulse":
    pulse(pin)
else:
    print("コマンドは on / off / pulse です")

GPIO.cleanup()
