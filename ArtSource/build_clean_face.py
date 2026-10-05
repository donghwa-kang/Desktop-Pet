"""Build a clean, symmetric face from continuous surfaces. No retriever geometry."""
import argparse, json
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'ArtSource/CleanFace'
p=argparse.ArgumentParser();p.add_argument('--tag',default='clean03');p.add_argument('--size',type=int,default=600);p.add_argument('--samples',type=int,default=24);args=p.parse_args()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene


def material(name,color,roughness=.5):
    m=bpy.data.materials.new(name);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=roughness
    return m


skin=material('White skin under coat',(.60,.585,.55),.72)
mouth=material('Mouth interior',(.013,.003,.004),.62)
lidmat=material('Soft dark eyelid',(.007,.004,.003),.5)
nosemat=material('Charcoal nose',(.008,.007,.006),.37)
nb=nosemat.node_tree.nodes['Principled BSDF'];nb.inputs['Coat Weight'].default_value=.12
nodes=nosemat.node_tree.nodes;links=nosemat.node_tree.links
tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=145;tex.inputs['Detail'].default_value=2
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.0005
links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],nb.inputs['Normal'])
tonguemat=material('Soft pink tongue',(.43,.105,.14),.47)
nb=tonguemat.node_tree.nodes['Principled BSDF'];nb.inputs['Subsurface Weight'].default_value=.13
nodes=tonguemat.node_tree.nodes;links=tonguemat.node_tree.links
tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=155;tex.inputs['Detail'].default_value=2
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00025
links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],nb.inputs['Normal'])
eye_mat=material('Deep brown iris and pupil',(.003,.0015,.001),.085)
eb=eye_mat.node_tree.nodes['Principled BSDF'];eb.inputs['IOR'].default_value=1.38
nodes=eye_mat.node_tree.nodes;links=eye_mat.node_tree.links
coord=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs['Generated'],sep.inputs[0])
vec=nodes.new('ShaderNodeCombineXYZ')
for src,dst in [('X','X'),('Z','Y')]:
    sub=nodes.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=.5
    links.new(sep.outputs[src],sub.inputs[0]);links.new(sub.outputs[0],vec.inputs[dst])
length=nodes.new('ShaderNodeVectorMath');length.operation='LENGTH';links.new(vec.outputs[0],length.inputs[0])
ramp=nodes.new('ShaderNodeValToRGB');cr=ramp.color_ramp
cr.elements.remove(cr.elements[1]);cr.elements[0].color=(.0005,.0004,.0003,1)
for pos,col in [(.21,(.0005,.0004,.0003,1)),(.255,(.008,.003,.001,1)),(.43,(.004,.0018,.0008,1)),(.47,(.001,.0007,.0005,1))]:cr.elements.new(pos).color=col
links.new(length.outputs['Value'],ramp.inputs[0]);links.new(ramp.outputs['Color'],eb.inputs['Base Color'])


def mesh_object(name,verts,faces,mat):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(np.asarray(verts).tolist(),[],np.asarray(faces).tolist());mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for f in mesh.polygons:f.use_smooth=True
    mesh.materials.append(mat)
    ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob)
    uv=mesh.uv_layers.new(name='UVMap')
    coords=np.array([v.co[:] for v in mesh.vertices]);vuv=np.column_stack([(np.arctan2(coords[:,1]+.64,coords[:,0])/(2*np.pi)+.5),coords[:,2]/.65])
    uv.data.foreach_set('uv',vuv[np.array([l.vertex_index for l in mesh.loops])].astype(np.float32).reshape(-1))
    return ob


def ellipsoid(x,y,z,c,r):
    qx=(x-c[0])/r[0];qy=(y-c[1])/r[1];qz=(z-c[2])/r[2]
    k0=np.sqrt(qx*qx+qy*qy+qz*qz);k1=np.sqrt((qx/r[0])**2+(qy/r[1])**2+(qz/r[2])**2)
    return k0*(k0-1)/np.maximum(k1,1e-12)


