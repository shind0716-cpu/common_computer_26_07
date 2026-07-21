"""[민옥] loader / extractor / assigner / analysis — 미니 스프린트에서는 수동·최소 구현.
- loader: 원본 소스 → issues/. 스프린트에선 ESA 픽스처 수동 배치로 대체.
- extractor: issue → facts/. 스프린트에선 파일럿 팩트 재사용. prior 프리필 프로브는 스프린트 이후.
- assigner: facts → assignments/. seed 기반 비대칭 배분. 스프린트에선 픽스처로 대체.
- analysis: judgments → far_by_stage 곡선, 4분할 표. 목요일 쌍 비교 때 구현.
계약 상세는 SCHEMA.md. 본실험 진입 시 각각 독립 모듈로 승격한다."""
