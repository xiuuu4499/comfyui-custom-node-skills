---
name: comfyui-node-datatypes
description: comfyui-node-datatypes: input/output data types (IMAGE, LATENT, MASK, model types, widgets). Use when the user wants to work with ComfyUI tensors, model types, or define input/output data types.
---

# ComfyUI Data Types

ComfyUI uses specific data types for node inputs and outputs. Understanding tensor shapes and data formats is essential.

## Complete Type Reference

### Tensor/Data Types

| Type | V3 Class | Format | Description |
|---|---|---|---|
| IMAGE | `io.Image` | `torch.Tensor [B,H,W,C]` float32 0-1 | Batch of RGB images |
| MASK | `io.Mask` | `torch.Tensor [H,W]` or `[B,H,W]` float32 0-1 | Grayscale masks |
| LATENT | `io.Latent` | `{"samples": Tensor[B,C,H,W] or [B,C,T,H,W], "noise_mask"?: Tensor, "batch_index"?: list[int], "type"?: str}` | Latent space (4D image / 5D video) |
| CONDITIONING | `io.Conditioning` | `list[tuple[Tensor, PooledDict]]` | Text conditioning with pooled outputs |
| AUDIO | `io.Audio` | `{"waveform": Tensor[B,C,T], "sample_rate": int}` | Audio data |
| VIDEO | `io.Video` | `VideoInput` ABC | Video data (abstract base class) |
| SIGMAS | `io.Sigmas` | `torch.Tensor` 1D, length steps+1 | Noise schedule |
| NOISE | `io.Noise` | Object with `generate_noise()` | Noise generator |
| LORA_MODEL | `io.LoraModel` | `dict[str, torch.Tensor]` | LoRA weight deltas |
| LOSS_MAP | `io.LossMap` | `{"loss": list[torch.Tensor]}` | Loss map |
| TRACKS | `io.Tracks` | `{"track_path": Tensor, "track_visibility": Tensor}` | Motion tracking data |
| WAN_CAMERA_EMBEDDING | `io.WanCameraEmbedding` | `torch.Tensor` | WAN camera embeddings |
| LATENT_OPERATION | `io.LatentOperation` | `Callable[[Tensor], Tensor]` | Latent transform function |
| TIMESTEPS_RANGE | `io.TimestepsRange` | `tuple[int, int]` | Range 0.0-1.0 |

### Model Types (opaque, typically pass-through)

| Type | V3 Class | Python Type |
|---|---|---|
| MODEL | `io.Model` | `ModelPatcher` |
| CLIP | `io.Clip` | `CLIP` |
| VAE | `io.Vae` | `VAE` |
| CONTROL_NET | `io.ControlNet` | `ControlNet` |
| CLIP_VISION | `io.ClipVision` | `ClipVisionModel` |
| CLIP_VISION_OUTPUT | `io.ClipVisionOutput` | `ClipVisionOutput` |
| STYLE_MODEL | `io.StyleModel` | `StyleModel` |
| GLIGEN | `io.Gligen` | `ModelPatcher` (wrapping Gligen) |
| UPSCALE_MODEL | `io.UpscaleModel` | `ImageModelDescriptor` |
| LATENT_UPSCALE_MODEL | `io.LatentUpscaleModel` | Any |
| SAMPLER | `io.Sampler` | `Sampler` |
| GUIDER | `io.Guider` | `CFGGuider` |
| HOOKS | `io.Hooks` | `HookGroup` |
| HOOK_KEYFRAMES | `io.HookKeyframes` | `HookKeyframeGroup` |
| MODEL_PATCH | `io.ModelPatch` | Any |
| AUDIO_ENCODER | `io.AudioEncoder` | Any |
| AUDIO_ENCODER_OUTPUT | `io.AudioEncoderOutput` | Any |
| PHOTOMAKER | `io.Photomaker` | Any |
| POINT | `io.Point` | Any |
| FACE_ANALYSIS | `io.FaceAnalysis` | Any |
| BBOX | `io.BBOX` | Any |
| SEGS | `io.SEGS` | Any |

### 3D Types

For details on 3D data formats (MESH, VOXEL, File3D, etc.), see [3D Data Types](3d-types.md).

### Widget Types (create UI controls)

For details on interactive input controls (INT, FLOAT, STRING, COLOR, etc.), see [Widget Data Types](widgets.md).

