"""Build a standing full-body study using the reference-proportion sculpt."""
import argparse, json
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector
from fullbody_fields import HEAD_SCALE, HEAD_OFFSET, EYE_LOCAL, EYE_RADIUS, to_head, mouth_local, eye_local, LANDMARKS

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'ArtSource/FullbodyStudy'
p=argparse.ArgumentParser();p.add_argument('--tag',default='fullbody05');p.add_argument('--render',action='store_true');a=p.parse_args()
anatomy=json.loads((OUT/f'{a.tag}_anatomy.json').read_text())
closed=anatomy['expression']=='closed'
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ArtSource/PortraitStudy/ogong_portrait02_structure.blend'))
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
scene=bpy.context.scene
for marker in list(scene.timeline_markers):scene.timeline_markers.remove(marker)
for collection in list(bpy.data.collections):
    if collection.name!='Collection' and not collection.objects:bpy.data.collections.remove(collection)


def mesh_object(name,v,f,material):
    m=bpy.data.meshes.new(name);m.from_pydata(np.asarray(v).tolist(),[],list(f));m.update()
    bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free()
    for poly in m.polygons:poly.use_smooth=True
    m.materials.append(material);ob=bpy.data.objects.new(name,m);scene.collection.objects.link(ob)
    uv=m.uv_layers.new(name='UVMap');co=np.array([v.co[:] for v in m.vertices])
    uvs=np.column_stack([np.arctan2(co[:,1],co[:,0])/(2*np.pi)+.5,co[:,2]])
    loopids=np.array([l.vertex_index for l in m.loops]);uv.data.foreach_set('uv',uvs[loopids].astype(np.float32).ravel())
    return ob


def mat(name,color,rough=.5):
    m=bpy.data.materials.new(name);m.use_nodes=True;sh=m.node_tree.nodes.get('Principled BSDF')
    sh.inputs['Base Color'].default_value=(*color,1);sh.inputs['Roughness'].default_value=rough
    return m


skin=bpy.data.materials['White skin under coat'];skin.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.52,.485,.42,1)
mouth=bpy.data.materials['Mouth interior'];lid=bpy.data.materials['Soft dark eyelid']
d=np.load(OUT/f'{a.tag}_body.npz');body=mesh_object('Ogong_Continuous_Anatomy',d['vertices'],d['faces'],skin)
body.data.materials.append(mouth);body.data.materials.append(lid)
c=np.array([f.center[:] for f in body.data.polygons]);hx,hy,hz=to_head(*c.T)
mi=np.zeros(len(c),np.int32)
if not closed:mi[np.abs(mouth_local(hx,hy,hz))<.0015]=1
body.data.polygons.foreach_set('material_index',mi)
# Vertex-interpolated eyelid pigment avoids a polygon-stepped dark rim.
vco=np.array([v.co[:] for v in body.data.vertices]);vx,vy,vz=to_head(*vco.T)
ed=np.abs(eye_local(vx,vy,vz));blend=np.clip((.0038-ed)/.0033,0,1)
blend=blend*blend*(3-2*blend)*(vy<-.732)
attribute=body.data.attributes.new('Eyelid_Pigment','FLOAT','POINT');attribute.data.foreach_set('value',blend.astype(np.float32))
sn=skin.node_tree.nodes;sl=skin.node_tree.links;sb=sn['Principled BSDF']
mask=sn.new('ShaderNodeAttribute');mask.attribute_name='Eyelid_Pigment'
pigment=sn.new('ShaderNodeMixRGB');pigment.blend_type='MIX';pigment.inputs[1].default_value=(.52,.485,.42,1);pigment.inputs[2].default_value=(.004,.0025,.002,1)
sl.new(mask.outputs['Fac'],pigment.inputs[0]);sl.new(pigment.outputs[0],sb.inputs['Base Color'])
sm=body.modifiers.new('Surface relaxation','SMOOTH');sm.factor=.3;sm.iterations=3
body['anatomy']='One continuous symmetric head, neck, chest, body and four-legged sculpt.'
if closed:
    from closed_mouth import add_closed_lips
    add_closed_lips(body)
