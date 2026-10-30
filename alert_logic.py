from task_processor import run_my_task

previous_door_open = None

def check_alert(door_open, umbrella_present, rain, text):
    global previous_door_open

    current_door_open = bool(door_open)

    if previous_door_open is None:
        previous_door_open = current_door_open
        return False

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
        result = run_my_task(text)
        return result is not False

    except Exception as error:
        print(f"TTS 호출 실패: {error}")
        return False