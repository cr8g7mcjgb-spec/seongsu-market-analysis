"""
성수동 상권분석 데이터 수집기
────────────────────────────
수집 항목:
  1. 서울 실시간 도시데이터 (유동인구·혼잡도)
  2. 자치구별 택배·배송 건수 (소비 활력 프록시)
  3. 서울 생활인구 (행정동별 시간대별)
  4. 소상공인 상권 정보 (유동인구·업종)

사용법:
  python collect_data.py
  python collect_data.py --schedule  # 자동 반복 수집
"""

import os
import json
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────
SEOUL_KEY    = os.getenv("SEOUL_API_KEY", "")
SBI_KEY      = os.getenv("SBI_KEY", "")
TARGET_AREA  = os.getenv("TARGET_AREA", "성수동")
TARGET_GU    = os.getenv("TARGET_GU_CD", "11200")       # 성동구
ADM_CODE     = os.getenv("TARGET_ADM_CODE", "1120068000") # 성수동
TARGET_LAT   = float(os.getenv("TARGET_LAT", "37.5477"))
TARGET_LNG   = float(os.getenv("TARGET_LNG", "127.0554"))

SEOUL_BASE   = "http://openapi.seoul.go.kr:8088"
DATA_DIR     = Path("data")
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ── 헬퍼 ──────────────────────────────────────────────────────

def seoul_api(service: str, start: int = 1, end: int = 1000) -> list:
    """서울 열린데이터광장 공통 호출"""
    if not SEOUL_KEY:
        log.warning("SEOUL_API_KEY 미설정 — 샘플 데이터 반환")
        return []
    url = f"{SEOUL_BASE}/{SEOUL_KEY}/json/{service}/{start}/{end}"
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        svc = data.get(service, {})
        if isinstance(svc, dict):
            return svc.get("row", [])
    except Exception as e:
        log.error(f"{service} 호출 실패: {e}")
    return []


def sbi_api(endpoint: str, params: dict) -> dict:
    """소상공인진흥공단 API 호출"""
    if not SBI_KEY:
        log.warning("SBI_KEY 미설정 — 소상공인 API 건너뜀")
        return {}
    base = "https://apis.data.go.kr/B553077/api/open/sdsc2"
    params["serviceKey"] = SBI_KEY
    params["type"] = "json"
    try:
        r = requests.get(f"{base}/{endpoint}", params=params, timeout=20)
        return r.json()
    except Exception as e:
        log.error(f"소상공인 API 실패: {e}")
    return {}


# ── 수집 함수 ──────────────────────────────────────────────────

def collect_city_data() -> pd.DataFrame:
    """
    [1] 서울 실시간 도시데이터
    115개 주요 장소 혼잡도·유동인구 스냅샷
    성수동/성동구 포함 데이터 필터링
    """
    log.info("[1] 실시간 도시데이터 수집 중...")
    rows = []
    for svc in ["SeoulRtd.citydata", "citydata_ppltn", "CITYDATA_PPLTN"]:
        rows = seoul_api(svc)
        if rows:
            break
        time.sleep(0.3)

    if not rows:
        log.warning("도시데이터 없음 — 샘플 데이터 사용")
        rows = _sample_city_data()

    df = pd.DataFrame(rows)
    df["collected_at"] = datetime.now().isoformat()

    # 성동구 / 성수 관련 필터
    if "AREA_NM" in df.columns:
        seongsu = df[df["AREA_NM"].str.contains("성수|성동", na=False)]
        log.info(f"  성수동 관련 장소: {len(seongsu)}개 / 전체 {len(df)}개")
    
    out = DATA_DIR / "city_data.json"
    df.to_json(out, orient="records", force_ascii=False)
    log.info(f"  저장: {out}")
    return df


def collect_delivery_stats() -> pd.DataFrame:
    """
    [2] 자치구별 배송건수 — 성동구 소비 활력 지수
    쿠팡이츠 포함 전체 배달 수요 유추 가능
    """
    log.info("[2] 배송 통계 수집 중 (성동구 소비 활력)...")
    rows = []
    for svc in ["DeliveryInfo", "LIVING_LOGISTICS", "LivingLogisticsInfo"]:
        rows = seoul_api(svc)
        if rows:
            break
        time.sleep(0.3)

    if not rows:
        log.warning("배송 데이터 없음 — 샘플 데이터 사용")
        rows = _sample_delivery_data()

    df = pd.DataFrame(rows)
    df["collected_at"] = datetime.now().isoformat()

    out = DATA_DIR / "delivery_stats.json"
    df.to_json(out, orient="records", force_ascii=False)
    log.info(f"  저장: {out}")
    
    # 성동구 배송량 출력
    gu_col = next((c for c in df.columns if "GU" in c.upper() or "구" in c), None)
    if gu_col:
        seongdong = df[df[gu_col].str.contains("성동", na=False)]
        if not seongdong.empty:
            log.info(f"  성동구 배송 데이터: {len(seongdong)}행")
    return df


