#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[파일 1] weather_fetcher.py
- 공공데이터포털(data.go.kr) 기상청 단기예보 API 연동
- 위도/경도 -> 기상청 격자 변환(LCC) 자체 내장 (외부 의존성 없음)
- 우산 지참 판단(현재 비/눈 여부, 오늘 비 예보 시간대, 강수확률)에 필요한 정보만 분석하여
  TTS 스피커 출력용 안내 문자열을 생성하는 write_text() 함수 제공
"""

import datetime
import json
import math
import urllib.request
import urllib.parse
from typing import Tuple, Optional


# --- 1. 위경도 -> 기상청 격자(nx, ny) 자체 변환 (이전 파일 내용 통합) ---
def lat_lon_to_grid(lat: float, lon: float) -> Tuple[int, int]:
    """WGS84 위도, 경도를 기상청 LCC 격자(nx, ny)로 변환"""
    RE = 6371.00877  # 지구 반경 (km)
    GRID = 5.0       # 격자 간격 (km)
    SLAT1 = 30.0     # 투영 위도1 (degree)
    SLAT2 = 60.0     # 투영 위도2 (degree)
    OLON = 126.0     # 기준점 경도 (degree)
    OLAT = 38.0      # 기준점 위도 (degree)
    XO = 43          # 기준점 X좌표
    YO = 136         # 기준점 Y좌표

    DEGRAD = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lon * DEGRAD - olon

    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = math.floor(ra * math.sin(theta) + XO + 0.5)
    ny = math.floor(ro - ra * math.cos(theta) + YO + 0.5)
    return int(nx), int(ny)


# --- 2. 기상청 단기예보 발표 시각 계산 ---
def _get_base_datetime() -> Tuple[str, str]:
    now = datetime.datetime.now()
    cur_mins = now.hour * 60 + now.minute
    slots = [
        ("0200", 2 * 60 + 10),
        ("0500", 5 * 60 + 10),
        ("0800", 8 * 60 + 10),
        ("1100", 11 * 60 + 10),
        ("1400", 14 * 60 + 10),
        ("1700", 17 * 60 + 10),
        ("2000", 20 * 60 + 10),
        ("2300", 23 * 60 + 10)
    ]
    for time_str, min_val in reversed(slots):
        if cur_mins >= min_val:
            return now.strftime("%Y%m%d"), time_str
    yesterday = now - datetime.timedelta(days=1)
    return yesterday.strftime("%Y%m%d"), "2300"


# --- 3. 핵심 write_text() 함수 ---
def write_text(
    service_key: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    nx: int = 60,
    ny: int = 127
) -> str:
    """
    우산을 챙겨야 하는지 판단하여 스피커로 말할 안내 텍스트를 반환하는 함수
    :param service_key: 공공데이터포털 일반 인증키 (Decoding)
    :param lat: 위도 (입력 시 nx/ny로 자동 변환)
    :param lon: 경도 (입력 시 nx/ny로 자동 변환)
    :param nx: 기상청 X 격자 (기본값: 서울 60)
    :param ny: 기상청 Y 격자 (기본값: 서울 127)
    :return: TTS 스피커로 출력할 안내 문자열
    """
    # 위도/경도가 들어오면 기상청 격자로 자동 변환
    if lat is not None and lon is not None:
        nx, ny = lat_lon_to_grid(lat, lon)

    # API 키가 아직 설정되지 않은 경우 시뮬레이션 테스트 텍스트 반환
    if not service_key or "YOUR_DATA_GO_KR" in service_key:
        print("💡 [알림] config.json에 아직 공공데이터포털 service_key가 등록되지 않아 테스트 예시 문장으로 출력합니다.")
        return "현재는 비가 오지 않지만, 오늘 오후 4시경부터 비 예보가 있습니다. 최고 강수확률은 70퍼센트입니다. 우산을 챙기시기 바랍니다."

    base_date, base_time = _get_base_datetime()
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

    params = {
        "serviceKey": urllib.parse.unquote(service_key),
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": str(nx),
        "ny": str(ny)
    }

    req_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(req_url, headers={"User-Agent": "WeatherApp/2.0"})

    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode('utf-8'))
        
        # 기상청 응답 검증
        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            return f"기상청 오류 응답: {header.get('resultMsg', '알 수 없는 오류')}"

        items = data["response"]["body"]["items"]["item"]
    except Exception as e:
        return f"날씨 정보를 불러오지 못했습니다. 오류: {e}"

    # 오늘 남은 시간대 비 예보 분석
    now = datetime.datetime.now()
    today_str = now.strftime("%Y%m%d")
    cur_hour = now.hour

    is_raining_now = False
    rain_hours = []
    max_pop = 0

    for item in items:
        if item.get("fcstDate") != today_str:
            continue
        try:
            fcst_hour = int(item.get("fcstTime")[:2])
        except (ValueError, TypeError):
            continue

        category = item.get("category")
        val = item.get("fcstValue")

        # 1. 강수형태 (PTY: 1 비, 2 비/눈, 4 소나기)
        if category == "PTY":
            pty = int(val)
            if fcst_hour == cur_hour and pty in [1, 2, 4]:
                is_raining_now = True
            if fcst_hour >= cur_hour and pty in [1, 2, 4]:
                if fcst_hour not in rain_hours:
                    rain_hours.append(fcst_hour)

        # 2. 강수확률 (POP)
        elif category == "POP":
            pop = int(val)
            if fcst_hour >= cur_hour:
                if pop > max_pop:
                    max_pop = pop
                if pop >= 60 and fcst_hour not in rain_hours:
                    rain_hours.append(fcst_hour)

    rain_hours.sort()

    # --- 우산 안내 텍스트 생성 ---
    # 상황 1: 지금 바깥에 비가 내리는 경우
    if is_raining_now:
        return "현재 바깥에 비가 내리고 있습니다. 외출하실 때 우산을 꼭 챙기세요."

    # 상황 2: 오늘 남은 시간 중 비 예보가 있는 경우
    if rain_hours:
        first_h = rain_hours[0]
        time_text = f"오후 {first_h - 12}시" if first_h >= 12 else f"오전 {first_h}시"
        return f"현재는 비가 오지 않지만, 오늘 {time_text}경부터 비 예보가 있습니다. 최고 강수확률은 {max_pop}퍼센트입니다. 우산을 챙기시기 바랍니다."

    # 상황 3: 오늘 하루 동안 비 소식이 없는 경우
    return "오늘 하루 동안 비 소식이 없습니다. 우산 없이 외출하셔도 좋습니다."


if __name__ == "__main__":
    test_key = "YOUR_DATA_GO_KR_DECODING_API_KEY"
    print("생성된 문장:", write_text(test_key, lat=37.5665, lon=126.9780))