h=np.load(OUT/'clean_head.npz');body=mesh_object('Clean_Continuous_Head_Muzzle_Collar',h['vertices'],h['faces'],skin)
body.data.materials.append(mouth);body.data.materials.append(lidmat)
centers=np.array([p.center[:] for p in body.data.polygons]);x,y,z=centers.T
mf=ellipsoid(x,y,z,(0,-.823,.376+.009*(x/.070)**2),(.068,.087,.026))
upper=z-(.399-.010*np.exp(-(x/.023)**2))
mh=np.clip(.5+.5*(mf-upper)/.004,0,1)
mf=upper*(1-mh)+mf*mh+.004*mh*(1-mh)
ef=ellipsoid(np.abs(x),y,z,(.070,-.767,.454),(.024,.035,.023))
indices=np.zeros(len(centers),np.int32)
indices[np.abs(mf)<.0012]=1
indices[(np.abs(ef)<.0010)&(y>-.764)]=2
body.data.polygons.foreach_set('material_index',indices)
# The surface is closed: every mouth and eye boundary is part of the head mesh.
body['construction']='New symmetric continuous implicit surface with smooth muzzle and recessed mouth/eye cavities.'
sm=body.modifiers.new('Very light surface relaxation','SMOOTH');sm.factor=.35;sm.iterations=3
n=np.load(OUT/'clean_nose.npz');nose=mesh_object('Clean_Symmetric_Nose_With_Nostrils',n['vertices'],n['faces'],nosemat)
sm=nose.modifiers.new('Nose surface relaxation','SMOOTH');sm.factor=.30;sm.iterations=2

for sign,label in [(-1,'L'),(1,'R')]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=40,radius=.026,location=(sign*.070,-.753,.454))
    ob=bpy.context.object;ob.name='Clean_Eye_'+label;ob.data.materials.append(eye_mat)
    for f in ob.data.polygons:f.use_smooth=True

# Closed tongue with a curved centreline, softly rounded tip and centre groove.
vv=[];ff=[];rings=64;sectors=64
for j in range(rings):
    t=j/(rings-1);cy=-.803-.045*np.sin(t*np.pi/2);cz=.382-.065*t+.004*np.sin(t*np.pi)
    dy=-.045*np.pi/2*np.cos(t*np.pi/2);dz=-.065+.004*np.pi*np.cos(t*np.pi)
    norm=np.array([0,dz,-dy]);norm/=np.linalg.norm(norm)
    width=.034*np.sqrt(max(.00001,1-((t-.35)/.65)**2))
    thick=.0035*(1-.40*t)
    for k in range(sectors):
        a=2*np.pi*k/sectors;xx=width*np.cos(a);offset=thick*np.sin(a)
        if np.sin(a)>0:offset-=.0008*np.exp(-(xx/.002)**2)*np.sin(a)*np.sin(t*np.pi)
        vv.append(np.array([xx,cy,cz])+norm*offset)
for j in range(rings-1):
    for k in range(sectors):ff.append([j*sectors+k,j*sectors+(k+1)%sectors,(j+1)*sectors+(k+1)%sectors,(j+1)*sectors+k])
for row,reverse in [(0,True),(rings-1,False)]:
    center=np.mean(vv[row*sectors:(row+1)*sectors],axis=0);idx=len(vv);vv.append(center)
    for k in range(sectors):
        tri=[idx,row*sectors+k,row*sectors+(k+1)%sectors]
        ff.append(tri[::-1] if reverse else tri)
# Mixed quad/triangle mesh uses lists rather than a rectangular ndarray.
mesh=bpy.data.meshes.new('Clean_Tongue');mesh.from_pydata(np.array(vv).tolist(),[],ff);mesh.update()
ob=bpy.data.objects.new('Clean_Tongue',mesh);scene.collection.objects.link(ob);mesh.materials.append(tonguemat)
for f in mesh.polygons:f.use_smooth=True
sub=ob.modifiers.new('Smooth tongue','SUBSURF');sub.levels=1

# Small upper side teeth give the mouth depth without a large black opening.
enamel=material('Warm enamel',(.63,.61,.54),.38)
for sign in [-1,1]:
    for x0,radius,height in [(.034,.0022,.0045),(.047,.0027,.007)]:
        top=.399-.010*np.exp(-(x0/.023)**2)-.002
        bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.0006,radius2=radius,depth=height,location=(sign*x0,-.796,top-height/2))
        tooth=bpy.context.object;tooth.name='Upper_Tooth';tooth.data.materials.append(enamel)
        bevel=tooth.modifiers.new('Rounded enamel','BEVEL');bevel.width=.001;bevel.segments=3
        for f in tooth.data.polygons:f.use_smooth=True