d=np.load(OUT/f'{a.tag}_nose.npz');nose=mesh_object('Ogong_Nose',d['vertices'],d['faces'],bpy.data.materials['Charcoal nose'])
sm=nose.modifiers.new('Nose relaxation','SMOOTH');sm.factor=.25;sm.iterations=2

# Dark iris under a separate refractive corneal shell.
iris=bpy.data.materials['Deep brown iris and pupil'];ib=iris.node_tree.nodes.get('Principled BSDF')
ib.inputs['Roughness'].default_value=.37;ib.inputs['Specular IOR Level'].default_value=.12
for node in iris.node_tree.nodes:
    if node.type=='VALTORGB':
        for e in node.color_ramp.elements:
            if .24<e.position<.46:e.color=(.004,.0017,.0007,1) if e.position<.30 else (.002,.0009,.0004,1)
cornea=mat('Clear cornea',(.96,.97,1),.045)
cb=cornea.node_tree.nodes['Principled BSDF'];cb.inputs['Transmission Weight'].default_value=1;cb.inputs['IOR'].default_value=1.376
for sign,label in [(-1,'L'),(1,'R')]:
    center=EYE_LOCAL.copy();center[0]*=sign;center=center*HEAD_SCALE+HEAD_OFFSET
    for label2,r,material in [('Iris',EYE_RADIUS,iris),('Cornea',EYE_RADIUS+.00065,cornea)]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=40,radius=r,location=center)
        ob=bpy.context.object;ob.name=f'Ogong_Eye_{label}_{label2}';ob.scale=HEAD_SCALE;ob.data.materials.append(material)
        for poly in ob.data.polygons:poly.use_smooth=True

# Open expression is retained as an explicit build option, not the default.
if not closed:
    # A tongue with a rounded, thicker tip, central groove and papillae shading.
    tongue=bpy.data.materials['Soft pink tongue'];tn=tongue.node_tree.nodes;tl=tongue.node_tree.links;tb=tn['Principled BSDF']
    tb.inputs['Roughness'].default_value=.38;tb.inputs['Coat Weight'].default_value=.09
    tex=tn.new('ShaderNodeTexVoronoi');tex.inputs['Scale'].default_value=70
    bump=tn.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.5;bump.inputs['Distance'].default_value=.0007
    tl.new(tex.outputs['Distance'],bump.inputs['Height']);tl.new(bump.outputs[0],tb.inputs['Normal'])
    vv=[];ff=[];rings=64;sectors=64
    for j in range(rings):
        t=j/(rings-1);cy=-.803-.040*np.sin(t*np.pi/2);cz=.369-.067*t+.004*np.sin(t*np.pi)
        dy=-.040*np.pi/2*np.cos(t*np.pi/2);dz=-.067+.004*np.pi*np.cos(t*np.pi)
        normal=np.array([0,dz,-dy]);normal/=np.linalg.norm(normal)
        w=.033*np.sqrt(max(.00001,1-((t-.35)/.65)**2));thick=.0048*(1-.18*t)
        for k in range(sectors):
            theta=2*np.pi*k/sectors;xx=w*np.cos(theta);off=thick*np.sin(theta)
            off-=.0011*np.exp(-(xx/.0022)**2)*max(0,np.sin(theta))*np.sin(t*np.pi)
            co=np.array([xx,cy,cz])+normal*off;vv.append(co*HEAD_SCALE+HEAD_OFFSET)
    for j in range(rings-1):
        for k in range(sectors):ff.append([j*sectors+k,j*sectors+(k+1)%sectors,(j+1)*sectors+(k+1)%sectors,(j+1)*sectors+k])
    for row,reverse in [(0,True),(rings-1,False)]:
        idx=len(vv);vv.append(np.mean(vv[row*sectors:(row+1)*sectors],axis=0))
        for k in range(sectors):
            tri=[idx,row*sectors+k,row*sectors+(k+1)%sectors];ff.append(tri[::-1] if reverse else tri)
    ob=mesh_object('Ogong_Tongue',vv,ff,tongue);sub=ob.modifiers.new('Tongue smoothing','SUBSURF');sub.levels=1

    enamel=bpy.data.materials['Warm enamel']
    for sign in [-1,1]:
        for x0,r,height in [(.042,.0021,.004),(.057,.0026,.007)]:
            pos=np.array([sign*x0,-.802,.371-height/2])*HEAD_SCALE+HEAD_OFFSET
            bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=.0005,radius2=r*1.1,depth=height*1.1,location=pos)
            ob=bpy.context.object;ob.name='Ogong_Upper_Tooth';ob.data.materials.append(enamel)
            bevel=ob.modifiers.new('Rounded enamel','BEVEL');bevel.width=.0008;bevel.segments=3
            for poly in ob.data.polygons:poly.use_smooth=True

