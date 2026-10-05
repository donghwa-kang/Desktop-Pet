"""Groom the clean symmetric face. Facial pairs share mirrored strand geometry."""
import argparse,json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'ArtSource/CleanFace'
p=argparse.ArgumentParser();p.add_argument('--tag',default='clean03');p.add_argument('--size',type=int,default=640);p.add_argument('--samples',type=int,default=28);p.add_argument('--views',nargs='+',default=['front']);a=p.parse_args()
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(OUT/f'ogong_{a.tag}_structure.blend'))
scene=bpy.context.scene;collection=bpy.data.collections.new('Balanced_Facial_Coat');scene.collection.children.link(collection)
hair=bpy.data.materials.get('Clean_White_Fur')
if hair is None:
    hair=bpy.data.materials.new('Clean_White_Fur');hair.use_nodes=True
    nodes=hair.node_tree.nodes;nodes.clear();links=hair.node_tree.links
    out=nodes.new('ShaderNodeOutputMaterial');shader=nodes.new('ShaderNodeBsdfHairPrincipled');shader.model='CHIANG';shader.parametrization='COLOR'
    shader.inputs['Color'].default_value=(.66,.64,.60,1);shader.inputs['Roughness'].default_value=.48;shader.inputs['Radial Roughness'].default_value=.55
    links.new(shader.outputs[0],out.inputs['Surface'])
rng=np.random.default_rng(100508);manifest={}


def norm(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-10)
def ss(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1);return t*t*(3-2*t)


def uv_at(r):return np.column_stack([np.arctan2(r[:,1]+.64,r[:,0])/(2*np.pi)+.5,r[:,2]/.65])


def sample(obj,count,positive_only=False):
    ob=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ob.to_mesh();m.calc_loop_triangles()
    v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    n=np.empty_like(v);m.vertices.foreach_get('normal',n.reshape(-1))
    f=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',f);f=f.reshape(-1,3)
    mat=np.empty(len(m.loop_triangles),np.int32);m.loop_triangles.foreach_get('material_index',mat)
    tri=v[f];centers=tri.mean(1);areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
    if positive_only:
        areas*=(centers[:,0]>.00001)&(mat==0)&(centers[:,2]>.085)
        areas*=np.where(centers[:,2]>.34,1.8,1.)
    ids=rng.choice(len(f),count,p=areas/areas.sum());ab=rng.random((count,2));s=np.sqrt(ab[:,0]);w=np.column_stack([1-s,s*(1-ab[:,1]),s*ab[:,1]])
    r=np.einsum('ni,nij->nj',w,tri[ids]);nn=norm(np.einsum('ni,nij->nj',w,n[f[ids]]))
    ob.to_mesh_clear();return r,nn


def emit(name,obj,r,n,under=False,paired=False,kind='head'):
    N=len(r);x,y,z=r.T
    if kind=='head':
        crown=ss(.435,.555,z);collar=1-ss(.27,.385,z)
        flow=np.column_stack([np.tanh(x*23)*(.88-.52*collar-.18*crown),np.full(N,.03),-.25+.98*crown-.80*collar])
        ex=np.where(x<0,-.070,.070);ed=np.hypot(x-ex,z-.454)
        front=1-ss(-.73,-.655,y);ew=(1-ss(.025,.073,ed))*front
        outward=norm(np.column_stack([x-ex,np.zeros(N),z-.454]))
        flow=flow*(1-ew[:,None])+outward*ew[:,None]
        mw=(1-ss(.052,.120,np.hypot(x,(z-.412)*1.1)))*front
        base=.084+.041*(1-ss(.21,.36,z))
        L=base*(1-.83*np.maximum(ew,mw))*(.62 if under else 1)
    else:
        flow=np.column_stack([np.sign(x)*.25,np.zeros(N),np.ones(N)]);L=np.full(N,.009)
    L*=np.clip(rng.lognormal(-.01,.13,N),.72,1.28)
    tangent=norm(flow-n*(flow*n).sum(1,keepdims=True));lateral=norm(np.cross(n,tangent))
    t=np.linspace(0,1,14,dtype=np.float32)[None,:,None]
    normal_bend=.70*t-.16*t*t if under else .62*t-.15*t*t
    tangent_bend=.12*t+.44*t*t if under else .15*t+.60*t*t
    points=r[:,None,:]+L[:,None,None]*(n[:,None,:]*normal_bend+tangent[:,None,:]*tangent_bend)
    cell=.015
    _,g=np.unique(np.floor(r/cell).astype(np.int32),axis=0,return_inverse=True);count=np.bincount(g)
    means=np.column_stack([np.bincount(g,weights=r[:,k])/count for k in range(3)])
    delta=means[g]-r;delta-=n*(delta*n).sum(1,keepdims=True)
    points+=delta[:,None,:]*t**2*(.16 if under else .5)
    phase=rng.uniform(0,2*np.pi,N)[:,None,None]
    points+=lateral[:,None,:]*L[:,None,None]*.045*(np.sin(t*6.5+phase)-np.sin(phase))*t
    points[:,:,2]-=L[:,None]*.055*t[0,:,0]**2
    rad=rng.uniform(.00007,.000105,N) if under else rng.uniform(.000065,.00011,N)
    if kind=='ear':rad*=.6
    radius=rad[:,None]*(.02+.98*(1-t[0,:,0])**.9)
    if paired:
        mirrored=points.copy();mirrored[:,:,0]*=-1
        points=np.concatenate([points,mirrored]);radius=np.concatenate([radius,radius]);N*=2
    d=bpy.data.hair_curves.new(name);d.add_curves([14]*N)
    d.attributes['position'].data.foreach_set('vector',points.astype(np.float32).reshape(-1))
    d.attributes.new('radius','FLOAT','POINT').data.foreach_set('value',radius.astype(np.float32).reshape(-1))
    d.attributes.new('surface_uv_coordinate','FLOAT2','CURVE').data.foreach_set('vector',uv_at(points[:,0]).astype(np.float32).reshape(-1))
    d.surface=obj;d.surface_uv_map='UVMap';d.materials.append(hair)
    ob=bpy.data.objects.new(name,d);collection.objects.link(ob)
    manifest[name]={'strands':N,'paired_symmetry':paired,'surface':obj.name}
    print('GROOM',name,N,flush=True)
    return ob


