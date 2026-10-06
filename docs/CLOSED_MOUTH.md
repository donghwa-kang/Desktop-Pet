# 입을 다문 기본 표정 — fullbody05

2026-10-06 사용자가 제공한 입을 다문 정면·후면·위·좌우 측면 그림을 기본 표정의 기준으로 삼았다. 기본 모델은 입을 다문 상태이며, 혀와 치아를 노출하지 않는다. 기존에 입을 연 `fullbody04` 파일은 별도로 보존한다.

## 변경

- 열린 입의 빈 공간을 만들던 표면 연산을 기본형에서 제거했다.
- 아래턱의 위치와 볼륨을 올려 위 주둥이와 이어지는 닫힌 표면을 만들었다.
- 측면 검토 후 아래턱을 더 작게 하고 뒤로 당겨, 주둥이 아래가 두툼하게 앞으로 나오는 형태를 줄였다.
- 얇은 입술 접촉선과 코 아래 중앙선을 실제 주둥이 표면에 맞춰 배치했다.
- 입선 주변의 털 길이와 밀도를 조정했다.
- 닫힌 기본형에는 혀·치아 오브젝트를 생성하지 않는다.
- 장면의 `default_expression` 값은 `closed`이다. 이것은 표정 리그나 애니메이션 제어기가 아니라 모델 상태를 기록하는 값이다.

눈·코·몸통·다리·꼬리의 기존 설정을 유지했다. 다각도 그림과의 픽셀 정합이나 실측 복원은 하지 않았으며, 전체 외형의 유사도에는 추가 조정이 필요하다.

## 생성

```sh
python ArtSource/sculpt_fullbody.py --tag fullbody05 --expression closed
python ArtSource/build_fullbody.py --tag fullbody05
python ArtSource/groom_fullbody.py --tag fullbody05 --size 720 --samples 28 --views Face Front Side Opposite Threequarter Back Top
python ArtSource/audit_fullbody.py --tag fullbody05
python ArtSource/export_fullbody_delivery.py --tag fullbody05
python ArtSource/package_fullbody.py --tag fullbody05
```

실행 환경과 선행 재질 장면은 [실행 안내](REPRODUCING.md)를 따른다. 중간 메시와 조형 기록은 태그별 이름으로 저장해 이전 버전의 데이터를 덮어쓰지 않는다. 입을 연 형태를 별도로 생성하려면 새로운 태그와 `--expression open`을 사용한다. 닫힌 모델과 열린 모델 사이를 변형하는 애니메이션은 아직 없다.

## 확인 항목

정면·양 측면·사선·위·후면·얼굴 확대에서 표정을 검토한다. 구조 검사는 기존의 닫힌 표면·좌우 대칭·털 참조 검사에 더해, 기본형에 혀와 치아가 없는지, 입안 재질 면이 남지 않았는지, 입선이 있는지를 확인한다. 검사 결과는 생성 파일의 `fullbody05_validation.json`에 기록한다.

전달본에서는 개인 원본 참고 사진을 제외한다. `.blend`, 렌더 7장, 설명서와 검수 기록을 ZIP으로 전달한다.
