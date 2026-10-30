#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[파일 2] arduino_speaker.py
- weather_fetcher.py의 write_text()를 호출하여 우산 안내 텍스트 수신
- config.json 자동 감지 및 템플릿 자동 생성 기능 통합
- 아두이노 Q (Qualcomm Linux MPU) 및 PC 환경 완벽 호환
- 아두이노 UNO Q (STM32 MCU) 내부 통신(Bridge RPC & UART Serial) 통합
"""

import sys
import os
import subprocess
import json

# 1. 파일 1에서 write_text 함수 import
from weather_fetcher import write_text

# 기본 설정 템플릿
DEFAULT_CONFIG = {
    "api_key": "YOUR_DATA_GO_KR_DECODING_API_KEY",
    "location": {
        "city_name": "서울특별시청",
        "use_lat_lon": True,
        "latitude": 37.5665,
        "longitude": 126.9780,
        "grid_nx": 60,
        "grid_ny": 127
    }
}


def load_or_create_config(config_path: str) -> dict:
    """설정 파일이 없으면 기본 템플릿을 자동 생성하고 불러옴"""
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"📄 새로운 설정 파일이 생성되었습니다: {config_path}")
        return DEFAULT_CONFIG

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG


def speak_text(text: str):
    """스피커를 통해 한국어 TTS 음성 출력 (Windows & Linux 자동 지원)"""
    print(f"\n📢 [TTS 스피커 방송] \"{text}\"")

    # 1. Windows 환경: 내장 SAPI SpeechSynthesizer 즉시 실행
    if sys.platform.startswith("win"):
        safe_text = text.replace("'", "''")
        cmd = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{safe_text}');"
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd])
        return

    # 2. Linux (아두이노 Q 환경)
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="ko")
        tts.save("/tmp/weather.mp3")
        subprocess.run(["mpg123", "-q", "/tmp/weather.mp3"])
    except Exception as e:
        print(f"오디오 재생 오류: {e}")


def send_to_arduino(has_rain_warning: bool):
    """
    아두이노 Q의 STM32 MCU로 신호 전송
    (App Lab Bridge RPC 및 내부 UART /dev/ttyHS1 모두 지원)
    """
    sound_code = 1 if has_rain_warning else 0

    # 방식 A: Arduino App Lab Bridge (RPC)
    try:
        from arduino.app_utils import Bridge
        Bridge.call("play_weather_audio", sound_code)
        print(f"   [아두이노 Q Bridge RPC 전송] sound_code={sound_code}")
        return
    except ImportError:
        pass

    # 방식 B: 내부 고속 UART Serial (/dev/ttyHS1)
    uart_port = "/dev/ttyHS1"
    if os.path.exists(uart_port):
        try:
            import serial
            with serial.Serial(uart_port, 115200, timeout=1) as ser:
                ser.write(f"PLAY:{sound_code}\n".encode("utf-8"))
            print(f"   [아두이노 Q UART 전송] PLAY:{sound_code}")
            return
        except Exception:
            pass


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, "config.json")

    # 1. 설정 로드 (파일이 없어도 자동 생성되어 절대 오류 나지 않음)
    cfg = load_or_create_config(config_file)
    service_key = cfg.get("api_key", "YOUR_DATA_GO_KR_DECODING_API_KEY")

    loc = cfg.get("location", {})
    lat = loc.get("latitude") if loc.get("use_lat_lon", True) else None
    lon = loc.get("longitude") if loc.get("use_lat_lon", True) else None
    nx = int(loc.get("grid_nx", 60))
    ny = int(loc.get("grid_ny", 127))

    # 2. weather_fetcher.py의 write_text() 호출!
    spoken_script = write_text(
        service_key=service_key,
        lat=lat,
        lon=lon,
        nx=nx,
        ny=ny
    )

    # 3. 우산 경보 여부 판단 (비 소식이 있으면 1, 없으면 0)
    is_rain = "우산을 챙기" in spoken_script or "비가 내리고 있습니다" in spoken_script

    # 4. 아두이노 보드로 신호 전송 및 스피커로 TTS 음성 출력
    send_to_arduino(has_rain_warning=is_rain)
    speak_text(spoken_script)


if __name__ == "__main__":
    main()