### Special Types

| Type | V3 Class | Description |
|---|---|---|
| `*` (ANY) | `io.AnyType` | Matches any type |
| COMFY_MULTITYPED_V3 | `io.MultiType` | Accept multiple specific types on one input |
| COMFY_MATCHTYPE_V3 | `io.MatchType` | Generic type matching across inputs/outputs |
| COMFY_AUTOGROW_V3 | `io.Autogrow` | Dynamic growing inputs |
| COMFY_DYNAMICCOMBO_V3 | `io.DynamicCombo` | Combo that reveals sub-inputs per option |
| FLOW_CONTROL | `io.FlowControl` | Internal testing only |
| ACCUMULATION | `io.Accumulation` | Internal testing only |

## IMAGE Type

Images are `torch.Tensor` with shape `[B, H, W, C]`:
- **B** = batch size (1 for single image)
- **H** = height in pixels
- **W** = width in pixels
- **C** = channels (3 for RGB, values 0.0-1.0)

```python
import torch
import numpy as np
from PIL import Image as PILImage

class ImageProcessor(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ImageProcessor",
            display_name="Image Processor",
            category="image",
            inputs=[io.Image.Input("image")],
            outputs=[io.Image.Output("IMAGE")],
        )

    @classmethod
    def execute(cls, image):
        b, h, w, c = image.shape
        result = torch.clamp(image * 1.5, 0.0, 1.0)
        return io.NodeOutput(result)
```

### Loading / Saving Images

```python
from PIL import ImageOps

# Load from file → tensor
def load_image(path):
    img = PILImage.open(path)
    img = ImageOps.exif_transpose(img)   # fix rotation from camera EXIF
    if img.mode == "I":                  # handle 16-bit images
        img = img.point(lambda i: i * (1 / 255))
    img = img.convert("RGB")
    return torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)

# Tensor → save to file
def save_image(tensor, path):
    if tensor.dim() == 4:
        tensor = tensor[0]
    PILImage.fromarray(np.clip(255.0 * tensor.cpu().numpy(), 0, 255).astype(np.uint8)).save(path)

# Batch operations
batch = torch.cat([img1, img2], dim=0)    # stack into batch
single = image[i]                          # extract from batch [H,W,C]
single_batch = image.unsqueeze(0)          # add batch dim [1,H,W,C]
```

## MASK Type

`torch.Tensor` with shape `[H, W]` or `[B, H, W]`, values 0.0-1.0.

```python
# Invert mask
inverted = 1.0 - mask

# Mask ↔ Image conversion
alpha = mask.unsqueeze(0).unsqueeze(-1)                   # [1,H,W,1]
gray_mask = 0.299*img[:,:,:,0] + 0.587*img[:,:,:,1] + 0.114*img[:,:,:,2]
image_from_mask = mask.unsqueeze(-1).repeat(1, 1, 1, 3)  # [B,H,W,3]

# Ensure batch dim
if mask.dim() == 2:
    mask = mask.unsqueeze(0)  # [1, H, W]
```

## LATENT Type

Dict with typed keys:

```python
class LatentDict(TypedDict):
    samples: torch.Tensor       # [B, C, H, W] (image) or [B, C, T, H, W] (video) - required
    noise_mask: NotRequired[torch.Tensor]
    batch_index: NotRequired[list[int]]
    type: NotRequired[str]      # only for "audio", "hunyuan3dv2"
```

**Image models** (SD1.5, SDXL, SD3, Flux): 4D `[B, C, H, W]` — SD1.5/SDXL = 4 channels, SD3/Flux = 16 channels. Latent dimensions are 1/8 of pixel dims.

**Video models** (Hunyuan Video, Wan, Cosmos, LTX Video, Mochi): 5D `[B, C, T, H, W]` — T is the temporal (frame) dimension.

```python
samples = latent["samples"]
# Check dimensionality:
if samples.ndim == 5:
    B, C, T, H, W = samples.shape   # video latent
else:
    B, C, H, W = samples.shape      # image latent

# Always preserve extra keys when modifying:
result = latent.copy()
result["samples"] = modified_samples
```

## CONDITIONING Type

`list[tuple[Tensor, PooledDict]]` — a list of (cond_tensor, metadata_dict) pairs.

The `PooledDict` contains many optional keys for different models:

