# 실행 환경과 제작 순서

이 저장소는 제작 스크립트와 기록을 보관한다. Unity 프로젝트나 Windows 실행 파일은 아직 포함하지 않는다.

## 환경

- 최신 전신 작업: Blender 5.2.2 LTS의 Python API (`bpy`), Cycles, OpenImageDenoise
- 표면 추출: Python, NumPy, SciPy, scikit-image
- 전달 ZIP의 이미지 확인: Pillow

현재 작업에서는 표면 추출에 Python 3.12, Blender API 실행에 Python 3.13과 `bpy` 모듈을 사용했다. Blender 모듈은 Python 버전 및 운영체제와 호환되는 배포본이 필요하다. 초기 v01·v02 스크립트는 Blender 4.3.2에서 실행한 실험으로 최신 API와의 호환성을 보장하지 않는다.

## 입력 파일과 의존성

`build_fullbody.py`는 `ArtSource/PortraitStudy/ogong_portrait02_structure.blend`에서 재질을 가져온다. 이 선행 장면은 `sculpt_portrait.py` → `build_portrait.py`로 생성했다. `build_portrait.py`는 로컬 `ReferencePhotos/`에 있는 아래 두 사진을 불러와 내장한다.

- `KakaoTalk_20261005_184824793_06.jpg`
- `KakaoTalk_20261005_184824793_01.png`

사진과 생성된 Blender 장면은 공개 저장소에 포함하지 않는다. 입력 자료 없이 그대로 실행하면 파일을 찾지 못하는 것이 현재 스크립트의 제약이다. 외부 리트리버 참고 모델을 사용하는 과거 실험에도 별도 입력 파일이 필요하다.

## 전신 제작 순서

저장소 루트에서 실행한다. 아래 `python`은 각 스크립트에 필요한 패키지가 설치된 Python을 뜻한다. Blender API를 사용하는 단계에는 `bpy`를 사용할 수 있는 Python을 지정한다.

```sh
python ArtSource/sculpt_portrait.py
python ArtSource/build_portrait.py --tag portrait02
python ArtSource/sculpt_fullbody.py
python ArtSource/build_fullbody.py --tag fullbody04
python ArtSource/groom_fullbody.py --tag fullbody04 --size 720 --samples 28 --views Front Side Threequarter Face Back Top Opposite
python ArtSource/audit_fullbody.py --tag fullbody04
```

표면 추출은 `.npz`를 저장하고, 장면 구성은 `_structure.blend`, 털 생성은 최종 `.blend`와 렌더를 저장한다. 결과는 `ArtSource/PortraitStudy/`, `ArtSource/FullbodyStudy/`에 생성된다. `groom_fullbody.py`의 `--views` 뒤를 비우면 렌더 없이 털을 생성하고 장면을 저장한다.

완성된 장면의 카메라만 다시 렌더하려면 다음을 사용한다.

```sh
python ArtSource/render_fullbody.py --tag fullbody04 --size 720 --samples 28 --views Front Side Threequarter Face Back Top Opposite
```

같은 태그로 실행하면 생성 파일을 덮어쓰므로 직접 수정한 장면은 다른 이름으로 저장한다. 스크립트는 Blender의 열린 장면을 교체하므로 편집 중인 작업을 저장한 뒤 별도 프로세스에서 실행한다.

## 검수와 전달

`audit_fullbody.py`는 닫힌 표면, 좌우 대칭, 털 좌표·반경·표면 참조, 카메라, 내장 사진을 검사한다. 이 구조 검사는 사진과의 유사도를 수치로 검증하는 절차가 아니다.

`export_fullbody_delivery.py`는 재질에 사용되지 않는 참고 사진을 제거한 별도 전달본을 만들고 다시 연다. `package_fullbody.py`는 그 파일과 렌더 7장, 설명서를 묶는다. 현재 두 전달 스크립트의 출력 경로는 클라우드 작업 환경의 `/workspace/Deliverables`로 지정돼 있으므로 다른 컴퓨터에서는 경로를 수정해야 한다.

최신 전달본은 재개방·구조 검사와 ZIP 무결성 확인을 마쳤다. 공개 미리보기는 생성된 PNG를 `Previews/fullbody04/`로 복사한 것이다. 공개 저장소에서 전체 제작 파이프라인을 새로 실행하는 CI는 아직 없다.
