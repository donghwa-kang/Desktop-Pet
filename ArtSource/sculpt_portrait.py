"""Create symmetrical, continuous facial surfaces without source-mesh fragments.
Run under Python with numpy/scipy/scikit-image. Outputs NPZ for Blender.
"""
from pathlib import Path
import numpy as np
from skimage.measure import marching_cubes
from scipy.spatial import cKDTree
import json

OUT=Path(__file__).resolve().parent/'PortraitStudy'
OUT.mkdir(exist_ok=True)


from portrait_fields import head_field, nose_field


def extract(name,bounds,step,fn):
    axes=[np.linspace(lo,hi,round((hi-lo)/step)+1,dtype=np.float64) for lo,hi in bounds]
    spacings=tuple(float(a[1]-a[0]) for a in axes)
    volume=np.empty(tuple(map(len,axes)),np.float32)
    x=axes[0][:,None];y=axes[1][None,:]
    for k,z in enumerate(axes[2]):volume[:,:,k]=fn(x,y,z)
    verts,faces,normals,values=marching_cubes(volume,0,spacing=spacings,gradient_direction='ascent',allow_degenerate=False)
    verts+=np.array([a[0] for a in axes])
    # Numerical grid centring: force both sides to use the same exact x plane.
    verts[:,0]-=(axes[0][0]+axes[0][-1])/2
    np.savez_compressed(OUT/(name+'.npz'),vertices=verts.astype(np.float32),faces=faces)
    mirrored=verts.copy();mirrored[:,0]*=-1
    distances=cKDTree(verts).query(mirrored,workers=4)[0]
    stats={'vertices':len(verts),'triangles':len(faces),'max_mirror_error':float(distances.max()),'mean_mirror_error':float(distances.mean())}
    print(name,json.dumps(stats),flush=True)
    return stats


report={}
report['head']=extract('clean_head',[(-.225,.225),(-.925,-.43),(.055,.64)],.002,head_field)


report['nose']=extract('clean_nose',[(-.046,.046),(-.858,-.795),(.397,.474)],.00055,nose_field)
(OUT/'surface_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
