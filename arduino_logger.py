#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import os
import sys
from datetime import datetime
import serial

PORT = "/dev/ttyHS1"      # 아두이노 포트 (/dev/ttyACM0 등 환경에 맞게 수정)
BAUD = 115200             # 통신 속도
CSV_FILE = "sensor_data.csv"
HEADER = ["time", "fsr", "door_open", "rain", "umbrella_taken", "alert"]

# 1. 파일이 없으면 헤더 먼저 작성
if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADER)

# 2. 시리얼 포트 열기
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"✅ 아두이노 연결 성공 ({PORT}). 수신 대기 중... (Ctrl+C로 종료)")
except Exception as e:
    print(f"❌ 포트 연결 실패: {e}")
    sys.exit(1)

# 3. 데이터 실시간 수신 및 CSV 저장
with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(",")]

            # 5개(fsr,door_open,rain,umbrella_taken,alert)가 오면 현재 시간 자동 추가
            if len(parts) == 5:
                parts.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # 6개 규격에 맞을 때만 CSV 저장
            if len(parts) == 6:
                writer.writerow(parts)
                f.flush()
                print("수신:", parts)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