pink=bpy.data.materials['Muted ear interior']
for sign,label in [(-1,'L'),(1,'R')]:
    v=[];f=[];na=48;nt=32
    for j in range(nt):
        t=j/(nt-1);w=.034*(1-t)**.8+.0007;depth=.011*(1-t)+.0007
        for k in range(na):
            th=2*np.pi*k/na;co=np.array([sign*(.096+.024*t)+w*np.cos(th),-.614+depth*np.sin(th),.515+.092*t])
            v.append(co*HEAD_SCALE+HEAD_OFFSET)
    for j in range(nt-1):
        for k in range(na):f.append([j*na+k,j*na+(k+1)%na,(j+1)*na+(k+1)%na,(j+1)*na+k])
    # Cap the ear for a closed editable surface.
    f.append(list(range(na-1,-1,-1)));f.append(list(range((nt-1)*na,nt*na)))
    ear=mesh_object('Ogong_Ear_'+label,v,f,skin);ear.data.materials.append(pink)
    for poly in ear.data.polygons:
        if poly.normal.y<-.65 and .82<poly.center.z<.902:poly.material_index=1
    mod=ear.modifiers.new('Ear smoothing','SUBSURF');mod.levels=1

# Curled tail tube, grown from the pelvis. The coat will supply the plume.
from mathutils.geometry import interpolate_bezier
controls=[(0,.416,.590),(.018,.468,.675),(.020,.452,.749),(.002,.343,.762),(-.020,.235,.717),(-.025,.223,.667)]
pts=[]
for i in range(len(controls)-1):
    p0=np.array(controls[max(0,i-1)]);p1=np.array(controls[i]);p2=np.array(controls[i+1]);p3=np.array(controls[min(len(controls)-1,i+2)])
    for t in np.linspace(0,1,16,endpoint=False):
        pts.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3))
pts.append(np.array(controls[-1]));pts=np.array(pts)
v=[];f=[];ns=32
for i,co in enumerate(pts):
    tangent=pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)];tangent/=np.linalg.norm(tangent)
    normal=np.cross(tangent,[1,0,0]);normal/=np.linalg.norm(normal);side=np.cross(tangent,normal)
    r=.045*(1-i/(len(pts)-1))**.6+.007
    for k in range(ns):v.append(co+r*(normal*np.cos(2*np.pi*k/ns)+side*np.sin(2*np.pi*k/ns)))
for i in range(len(pts)-1):
    for k in range(ns):f.append([i*ns+k,i*ns+(k+1)%ns,(i+1)*ns+(k+1)%ns,(i+1)*ns+k])
f.append(list(range(ns-1,-1,-1)));f.append(list(range((len(pts)-1)*ns,len(pts)*ns)))
tail=mesh_object('Ogong_Curled_Tail',v,f,skin)
np.savez_compressed(OUT/'tail_guide.npz',centers=pts)

# Hidden locator collection provides explicit, editable proportional anchors.
guides=bpy.data.collections.new('Reference_Proportion_Landmarks');scene.collection.children.link(guides)
for name,co in LANDMARKS.items():
    ob=bpy.data.objects.new(name,None);guides.objects.link(ob);ob.location=co;ob.empty_display_size=.013;ob.hide_render=True
guides.hide_viewport=True;guides.hide_render=True

