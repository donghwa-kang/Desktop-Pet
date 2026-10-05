"""Build the first, editable Ogong proportion study in Blender 4.3+.

Run: blender -b --python ArtSource/create_ogong_blockout.py
The face, body, legs, and tail remain separate objects for manual refinement.
"""

from math import atan2, cos, pi, sin
from pathlib import Path
import random

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ArtSource" / "ogong_blockout_v01.blend"
PREVIEWS = ROOT / "Previews"
PHOTOS = ROOT / "ReferencePhotos"
PREVIEWS.mkdir(exist_ok=True)
random.seed(20261005)

bpy.ops.wm.read_factory_settings(use_empty=True)


def collection(name):
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


model = collection("OGONG_MODEL · editable shapes")
fur = collection("OGONG_FUR · preview fibers")
refs = collection("REFERENCES · packed photos")
studio = collection("STUDIO · preview only")


def move_to(obj, target):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    target.objects.link(obj)


def material(name, color, roughness=0.83, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


coat = material("Coat · soft natural white", (0.88, 0.875, 0.83))
coat_highlight = material("Coat · brighter face", (0.94, 0.935, 0.90))
cream = material("Muzzle · warm ivory", (0.92, 0.90, 0.85))
ear_pink = material("Ear interior · muted rose", (0.60, 0.43, 0.43))
eye_socket = material("Eye rim · charcoal", (0.043, 0.038, 0.035), 0.8)
eye = material("Eyes · glossy dark brown", (0.009, 0.006, 0.005), 0.085)
nose = material("Nose · charcoal black", (0.025, 0.022, 0.023), 0.31)
mouth = material("Mouth · shadow", (0.023, 0.012, 0.013), 0.8)
tongue_mat = material("Tongue · pink", (0.70, 0.275, 0.35), 0.5)
fur_mat = material("Fur · white fibers", (0.92, 0.91, 0.87), 0.95)
floor_mat = material("Preview ground", (0.69, 0.70, 0.70), 1)


def ellipsoid(name, location, scale, mat, seg=40, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    move_to(obj, model)
    return obj


# Forward is -Y, height is Z. Dimensions are proportion-study units.
body = ellipsoid("Body · broad coat volume", (0, 0.19, 0.72), (0.49, 0.74, 0.43), coat)
chest = ellipsoid("Chest · deep fluffy bib", (0, -0.38, 0.73), (0.54, 0.43, 0.57), coat_highlight)
neck = ellipsoid("Neck · rounded ruff", (0, -0.49, 0.92), (0.57, 0.40, 0.47), coat)
head = ellipsoid("Head · round silhouette", (0, -0.64, 1.26), (0.46, 0.39, 0.43), coat_highlight)

for side, suffix in ((-1, "L"), (1, "R")):
    # Small ears are mostly concealed by the large head coat.
    ear = ellipsoid(f"Ear {suffix} · mostly buried", (side * 0.345, -0.59, 1.49),
                    (0.115, 0.095, 0.18), coat)
    ear.rotation_euler[1] = side * 0.25
    inner = ellipsoid(f"Ear {suffix} · inner shadow", (side * 0.346, -0.686, 1.49),
                      (0.056, 0.015, 0.095), ear_pink)
    inner.rotation_euler[1] = side * 0.25

    # Strongly foreshortened legs under the coat, with small rounded paws.
    for label, y in (("Front", -0.49), ("Hind", 0.66)):
        x = side * (0.33 if label == "Front" else 0.34)
        ellipsoid(f"{label} leg {suffix}", (x, y, 0.30), (0.15, 0.19, 0.32), coat)
        ellipsoid(f"{label} paw {suffix}", (x, y - 0.085, 0.095),
                  (0.17, 0.215, 0.105), coat_highlight)

    # Eye sockets sit behind glossy eye globes; tiny glints are geometry.
    ellipsoid(f"Eye socket {suffix}", (side * 0.206, -0.968, 1.285),
              (0.122, 0.030, 0.106), eye_socket)
    ellipsoid(f"Eye {suffix}", (side * 0.206, -1.001, 1.287),
              (0.082, 0.060, 0.083), eye, 48, 32)
    ellipsoid(f"Eye glint {suffix}", (side * 0.184, -1.056, 1.319),
              (0.016, 0.010, 0.016), coat_highlight, 24, 16)

# Short muzzle and small nose, with the dark mouth set below rather than
# making an exaggerated cartoon snout.
ellipsoid("Muzzle bridge", (0, -1.014, 1.101), (0.159, 0.162, 0.119), cream)
ellipsoid("Muzzle cheek L", (-0.105, -1.085, 1.066), (0.137, 0.111, 0.100), cream)
ellipsoid("Muzzle cheek R", (0.105, -1.085, 1.066), (0.137, 0.111, 0.100), cream)
ellipsoid("Nose · compact", (0, -1.183, 1.122), (0.085, 0.063, 0.071), nose, 48, 32)
ellipsoid("Nose tip", (0, -1.234, 1.126), (0.047, 0.019, 0.026), nose, 32, 20)
ellipsoid("Mouth opening", (0, -1.116, 0.979), (0.174, 0.052, 0.081), mouth)
ellipsoid("Lower chin", (0, -1.083, 0.913), (0.142, 0.075, 0.047), cream)
ellipsoid("Tongue · happy expression", (0, -1.165, 0.938),
          (0.080, 0.038, 0.089), tongue_mat, 32, 20)

# The plume rises from the rump and folds toward the back, as seen in side photos.
tail_segments = [
    ((0.0, 0.87, 0.92), (0.16, 0.19, 0.17)),
    ((0.0, 1.04, 1.10), (0.20, 0.23, 0.20)),
    ((0.0, 1.03, 1.32), (0.24, 0.22, 0.22)),
    ((0.0, 0.84, 1.42), (0.26, 0.28, 0.18)),
]
tail_objs = [ellipsoid(f"Tail plume {i+1}", center, scale, coat_highlight)
             for i, (center, scale) in enumerate(tail_segments)]


def strand_group(name, center, radii, count, length, spread, skip_face=False):
    """Loose, tapered coat guides for a visual proportion check, not final fur."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = 0.0015
    curve.bevel_resolution = 0
    curve.use_fill_caps = False
    for _ in range(count):
        z = random.uniform(-1, 1)
        a = random.uniform(0, 2*pi)
        r = (max(0, 1-z*z))**0.5
        normal = Vector((r*cos(a), r*sin(a), z))
        if skip_face and normal.y < -0.43 and -0.25 < normal.z < 0.43:
            continue
        root = Vector(center) + Vector((normal.x*radii[0],
                                        normal.y*radii[1], normal.z*radii[2]))
        direction = Vector((normal.x*spread,
                            normal.y*spread + 0.12,
                            normal.z*0.56 - 0.25))
        direction += Vector((random.uniform(-0.18, 0.18),
                             random.uniform(-0.15, 0.15),
                             random.uniform(-0.08, 0.08)))
        direction.normalize()
        size = length * random.uniform(0.62, 1.25)
        spline = curve.splines.new("POLY")
        spline.points.add(2)
        for i, factor in enumerate((0, 0.55, 1)):
            p = root + direction * size * factor
            p.z -= size * 0.09 * factor * factor
            spline.points[i].co = (*p, 1)
            spline.points[i].radius = (1.0, 0.72, 0.05)[i]
    obj = bpy.data.objects.new(name, curve)
    fur.objects.link(obj)
    obj.data.materials.append(fur_mat)
    return obj


strand_group("Body topcoat", (0, 0.19, 0.72), (0.49, 0.74, 0.43), 2100, 0.15, 0.9)
strand_group("Chest ruff", (0, -0.38, 0.73), (0.54, 0.43, 0.57), 1900, 0.19, 1.0)
strand_group("Head halo", (0, -0.64, 1.26), (0.46, 0.39, 0.43), 2600, 0.12, 1.0, True)
for i, (center, scale) in enumerate(tail_segments):
    strand_group(f"Tail fringe {i+1}", center, scale, 350, 0.16, 1.0)


# Reference photos are packed into the scene but kept outside the rendered set.
for i, filename in enumerate((
    "KakaoTalk_20261005_184824793_06.jpg",  # face detail
    "KakaoTalk_20261005_184824793_08.png",  # closed-mouth front
    "KakaoTalk_20261005_184824793_15.jpg",  # left profile
    "KakaoTalk_20261005_193855628.jpg",     # rear / tail
)):
    path = PHOTOS / filename
    if not path.exists():
        continue
    image = bpy.data.images.load(str(path), check_existing=True)
    image.pack()
    obj = bpy.data.objects.new("Reference · " + filename, None)
    refs.objects.link(obj)
    obj.empty_display_type = "IMAGE"
    obj.data = image
    obj.empty_display_size = 1.8
    obj.location = (-3.5 + i * 2.3, 2.3, 1.1)
    obj.hide_render = True


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def area(name, location, energy, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    studio.objects.link(obj)
    obj.location = location
    point_at(obj, (0, 0, 0.8))


area("Softbox front left", (-3, -3, 4.5), 700, 4)
area("Softbox front right", (3, -2, 3.2), 450, 3)
area("Rim light", (0, 3, 3.5), 500, 3)

bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.012))
ground = bpy.context.object
ground.name = "Ground for scale and shadow"
ground.data.materials.append(floor_mat)
move_to(ground, studio)

cameras = {}
for name, position in (
    ("Front", (0, -5.5, 1.55)),
    ("Side", (5.5, 0, 1.56)),
    ("ThreeQuarter", (3.9, -4.6, 2.0)),
):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new("Camera · " + name, data)
    studio.objects.link(obj)
    obj.location = position
    point_at(obj, (0, 0, 0.85))
    data.type = "ORTHO"
    data.ortho_scale = 2.9 if name != "Side" else 3.2
    cameras[name] = obj

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 20
scene.cycles.use_denoising = False
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world = bpy.data.worlds.new("Soft studio ambience")
scene.world.color = (0.65, 0.65, 0.65)
scene.camera = cameras["ThreeQuarter"]

# The source file opens on the character, ready for editing in Blender 5.x.
bpy.ops.object.select_all(action="DESELECT")
head.select_set(True)
bpy.context.view_layer.objects.active = head
for screen in bpy.data.screens:
    for area_obj in screen.areas:
        if area_obj.type == "VIEW_3D":
            area_obj.spaces.active.region_3d.view_distance = 3.5
            area_obj.spaces.active.region_3d.view_location = (0, 0, 0.8)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
for name in ("Front", "Side", "ThreeQuarter"):
    scene.camera = cameras[name]
    scene.render.filepath = str(PREVIEWS / f"ogong_blockout_v01_{name.lower()}.png")
    bpy.ops.render.render(write_still=True)

print("Saved", OUT)
