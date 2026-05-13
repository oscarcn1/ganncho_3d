"""Genera un gancho 3D imprimible (Creality K1C) en Blender.

Uso:
    Dentro de Blender: abrir el script en el editor de texto y "Run Script".
    Headless:          blender --background --python gancho.py -- --export gancho.stl

Todas las medidas estan en milimetros. Blender trabaja internamente en metros, por
eso se aplica un factor 0.001 al crear primitivas y un global_scale=1000 al
exportar el STL, para que el slicer lo interprete en mm.
"""

import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


# ---------- Parametros (mm) ----------
PLATE_X = 25.15
PLATE_Y = 57.74
PLATE_Z = 5.0

# Pared de montaje: dos orificios cuadrados de WALL_HOLE_SIZE de lado,
# separados WALL_HOLE_GAP entre sus bordes interiores. La parte horizontal
# de cada patita se centra en su orificio respectivo.
WALL_HOLE_SIZE = 10.0
WALL_HOLE_GAP = 28.10
PATITA_CENTER_Y = (WALL_HOLE_GAP + WALL_HOLE_SIZE) / 2.0  # ±16.05

POST_D = 9.39
POST_H = 25.0                       # tramo vertical
BEND_LEN = 9.25                     # tramo inclinado
BEND_ANGLE_FROM_HORIZONTAL_DEG = 45.0  # 45deg sobre la horizontal => 45deg desde la vertical
BEND_DIR_Y = +1.0                   # +1 dobla hacia +Y, -1 hacia -Y

FOOT_WIDTH = 8.0        # ancho del clip en X
FOOT_LONG_LEN = 8.0     # largo de la parte horizontal de la L (a lo largo de Y)
FOOT_SHORT_H = 4.0      # altura de la parte vertical (corta) de la L, lo que la patita sobresale por debajo de la placa
FOOT_THICK_SHORT = 1.9  # espesor (en Y) de la parte vertical de la L
FOOT_THICK_LONG = 1.9   # espesor (en Z) de la parte horizontal de la L

CYL_VERTS = 96
MM = 0.001  # mm -> m para Blender


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--export", type=str, default=None, help="Ruta de salida para STL")
    return p.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for item in list(block):
            block.remove(item)


def set_mm_units():
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.length_unit = "MILLIMETERS"
    s.unit_settings.scale_length = 1.0


def add_box(name, sx, sy, sz, center):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=Vector(center) * MM)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx * MM, sy * MM, sz * MM)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def add_l_foot(name, corner_y, dir_y, width_x, long_len, short_h, thick_short, thick_long):
    """Patita en forma de L sujeta solo por la parte corta (vertical).

    - Parte corta (vertical): sujeta a la cara inferior de la placa, baja
      `short_h` mm hasta el codo de la L. Tiene espesor `thick_short` en Y.
    - Parte larga (horizontal): nace del codo y se extiende `long_len` mm en
      direccion +Y*dir_y. Tiene espesor `thick_long` en Z.
    - El codo se ubica en Y=corner_y, Z=-short_h. La parte larga se apoya
      con su cara INFERIOR en Z=-short_h, asi el punto mas bajo es -short_h.
    """
    # Parte corta (vertical): cara superior en Z=0 (penetra la placa para unirse).
    short_y_center = corner_y - dir_y * thick_short / 2.0
    short = add_box(
        name + "_short",
        width_x,
        thick_short,
        short_h,
        (0.0, short_y_center, -short_h / 2.0),
    )

    # Parte larga (horizontal): nace del codo y se extiende dir_y*long_len.
    long_y_center = corner_y + dir_y * long_len / 2.0
    long_part = add_box(
        name + "_long",
        width_x,
        long_len,
        thick_long,
        (0.0, long_y_center, -short_h + thick_long / 2.0),
    )

    boolean(short, long_part, "UNION")
    short.name = name
    return short


