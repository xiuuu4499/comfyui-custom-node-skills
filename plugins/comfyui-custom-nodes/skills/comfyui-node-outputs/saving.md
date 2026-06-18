# Saving Images, Audio, and Temporary Previews

This guide details how ComfyUI V3 nodes save output files permanently and generate temporary previews.

## Saving Images

### Using ImageSaveHelper
The `ui.ImageSaveHelper` class provides static methods for saving images in various formats (PNG, animated PNG, WebP) and returning the corresponding UI configurations:

```python
from comfy_api.latest import io, ui

# Save as PNG (returns list[SavedResult])
results = ui.ImageSaveHelper.save_images(
    images,                              # tensor [B,H,W,C]
    filename_prefix="ComfyUI",
    folder_type=io.FolderType.output,    # output, temp, or input
    cls=cls,                             # node class (for metadata)
    compress_level=4,
)

# Save and get UI object directly (saves to output folder)
saved_ui = ui.ImageSaveHelper.get_save_images_ui(images, "ComfyUI", cls=cls)
return io.NodeOutput(ui=saved_ui)

# Save animated WebP and get UI
saved_ui = ui.ImageSaveHelper.get_save_animated_webp_ui(
    images, "anim", cls=cls, fps=12.0, lossless=False, quality=80, method=4
)
```

### Simple Save Image Node Example
```python
class SaveImageNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SaveImageNode",
            display_name="Save Image",
            category="image",
            is_output_node=True,
            inputs=[
                io.Image.Input("images"),
                io.String.Input("filename_prefix", default="ComfyUI"),
            ],
            outputs=[],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
        )

    @classmethod
    def execute(cls, images, filename_prefix):
        saved = ui.ImageSaveHelper.get_save_images_ui(images, filename_prefix, cls=cls)
        return io.NodeOutput(ui=saved)
```

### Manual Image Saving (with Metadata)
To customize filenames or write workflow metadata directly into PNG headers:

```python
import os
import json
import numpy as np
from PIL import Image as PILImage
from PIL.PngImagePlugin import PngInfo
import folder_paths

class CustomSaveNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="CustomSaveNode",
            display_name="Custom Save",
            category="image",
            is_output_node=True,
            inputs=[
                io.Image.Input("images"),
                io.String.Input("prefix", default="output"),
            ],
            outputs=[],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
        )

    @classmethod
    def execute(cls, images, prefix):
        output_dir = folder_paths.get_output_directory()
        results = []

        for i, image in enumerate(images):
            # Convert tensor to PIL Image
            img_array = np.clip(255.0 * image.cpu().numpy(), 0, 255).astype(np.uint8)
            pil_image = PILImage.fromarray(img_array)

            # Write prompt/workflow data into EXIF PNG metadata
            metadata = PngInfo()
            if cls.hidden.prompt:
                metadata.add_text("prompt", json.dumps(cls.hidden.prompt))
            if cls.hidden.extra_pnginfo:
                for k, v in cls.hidden.extra_pnginfo.items():
                    metadata.add_text(k, json.dumps(v))

            # Save to output folder
            filename = f"{prefix}_{i:05d}.png"
            filepath = os.path.join(output_dir, filename)
            pil_image.save(filepath, pnginfo=metadata)

            results.append(ui.SavedResult(
                filename=filename,
                subfolder="",
                type=io.FolderType.output,
            ))

        return io.NodeOutput(ui=ui.SavedImages(results))
```

---

## Saving Audio

The `ui.AudioSaveHelper` supports saving audio waveforms to output files:

```python
from comfy_api.latest import io, ui

# Save and get UI configuration (supports flac, mp3, opus)
saved_ui = ui.AudioSaveHelper.get_save_audio_ui(
    audio,                           # {"waveform": Tensor, "sample_rate": int}
    filename_prefix="audio",
    cls=cls,
    format="flac",
    quality="128k",                  # MP3: "V0","128k","320k"; Opus: "64k"-"320k"
)
return io.NodeOutput(ui=saved_ui)
```

---

## Temporary Previews vs Permanent Saves

* **Previews** (using `ui.PreviewImage`, `ui.PreviewMask`, `ui.PreviewAudio`) write to the `temp` folder. These files are ephemeral and cleaned up regularly.
* **Saves** (using `ui.ImageSaveHelper` or manual saving to `folder_paths.get_output_directory()`) write to the `output` directory and are persistent.
