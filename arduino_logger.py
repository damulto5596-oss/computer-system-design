#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arduino_logger.py
- 여러 포트(시리얼 포트 또는 소켓 포트)에서 각 센서 값을 독립적으로 수신
- 최신 상태를 유지하며 time,fsr,door_open,rain,umbrella_taken,alert 형식으로 CSV에 실시간 저장
"""

import csv
import os
import threading
import time
from datetime import datetime

# 1. 각 센서가 데이터를 보내오는 포트 설정
# - 시리얼 포트: "/dev/ttyUSB0", "/dev/ttyACM0" 등 문자열
# - 네트워크 소켓 포트: 5001, 5002 등 숫자(int)
SENSOR_PORTS = {
    "fsr": "/dev/ttyUSB0",            # 압력 센서 포트
    "door_open": "/dev/ttyUSB1",      # 문 열림 센서 포트
    "rain": "/dev/ttyACM0",           # 비 예보 포트
    "umbrella_taken": "/dev/ttyACM1", # 우산 상태 포트
    "alert": "/dev/ttyHS1",           # 경보 발생 포트
}

BAUD = 115200
CSV_FILE = "sensor_data.csv"
HEADER = ["time", "fsr", "door_open", "rain", "umbrella_taken", "alert"]

# 모든 센서의 최신 값을 보관하는 딕셔너리
state = {k: 0 for k in SENSOR_PORTS}
lock = threading.Lock()

# CSV 헤더 작성 (파일이 없을 때만)
if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADER)


def save_to_csv():
    """센서 값이 하나라도 갱신되면 CSV 파일에 현재 시각과 함께 전체 상태를 한 줄 기록"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [now, state["fsr"], state["door_open"], state["rain"], state["umbrella_taken"], state["alert"]]
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)
        f.flush()
    print(f"[{now}] 갱신 기록: {row}")


def listen_serial(sensor_name, port_path):
    """시리얼 포트 수신 스레드"""
    import serial
    try:
        ser = serial.Serial(port_path, BAUD, timeout=1)
        print(f"✅ [{sensor_name}] 시리얼 연결 성공: {port_path}")
    except Exception as e:
        print(f"❌ [{sensor_name}] 시리얼 연결 실패 ({port_path}): {e}")
        return

    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            with lock:
                state[sensor_name] = line
                save_to_csv()


def listen_socket(sensor_name, port_num):
    """UDP 소켓 포트 수신 스레드 (다른 파이썬/프로세스에서 전송할 때)"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port_num))
    print(f"✅ [{sensor_name}] 소켓 포트 대기 중: {port_num}")

    while True:
        data, _ = sock.recvfrom(1024)
        val = data.decode("utf-8", errors="ignore").strip()
        if val:
            with lock:
                state[sensor_name] = val
                save_to_csv()


# 2. 각 포트별로 독립된 스레드를 띄워 동시에 수신
for sensor_name, port in SENSOR_PORTS.items():
    if isinstance(port, int) or (isinstance(port, str) and port.isdigit()):
        # 포트 번호가 숫자면 소켓 수신
        t = threading.Thread(target=listen_socket, args=(sensor_name, int(port)), daemon=True)
    else:
        # 포트 번호가 문자열(/dev/tty...)이면 시리얼 수신
        t = threading.Thread(target=listen_serial, args=(sensor_name, str(port)), daemon=True)
    t.start()

print("=" * 60)
print("📡 모든 센서 포트 수신 대기 중... (종료: Ctrl + C)")
print("=" * 60)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n수신을 종료합니다.")