def collect_living_population() -> dict:
    """
    [3] 서울 생활인구 — 성수동 시간대별 인구
    버스·지하철 이용자 포함 유동인구 추정
    """
    log.info("[3] 생활인구 수집 중 (성수동 시간대별)...")
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    hour_str = str(now.hour).zfill(2)

    url = (
        f"{SEOUL_BASE}/{SEOUL_KEY}/json/RtmddpMobilityStats"
        f"/1/100/{ADM_CODE}/{date_str}{hour_str}00"
    ) if SEOUL_KEY else ""

    result = {"adm_code": ADM_CODE, "area": TARGET_AREA, "hour": hour_str, "date": date_str}

    if url:
        try:
            r = requests.get(url, timeout=20)
            data = r.json()
            result["raw"] = data
            log.info(f"  생활인구 수집 완료 (성수동 {hour_str}시)")
        except Exception as e:
            log.error(f"  생활인구 API 실패: {e}")
            result["error"] = str(e)
    else:
        result["error"] = "SEOUL_API_KEY 미설정"
        log.warning("  생활인구 API 건너뜀")

    out = DATA_DIR / f"living_pop_{date_str}_{hour_str}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f"  저장: {out}")
    return result


def collect_commercial_area() -> dict:
    """
    [4] 소상공인 상권 정보 — 성수동 반경 500m
    업종별 유동인구, 점포 수, 상권 유형
    """
    log.info("[4] 소상공인 상권 수집 중 (성수동 반경 500m)...")
    result = sbi_api("baroApi", {
        "cx": TARGET_LNG,
        "cy": TARGET_LAT,
        "radius": 500,
        "numOfRows": 20,
    })

    out = DATA_DIR / "commercial_area.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f"  저장: {out}")
    return result


# ── 샘플 데이터 (API 키 없을 때) ─────────────────────────────

def _sample_city_data() -> list:
    return [
        {"AREA_NM": "성수카페거리", "AREA_CONGEST_LVL": "약간 붐빔", "PPLTN_MIN": 3000, "PPLTN_MAX": 4000},
        {"AREA_NM": "서울숲",      "AREA_CONGEST_LVL": "보통",      "PPLTN_MIN": 2000, "PPLTN_MAX": 3000},
        {"AREA_NM": "성수역",      "AREA_CONGEST_LVL": "약간 붐빔", "PPLTN_MIN": 4000, "PPLTN_MAX": 5000},
    ]

def _sample_delivery_data() -> list:
    return [
        {"GU_NM": "성동구", "DLVR_CNT": 284000, "YEAR_MONTH": "202406"},
        {"GU_NM": "강남구", "DLVR_CNT": 467000, "YEAR_MONTH": "202406"},
        {"GU_NM": "마포구", "DLVR_CNT": 267000, "YEAR_MONTH": "202406"},
    ]


# ── 메인 ──────────────────────────────────────────────────────

def run_all():
    """전체 데이터 수집 실행"""
    print("\n" + "="*50)
    print(f"🏪 성수동 상권분석 데이터 수집 시작")
    print(f"   시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*50 + "\n")

    results = {}
    results["city_data"]        = collect_city_data()
    results["delivery_stats"]   = collect_delivery_stats()
    results["living_population"] = collect_living_population()
    results["commercial_area"]  = collect_commercial_area()

    print("\n" + "="*50)
    print("✅ 수집 완료! analyze.py를 실행해 Claude 분석을 받으세요.")
    print("   python analyze.py")
    print("="*50 + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true", help="1시간마다 자동 수집")
    args = parser.parse_args()

    if args.schedule:
        import schedule
        log.info("⏰ 자동 수집 모드 시작 (1시간 간격)")
        schedule.every(1).hours.do(run_all)
        run_all()  # 즉시 1회 실행
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_all()
