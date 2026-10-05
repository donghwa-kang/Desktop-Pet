"""Reopen the delivery scene and audit surfaces, groom data and packed references."""
import argparse
import json
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils.kdtree import KDTree

parser = argparse.ArgumentParser()
parser.add_argument('--tag', default='portrait02')
args = parser.parse_args()
out = Path(__file__).resolve().parent / 'PortraitStudy'
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.open_mainfile(filepath=str(out / f'ogong_{args.tag}.blend'))
report = {'blender': bpy.app.version_string, 'meshes': {}, 'groom': {}}
for name in ['Clean_Continuous_Head_Muzzle_Collar', 'Clean_Symmetric_Nose_With_Nostrils']:
    ob = bpy.data.objects[name]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    tree = KDTree(len(bm.verts))
    for index, vertex in enumerate(bm.verts):
        tree.insert(vertex.co, index)
    tree.balance()
    mirror_error = max(tree.find((-v.co.x, v.co.y, v.co.z))[2] for v in bm.verts)
    stats = {'vertices': len(bm.verts), 'faces': len(bm.faces),
             'boundary_edges': sum(e.is_boundary for e in bm.edges),
             'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
             'max_mirror_error': mirror_error}
    assert stats['boundary_edges'] == stats['nonmanifold_edges'] == 0, stats
    assert mirror_error < 1e-6, stats
    report['meshes'][name] = stats
    bm.free()
for ob in bpy.data.objects:
    if ob.type != 'CURVES':
        continue
    data = ob.data
    points = np.empty(len(data.points) * 3, dtype=np.float32)
    data.attributes['position'].data.foreach_get('vector', points)
    radii = np.empty(len(data.points), dtype=np.float32)
    data.attributes['radius'].data.foreach_get('value', radii)
    stats = {'curves': len(data.curves), 'points': len(data.points),
             'finite_points': bool(np.isfinite(points).all()),
             'finite_positive_radii': bool(np.isfinite(radii).all() and (radii > 0).all()),
             'surface': data.surface.name if data.surface else None,
             'valid_surface_uv': bool(data.surface and data.surface_uv_map in data.surface.data.uv_layers)}
    assert stats['finite_points'] and stats['finite_positive_radii'] and stats['valid_surface_uv'], stats
    report['groom'][ob.name] = stats
report['total_strands'] = sum(s['curves'] for s in report['groom'].values())
report['packed_references'] = [im.name for im in bpy.data.images if im.packed_file]
assert len(report['packed_references']) == 2, report['packed_references']
report['review_cameras'] = [ob.name for ob in bpy.data.objects if ob.type == 'CAMERA']
assert all('Review_' + s in report['review_cameras'] for s in ['Front', 'Threequarter', 'Side'])
report['rigged'] = any(ob.type == 'ARMATURE' for ob in bpy.data.objects)
report['scope'] = 'Head and chest portrait study. Dense sculpt and native curves; not a runtime asset.'
(out / f'{args.tag}_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2), flush=True)