floor=mat('Warm neutral backdrop',(.62,.54,.44),.85)
fb=floor.node_tree.nodes['Principled BSDF'];fb.inputs['Emission Color'].default_value=(.62,.54,.44,1);fb.inputs['Emission Strength'].default_value=.12
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.003));ob=bpy.context.object;ob.name='Studio_Ground';ob.data.materials.append(floor)
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.47,.42,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
wn=scene.world.node_tree.nodes;wl=scene.world.node_tree.links
camera_bg=wn.new('ShaderNodeBackground');camera_bg.inputs[0].default_value=(.46,.39,.315,1);camera_bg.inputs[1].default_value=1
light_path=wn.new('ShaderNodeLightPath');bg_mix=wn.new('ShaderNodeMixShader')
wl.new(light_path.outputs['Is Camera Ray'],bg_mix.inputs[0]);wl.new(wn['Background'].outputs[0],bg_mix.inputs[1]);wl.new(camera_bg.outputs[0],bg_mix.inputs[2]);wl.new(bg_mix.outputs[0],wn['World Output'].inputs['Surface'])


def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()


for name,loc,power,size in [('Key',(-2,-3,3),450,1.8),('Fill',(2.8,-1.7,1.8),120,2.2),('Rim',(.7,2.3,2.8),350,1.8)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;aim(ob,(0,0,.5))
views={'Front':((0,-4,.66),(0,0,.52),1.20),'Side':((8,0,.78),(0,0,.52),1.48),
       'Back':((0,4,.66),(0,0,.52),1.20),'Top':((0,0,4),(0,0,0),1.5),
       'Threequarter':((2.8,-3.8,1.40),(0,0,.48),1.50),
       'Face':((0,-4,.76),(0,-.39,.748),.62),
       'Opposite':((-8,0,.78),(0,0,.52),1.48)}
for frame,(name,(loc,target,scale)) in enumerate(views.items(),start=1):
    data=bpy.data.cameras.new('Review_'+name);data.type='ORTHO';data.ortho_scale=scale
    ob=bpy.data.objects.new('Review_'+name,data);scene.collection.objects.link(ob);ob.location=loc;aim(ob,target)
    scene.timeline_markers.new(name,frame=frame).camera=ob
scene.frame_set(1);scene.camera=bpy.data.objects['Review_Front']
scene.render.engine='CYCLES';scene.render.threads_mode='FIXED';scene.render.threads=6
scene.cycles.samples=20;scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE'
scene.cycles.max_bounces=7;scene.cycles.diffuse_bounces=4;scene.cycles.glossy_bounces=5;scene.cycles.transmission_bounces=6
scene.cycles.adaptive_threshold=.035
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.0
scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene['scope']='Standing full-body proportion study from the user supplied five-view sheet. No rig.'
scene['reference_fit']='Visual landmark estimates. No exact pixel overlay or real-world measurements.'
scene['default_expression']='closed' if closed else 'open'
note=bpy.data.texts.get('READ_ME_CLEAN_FACE')
if note:bpy.data.texts.remove(note)
note=bpy.data.texts.new('READ_ME_FULLBODY')
note.write('오공이 전신 비율 작업본.\n1 정면 / 2 측면 / 3 후면 / 4 위 / 5 사선 / 6 얼굴 / 7 반대 측면 카메라.\n첨부한 다각도 이미지를 눈으로 비교해 비율을 맞춘 작업본이며 실측 3D 복원은 아닙니다.\nReference_Proportion_Landmarks 컬렉션에 기준점을 보관했습니다.\n리깅 및 애니메이션 미포함.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'ogong_{a.tag}_structure.blend'),compress=True)
if a.render:
    for view,frame in [('Front',1),('Side',2)]:
        scene.frame_set(frame);scene.camera=bpy.data.objects['Review_'+view]
        scene.render.filepath=str(OUT/f'{a.tag}_structure_{view.lower()}.png');print('RENDER',view,flush=True);bpy.ops.render.render(write_still=True)
print('FULLBODY_STRUCTURE_SAVED',flush=True)
