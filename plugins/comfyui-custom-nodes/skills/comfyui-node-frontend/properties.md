# Declarative Extension Properties

This reference details the declarative properties available when registering ComfyUI frontend JavaScript extensions.

## Commands
```javascript
app.registerExtension({
    name: "my.ext",
    commands: [
        {
            id: "my.ext.doSomething",
            label: "Do Something",
            icon: "pi pi-bolt",
            function: () => { console.log("Executed!"); },
        },
    ],
});
```

## Keybindings
```javascript
keybindings: [
    {
        commandId: "my.ext.doSomething",
        combo: { key: "d", ctrl: true, shift: true },
    },
],
```

## Settings
```javascript
settings: [
    {
        id: "my.ext.mySetting",
        name: "My Setting",
        type: "boolean",
        defaultValue: true,
        onChange: (value) => { console.log("Setting changed:", value); },
    },
    {
        id: "my.ext.mode",
        name: "Processing Mode",
        type: "combo",
        options: ["fast", "quality", "balanced"],
        defaultValue: "balanced",
    },
],
```
**Setting types**: `boolean`, `number`, `slider`, `knob`, `combo`, `radio`, `text`, `image`, `color`, `url`, `hidden`, `backgroundImage`

## Sidebar Tabs
```javascript
async setup(app) {
    app.extensionManager.registerSidebarTab({
        id: "my-sidebar",
        title: "My Panel",
        icon: "pi pi-cog",
        type: "custom",
        render: (container) => {
            container.innerHTML = "<h3>My Custom Panel</h3>";
        },
        destroy: () => {
            // Cleanup
        },
    });
},
```

## Bottom Panel Tabs
```javascript
bottomPanelTabs: [
    {
        id: "my-panel",
        title: "My Panel",
        type: "custom",
        render: (container) => {
            container.innerHTML = "<div>Panel content</div>";
        },
    },
],
```

## Menu Commands
```javascript
menuCommands: [
    {
        path: ["My Extension"],
        commands: ["my.ext.doSomething"],
    },
],
```

## About Page Badges
```javascript
aboutPageBadges: [
    { label: "v1.0.0", url: "https://github.com/...", icon: "pi pi-github", severity: "warn" },
    // severity is optional: "danger" | "warn"
],
```

## Top Bar Badges
```javascript
topbarBadges: [
    {
        text: "My Extension",        // required
        label: "BETA",               // optional badge label
        variant: "info",             // "info" | "warning" | "error"
        icon: "pi pi-star",          // optional icon
        tooltip: "Extension info",   // optional tooltip
    },
],
```

## Action Bar Buttons
```javascript
actionBarButtons: [
    {
        icon: "pi pi-bolt",           // required
        label: "My Action",           // optional label
        tooltip: "Run my action",     // optional tooltip
        onClick: () => { /* ... */ },  // required click handler
    },
],
```