def build_hook_curve(name, points_mm, radius_mm):
    """Construye el gancho como una curva Bezier con bevel circular.

    points_mm es la lista de vertices (Vector en mm) que forma el trazo.
    Con handles VECTOR cada vertice intermedio produce un codo mitrado limpio,
    asi el resultado es un solido continuo en lugar de dos cilindros pegados.
    """
    curve_data = bpy.data.curves.new(name + "_curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 12
    curve_data.bevel_depth = radius_mm * MM
    curve_data.bevel_resolution = max(8, CYL_VERTS // 8)  # vueltas del perfil
    curve_data.use_fill_caps = True

    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(len(points_mm) - 1)
    for bp, p in zip(spline.bezier_points, points_mm):
        bp.co = p * MM
        bp.handle_left_type = "VECTOR"
        bp.handle_right_type = "VECTOR"

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return obj


def boolean(target, tool, op):
    """Aplica un modificador boolean (DIFFERENCE / UNION) y lo materializa."""
    mod = target.modifiers.new(name=f"bool_{op.lower()}", type="BOOLEAN")
    mod.operation = op
    mod.object = tool
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def cleanup_mesh(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def build():
    # 1) Placa base solida, cara inferior en Z=0
    plate = add_box("plate", PLATE_X, PLATE_Y, PLATE_Z, (0.0, 0.0, PLATE_Z / 2.0))

    # Variante sin patitas: la rama `sin-patitas` omite el bloque de clips L
    # bajo la placa. La pieza se monta sin entrar en orificios de pared.

    # 4) Gancho (poste vertical + tramo doblado) como UNA sola curva Bezier
    # con bevel circular. Asi el gancho sale continuo, sin discos visibles
    # en el codo. El angulo se mide desde la horizontal: 60deg => el tramo
    # se inclina 30deg respecto al eje vertical.
    deflect = math.radians(90.0 - BEND_ANGLE_FROM_HORIZONTAL_DEG)
    axis = Vector((0.0, BEND_DIR_Y * math.sin(deflect), math.cos(deflect)))

    p0 = Vector((0.0, 0.0, PLATE_Z))                       # base, sobre la placa
    p1 = Vector((0.0, 0.0, PLATE_Z + POST_H))              # codo
    p2 = p1 + axis * BEND_LEN                              # punta del gancho

    hook = build_hook_curve("hook", [p0, p1, p2], POST_D / 2.0)
    boolean(plate, hook, "UNION")

    # 6) Semi-esfera en la punta del gancho. La mitad de la esfera queda
    # dentro del cilindro y la otra mitad forma el cap redondeado.
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=(POST_D / 2.0) * MM,
        segments=CYL_VERTS,
        ring_count=max(8, CYL_VERTS // 2),
        location=(p2.x * MM, p2.y * MM, p2.z * MM),
    )
    tip = bpy.context.active_object
    tip.name = "hook_tip"
    boolean(plate, tip, "UNION")

    plate.name = "gancho"
    cleanup_mesh(plate)

    # 7) Reorientar para impresion 3D. La placa tiene features en sus dos
    # caras grandes (gancho arriba, patitas abajo), asi que ninguna cara
    # grande puede tocar la cama sin chocar con algo. La mejor opcion es
    # apoyar la cara lateral LARGA (5 x 57.74 mm ~= 289 mm²) en la cama:
    # rotamos -90deg alrededor de Y. La placa pasa a ser un muro vertical
    # (no requiere puentes), y gancho + patitas quedan como voladizos
    # horizontales para los que el slicer pondra soportes.
    bpy.ops.object.select_all(action="DESELECT")
    plate.select_set(True)
    bpy.context.view_layer.objects.active = plate
    plate.rotation_euler = (0.0, math.radians(-90.0), 0.0)
    bpy.ops.object.transform_apply(rotation=True)

    # Bajar la pieza para que su cara inferior quede en Z=0
    min_z_local = min(v.co.z for v in plate.data.vertices)
    plate.location = (0.0, 0.0, -min_z_local)
    bpy.ops.object.transform_apply(location=True)

    return plate


def export_stl(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    out = str(Path(path).expanduser().resolve())
    # global_scale=1000 hace que el STL salga numerado en mm (Blender exporta
    # las unidades internas; multiplicamos por 1000 para que m -> mm).
    # Blender 4.1+ usa wm.stl_export; versiones anteriores usaban export_mesh.stl.
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(
            filepath=out,
            export_selected_objects=True,
            ascii_format=False,
            global_scale=1000.0,
            apply_modifiers=True,
        )
    else:
        bpy.ops.export_mesh.stl(
            filepath=out,
            use_selection=True,
            ascii=False,
            global_scale=1000.0,
            use_mesh_modifiers=True,
        )
    print(f"[gancho] STL exportado a: {out}")


def main():
    args = parse_args()
    clear_scene()
    set_mm_units()
    obj = build()
    if args.export:
        export_stl(obj, args.export)


if __name__ == "__main__":
    main()
