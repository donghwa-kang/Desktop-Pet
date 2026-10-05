"""Directional full-body groom with independent facial, limb and tail regions."""
import argparse,json
from pathlib import Path
import bpy
import numpy as np
from mathutils.kdtree import KDTree
from fullbody_fields import to_head

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'ArtSource/FullbodyStudy'
p=argparse.ArgumentParser();p.add_argument('--tag',default='fullbody04');p.add_argument('--samples',type=int,default=20);p.add_argument('--size',type=int,default=640);p.add_argument('--views',nargs='*',default=['Front','Side']);a=p.parse_args()
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(OUT/f'ogong_{a.tag}_structure.blend'))
scene=bpy.context.scene;collection=bpy.data.collections.new('Ogong_Groom_Regions');scene.collection.children.link(collection)
rng=np.random.default_rng(100601);report={}
hair=bpy.data.materials['Clean_White_Fur'];hair.name='Ogong_Ivory_White_Fibres'
nodes=hair.node_tree.nodes;links=hair.node_tree.links
shader=next(n for n in nodes if n.type=='BSDF_HAIR_PRINCIPLED')
shader.inputs['Roughness'].default_value=.42;shader.inputs['Radial Roughness'].default_value=.52
info=nodes.new('ShaderNodeHairInfo');random=nodes.new('ShaderNodeValToRGB')
random.color_ramp.elements[0].color=(.48,.444,.378,1);random.color_ramp.elements[1].color=(.75,.721,.66,1)
links.new(info.outputs['Random'],random.inputs[0])
root=nodes.new('ShaderNodeValToRGB');root.color_ramp.elements[0].color=(.64,.62,.58,1);root.color_ramp.elements[1].color=(1,1,1,1);root.color_ramp.elements[1].position=.65
links.new(info.outputs['Intercept'],root.inputs[0])
mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
links.new(random.outputs[0],mix.inputs[1]);links.new(root.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],shader.inputs['Color'])


def norm(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-10)
def ss(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1);return t*t*(3-2*t)
def uv_at(r):return np.column_stack([np.arctan2(r[:,1],r[:,0])/(2*np.pi)+.5,r[:,2]])


def sample(ob,count,paired=False):
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles()
    v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    normals=np.empty_like(v);m.vertices.foreach_get('normal',normals.ravel())
    f=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',f);f=f.reshape(-1,3)
    material=np.empty(len(f),np.int32);m.loop_triangles.foreach_get('material_index',material)
    tri=v[f];centers=tri.mean(1);area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
    if paired:
        x,y,z=centers.T;area*=(x>0)&(material==0)&(z>.018)
        area*=np.where((y<-.17)&(z>.40),1.8,1.)
        area*=np.where((y<-.50)&(x<.105)&(z>.625)&(z<.730),3.0,1.)
    ids=rng.choice(len(f),count,p=area/area.sum());s=np.sqrt(rng.random(count));q=rng.random(count)
    w=np.column_stack([1-s,s*(1-q),s*q]);r=np.einsum('ni,nij->nj',w,tri[ids]);n=norm(np.einsum('ni,nij->nj',w,normals[f[ids]]))
    ev.to_mesh_clear();return r,n


def write_curves(name,surface,points,radii,paired=False):
    if paired:
        other=points.copy();other[:,:,0]*=-1
        other+=rng.uniform(-.0006,.0006,(len(other),1,3))*np.linspace(0,1,points.shape[1])[None,:,None]**2
        points=np.concatenate([points,other]);radii=np.concatenate([radii,radii])
    points[:,:,2]=np.maximum(points[:,:,2],.0035)
    d=bpy.data.hair_curves.new(name);d.add_curves([points.shape[1]]*len(points))
    d.attributes['position'].data.foreach_set('vector',points.astype(np.float32).ravel())
    d.attributes.new('radius','FLOAT','POINT').data.foreach_set('value',radii.astype(np.float32).ravel())
    d.attributes.new('surface_uv_coordinate','FLOAT2','CURVE').data.foreach_set('vector',uv_at(points[:,0]).astype(np.float32).ravel())
    d.surface=surface;d.surface_uv_map='UVMap';d.materials.append(hair)
    ob=bpy.data.objects.new(name,d);collection.objects.link(ob)
    report[name]={'strands':len(points),'points_per_strand':points.shape[1],'surface':surface.name}
    print('GROOM',name,len(points),flush=True)


