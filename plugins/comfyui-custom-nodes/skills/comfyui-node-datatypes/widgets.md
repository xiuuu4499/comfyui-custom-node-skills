# Widget Data Types

ComfyUI provides a set of widget inputs that create interactive UI controls on the nodes in the frontend canvas.

## Widget Types Reference

| Type | V3 Class | Python Type | Description |
|---|---|---|---|
| INT | `io.Int` | `int` | Integer with min/max/step |
| FLOAT | `io.Float` | `float` | Float with min/max/step/round |
| STRING | `io.String` | `str` | Text (single/multi-line) |
| BOOLEAN | `io.Boolean` | `bool` | Toggle with labels |
| COMBO | `io.Combo` | `str` | Dropdown selection |
| COMBO (multi) | `io.MultiCombo` | `list[str]` | Multi-select dropdown |
| COLOR | `io.Color` | `str` (hex) | Color picker, default `#ffffff` |
| BOUNDING_BOX | `io.BoundingBox` | `{"x": int, "y": int, "width": int, "height": int}` | Rectangle region |
| CURVE | `io.Curve` | `list[tuple[float, float]]` | Spline curve points |
| IMAGECOMPARE | `io.ImageCompare` | `dict` | Image comparison widget |
| WEBCAM | `io.Webcam` | `str` | Webcam capture widget |
| HISTOGRAM | `io.Histogram` | `list[int]` | Histogram bin counts |

---

## Widget Details & Options

### Color Picker
```python
io.Color.Input("color", default="#ff0000", socketless=True)
# Value is a hex string like "#ff0000"
```

### BoundingBox (Rectangle Selector)
```python
io.BoundingBox.Input("bbox",
    default={"x": 0, "y": 0, "width": 512, "height": 512},
    socketless=True,
    component="my_component",  # optional custom UI component
)
# Value is {"x": int, "y": int, "width": int, "height": int}
```

### Curve (Spline Editor)
```python
io.Curve.Input("curve",
    default=[(0.0, 0.0), (1.0, 1.0)],  # linear
    socketless=True,
)
# Value is list of (x, y) tuples
```

### MultiCombo (Multi-select Dropdown)
```python
io.MultiCombo.Input("tags",
    options=["tag1", "tag2", "tag3"],
    default=["tag1"],
    placeholder="Select tags...",
    chip=True,  # show as chips
)
# Value is list[str]
```

### Webcam (Camera Capture)
```python
io.Webcam.Input("webcam_capture")
# Value is str (captured image data)
```

### ImageCompare (Comparison Slider)
```python
io.ImageCompare.Input("comparison", socketless=True)
# Value is dict
```
