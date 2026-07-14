"""
성수동 상권분석 — Claude AI 자동 리포트 생성기
──────────────────────────────────────────
수집된 데이터를 Claude에 전달해 소비자 니즈·트렌드 리포트 생성

사용법:
  python analyze.py              # 기본 리포트
  python analyze.py --topic 카페  # 특정 업종 분석
  python analyze.py --compare 홍대 # 타 상권 비교
"""

import os
import json
from pathlib import Path
from datetime import datetime

import anthropic
from dotenv import load_dotenv

load_dotenv()

CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def load_collected_data() -> dict:
    """data/ 폴더에서 최신 수집 데이터 로드"""
    data = {}

    # 도시데이터
    city_file = DATA_DIR / "city_data.json"
    if city_file.exists():
        import pandas as pd
        df = pd.read_json(city_file)
        # 성수동 관련 필터
        if "AREA_NM" in df.columns:
            seongsu = df[df["AREA_NM"].str.contains("성수|성동|서울숲", na=False)]
            data["유동인구_혼잡도"] = seongsu.to_dict(orient="records")
        else:
            data["유동인구_혼잡도"] = df.head(5).to_dict(orient="records")
    else:
        data["유동인구_혼잡도"] = [
            {"AREA_NM": "성수카페거리", "AREA_CONGEST_LVL": "약간 붐빔", "PPLTN_MAX": 4000},
            {"AREA_NM": "성수역",      "AREA_CONGEST_LVL": "약간 붐빔", "PPLTN_MAX": 5000},
        ]

    # 배송 데이터
    delivery_file = DATA_DIR / "delivery_stats.json"
    if delivery_file.exists():
        import pandas as pd
        df = pd.read_json(delivery_file)
        seongdong = df[df.apply(
            lambda r: any("성동" in str(v) for v in r.values), axis=1
        )] if not df.empty else df
        data["성동구_배송량"] = seongdong.head(3).to_dict(orient="records") if not seongdong.empty else df.head(3).to_dict(orient="records")
    else:
        data["성동구_배송량"] = [{"GU_NM": "성동구", "DLVR_CNT": 284000, "YEAR_MONTH": "202406"}]

    # 상권 데이터
    commercial_file = DATA_DIR / "commercial_area.json"
    if commercial_file.exists():
        with open(commercial_file, encoding="utf-8") as f:
            data["상권정보"] = json.load(f)

    return data


def build_prompt(data: dict, topic: str = None, compare: str = None) -> str:
    """Claude에 보낼 프롬프트 구성"""
    now = datetime.now().strftime("%Y년 %m월 %d일 %H시")

    data_str = json.dumps(data, ensure_ascii=False, indent=2)

    base = f"""당신은 서울 성수동 상권 전문 시장조사 애널리스트입니다.
아래 실시간 수집 데이터를 바탕으로 성수동 소비자 니즈와 상권 트렌드를 분석해주세요.

수집 시각: {now}
분석 대상: 서울 성동구 성수동 (성수카페거리, 서울숲, 성수역 일대)

[수집된 데이터]
{data_str}

다음 항목을 포함해 마크다운 형식으로 리포트를 작성해주세요:

## 1. 성수동 현재 상권 현황
- 유동인구 수준 및 혼잡도
- 배달 수요 추정 (성동구 배송량 기반)

## 2. 소비자 니즈 분석
- 주요 방문 고객층 추정 (20-30대 트렌디 소비자 중심)
- 시간대별 소비 패턴
- 배달 vs 방문 소비 비율 추정

## 3. 쿠팡이츠/배달 수요 유추
- 성동구 전체 배송량 기반 성수동 배달 수요 추정
- 음식 카테고리별 수요 예측

## 4. 상권 트렌드 및 기회
- 현재 성수동에서 유망한 업종
- 경쟁 강도 분석
- 진입 추천 시간대

## 5. 실행 인사이트
- 즉시 활용 가능한 마케팅 포인트 3가지
- 리스크 요인
"""

    if topic:
        base += f"\n\n특히 **{topic}** 업종에 집중해서 분석해주세요."

    if compare:
        base += f"\n\n성수동을 **{compare}** 상권과 비교 분석도 포함해주세요."

    return base


def run_analysis(topic: str = None, compare: str = None):
    """Claude API 호출 → 스트리밍 리포트 출력"""
    print("\n" + "="*60)
    print("🤖 Claude 성수동 상권분석 리포트 생성 중...")
    print("="*60 + "\n")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("sk-ant-여기에"):
        print("⚠️  ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 Claude API 키를 입력해주세요.\n")
        # 데모 리포트 출력
        _demo_report()
        return

    data = load_collected_data()
    prompt = build_prompt(data, topic=topic, compare=compare)

    # Claude 스트리밍 호출
    full_report = ""
    with CLIENT.messages.stream(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_report += text

    # 리포트 저장
    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    out = Path(f"report_{now_str}.md")
    out.write_text(full_report, encoding="utf-8")
    print(f"\n\n✅ 리포트 저장: {out}")


def _demo_report():
    """API 키 없을 때 데모 출력"""
    print("""
## 🏪 성수동 상권분석 리포트 (데모)

### 1. 현재 상권 현황
- 성수카페거리: **약간 붐빔** (유동인구 3,000~4,000명)
- 성수역: **약간 붐빔** (유동인구 4,000~5,000명)
- 성동구 월 배송건수: **284,000건** (소비 활력 상위권)

### 2. 소비자 니즈 분석
- 주요 고객층: **20-30대 트렌디 소비자** (MZ세대 성지)
- 피크 타임: **점심 12-14시, 저녁 18-21시**
- 배달 수요: 성동구 배송량 기준 **음식배달 약 30-40% 추정**

### 3. 쿠팡이츠 배달 수요 유추
- 성동구 월 배송 28.4만건 중 음식배달 추정 **8-11만건**
- 성수동 집중도: 성동구 전체의 약 **25-30%**
- 인기 카테고리: 카페·디저트, 한식, 브런치

### 4. 유망 업종
- ✅ 브런치 카페 (10-14시 집중)
- ✅ 팝업스토어 연계 F&B
- ✅ 건강식·샐러드 (2030 웰니스 트렌드)
- ⚠️ 일반 치킨·피자는 경쟁 과포화

### 5. 실행 인사이트
1. **인스타그램 마케팅** 필수 (성수동 방문객 SNS 공유율 매우 높음)
2. **주말 팝업 연계** 마케팅으로 인지도 급상승 가능
3. **배달 앱 점심 특가** 전략으로 평일 배달 수요 공략
    """)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="성수동 Claude 상권 분석")
    parser.add_argument("--topic",   type=str, help="특정 업종 집중 분석 (예: 카페, 브런치)")
    parser.add_argument("--compare", type=str, help="비교 상권 (예: 홍대, 이태원)")
    args = parser.parse_args()
    run_analysis(topic=args.topic, compare=args.compare)
