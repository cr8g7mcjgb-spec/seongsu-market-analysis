# 🏪 성수동 상권분석 자동화 시스템

성수동(성동구) 실시간 시장조사 & 소비자 니즈 분석 자동화 파이프라인

## 데이터 소스
- 🏙️ 서울 실시간 도시데이터 (유동인구·혼잡도)
- 📦 자치구별 배송건수 (배달 수요 프록시)
- 🚇 생활인구 (버스·지하철 이동 추정)
- 🏪 소상공인 상권 매출·폐업률
- 🤖 Claude AI 자동 리포트 생성

## 사용법
```bash
pip install -r requirements.txt
cp .env.example .env  # API 키 입력
python collect_data.py  # 데이터 수집
python analyze.py       # Claude 분석 리포트
```

## API 키 발급
- 서울 열린데이터광장: https://data.seoul.go.kr
- 소상공인진흥공단: https://www.data.go.kr
- Anthropic Claude: https://console.anthropic.com