```python
class PooledDict(TypedDict):
    pooled_output: torch.Tensor
    control: NotRequired[ControlNet]
    area: NotRequired[tuple[int, ...]]
    strength: NotRequired[float]           # default 1.0
    mask: NotRequired[torch.Tensor]
    start_percent: NotRequired[float]      # 0.0-1.0
    end_percent: NotRequired[float]        # 0.0-1.0
    guidance: NotRequired[float]           # Flux-like models
    hooks: NotRequired[HookGroup]
    # ... many more model-specific keys (SDXL, SVD, WAN, etc.)
```

Combine conditioning: `result = cond_a + cond_b` (list concatenation).

## VIDEO Type

`VideoInput` is an abstract base class with methods:

```python
class VideoInput(ABC):
    def get_components(self) -> VideoComponents    # images tensor + audio + frame_rate
    def save_to(self, path, format, codec, metadata)
    def as_trimmed(self, start_time, duration) -> VideoInput | None
    def get_stream_source(self) -> str | BytesIO
    def get_dimensions(self) -> tuple[int, int]     # (width, height)
    def get_duration(self) -> float                  # seconds
    def get_frame_count(self) -> int
    def get_frame_rate(self) -> Fraction
    def get_container_format(self) -> str
```

Concrete implementations: `VideoFromFile`, `VideoFromComponents` (available via `from comfy_api.latest import InputImpl`).



## Custom Types

```python
# Simple: create inline custom type
MyData = io.Custom("MY_DATA_TYPE")

# Use in inputs/outputs
io.Schema(
    inputs=[MyData.Input("data")],
    outputs=[MyData.Output("MY_DATA")],
)
```

### Advanced: @comfytype decorator

For custom types with type hints or custom Input/Output classes:

```python
from comfy_api.latest._io import comfytype, ComfyTypeIO

@comfytype(io_type="MY_DATA_TYPE")
class MyData(ComfyTypeIO):
    Type = dict[str, Any]  # type hint for the data
```

## AnyType / Wildcard

```python
# Accept any single type (always a connection input, no widget)
io.AnyType.Input("anything")

# Accept specific multiple types
io.MultiType.Input("data", types=[io.Image, io.Mask, io.Latent])

# MultiType with widget override (shows widget for first type)
io.MultiType.Input(
    io.Float.Input("value", default=1.0),
    types=[io.Float, io.Int],
)
```

## Imports from comfy_api.latest

```python
from comfy_api.latest import (
    ComfyExtension,  # extension registration
    ComfyAPI,        # runtime API (progress, node replacement)
    io,              # all io types (io.Image, io.Schema, io.ComfyNode, etc.)
    ui,              # UI output helpers (ui.PreviewImage, ui.SavedImages, etc.)
    Input,           # Input.Image (ImageInput), Input.Audio, Input.Mask, Input.Latent, Input.Video
    InputImpl,       # InputImpl.VideoFromFile, InputImpl.VideoFromComponents
    Types,           # Types.MESH, Types.VOXEL, Types.File3D, Types.VideoCodec, etc.
)
```

## Tensor Safety

When checking if a tensor exists, always use `is not None` instead of truthiness:

```python
# CORRECT
if image is not None:
    process(image)

# WRONG — multi-element tensors don't support bool()
if image:       # raises RuntimeError
    process(image)

# For boolean conditions on tensors, use .all() or .any()
if (mask > 0.5).all():
    ...
```

## Type Conversion Patterns

```python
# IMAGE [B,H,W,C] → MASK [B,H,W]
mask = 0.299 * image[:,:,:,0] + 0.587 * image[:,:,:,1] + 0.114 * image[:,:,:,2]

# MASK [B,H,W] → IMAGE [B,H,W,C]
image = mask.unsqueeze(-1).repeat(1, 1, 1, 3)

# Resize image tensor
import torch.nn.functional as F
resized = F.interpolate(
    image.permute(0, 3, 1, 2),  # [B,C,H,W] for interpolate
    size=(new_h, new_w), mode='bilinear', align_corners=False
).permute(0, 2, 3, 1)  # back to [B,H,W,C]
```

## See Also

- `comfyui-node-basics` - Node class structure and registration
- `comfyui-node-inputs` - Input configuration details (widget options)
- `comfyui-node-outputs` - Output types and UI outputs
- `comfyui-node-advanced` - MatchType, MultiType, Autogrow, DynamicCombo
