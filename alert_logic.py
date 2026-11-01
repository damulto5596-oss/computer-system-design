from task_processor import run_my_task


previous_door_open = None


def check_alert(door_open, umbrella_present, rain, text):
    global previous_door_open

    current_door_open = bool(door_open)

    # 첫 호출에서는 현재 문 상태만 저장
    if previous_door_open is None:
        previous_door_open = current_door_open
        return False

    # 닫힘 → 열림 전환 확인
    just_opened = (
        previous_door_open is False
        and current_door_open is True
    )

    previous_door_open = current_door_open

    if not just_opened:
        return False

    if rain != 1 or umbrella_present != 1:
        return False

    text = text.strip()

    if not text:
        return False

    try:
        return run_my_task(text)

    except Exception as error:
        print(f"TTS 호출 실패: {error}")
        return False
