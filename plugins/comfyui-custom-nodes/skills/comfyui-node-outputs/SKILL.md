---
name: comfyui-node-outputs
description: comfyui-node-outputs: V3 output types (NodeOutput, UI previews, saving media). Use when the user wants to return results from nodes, display previews, or save output files.
---

# ComfyUI Node Outputs

Nodes return data through `io.NodeOutput`. V3 provides built-in UI helpers for previews and file saving.

## Basic Output

```python
class SimpleNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SimpleNode",
            display_name="Simple Node",
            category="example",
            inputs=[io.Float.Input("a"), io.Float.Input("b")],
            outputs=[
                io.Float.Output("SUM"),
                io.Float.Output("PRODUCT"),
            ],
        )

    @classmethod
    def execute(cls, a, b):
        # Values must match output order
        return io.NodeOutput(a + b, a * b)
```

## Output Configuration

```python
io.Schema(
    outputs=[
        io.Image.Output("IMAGE"),                    # basic output
        io.Int.Output("COUNT"),                      # integer output
        io.Float.Output("VALUE", display_name="Result"),  # custom display name
        io.String.Output("TEXT", tooltip="The processed text"),
        io.Image.Output("FRAMES", is_output_list=True),  # outputs a list
    ],
)
```

## NodeOutput Variants

```python
# Data only
return io.NodeOutput(image_tensor, mask_tensor)

# UI only (output node with no data outputs)
return io.NodeOutput(ui=ui.PreviewImage(images, cls=cls))

# Data + UI
return io.NodeOutput(image_tensor, ui=ui.PreviewImage(images, cls=cls))

# No output
return io.NodeOutput()

# Block execution
return io.NodeOutput(block_execution="Reason for blocking")

# Node expansion (positional args are outputs, not result= keyword)
return io.NodeOutput(output_ref, expand=graph.finalize())
```

## UI Preview Helpers

Import `ui` from `comfy_api.latest`:

```python
from comfy_api.latest import io, ui
```

### PreviewImage

Display image previews on the node. Saves to temp directory automatically.

```python
# Constructor: PreviewImage(image, animated=False, cls=None)
class PreviewNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="PreviewNode",
            display_name="Preview Image",
            category="image",
            is_output_node=True,
            inputs=[io.Image.Input("images")],
            outputs=[],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
        )

    @classmethod
    def execute(cls, images):
        return io.NodeOutput(ui=ui.PreviewImage(images, cls=cls))
```

### PreviewMask

```python
# Constructor: PreviewMask(mask, animated=False, cls=None)
# Auto-converts mask to 3-channel grayscale for display
return io.NodeOutput(ui=ui.PreviewMask(masks, cls=cls))
```

### PreviewAudio

```python
# Constructor: PreviewAudio(audio, cls=None)
# Saves as FLAC to temp directory
return io.NodeOutput(ui=ui.PreviewAudio(audio, cls=cls))
```

### PreviewVideo

```python
# Constructor: PreviewVideo(values: list[SavedResult | dict])
return io.NodeOutput(ui=ui.PreviewVideo(saved_video_results))
```

### PreviewText

Display text output:

```python
return io.NodeOutput(ui=ui.PreviewText(value))
```

### PreviewUI3D

Display 3D model preview:

```python
return io.NodeOutput(ui=ui.PreviewUI3D(
    model_file=saved_result,   # SavedResult for the 3D file
    camera_info=camera_dict,   # camera position/target/zoom
    bg_image=image_tensor,     # optional background image (via **kwargs)
))
```

## Saving Images, Audio, and Previews

For details on how to use `ui.ImageSaveHelper`, `ui.AudioSaveHelper`, manual file-saving node structures, and the difference between temporary previews and permanent saves, see [Saving Images, Audio, and Temporary Previews](saving.md).

For legacy V1 output details, see [comfyui-node-migration](../comfyui-node-migration/SKILL.md).

## See Also

- `comfyui-node-basics` - Node structure and Schema
- `comfyui-node-datatypes` - Data type formats
- `comfyui-node-lifecycle` - Execution flow
