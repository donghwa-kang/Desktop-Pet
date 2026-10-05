"""Rebuild the reference bust into Pomeranian facial proportions.

Uses the supplied mesh only for the detailed nose/muzzle/mouth/tongue region.
Builds a new continuous lofted cranium/collar, upright ears and dark eyes.
The source GLB and previous studies remain unchanged.
Run with Blender 5.2.2's official bpy module.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'ArtSource/FaceRebuild'
OUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('--groom', action='store_true')
parser.add_argument('--samples', type=int, default=32)
parser.add_argument('--size', type=int, default=640)
parser.add_argument('--tag', default='v10')
args = parser.parse_args()
rng = np.random.default_rng(1006)
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ArtSource/FurStudy/ogong_fur_study_v03.blend'))
scene = bpy.context.scene
for obj in list(scene.objects):
    if obj.type == 'CURVES': bpy.data.objects.remove(obj, do_unlink=True)
source = next(o for o in scene.objects if o.type == 'MESH')
old = source.data
v = np.empty(len(old.vertices)*3,dtype=np.float32);old.vertices.foreach_get('co',v);v=v.reshape(-1,3)
f = np.empty(len(old.loops),dtype=np.int32);old.loops.foreach_get('vertex_index',f);f=f.reshape(-1,3)
uv = np.empty(len(old.loops)*2,dtype=np.float32);old.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,3,2)
centers = v[f].mean(axis=1)
keep = (centers[:,1]<-.71)&((centers[:,2]>.25)|(centers[:,1]<-.85))&(centers[:,2]<.418)&(np.abs(centers[:,0])<.107)
face_ids, inverse = np.unique(f[keep].reshape(-1),return_inverse=True)
original = v[face_ids].copy()
face_vertices = original.copy()
# Compress the projected muzzle and lower face; preserve nose/mouth detail.
face_vertices[:,1] = np.where(original[:,1]<-.74,-.74+(original[:,1]+.74)*.43,original[:,1])
face_vertices[:,1] -= .024
face_vertices[:,2] = .452+(original[:,2]-.452)*.52
nose = np.clip((-original[:,1]-.84)/.06,0,1)*np.clip((original[:,2]-.33)/.045,0,1)
face_vertices[:,0] *= 1.28-.22*nose
nose_z=.418+(original[:,2]-.386)*1.05
face_vertices[:,2] = face_vertices[:,2]*(1-nose)+nose_z*nose
face_vertices[:,0] *= 1-.23*nose
face_vertices[:,2] = face_vertices[:,2]*(1-.17*nose)+.418*(.17*nose)
tongue = np.clip((-original[:,1]-.84)/.04,0,1)*np.clip((.32-original[:,2])/.10,0,1)
face_vertices[:,2] -= .036*tongue
face_vertices[:,0] *= 1-.18*tongue


def mesh_object(name, vertices, faces, material=None, uv_values=None):
    data=bpy.data.meshes.new(name)
    data.from_pydata(np.asarray(vertices).tolist(),[],np.asarray(faces).tolist())
    data.update()
    data.polygons.foreach_set('use_smooth',np.ones(len(data.polygons),dtype=bool))
    if uv_values is not None:
        data.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(uv_values,dtype=np.float32).reshape(-1))
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
    if material:data.materials.append(material)
    return ob


def principled(name, color, roughness=.5):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=roughness
    return m


skin=principled('Ogong_White_Skin_Under_Coat',(.64,.63,.60),.7)
black=principled('Ogong_Dark_Eyelid',(.006,.004,.004),.62)
black.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.1
eye_mat=principled('Ogong_Dark_Brown_Eye',(.0035,.0025,.003),.10)
eye_bs=eye_mat.node_tree.nodes['Principled BSDF']
eye_bs.inputs['IOR'].default_value=1.38
eye_bs.inputs['Specular IOR Level'].default_value=.42
# An actual dark pupil and brown iris under the wet reflection, rather than
# a uniformly black button. Generated coordinates are local to each globe.
en,el=eye_mat.node_tree.nodes,eye_mat.node_tree.links
coord=en.new('ShaderNodeTexCoord');sep=en.new('ShaderNodeSeparateXYZ');el.new(coord.outputs['Generated'],sep.inputs[0])
rad=en.new('ShaderNodeCombineXYZ')
for source_axis,target_axis in [('X','X'),('Z','Y')]:
    sub=en.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=.5
    el.new(sep.outputs[source_axis],sub.inputs[0]);el.new(sub.outputs[0],rad.inputs[target_axis])
dist=en.new('ShaderNodeVectorMath');dist.operation='LENGTH';el.new(rad.outputs[0],dist.inputs[0])
iris=en.new('ShaderNodeValToRGB')
stops=[(0,(.0007,.0005,.0004,1)),(.215,(.0007,.0005,.0004,1)),(.255,(.006,.0025,.001,1)),(.425,(.004,.0018,.0008,1)),(.475,(.001,.0008,.0007,1)),(1,(.001,.0008,.0007,1))]
cr=iris.color_ramp
cr.elements.remove(cr.elements[1])
cr.elements[0].position=stops[0][0];cr.elements[0].color=stops[0][1]
for pos,color in stops[1:]:cr.elements.new(pos).color=color
el.new(dist.outputs['Value'],iris.inputs[0]);el.new(iris.outputs['Color'],eye_bs.inputs['Base Color'])
pink=principled('Ogong_Inner_Ear',(.42,.23,.22),.65)
mat=source.data.materials[0].copy();mat.name='Ogong_Remapped_Nose_Mouth_Material'
face=mesh_object('Ogong_Short_Muzzle_Nose_Mouth',face_vertices,inverse.reshape(-1,3),mat,uv[keep])
face['construction']='Detailed reference face compressed in depth and vertical length; nose/mouth texture retained.'
mouth_preserve=np.clip((-original[:,1]-.77)/.045,0,1)*np.clip((.345-original[:,2])/.03,0,1)
nose_preserve=np.clip((-original[:,1]-.885)/.02,0,1)*np.clip((original[:,2]-.337)/.021,0,1)
mouth_preserve=np.maximum(mouth_preserve,nose_preserve)
face.data.attributes.new('preserve_mouth','FLOAT','POINT').data.foreach_set('value',mouth_preserve.astype(np.float32))
# The source has a pale brown nose; give its existing detailed surface the
# charcoal pigment seen in Ogong's photos, while retaining texture variation.
face.data.attributes.new('nose_pigment','FLOAT','POINT').data.foreach_set('value',nose_preserve.astype(np.float32))
nodes,links=mat.node_tree.nodes,mat.node_tree.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
old_color=bs.inputs['Base Color'].links[0].from_socket
source_color=next(n for n in nodes if n.type=='MIX_RGB').inputs[1].links[0].from_socket
pigment=nodes.new('ShaderNodeAttribute');pigment.attribute_name='nose_pigment'
dark=nodes.new('ShaderNodeMixRGB');dark.blend_type='MULTIPLY';dark.inputs[0].default_value=1
links.new(source_color,dark.inputs[1]);dark.inputs[2].default_value=(.055,.065,.078,1)
colored=nodes.new('ShaderNodeMixRGB');links.new(pigment.outputs['Fac'],colored.inputs[0])
links.new(old_color,colored.inputs[1]);links.new(dark.outputs[0],colored.inputs[2]);links.new(colored.outputs[0],bs.inputs['Base Color'])
bpy.data.objects.remove(source,do_unlink=True)

# Quad loft combines the collar, jaw and rounded cranium in one surface.
# Columns: z, lateral radius, depth radius, center-y.
sections=np.array([
    [.005,.150,.090,-.565], [.055,.218,.125,-.590],
    [.140,.225,.145,-.610], [.230,.208,.142,-.627],
    [.295,.177,.123,-.650], [.335,.166,.113,-.660],
    [.375,.170,.123,-.661], [.420,.171,.134,-.659],
    [.465,.171,.128,-.653], [.505,.162,.121,-.643],
    [.550,.134,.108,-.631], [.588,.083,.075,-.619],
    [.610,.009,.012,-.614],
])
zs=np.linspace(sections[0,0],sections[-1,0],100)
nr=192
ang=np.linspace(0,2*np.pi,nr,endpoint=False)
loft=[]
def smooth_interp(z,col):
    x=sections[:,0];y=sections[:,col]
    slopes=np.diff(y)/np.diff(x)
    m=np.zeros_like(y);m[0]=slopes[0];m[-1]=slopes[-1]
    for i in range(1,len(y)-1):
        if slopes[i-1]*slopes[i]>0:m[i]=2*slopes[i-1]*slopes[i]/(slopes[i-1]+slopes[i])
    i=min(max(np.searchsorted(x,z)-1,0),len(x)-2);h=x[i+1]-x[i];t=(z-x[i])/h
    return (2*t**3-3*t*t+1)*y[i]+(t**3-2*t*t+t)*h*m[i]+(-2*t**3+3*t*t)*y[i+1]+(t**3-t*t)*h*m[i+1]

def smoothstep(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)

def front_surface(x,z):
    rx,ry,cy=[smooth_interp(z,col) for col in (1,2,3)]
    y=cy-ry*np.sqrt(max(0,1-(x/rx)**2))
    return y-.027*np.exp(-((abs(x)-.044)/.036)**2-((z-.408)/.031)**2)

# Feather the perimeter of the retained detail into the new cranial surface.
# The central nose, lips and tongue remain in their independently shaped pose.
edge_top=smoothstep(.395,.418,original[:,2])*(1-nose_preserve)
edge_side=smoothstep(.078,.107,np.abs(original[:,0]))
edge_low=(1-smoothstep(.25,.282,original[:,2]))
edge=np.maximum(np.maximum(edge_top,edge_side),edge_low)
mouth_detail=(original[:,1]<-.835)&(original[:,2]<.345)
edge[mouth_detail]=0
for i in np.flatnonzero(edge>.001):
    x,y,z=face_vertices[i]
    skin_y=front_surface(x,z)-.0008
    face_vertices[i,1]=(1-edge[i])*y+edge[i]*skin_y
face.data.vertices.foreach_set('co',face_vertices.astype(np.float32).reshape(-1))
face.data.update()
for z in zs:
    rx,ry,cy=[smooth_interp(z,col) for col in (1,2,3)]
    # Superellipse-inspired cheek breadth without primitive sphere intersections.
    for a in ang:
        x=rx*np.cos(a);y=cy+ry*np.sin(a)
        y-=.027*np.exp(-((abs(x)-.044)/.036)**2-((z-.408)/.031)**2)*(1-smoothstep(-.74,-.68,y))
        loft.append((x,y,z))
loft=np.asarray(loft)
quads=[]
eye_positions=[(-.075,-.755,.455),(.075,-.755,.455)]
for j in range(len(zs)-1):
    for k in range(nr):
        ids=[j*nr+k,j*nr+(k+1)%nr,(j+1)*nr+(k+1)%nr,(j+1)*nr+k]
        c=loft[ids].mean(0)
        # Opening behind the detailed muzzle and mouth. Eye holes receive globes/lids.
        mouth_open=(c[1]<-.708 and ((c[0]/.056)**2+((c[2]-.375)/.031)**2)<1)
        eyes_open=any(c[1]<-.71 and (((c[0]-ex)/.0235)**2+((c[2]-ez)/.0245)**2)<1 for ex,ey,ez in eye_positions)
        if not mouth_open and not eyes_open: quads.append(ids)
body=mesh_object('Ogong_Rounded_Head_And_Collar',loft,quads,skin)
luv=[]
for quad in quads:
    row=[(i%nr/nr,i//nr/(len(zs)-1)) for i in quad]
    if max(u for u,t in row)-min(u for u,t in row)>.5:row=[(1.0 if u<.1 else u,t) for u,t in row]
    luv.extend(row)
body.data.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(luv,dtype=np.float32).reshape(-1))
body['construction']='Continuous quad loft shaped for a rounded Pomeranian head and compact collar; mouth/eye openings.'
sub=body.modifiers.new('Smooth cranial surface','SUBSURF');sub.levels=2;sub.render_levels=2


def tube(name,coords,radius,material):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=2
    cu.bevel_depth=radius;cu.bevel_resolution=3
    s=cu.splines.new('POLY');s.points.add(len(coords)-1)
    s.points.foreach_set('co',np.column_stack([coords,np.ones(len(coords))]).reshape(-1))
    s.use_cyclic_u=True
    ob=bpy.data.objects.new(name,cu);scene.collection.objects.link(ob);cu.materials.append(material)
    return ob


for side,(ex,ey,ez) in zip(['L','R'],eye_positions):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=.027,location=(ex,ey,ez))
    eye=bpy.context.object;eye.name=f'Ogong_Eye_{side}';eye.data.materials.append(eye_mat)
    for p in eye.data.polygons:p.use_smooth=True
    theta=np.linspace(0,2*np.pi,128,endpoint=False)
    x=.0215*np.cos(theta);z=.022*np.sin(theta)
    y=-np.sqrt(np.maximum(.027**2-x*x-z*z,0))-.001
    tube(f'Ogong_Eyelid_Rim_{side}',np.column_stack([x+ex,y+ey,z+ez]),.00125,black)
    # Smooth skin annulus covers the grid opening and gives each eye real lids.
    # Its inner edge follows the globe; the outer edge joins the cranial surface.
    lv=[];lf=[];lu=[];sectors=96;rings=14
    for j in range(rings):
        t=j/(rings-1);s=t*t*(3-2*t)
        for k in range(sectors):
            a=2*np.pi*k/sectors
            ix=.0215*np.cos(a);iz=.022*np.sin(a)
            xx=(.0215+(.041-.0215)*t)*np.cos(a)
            zz=(.022+(.038-.022)*t)*np.sin(a)
            yi=ey-np.sqrt(max(0,.027**2-ix*ix-iz*iz))-.0006
            yo=front_surface(ex+xx,ez+zz)-.001
            lv.append((ex+xx,yi*(1-s)+yo*s,ez+zz))
    for j in range(rings-1):
        for k in range(sectors):
            quad=[j*sectors+k,(j+1)*sectors+k,(j+1)*sectors+(k+1)%sectors,j*sectors+(k+1)%sectors]
            lf.append(quad)
            lu.extend([(i%sectors/sectors,i//sectors/(rings-1)) for i in quad])
    lid=mesh_object(f'Ogong_Eyelid_Skin_{side}',lv,lf,skin,lu)

# Remove the long hanging ears entirely: new small upright tapered ear shells.
ears=[]
for sign,label in [(-1,'L'),(1,'R')]:
    ev=[];ef=[];mi=[];na=64;nt=24
    for j in range(nt):
        t=j/(nt-1)
        width=.041*(1-t)**.82+.001
        depth=.011*(1-t)+.001
        cx=sign*(.113+.024*t);cz=.505+.123*t
        for k in range(na):
            a=2*np.pi*k/na
            ev.append((cx+width*np.cos(a),-.621+depth*np.sin(a),cz))
    for j in range(nt-1):
        for k in range(na):
            ef.append([j*na+k,j*na+(k+1)%na,(j+1)*na+(k+1)%na,(j+1)*na+k])
            mi.append(1 if np.sin(2*np.pi*(k+.5)/na)<-.65 and .15<j/(nt-1)<.82 else 0)
    ob=mesh_object(f'Ogong_Upright_Ear_{label}',ev,ef,skin)
    ear_uv=[(i%na/na,i//na/(nt-1)) for q in ef for i in q]
    ob.data.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(ear_uv,dtype=np.float32).reshape(-1))
    ob.data.materials.append(pink)
    ob.data.polygons.foreach_set('material_index',np.asarray(mi,dtype=np.int32))
    sub=ob.modifiers.new('Soft ear edges','SUBSURF');sub.levels=1;sub.render_levels=1
    ears.append(ob)

# The old source text must not describe the current mesh as an unchanged retriever.
text=bpy.data.texts.get('READ_ME_FUR_STUDY')
if text:bpy.data.texts.remove(text)
note=bpy.data.texts.new('READ_ME_POMERANIAN_FACE')
note.write('Pomeranian face reconstruction in Blender 5.2.2.\n'
           'New rounded cranium/collar, small upright ears, dark eyes and eyelids.\n'
           'Original detailed muzzle/nose/mouth/tongue geometry shortened and repositioned.\n'
           'Photo-based proportions remain an artistic approximation; no animation rig yet.\n')

scene.render.engine='CYCLES';scene.render.threads_mode='FIXED';scene.render.threads=6
scene.cycles.samples=args.samples;scene.cycles.use_denoising=True
scene.cycles.denoiser='OPENIMAGEDENOISE';scene.cycles.denoising_input_passes='RGB_ALBEDO_NORMAL'
scene.cycles.adaptive_threshold=.015
scene.view_settings.exposure=-.6
# Broad lighting for the white coat, with a smaller rectangular eye catchlight.
key=bpy.data.lights.get('Soft Key')
if key:key.shape='RECTANGLE';key.size=.9;key.size_y=1.2;key.energy=110
fill=bpy.data.lights.get('Soft Fill')
if fill:fill.energy=40;fill.size=1.4
scene.render.resolution_x=args.size;scene.render.resolution_y=int(args.size*1.05)
scene.render.resolution_percentage=100
scene['study_status']='Pomeranian facial reconstruction: rounded cranium, shortened muzzle, upright ears, dark eyes.'
scene['render_revision']=args.tag
cam=scene.camera;target=Vector((0,-.65,.335));cam.location=(0,-2.5,.375)
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.77

# Groom is built in a separate script, so anatomy can be inspected first.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'ogong_face_{args.tag}_structure.blend'),compress=True)
scene.render.filepath=str(OUT/f'{args.tag}_structure_front.png')
print('RENDER_STRUCTURE_FRONT',flush=True);bpy.ops.render.render(write_still=True)
cam.location=(.85,-2.15,.46);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/f'{args.tag}_structure_threequarter.png')
print('RENDER_STRUCTURE_ANGLE',flush=True);bpy.ops.render.render(write_still=True)
print('FACE_STRUCTURE_COMPLETE',flush=True)
