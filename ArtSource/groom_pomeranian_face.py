"""Regroom the reconstructed Pomeranian head and collar, not the old retriever.

Native editable Hair Curves are sampled from the new evaluated surfaces.
"""
import argparse
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'ArtSource/FaceRebuild'
p=argparse.ArgumentParser();p.add_argument('--tag',default='v10');p.add_argument('--samples',type=int,default=40);p.add_argument('--size',type=int,default=720);p.add_argument('--views',nargs='+',default=['front','threequarter','small']);args=p.parse_args()
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(OUT/f'ogong_face_{args.tag}_structure.blend'))
scene=bpy.context.scene
rng=np.random.default_rng(1007)
collection=bpy.data.collections.new('Ogong_Facial_Groom');scene.collection.children.link(collection)
hair=bpy.data.materials['White_Fur_Fiber']
manifest={'version':args.tag,'blender':bpy.app.version_string,'regions':{},'source':'reconstructed Pomeranian cranium, muzzle and upright ears','rigged':False}


def normalize(a):return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-10)


def smoothstep(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)


def sample_surface(obj,count,attribute=None):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
    v=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    n=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('normal',n);n=n.reshape(-1,3)
    f=np.empty(len(mesh.loop_triangles)*3,dtype=np.int32);mesh.loop_triangles.foreach_get('vertices',f);f=f.reshape(-1,3)
    loops=np.empty(len(mesh.loop_triangles)*3,dtype=np.int32);mesh.loop_triangles.foreach_get('loops',loops);loops=loops.reshape(-1,3)
    u=np.empty(len(mesh.loops)*2,dtype=np.float32);mesh.uv_layers.active.data.foreach_get('uv',u);u=u.reshape(-1,2)
    tri=v[f];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
    if 'Rounded' in obj.name:areas*=np.where(tri[:,:,2].mean(1)>.32,1.7,1.0)
    ids=rng.choice(len(f),count,p=areas/areas.sum())
    ab=rng.random((count,2));s=np.sqrt(ab[:,0]);w=np.column_stack([1-s,s*(1-ab[:,1]),s*ab[:,1]])
    roots=np.einsum('ni,nij->nj',w,tri[ids]);normals=normalize(np.einsum('ni,nij->nj',w,n[f[ids]]))
    root_uv=np.einsum('ni,nij->nj',w,u[loops[ids]])
    if attribute:
        values=np.empty(len(mesh.vertices),dtype=np.float32)
        mesh.attributes[attribute].data.foreach_get('value',values)
        root_values=np.einsum('ni,ni->n',w,values[f[ids]])
    evaluated.to_mesh_clear()
    if attribute:return roots,normals,root_uv,root_values
    return roots,normals,root_uv


