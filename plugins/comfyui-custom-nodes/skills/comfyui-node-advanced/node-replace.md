# Node replacement & Runtime ComfyAPI

This reference describes how to set up node replacement mappings for migrating old workflows, and how to use the runtime `ComfyAPI` client.

## NodeReplace - Migration Between Nodes

Register node replacements during extension loading (`on_load`) so old workflows auto-migrate to new V3 node definitions when loaded in the frontend:

```python
from typing_extensions import override
from comfy_api.latest import ComfyAPI, ComfyExtension, io

class MyExtension(ComfyExtension):
    @override
    async def on_load(self):
        api = ComfyAPI()
        await api.node_replacement.register(io.NodeReplace(
            new_node_id="MyNewNode_v2",
            old_node_id="MyOldNode",
            old_widget_ids=["width", "height", "mode"],  # positional widget order (very important)
            input_mapping=[
                {"new_id": "image_in", "old_id": "image"},     # map and rename input
                {"new_id": "size", "set_value": 512},           # set new fixed value
            ],
            output_mapping=[
                {"new_idx": 0, "old_idx": 0},       # index-based output mapping
            ],
        ))

    @override
    async def get_node_list(self):
        return [MyNewNodeV2]
```

### Key NodeReplace Properties

* **`old_widget_ids`**: Positional list of widget names in the V1 node. This is required because workflow JSON stores widget values by position indexes rather than widget IDs.
* **`input_mapping`**: List of input mappings to direct old values to the new schema:
  * `InputMapOldId`: `{"new_id": str, "old_id": str}` — maps old input to new
  * `InputMapSetValue`: `{"new_id": str, "set_value": Any}` — sets a fixed value
  * Dot notation maps nested autogrow slots: `{"new_id": "images.image0", "old_id": "image1"}`
* **`output_mapping`**: List of output mappings matching positional indexes:
  * `{"new_idx": int, "old_idx": int}` — maps old output index to new output index

---

## ComfyAPI - Runtime API Client

The `ComfyAPI` class provides runtime interface access (e.g. progress tracking, live status updates) in sync and async contexts:

```python
from comfy_api.latest import ComfyAPI, ComfyAPISync

# In sync execute() methods: use ComfyAPISync (no await)
api = ComfyAPISync()
api.execution.set_progress(value=50, max_value=100)
api.execution.set_progress(
    value=50, max_value=100,
    node_id=None,                   # optional: defaults to current node
    preview_image=pil_image,        # PIL Image or ImageInput tensor
    ignore_size_limit=False,
)

# In async execute() methods: use ComfyAPI (requires await)
api = ComfyAPI()
await api.execution.set_progress(value=50, max_value=100)

# Node replacement registration (in async on_load)
await api.node_replacement.register(io.NodeReplace(...))
```