def groom(name,surface,r,n,kind,under=False,paired=True):
    count=len(r);x,y,z=r.T
    if kind=='head':
        hx,hy,hz=to_head(x,y,z);crown=ss(.435,.555,hz);collar=1-ss(.27,.385,hz)
        flow=np.column_stack([np.tanh(x*20)*(.85-.49*collar-.16*crown),np.full(count,.035),-.26+.97*crown-.82*collar])
        ex=np.sign(x)*.077;ed=np.hypot(x-ex,z-.742)
        front=1-ss(-.475,-.395,y);ew=(1-ss(.024,.080,ed))*front
        away=norm(np.column_stack([x-ex,np.zeros(count),z-.742]))
        flow=flow*(1-ew[:,None])+away*ew[:,None]
        mw=(1-ss(.053,.132,np.hypot(x,(z-.686)*1.15)))*front
        L=(.103+.090*(1-ss(.48,.63,z)))*(1-.78*np.maximum(ew,mw))
        # Avoid a long, straight beard hanging away from the jaw in profile.
        jaw=(y<-.47)&(z<.620)&(z>.540);L*=np.where(jaw,.52,1.)
        amplitude=.035+.055*(1-ss(.48,.63,z))
    elif kind=='muzzle':
        flow=np.column_stack([np.tanh(x*26),np.full(count,-.10),-.35+3.0*(z-.70)])
        L=np.full(count,.020);ed=np.hypot(x-.077,z-.742);L*=.28+.72*ss(.023,.050,ed)
        amplitude=np.full(count,.023)
    elif kind=='body':
        rear=ss(.30,.49,y)
        flow=np.column_stack([np.sign(x)*.10,.30-.36*rear,-.83+1.0*ss(.48,.69,z)])
        L=(.115+.060*(1-ss(.38,.65,z)))*(1-.33*rear)
        amplitude=.07+.03*ss(.15,.50,y)
    elif kind=='legs':
        flow=np.column_stack([np.sign(x)*.06,.06+.2*ss(0,.3,y),np.full(count,-1.)])
        hind=ss(.1,.3,y);L=.030+.022*ss(.07,.21,z)+.038*ss(.13,.30,z)*hind
        L*=.58+.42*ss(.035,.09,z);amplitude=np.full(count,.055)
    elif kind=='ear':
        flow=np.column_stack([np.sign(x)*.20,np.zeros(count),np.ones(count)])
        L=np.full(count,.012);amplitude=np.full(count,.03)
    else:
        centers=np.load(OUT/'tail_guide.npz')['centers'];tree=KDTree(len(centers))
        for i,co in enumerate(centers):tree.insert(co,i)
        tree.balance();ids=np.array([tree.find(co)[1] for co in r])
        tangents=np.gradient(centers,axis=0);flow=norm(tangents[ids]);flow[:,2]-=.75
        u=ids/(len(centers)-1);L=.145+.085*np.sin(np.pi*u);amplitude=np.full(count,.135)
    L*=.52 if under else 1.
    tangent=norm(flow-n*np.sum(flow*n,axis=1,keepdims=True));lateral=norm(np.cross(n,tangent))
    guides=rng.choice(count,min(count,max(100,count//45)),replace=False);tree=KDTree(len(guides))
    for i,co in enumerate(r[guides]):tree.insert(co,i)
    tree.balance();g=np.array([tree.find(co)[1] for co in r])
    L*=np.clip(rng.lognormal(-.015,.17,len(guides))[g]*rng.lognormal(-.005,.075,count),.62,1.5)
    if not under:
        fly=rng.random(count)<.012;L*=np.where(fly,1.36,1.);amplitude*=np.where(fly,1.7,1.)
    t=np.linspace(0,1,12,dtype=np.float32)[None,:,None]
    normal_bend=.69*t-.16*t*t if under else .64*t-.15*t*t
    tangent_bend=.10*t+.45*t*t if under else .13*t+.59*t*t
    if kind=='tail':normal_bend=.52*t-.18*t*t;tangent_bend=.17*t+.70*t*t
    points=r[:,None,:]+L[:,None,None]*(n[:,None,:]*normal_bend+tangent[:,None,:]*tangent_bend)
    delta=r[guides[g]]-r;delta-=n*np.sum(delta*n,axis=1,keepdims=True)
    points+=delta[:,None,:]*t*t*(.12 if under else (.28 if kind=='muzzle' else .52))
    phase=rng.uniform(0,2*np.pi,len(guides))[g,None,None]
    wave=(np.sin(t*8.0+phase)-np.sin(phase))*t
    points+=lateral[:,None,:]*L[:,None,None]*amplitude[:,None,None]*wave
    points[:,:,2]-=L[:,None]*(.08 if kind=='tail' else .045)*t[0,:,0]**2
    radius=rng.uniform(.000075,.000125,count)
    if under:radius*=.86
    if kind in ['muzzle','ear']:radius*=.58
    radii=radius[:,None]*(.018+.982*(1-t[0,:,0])**.82)
    write_curves(name,surface,points,radii,paired)


body=bpy.data.objects['Ogong_Continuous_Anatomy'];r,n=sample(body,190000,paired=True)
x,y,z=r.T
keep=~((y<-.50)&((x/.035)**2+((z-.7096)/.028)**2<1.05))
keep&=~((y<-.477)&(((x-.077)/.024)**2+((z-.742)/.0215)**2<1))
r,n=r[keep],n[keep];x,y,z=r.T
muzzle=(y<-.50)&(x<.105)&(z>.622)&(z<.730)
leg=z<.325
head=(y<-.185)&(z>.325)&~muzzle
trunk=~(muzzle|head|leg)
for region,mask in [('muzzle',muzzle),('head',head),('body',trunk),('legs',leg)]:
    rr,nn=r[mask],n[mask]
    if region in ['head','body']:
        outer=np.arange(len(rr))%2==0
        groom(region.title()+'_Guard',body,rr[outer],nn[outer],region)
        groom(region.title()+'_Under',body,rr[~outer],nn[~outer],region,under=True)
    else:groom(region.title()+'_Fine',body,rr,nn,region)
for label in ['L','R']:
    ob=bpy.data.objects['Ogong_Ear_'+label];rr,nn=sample(ob,3600);groom('Ear_'+label,ob,rr,nn,'ear',paired=False)
tail=bpy.data.objects['Ogong_Curled_Tail'];rr,nn=sample(tail,52000);groom('Tail_Plume',tail,rr,nn,'tail',paired=False)

# Sparse whiskers remain independent of the coat.
rr,nn=sample(body,20000,paired=True);xx,yy,zz=rr.T
rr=rr[(yy<-.54)&(xx>.034)&(xx<.075)&(zz>.671)&(zz<.700)]
rr=rr[rng.choice(len(rr),10,replace=False)];t=np.linspace(0,1,12)[None,:,None]
direction=norm(np.column_stack([rng.uniform(.8,1,10),rng.uniform(-.2,-.1,10),rng.uniform(-.3,.05,10)]))
wp=rr[:,None,:]+direction[:,None,:]*rng.uniform(.045,.085,(10,1,1))*t
wp[:,:,2]-=.009*t[0,:,0]**2
rad=rng.uniform(.000055,.00008,(10,1))*(1-t[0,:,0])**.7+.000002
write_curves('Muzzle_Whiskers',body,wp,rad,paired=True)

scene.cycles.samples=a.samples;scene.render.resolution_x=a.size;scene.render.resolution_y=a.size
scene.frame_set(1);scene.camera=bpy.data.objects['Review_Front']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
manifest={'revision':a.tag,'regions':report,'total_strands':sum(v['strands'] for v in report.values()),'rigged':False}
(OUT/f'{a.tag}_groom.json').write_text(json.dumps(manifest,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'ogong_{a.tag}.blend'),compress=True)
for view in a.views:
    scene.frame_set(['Front','Side','Back','Top','Threequarter','Face','Opposite'].index(view)+1);scene.camera=bpy.data.objects['Review_'+view]
    scene.render.filepath=str(OUT/f'{a.tag}_{view.lower()}.png');print('RENDER',view,flush=True);bpy.ops.render.render(write_still=True)
print('FULLBODY_GROOM_COMPLETE',manifest['total_strands'],flush=True)
