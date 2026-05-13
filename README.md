# ganncho_3d

Script paramétrico de Blender que genera una pieza tipo gancho con base y patitas tipo clip en L, lista para imprimir en una **Creality K1C** (boquilla 0.4 mm, PLA).

La pieza completa se construye desde cero con `bpy` (Python API de Blender). Todas las medidas son editables como constantes al inicio de `gancho.py`.

## Geometría

| Pieza | Dimensiones (mm) |
|---|---|
| Placa base (sólida) | 25.15 × 57.74 × 5.0 |
| Poste vertical del gancho | Ø9.39, altura 25.0 |
| Tramo doblado del gancho | largo 9.25, doblez a 45° sobre la horizontal, punta semi-esférica |
| Patitas en L (×2) | parte corta 8.0 × 1.9 × 4 vertical + parte larga 8.0 × 8.0 × 1.9 horizontal |
| Orificios de la pared destino | 10 × 10, separados 28.10 mm entre bordes interiores (las patitas se centran ahí) |

Bounding box final tras orientar para impresión: **45.2 × 57.74 × 25.15 mm**.

## Uso

### Generar el STL (headless)

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python gancho.py \
  -- --export gancho.stl
```

### Visualizar / editar en Blender

Abrir Blender → editor de texto → cargar `gancho.py` → **Run Script**. La pieza aparece ya orientada para impresión, apoyada sobre la cara lateral larga de la placa (5 × 57.74 mm = 289 mm² de contacto con la cama).

## Cómo modificar las dimensiones

Las constantes al inicio de `gancho.py` están agrupadas y comentadas. Las más relevantes:

| Constante | Valor actual | Qué controla |
|---|---|---|
| `PLATE_X`, `PLATE_Y`, `PLATE_Z` | 25.15, 57.74, 5.0 | Dimensiones de la placa base |
| `WALL_HOLE_SIZE`, `WALL_HOLE_GAP` | 10.0, 22.10 | Geometría de los orificios de la pared (lado y separación entre bordes); deriva `PATITA_CENTER_Y` para alinear las patitas |
| `POST_D`, `POST_H` | 9.39, 25.0 | Diámetro y altura del poste |
| `BEND_LEN`, `BEND_ANGLE_FROM_HORIZONTAL_DEG`, `BEND_DIR_Y` | 9.25, 45.0, +1.0 | Geometría del doblez del gancho |
| `FOOT_WIDTH`, `FOOT_LONG_LEN`, `FOOT_SHORT_H` | 8.0, 8.0, 4.0 | Dimensiones de las patitas en L |
| `FOOT_THICK_SHORT`, `FOOT_THICK_LONG` | 1.9, 1.9 | Espesor de las dos partes de la L |

Cambiar cualquier constante y volver a ejecutar el script regenera el STL automáticamente con la geometría nueva.

## Recomendaciones de impresión (Orca / Creality Print, K1C, PLA)

### Quality

- **Layer height**: 0.16 mm (0.12 mm si quieres acabado tipo espejo en las curvas)
- **Seam position**: Random o Rear
- **Ironing type**: Smoothest (cara top más limpia)
- **Arc fitting**: ✓

### Strength

- **Wall loops**: 5
- **Sparse infill density**: 100%
- **Sparse infill pattern**: Concentric (refuerza el cilindro del gancho) o Rectilinear
- **Top shell layers**: 6 / thickness 1.0 mm
- **Bottom shell layers**: 4 / thickness 1.0 mm
- **Alternate extra wall**: ✓
- **Detect thin walls**: ✓

### Soportes

- **Type**: Tree (organic) — mucho más fácil de quitar que Normal
- **On build plate only**: ✓ (evita marcas sobre el cilindro)
- **Threshold angle**: 40°
- **Top Z distance**: 0.25 mm
- **Top interface layers**: 1

## Estructura del repo

```
ganncho_3d/
├── gancho.py          Script de Blender que construye la pieza
├── gancho.stl         STL exportado (regenerable desde gancho.py)
├── LICENSE
├── README.md
└── .gitignore
```
