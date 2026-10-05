"""Validate the saved full-body scene and record its actual landmark dimensions."""
import argparse,json
from pathlib import Path
import bpy,bmesh
import numpy as np
from mathutils.kdtree import KDTree

p=argparse.ArgumentParser();p.add_argument('--tag',default='fullbody04');a=p.parse_args()
out=Path(__file__).resolve().parent/'FullbodyStudy'
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(out/f'ogong_{a.tag}.blend'))
report={'blender':bpy.app.version_string,'revision':a.tag,'meshes':{},'groom':{}}
for name in ['Ogong_Continuous_Anatomy','Ogong_Nose','Ogong_Tongue','Ogong_Curled_Tail','Ogong_Ear_L','Ogong_Ear_R']:
    ob=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(ob.data)
    stats={'vertices':len(bm.verts),'faces':len(bm.faces),
           'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)}
    assert stats['boundary_edges']==stats['nonmanifold_edges']==0,(name,stats)
    if name in ['Ogong_Continuous_Anatomy','Ogong_Nose']:
        tree=KDTree(len(bm.verts))
        for i,v in enumerate(bm.verts):tree.insert(v.co,i)
        tree.balance();stats['max_mirror_error']=max(tree.find((-v.co.x,v.co.y,v.co.z))[2] for v in bm.verts)
        assert stats['max_mirror_error']<1e-6
    report['meshes'][name]=stats;bm.free()
coat_bounds=[]
for ob in bpy.data.objects:
    if ob.type!='CURVES':continue
    d=ob.data;pos=np.empty(len(d.points)*3,np.float32);d.attributes['position'].data.foreach_get('vector',pos);pos=pos.reshape(-1,3)
    rad=np.empty(len(d.points),np.float32);d.attributes['radius'].data.foreach_get('value',rad)
    assert np.isfinite(pos).all() and np.isfinite(rad).all() and (rad>0).all()
    assert d.surface and d.surface_uv_map in d.surface.data.uv_layers
    assert pos[:,2].min()>=.00349
    report['groom'][ob.name]={'strands':len(d.curves),'surface':d.surface.name,'min':pos.min(0).tolist(),'max':pos.max(0).tolist()}
    coat_bounds.extend([pos.min(0),pos.max(0)])
report['total_strands']=sum(v['strands'] for v in report['groom'].values())
report['coat_bounds']={'min':np.min(coat_bounds,axis=0).tolist(),'max':np.max(coat_bounds,axis=0).tolist()}
from fullbody_fields import LANDMARKS
report['landmarks']=LANDMARKS
report['actual_anatomy_ratios_in_scene_units']={
    'eye_center_spacing':2*LANDMARKS['eye_R'][0],
    'withers_height_above_paw_baseline':LANDMARKS['estimated_withers'][2]-.011,
    'front_hind_paw_center_spacing':LANDMARKS['hind_paw_R'][1]-LANDMARKS['fore_paw_R'][1],
    'fore_paw_left_right_spacing':2*LANDMARKS['fore_paw_R'][0],
    'hind_paw_left_right_spacing':2*LANDMARKS['hind_paw_R'][0],
}
report['reference_comparison']='Visually guided only; not an automated registration against reference pixels.'
report['cameras']=[o.name for o in bpy.data.objects if o.type=='CAMERA']
assert all('Review_'+v in report['cameras'] for v in ['Front','Side','Back','Top','Threequarter','Face','Opposite'])
report['packed_photos']=[im.name for im in bpy.data.images if im.packed_file]
assert len(report['packed_photos'])==2
report['rigged']=any(o.type=='ARMATURE' for o in bpy.data.objects)
(out/f'{a.tag}_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
