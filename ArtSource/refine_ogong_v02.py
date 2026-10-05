"""Smooth the first blockout into a more useful sculpting base.

Run after create_ogong_blockout.py. This preserves v01 and writes v02.
"""

from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ArtSource" / "ogong_blockout_v01.blend"
DEST = ROOT / "ArtSource" / "ogong_blockout_v02.blend"
PREVIEWS = ROOT / "Previews"
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))


def merged_voxel(name, objects, size):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    active = objects[0]
    bpy.context.view_layer.objects.active = active
    bpy.ops.object.join()
    active.name = name
    active.data.remesh_voxel_size = size
    bpy.ops.object.voxel_remesh()
    smooth = active.modifiers.new("Soften voxel facets", "SMOOTH")
    smooth.factor = 1.25
    smooth.iterations = 4
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    for polygon in active.data.polygons:
        polygon.use_smooth = True
    return active


body_names = (
    "Head · round silhouette",
    "Neck · rounded ruff",
    "Chest · deep fluffy bib",
    "Body · broad coat volume",
)
body = merged_voxel("Body and head · sculpt base", [bpy.data.objects[n] for n in body_names], 0.025)
tail = merged_voxel("Tail plume · sculpt base", [bpy.data.objects[f"Tail plume {i}"] for i in range(1, 5)], 0.025)

for suffix in ("L", "R"):
    eye = bpy.data.objects[f"Eye {suffix}"]
    eye.location.y += 0.015
    eye.scale = (0.94, 0.9, 0.94)
    socket = bpy.data.objects[f"Eye socket {suffix}"]
    socket.location.y += 0.010
    socket.scale = (0.93, 0.75, 0.93)
    outer_ear = bpy.data.objects[f"Ear {suffix} · mostly buried"]
    inner_ear = bpy.data.objects[f"Ear {suffix} · inner shadow"]
    outer_ear.location.y += 0.035
    inner_ear.location.y += 0.035
    for part in ("Front", "Hind"):
        paw = bpy.data.objects[f"{part} paw {suffix}"]
        paw.scale.z = 0.7
        paw.location.z -= 0.025

bpy.data.materials["Nose · charcoal black"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.48

scene = bpy.context.scene
scene.camera = bpy.data.objects["Camera · ThreeQuarter"]
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.wm.save_as_mainfile(filepath=str(DEST))

for view in ("Front", "Side", "ThreeQuarter", "Face"):
    scene.camera = bpy.data.objects["Camera · " + view]
    scene.render.filepath = str(PREVIEWS / f"ogong_blockout_v02_{view.lower()}.png")
    bpy.ops.render.render(write_still=True)

print("Saved", DEST)
