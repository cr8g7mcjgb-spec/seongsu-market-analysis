"""
성수동 상권분석 완전 자동화 스케줄러
──────────────────────────────────
- 매시간: 유동인구·혼잡도 수집
- 매일 오전 9시: 배송량 업데이트
- 매주 월요일: Claude 주간 트렌드 리포트 자동 생성

실행: python schedule_automation.py
"""

import schedule
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def hourly_collection():
    """매시간 실행: 유동인구 스냅샷"""
    from collect_data import collect_city_data, collect_living_population
    log.info("⏰ 시간별 수집 시작")
    collect_city_data()
    collect_living_population()


def daily_collection():
    """매일 오전 9시: 전체 데이터 수집"""
    from collect_data import run_all
    log.info("📅 일별 전체 수집 시작")
    run_all()


def weekly_report():
    """매주 월요일: Claude 주간 리포트"""
    from analyze import run_analysis
    log.info("📊 주간 Claude 리포트 생성 시작")
    run_analysis()


if __name__ == "__main__":
    print("\n🚀 성수동 상권분석 자동화 스케줄러 시작")
    print("   Ctrl+C로 종료\n")

    # 스케줄 등록
    schedule.every(1).hours.do(hourly_collection)
    schedule.every().day.at("09:00").do(daily_collection)
    schedule.every().monday.at("08:00").do(weekly_report)

    # 즉시 1회 실행
    daily_collection()

    log.info("✅ 스케줄 등록 완료")
    log.info("   - 매시간: 유동인구 수집")
    log.info("   - 매일 09:00: 전체 수집")
    log.info("   - 매주 월요일 08:00: Claude 리포트")

    while True:
        schedule.run_pending()
        time.sleep(30)
