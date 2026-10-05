"""Package the verified Blender scene and real rendered views for Drive delivery."""
import hashlib,json
from pathlib import Path
from zipfile import ZipFile,ZIP_STORED
from PIL import Image

root=Path(__file__).resolve().parents[1];src=root/'ArtSource/FullbodyStudy'
tag='fullbody04';out=Path('/workspace/Deliverables');out.mkdir(exist_ok=True)
delivery=out/f'ogong_{tag}'
files=[f'ogong_{tag}.blend',f'{tag}_validation.json']
for view in ['front','side','back','top','threequarter','face','opposite']:
    name=f'{tag}_{view}.png'
    with Image.open(src/name) as im:im.verify()
    files.append(name)
readme='''오공이 전신 비율 수정본 — fullbody04

1. ZIP을 압축 해제하세요.
2. Blender 5.2.2 LTS의 File > Open에서 ogong_fullbody04.blend를 여세요.
3. 숫자패드 0을 누르면 카메라 화면을 볼 수 있습니다.

타임라인 프레임별 카메라:
1 정면 / 2 측면 / 3 후면 / 4 위 / 5 사선 / 6 얼굴 확대 / 7 반대 측면

Ogong_Groom_Regions 컬렉션에서 부위별 털을 숨기거나 편집할 수 있습니다.
Reference_Proportion_Landmarks는 확인용 기준점이며 변형 리그가 아닙니다.

머리·목·몸통·네 다리·꼬리를 포함한 전신 작업본입니다.
리깅과 걷기·앉기·잠자기 애니메이션은 아직 포함하지 않습니다.
첨부 다각도 그림을 육안으로 비교해 맞춘 비율이며,
그림과의 픽셀 겹치기나 실측 3D 복원으로 일치도를 검증하지 않았습니다.

전달용 Blender 파일에는 원본 참고 사진을 내장하지 않았습니다.
모델의 재질과 형태는 사진 제외 전후 동일합니다.
'''
target=out/f'ogong_{tag}.zip'
with ZipFile(target,'w',compression=ZIP_STORED) as z:
    for name in files:
        source=(delivery/name) if name.endswith(('.blend','.json')) else (src/name)
        z.write(source,f'ogong_{tag}/{name}')
    z.writestr(f'ogong_{tag}/README.txt',readme.encode('utf-8-sig'))
    z.write(root/'docs/FULLBODY_PROPORTIONS.md',f'ogong_{tag}/PROPORTION_NOTES.md')
with ZipFile(target) as z:assert z.testzip() is None
target.chmod(0o644)
report={'file':str(target),'bytes':target.stat().st_size,'md5':hashlib.md5(target.read_bytes()).hexdigest(),'render_count':7,'reference_photos':0}
(out/f'ogong_{tag}_package.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
