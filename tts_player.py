import io
import struct
import subprocess
import threading

import serial
from gtts import gTTS


SERIAL_PORT = "실제 시리얼 포트 입력"
BAUD_RATE = 115200

SAMPLE_RATE = 8000
BITS_PER_SAMPLE = 8
CHANNELS = 1

audio_lock = threading.Lock()


def light_text(text):
    text = text.strip()

    if not text or not audio_lock.acquire(blocking=False):
        return False

    try:
        # 1. 안내 문자열을 MP3 데이터로 변환
        audio_buffer = io.BytesIO()

        tts = gTTS(text=text, lang="ko")
        tts.write_to_fp(audio_buffer)

        mp3_data = audio_buffer.getvalue()

        # 2. MP3 → 8kHz / 8비트 unsigned / 모노 PCM 변환
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-i", "pipe:0",
                "-ar", str(SAMPLE_RATE),
                "-ac", str(CHANNELS),
                "-c:a", "pcm_u8",
                "-f", "u8",
                "pipe:1",
            ],
            input=mp3_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if result.returncode != 0:
            error_message = result.stderr.decode(
                "utf-8",
                errors="replace",
            )
            raise RuntimeError(
                f"PCM 변환 실패: {error_message}"
            )

        pcm_data = result.stdout

        if not pcm_data:
            raise RuntimeError("변환된 PCM 데이터가 없습니다.")

        # 3. 시리얼 연결
        with serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=10,
            write_timeout=30,
        ) as connection:

            # 아두이노의 수신 준비 응답 확인
            ready = connection.read_until(b"\n")

            if ready.strip() != b"READY":
                raise RuntimeError(
                    "아두이노의 READY 응답이 없습니다."
                )

            # 4. 헤더 전송
            # PCM 표시: 3바이트
            # 샘플링 주파수: 4바이트
            # 비트 깊이: 1바이트
            # 채널 수: 1바이트
            # PCM 데이터 크기: 4바이트
            # 숫자는 빅엔디언
            header = b"PCM" + struct.pack(
                ">IBBI",
                SAMPLE_RATE,
                BITS_PER_SAMPLE,
                CHANNELS,
                len(pcm_data),
            )

            connection.write(header)

            # 5. PCM 본문 전송
            for start in range(0, len(pcm_data), 512):
                connection.write(
                    pcm_data[start:start + 512]
                )

            connection.flush()

            # 6. 수신 완료 응답 확인
            response = connection.read_until(b"\n")

            if response.strip() != b"OK":
                raise RuntimeError(
                    "PCM 수신 완료 응답이 없습니다."
                )

        print(
            f"PCM 전송 완료: "
            f"{len(pcm_data)}바이트, "
            f"약 {len(pcm_data) / SAMPLE_RATE:.2f}초"
        )

        return True

    except Exception as error:
        print(f"음성 생성·전송 실패: {error}")
        return False

    finally:
        audio_lock.release()