def build_strands(name,obj,roots,normals,uv,length,kind,under):
    N=len(roots)
    if N==0:return
    x,y,z=roots.T;sgn=np.tanh(x*20)
    if kind=='continuous':
        # One continuous direction field avoids crown/cheek/chest shelves.
        crown=smoothstep(.44,.56,z)
        collar=1-smoothstep(.28,.385,z)
        flow=np.column_stack([sgn*(.90-.52*collar-.22*crown),np.full(N,.04),-.25+.95*crown-.75*collar])
        ex=np.where(x<0,-.075,.075)
        eye_dist=np.hypot(x-ex,z-.455)
        eye_weight=(1-smoothstep(.030,.073,eye_dist))*(1-smoothstep(-.73,-.655,y))
        outward=normalize(np.column_stack([x-ex,np.zeros(N),z-.455]))
        flow=flow*(1-eye_weight[:,None])+outward*eye_weight[:,None]
    elif kind=='eyelid':flow=np.column_stack([x-np.where(x<0,-.075,.075),np.zeros(N),z-.455])
    elif kind=='chest':flow=np.column_stack([sgn*.35,np.full(N,.05),np.full(N,-1.)])
    elif kind=='cheek':flow=np.column_stack([sgn,np.full(N,.08),-.22+1.4*(z-.42)])
    elif kind=='forehead':flow=np.column_stack([sgn*.62,np.full(N,.10),np.full(N,.8)])
    elif kind=='ear':flow=np.column_stack([sgn*.24,np.zeros(N),np.ones(N)])
    else:flow=np.column_stack([sgn*.7,np.zeros(N),np.full(N,-.28)])
    tangent=normalize(flow-normals*(flow*normals).sum(1,keepdims=True));lateral=normalize(np.cross(normals,tangent))
    if kind=='continuous':
        eye_d=np.minimum(np.hypot(x-.075,z-.455),np.hypot(x+.075,z-.455))
        front=1-smoothstep(-.73,-.655,y)
        # Short mask is localized around the eyes, not a horizontal band.
        eye_weight=(1-smoothstep(.026,.080,eye_d))*front
        muzzle_weight=(1-smoothstep(.055,.14,np.hypot(x,(z-.402)*1.1)))*front
        base_L=.102+.027*(1-smoothstep(.22,.38,z))
        lengths=base_L*(1-.77*np.maximum(eye_weight,muzzle_weight))
        L=lengths*(.49 if under else 1)
    else:L=np.full(N,length)
    L*=np.clip(rng.lognormal(-.024,.22,N),.5,1.6)
    # Taper near eye rims and the mouth so hair cannot obscure the landmarks.
    if kind in ['cheek','forehead','face']:
        d=np.minimum(np.hypot(x-.075,z-.455),np.hypot(x+.075,z-.455))
        L*=np.clip((d-.027)/.035,.18,1)
    steps=12;t=np.linspace(0,1,steps,dtype=np.float32)[None,:,None]
    normal_bend=.88*t-.27*t*t if under else .84*t-.25*t*t
    tangent_bend=.10*t+.40*t*t if under else .10*t+.62*t*t
    pts=roots[:,None,:]+L[:,None,None]*(normals[:,None,:]*normal_bend+tangent[:,None,:]*tangent_bend)
    cell=.020 if kind in ['chest','continuous'] else .012
    _,groups=np.unique(np.floor(roots/cell).astype(np.int32),axis=0,return_inverse=True)
    weights=np.bincount(groups)
    means=np.column_stack([np.bincount(groups,weights=roots[:,i])/weights for i in range(3)])
    delta=means[groups]-roots;delta-=normals*(delta*normals).sum(1,keepdims=True)
    pts+=delta[:,None,:]*t**2*(.12 if under else .38)
    phase=rng.uniform(0,2*np.pi,N)[:,None,None]
    amp=.052 if kind in ['chest','continuous'] else .023
    pts+=lateral[:,None,:]*L[:,None,None]*amp*(np.sin(t*6.5+phase)-np.sin(phase))*t
    if kind=='chest':pts[:,:,2]-=L[:,None]*.12*t[0,:,0]**2
    radius=rng.uniform(.000095,.000145,N) if under else rng.uniform(.000075,.00012,N)
    if kind in ['face','ear','eyelid']:radius*=.70
    radii=radius[:,None]*(.025+.975*(1-t[0,:,0])**.8)
    data=bpy.data.hair_curves.new(name);data.add_curves([steps]*N)
    data.attributes['position'].data.foreach_set('vector',pts.astype(np.float32).reshape(-1))
    data.attributes.new('radius','FLOAT','POINT').data.foreach_set('value',radii.astype(np.float32).reshape(-1))
    data.attributes.new('surface_uv_coordinate','FLOAT2','CURVE').data.foreach_set('vector',uv.astype(np.float32).reshape(-1))
    data.surface=obj;data.surface_uv_map='UVMap';data.materials.append(hair)
    ob=bpy.data.objects.new(name,data);collection.objects.link(ob)
    ob['region']=kind;ob['layer']='undercoat' if under else 'outercoat';ob['length']=length
    manifest['regions'][name]={'strands':N,'length_scale_min':float(L.min()),'length_scale_median':float(np.median(L)),'length_scale_max':float(L.max())}
    print('GROOM',name,N,flush=True)


body=bpy.data.objects['Ogong_Rounded_Head_And_Collar']
r,n,u=sample_surface(body,230000)
valid=r[:,2]>.020
for ex in [-.075,.075]:valid&=~((r[:,1]<-.71)&(((r[:,0]-ex)/.025)**2+((r[:,2]-.455)/.026)**2<1))
r,n,u=r[valid],n[valid],u[valid]
for label,mask,length,kind in [('Face_And_Collar',np.ones(len(r),dtype=bool),.105,'continuous')]:
    ids=np.flatnonzero(mask)
    for under,selected in [(False,ids[::3]),(True,np.delete(ids,np.arange(0,len(ids),3)))]:
        build_strands(label+('_Under' if under else '_Outer'),body,r[selected],n[selected],u[selected],length*(.40 if under else 1),kind,under)