# Fine midline crease ties the nose to the symmetric upper lip.
cu=bpy.data.curves.new('Philtrum','CURVE');cu.dimensions='3D';cu.bevel_depth=.00065;cu.bevel_resolution=3
sp=cu.splines.new('BEZIER');sp.bezier_points.add(2)
for point,co in zip(sp.bezier_points,[(0,-.818,.408),(0,-.815,.400),(0,-.812,.390)]):
    point.co=co;point.handle_left_type='AUTO';point.handle_right_type='AUTO'
ob=bpy.data.objects.new('Clean_Philtrum',cu);scene.collection.objects.link(ob);cu.materials.append(lidmat)

pink=material('Muted ear interior',(.36,.20,.18),.7)
for sign,label in [(-1,'L'),(1,'R')]:
    ev=[];ef=[];na=64;nt=32
    for j in range(nt):
        t=j/(nt-1);width=.038*(1-t)**.8+.001;depth=.011*(1-t)+.001
        for k in range(na):
            a=2*np.pi*k/na;ev.append((sign*(.103+.025*t)+width*np.cos(a),-.614+depth*np.sin(a),.510+.105*t))
    for j in range(nt-1):
        for k in range(na):ef.append([j*na+k,j*na+(k+1)%na,(j+1)*na+(k+1)%na,(j+1)*na+k])
    ear=mesh_object('Clean_Upright_Ear_'+label,ev,ef,skin);ear.data.materials.append(pink)
    for f in ear.data.polygons:
        if f.normal.y<-.60 and .53<f.center.z<.594:f.material_index=1
    sub=ear.modifiers.new('Ear smoothing','SUBSURF');sub.levels=2

# Native strand material for the subsequent groom.
hair=bpy.data.materials.new('Clean_White_Fur');hair.use_nodes=True;hair.use_fake_user=True
nodes=hair.node_tree.nodes;nodes.clear();links=hair.node_tree.links
out=nodes.new('ShaderNodeOutputMaterial');h=nodes.new('ShaderNodeBsdfHairPrincipled');h.model='CHIANG';h.parametrization='COLOR'
h.inputs['Color'].default_value=(.66,.64,.60,1);h.inputs['Roughness'].default_value=.48;h.inputs['Radial Roughness'].default_value=.55
links.new(h.outputs[0],out.inputs['Surface'])

world=bpy.data.worlds.new('Neutral studio');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.20,.23,1);world.node_tree.nodes['Background'].inputs[1].default_value=.4

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size in [('Key',(-.8,-1.5,1.6),100,1.1),('Fill',(.9,-1.2,.65),28,1.3),('Rim',(.2,.05,1.3),90,1.0)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;aim(ob,(0,-.65,.43))
camdata=bpy.data.cameras.new('Face review');cam=bpy.data.objects.new('Face review',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=.57
cam.location=(0,-2.4,.435);aim(cam,(0,-.65,.425))
scene.render.engine='CYCLES';scene.render.threads_mode='FIXED';scene.render.threads=6
scene.cycles.samples=args.samples;scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.55
scene.render.resolution_x=args.size;scene.render.resolution_y=int(args.size*1.05);scene.render.resolution_percentage=100
scene['construction']='All new clean facial surfaces; no geometry or textures from the rejected retriever face.'
scene['scope']='Head and collar correction. Likeness still subject to photographic comparison.'
note=bpy.data.texts.new('READ_ME_CLEAN_FACE');note.write('Clean symmetric head and muzzle, sculpted nostrils, recessed eyes, closed tongue.\nNo cut retriever face geometry is retained.\n')
for filename in ['KakaoTalk_20261005_184824793_06.jpg','KakaoTalk_20261005_184824793_01.png']:
    photo=bpy.data.images.load(str(ROOT/'ReferencePhotos'/filename));photo.pack();photo.use_fake_user=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'ogong_{args.tag}_structure.blend'),compress=True)
for view,loc in [('front',(0,-2.4,.435)),('threequarter',(.85,-2.1,.46))]:
    cam.location=loc;aim(cam,(0,-.65,.425));scene.render.filepath=str(OUT/f'{args.tag}_structure_{view}.png')
    print('RENDER',view,flush=True);bpy.ops.render.render(write_still=True)
print('CLEAN_STRUCTURE_SAVED',flush=True)
