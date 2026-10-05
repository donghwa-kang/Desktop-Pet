"""Extract the continuous full-body sculpt. Requires numpy/scipy/scikit-image."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
from fullbody_fields import body_field, nose_field, LANDMARKS

OUT=Path(__file__).resolve().parent/'FullbodyStudy'
OUT.mkdir(exist_ok=True)


def extract(name, bounds, step, field):
    axes=[np.linspace(lo,hi,round((hi-lo)/step)+1) for lo,hi in bounds]
    volume=np.empty(tuple(map(len,axes)),np.float32)
    for k,z in enumerate(axes[2]):
        volume[:,:,k]=field(axes[0][:,None],axes[1][None,:],z)
    vertices,faces,_,_=marching_cubes(volume,0,spacing=tuple(a[1]-a[0] for a in axes),
                                     gradient_direction='ascent',allow_degenerate=False)
    vertices+=np.array([a[0] for a in axes])
    np.savez_compressed(OUT/f'{name}.npz',vertices=vertices.astype(np.float32),faces=faces)
    mirror=vertices.copy();mirror[:,0]*=-1
    error=cKDTree(vertices).query(mirror,workers=4)[0]
    stats={'vertices':len(vertices),'faces':len(faces),'mirror_max':float(error.max())}
    print(name,stats,flush=True)
    return stats


report={
    'body':extract('body',[(-.33,.33),(-.69,.66),(-.005,.96)],.003,body_field),
    'nose':extract('nose',[(-.048,.048),(-.633,-.545),(.668,.754)],.0008,nose_field),
    'landmarks':LANDMARKS,
    'units':'normalized approximate overall coat height; not real-world metres',
    'reference':'User supplied five-view white Pomeranian sheet, 2026-10-06 KST',
    'measurement_method':'Visual landmark estimates from displayed sheet, not pixel-overlay fitting',
}
(OUT/'anatomy.json').write_text(json.dumps(report,indent=2))
