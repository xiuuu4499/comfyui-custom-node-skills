# ComfyUI Frontend APIs & Script Imports

Reference for the JavaScript APIs, WebSocket events, dialog boxes, toast notifications, and module imports available to ComfyUI frontend extensions.

## API Events

Listen to execution events on the client side:
```javascript
// Node execution completed
app.api.addEventListener("executed", ({ detail }) => {
    const { node, output } = detail;
    // output contains images, text, etc.
});

// Execution progress
app.api.addEventListener("progress", ({ detail }) => {
    const { value, max, node } = detail;
});

// Execution started/completed
app.api.addEventListener("execution_start", ({ detail }) => {});
app.api.addEventListener("execution_success", ({ detail }) => {});
app.api.addEventListener("execution_error", ({ detail }) => {});

// Status updates
app.api.addEventListener("status", ({ detail }) => {
    const { exec_info } = detail;
});
```

## Server-to-Client Communication

### Python (server side):
```python
from server import PromptServer

PromptServer.instance.send_sync(
    "my_extension.update",
    {"status": "complete", "data": result}
)
```

### JavaScript (client side):
```javascript
app.api.addEventListener("my_extension.update", ({ detail }) => {
    console.log("Received:", detail);
});
```

## Toast Notifications
```javascript
app.extensionManager.toast.add({
    severity: "info",  // "success", "info", "warn", "error"
    summary: "Title",
    detail: "Message content",
    life: 3000,  // auto-dismiss after ms
});
```

## Dialogs
```javascript
// Confirmation dialog
const result = await app.extensionManager.dialog.confirm({
    title: "Confirm Action",
    message: "Are you sure?",
});

// Prompt dialog
const value = await app.extensionManager.dialog.prompt({
    title: "Enter Value",
    message: "Provide a name:",
    defaultValue: "default",
});
```

## ExtensionManager Utilities

### Setting Access
```javascript
// Read a setting value
const val = app.extensionManager.setting.get("my.ext.mySetting");

// Write a setting value
app.extensionManager.setting.set("my.ext.mySetting", newValue);
```

### Execution Errors (read-only)
```javascript
// Last node-level errors (keyed by node ID)
const nodeErrors = app.extensionManager.lastNodeErrors;

// Last execution-level error
const execError = app.extensionManager.lastExecutionError;
```

### Markdown Rendering
```javascript
// Render markdown to sanitized HTML (marked + DOMPurify, safe for innerHTML)
const html = app.extensionManager.renderMarkdownToHtml(markdownStr, baseUrl);
```

## Context Menu Items
```javascript
app.registerExtension({
    name: "my.ext",

    // Canvas right-click menu
    getCanvasMenuItems(canvas) {
        return [{
            content: "My Action",
            callback: () => { console.log("Canvas menu clicked"); },
        }];
    },

    // Node right-click menu
    getNodeMenuItems(node) {
        if (node.comfyClass === "MyNode") {
            return [{
                content: "Custom Action",
                callback: () => { console.log("Node:", node.id); },
            }];
        }
        return [];
    },
});
```

## Node Instance Properties (LGraphNode Augmentations)
```javascript
// Available on node instances:
node.comfyClass       // ComfyUI node type name
node.isVirtualNode    // true for frontend-only nodes
node.imgs             // preview images array
node.imageIndex       // current preview image index

// Callbacks:
node.onExecuted = function(output) { /* execution result */ };
node.onExecutionStart = function() { /* about to execute */ };
node.onDragOver = function(event) { /* file drag over */ };
node.onDragDrop = function(event) { /* file dropped */ };
```

## Frontend Scripts API

Custom node JavaScript can import from the frontend's `src/scripts/` modules. Imports use the Vite shim pattern:
```javascript
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
```
Symbols are also accessible via `window.comfyAPI.<module>.<export>`.

### Stability Levels
| Level | Modules | Notes |
|---|---|---|
| **Stable** | `scripts/app`, `scripts/api` | Guaranteed public API |
| **Internal** (warning) | `scripts/widgets`, `scripts/domWidget`, `scripts/utils`, `scripts/pnginfo`, `scripts/changeTracker`, `scripts/defaultGraph`, `scripts/metadata/*` | Usable but may change |
| **Deprecated** | `scripts/ui` | Will be removed; use Vue alternatives |

### Key Modules
- **`scripts/api`** — `ComfyApi` class: `fetchApi()`, `queuePrompt()`, `getNodeDefs()`, WebSocket events, settings, user data, system stats
- **`scripts/app`** — `ComfyApp` singleton (`app`): graph operations, `registerExtension()`, `extensionManager`, clipboard, coordinate conversion
- **`scripts/widgets`** — `ComfyWidgets` registry (INT, FLOAT, STRING, BOOLEAN, COMBO, IMAGEUPLOAD, etc.), `addValueControlWidgets()`
- **`scripts/domWidget`** — `addDOMWidget()`, `DOMWidgetImpl`, `ComponentWidgetImpl` (Vue component wrapper)
- **`scripts/utils`** — `clone()`, `addStylesheet()`, `uploadFile()`, `downloadBlob()`, storage helpers
- **`scripts/pnginfo`** — `getPngMetadata()`, `getWebpMetadata()`, `importA1111()`, format-specific extractors
