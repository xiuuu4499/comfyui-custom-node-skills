# 3D Data Types

ComfyUI supports 3D data workflows via specific classes and file-wrapping objects.

## Complete 3D Type Reference

| Type | V3 Class | Python Type | Description |
|---|---|---|---|
| MESH | `io.Mesh` | `MESH(vertices, faces)` | 3D mesh with vertices + faces tensors |
| VOXEL | `io.Voxel` | `VOXEL(data)` | Voxel data tensor |
| FILE_3D | `io.File3DAny` | `File3D` | Any supported 3D format |
| FILE_3D_GLB | `io.File3DGLB` | `File3D` | Binary glTF |
| FILE_3D_GLTF | `io.File3DGLTF` | `File3D` | JSON-based glTF |
| FILE_3D_FBX | `io.File3DFBX` | `File3D` | FBX format |
| FILE_3D_OBJ | `io.File3DOBJ` | `File3D` | OBJ format |
| FILE_3D_STL | `io.File3DSTL` | `File3D` | STL format (3D printing) |
| FILE_3D_USDZ | `io.File3DUSDZ` | `File3D` | Apple AR format |
| SVG | `io.SVG` | `SVG` | Scalable vector graphics |
| LOAD_3D | `io.Load3D` | `{"image": str, "mask": str, "normal": str, "camera_info": CameraInfo}` | 3D model with renders |
| LOAD_3D_ANIMATION | `io.Load3DAnimation` | Same as Load3D | Animated 3D model |
| LOAD3D_CAMERA | `io.Load3DCamera` | `{"position": dict, "target": dict, "zoom": int, "cameraType": str}` | 3D camera info |

---

## File3D Usage

`File3D` wraps a 3D file on disk or in memory (as a `BytesIO` stream):

```python
from comfy_api.latest import Types

# Create File3D instance
file_3d = Types.File3D(source="/path/to/model.glb", file_format="glb")

# Properties and methods
file_3d.format              # "glb"
file_3d.is_disk_backed      # True
file_3d.get_data()          # returns BytesIO
file_3d.get_bytes()         # returns raw bytes
file_3d.save_to("/output/model.glb")
```

---

## MESH and VOXEL Construction

```python
from comfy_api.latest import Types

# Mesh wraps vertices and faces tensors
mesh = Types.MESH(vertices=torch.tensor(...), faces=torch.tensor(...))

# Voxel wraps raw voxel data tensor
voxel = Types.VOXEL(data=torch.tensor(...))
```
