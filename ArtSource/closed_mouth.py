"""Subtle closed lip contact following the evaluated muzzle surface."""
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree
from fullbody_fields import HEAD_SCALE, HEAD_OFFSET, closed_lip_height


def add_closed_lips(body):
    deps=bpy.context.evaluated_depsgraph_get()
    deps.update()
    tree=BVHTree.FromObject(body,deps)
    mat=bpy.data.materials.new('Neutral lip contact')
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(.065,.044,.034,1)
    bsdf.inputs['Roughness'].default_value=.64

    def surface_curve(name,x,z,radii):
        points=[]
        for px,pz in zip(x,z):
            world=np.array([px,0,pz])*HEAD_SCALE+HEAD_OFFSET
            hit,normal,_,_=tree.ray_cast((world[0],-1.2,world[2]),(0,1,0))
            assert hit is not None,(name,px,pz)
            points.append(hit+normal*.00018)
        data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D'
        data.bevel_depth=1.;data.bevel_resolution=3;data.use_fill_caps=True
        spline=data.splines.new('POLY');spline.points.add(len(points)-1)
        for p,co,r in zip(spline.points,points,radii):p.co=(*co,1);p.radius=float(r)
        ob=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(ob)
        data.materials.append(mat)
        ob['purpose']='Closed lip contact detail; not an open cavity or expression rig.'
        return ob

    x=np.linspace(-.038,.038,129)
    taper=np.clip(1-(np.abs(x)/.038)**2,.035,1)
    surface_curve('Ogong_Closed_Lip_Seam',x,closed_lip_height(x),.00055*taper)
    z=np.linspace(float(closed_lip_height(0)),.404,40)
    surface_curve('Ogong_Philtrum',np.zeros(len(z)),z,np.linspace(.00030,.00040,len(z)))