head=bpy.data.objects['Clean_Continuous_Head_Muzzle_Collar'];r,n=sample(head,120000,True)
# Do not grow fur through the nose or across the eye openings.
keep=~((r[:,1]<-.765)&((r[:,0]/.032)**2+((r[:,2]-.427)/.026)**2<1.05))
keep&=~((r[:,1]<-.733)&(((r[:,0]-.070)/.025)**2+((r[:,2]-.454)/.024)**2<1))
r,n=r[keep],n[keep]
outer=np.arange(0,len(r),3);under=np.ones(len(r),bool);under[outer]=False
emit('Face_Collar_Outer',head,r[outer],n[outer],paired=True)
emit('Face_Collar_Under',head,r[under],n[under],under=True,paired=True)
ear=bpy.data.objects['Clean_Upright_Ear_R'];r,n=sample(ear,4500)
right=emit('Ear_R_Coat',ear,r,n,kind='ear')
left=right.copy();left.data=right.data.copy();left.name='Ear_L_Coat';collection.objects.link(left)
pos=np.empty(len(left.data.points)*3,np.float32);left.data.attributes['position'].data.foreach_get('vector',pos);pos=pos.reshape(-1,3);pos[:,0]*=-1
left.data.attributes['position'].data.foreach_set('vector',pos.reshape(-1));left.data.surface=bpy.data.objects['Clean_Upright_Ear_L']
left.data.attributes['surface_uv_coordinate'].data.foreach_set('vector',uv_at(pos.reshape(-1,14,3)[:,0]).astype(np.float32).reshape(-1))
manifest['Ear_L_Coat']={'strands':len(left.data.curves),'paired_symmetry':True,'surface':left.data.surface.name}
scene.cycles.samples=a.samples;scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE';scene.cycles.adaptive_threshold=.025
scene.render.resolution_x=a.size;scene.render.resolution_y=int(a.size*1.05)
cam=scene.camera;target=Vector((0,-.65,.423));cam.data.ortho_scale=.64

def aim(loc):cam.location=loc;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()

aim((0,-2.4,.433))
scene['replaces']='Rejected v10: irregular retriever face fragments have been removed completely.'
scene['groom_symmetry']='Paired facial strands mirrored about X=0; no asymmetric cropped texture patches.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
report={'revision':a.tag,'blender':bpy.app.version_string,'regions':manifest,'total_strands':sum(v['strands'] for v in manifest.values()),'source_geometry':'new continuous surfaces; no retriever geometry','rigged':False}
(OUT/f'{a.tag}_groom.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'ogong_{a.tag}.blend'),compress=True)
for view in a.views:
    aim((.85,-2.1,.455) if view=='threequarter' else (0,-2.4,.433))
    scene.render.resolution_x=256 if view=='small' else a.size;scene.render.resolution_y=int(scene.render.resolution_x*1.05)
    scene.render.filepath=str(OUT/f'{a.tag}_{view}.png');print('RENDER',view,flush=True);bpy.ops.render.render(write_still=True)
print('CLEAN_GROOM_COMPLETE',json.dumps(report),flush=True)
