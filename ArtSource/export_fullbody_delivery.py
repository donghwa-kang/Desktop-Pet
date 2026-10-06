"""Create a delivery copy without the two private reference photographs."""
import argparse,json
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[1]
src = root / 'ArtSource/FullbodyStudy'
p=argparse.ArgumentParser();p.add_argument('--tag',default='fullbody05');p.add_argument('--output-root',type=Path,default=Path('/workspace/Deliverables'));args=p.parse_args()
tag=args.tag
out = args.output_root / f'ogong_{tag}'
out.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.open_mainfile(filepath=str(src / f'ogong_{tag}.blend'))

def signature():
    return {
        'objects': sorted((o.name, o.type) for o in bpy.data.objects),
        'meshes': sorted((m.name, len(m.vertices), len(m.polygons)) for m in bpy.data.meshes),
        'hair': sorted((o.name, len(o.data.curves), len(o.data.points)) for o in bpy.data.objects if o.type == 'CURVES'),
    }

before = signature()
photos = [im for im in bpy.data.images if im.packed_file]
assert len(photos) == 2
for im in photos:
    assert not any(getattr(o, 'data', None) == im for o in bpy.data.objects)
    for mat in bpy.data.materials:
        if mat.node_tree:
            assert not any(getattr(n, 'image', None) == im for n in mat.node_tree.nodes)
    bpy.data.images.remove(im, do_unlink=True)
assert not list(bpy.data.images)
bpy.context.preferences.filepaths.save_version = 0
target = out / f'ogong_{tag}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target))
bpy.ops.wm.open_mainfile(filepath=str(target))
assert signature() == before
assert not list(bpy.data.images)
report = json.loads((src / f'{tag}_validation.json').read_text())
report['packed_photos'] = []
report['delivery'] = {
    'reference_photos_removed': True,
    'reopened_successfully': True,
    'object_mesh_hair_counts_unchanged': True,
    'image_datablocks': len(bpy.data.images),
}
(out / f'{tag}_validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'delivery_blend': str(target), 'bytes': target.stat().st_size, 'reference_photos': 0}), flush=True)
