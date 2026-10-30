import subprocess
import tempfile
import threading

from pathlib import Path
from gtts import gTTS

audio_lock = threading.Lock()

def light_text(text):
    text = text.strip()

    if not text or not audio_lock.acquire(blocking=False):
        return False

    worker = threading.Thread(
        target=create_and_play,
        args=(text,),
        daemon=True,
    )

    try:
        worker.start()
        return True

    except Exception as error:
        audio_lock.release()
        print(f"TTS 작업 시작 실패: {error}")
        return False

def create_and_play(text):
    try:
        with tempfile.TemporaryDirectory() as folder:
            audio_path = Path(folder) / "speech.mp3"

            tts = gTTS(
                text=text,
                lang="ko",
                timeout=(5, 15),
            )

            tts.save(str(audio_path))

            subprocess.run(
                ["mpg123", "-q", str(audio_path)],
                check=True,
                timeout=60,
            )

    except Exception as error:
        print(f"TTS 처리 실패: {error}")

    finally:
        audio_lock.release()