face=bpy.data.objects['Ogong_Short_Muzzle_Nose_Mouth']
r,n,u,nose_mask=sample_surface(face,80000,'nose_pigment')
mat=face.data.materials[0]
mix=next(x for x in mat.node_tree.nodes if x.type=='MIX_RGB')
image=mix.inputs[1].links[0].from_node.image
pixels=np.empty(image.size[0]*image.size[1]*4,dtype=np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape(image.size[1],image.size[0],4)
xy=np.clip((u*[image.size[0]-1,image.size[1]-1]).astype(int),0,[image.size[0]-1,image.size[1]-1])
rgb=pixels[xy[:,1],xy[:,0],:3];luma=rgb@np.array([.2126,.7152,.0722])
valid=(luma>.14)&(r[:,2]>.385)
valid&=nose_mask<.04
valid&=~(((r[:,0]/.033)**2+((r[:,2]-.420)/.030)**2)<1.15)
build_strands('Muzzle_Soft_White_Fur',face,r[valid],n[valid],u[valid],.020,'face',False)
for label in ['L','R']:
    lid=bpy.data.objects['Ogong_Eyelid_Skin_'+label]
    r,n,u=sample_surface(lid,5000)
    build_strands('Eyelid_'+label+'_Short_Coat',lid,r,n,u,.007,'eyelid',False)
    ear=bpy.data.objects['Ogong_Upright_Ear_'+label]
    r,n,u=sample_surface(ear,7000)
    # Fine short ear coat leaves an indication of the inner ear.
    build_strands('Ear_'+label+'_Fur',ear,r,n,u,.010,'ear',False)

scene.render.engine='CYCLES';scene.render.threads_mode='FIXED';scene.render.threads=6
scene.cycles.samples=args.samples;scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE'
scene.cycles.adaptive_threshold=.018;scene.render.resolution_x=args.size;scene.render.resolution_y=int(args.size*1.05);scene.render.resolution_percentage=100
scene['study_status']='Photo-guided Pomeranian face reconstruction with new rounded head, eyes and upright ears.'
cam=scene.camera;target=Vector((0,-.65,.430));cam.data.ortho_scale=.65
def point_camera(location):
    cam.location=location;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
point_camera((0,-2.5,.46))
# Pack the actual supplied photos for local visual comparison in Blender.
refs=bpy.data.collections.new('Ogong_Photo_References');scene.collection.children.link(refs)
for index,filename in enumerate(['KakaoTalk_20261005_184824793_06.jpg','KakaoTalk_20261005_184824793_01.png']):
    path=ROOT/'ReferencePhotos'/filename
    photo=bpy.data.images.load(str(path),check_existing=True);photo.pack()
    ref=bpy.data.objects.new('Reference_Photo_'+str(index+1),None)
    ref.empty_display_type='IMAGE';ref.data=photo;ref.empty_display_size=.65
    ref.location=(-.75 if index==0 else .75,0,.4);ref.rotation_euler=(np.pi/2,0,0)
    ref.hide_render=True;refs.objects.link(ref);ref.hide_set(True)
scene['scope']='Editable head and chest portrait. Full body and animation rig remain unfinished.'
scene['reference_photos']='Two original photos packed in hidden Ogong_Photo_References collection.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
manifest['total_strands']=sum(x['strands'] for x in manifest['regions'].values())
(OUT/f'{args.tag}_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'ogong_pomeranian_face_{args.tag}.blend'),compress=True)
for view in args.views:
    point_camera((.90,-2.15,.50) if view=='threequarter' else (0,-2.5,.46))
    if view=='small':scene.render.resolution_x=256;scene.render.resolution_y=268
    else:scene.render.resolution_x=args.size;scene.render.resolution_y=int(args.size*1.05)
    scene.render.filepath=str(OUT/f'{args.tag}_{view}.png');print('RENDER',view,flush=True);bpy.ops.render.render(write_still=True)
print('POMERANIAN_FACE_COMPLETE',json.dumps(manifest),flush=True)
