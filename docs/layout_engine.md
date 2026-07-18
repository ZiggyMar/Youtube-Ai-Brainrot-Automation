# Layout Engine & Custom Frontends

The Video Rendering Framework is fundamentally headless. It knows *what* to render based on the LLM output, but relies on `layout_config.json` to determine *where* and *how* to render the visual elements.

## Understanding `layout_config.json`

The layout configuration schema acts as the visual source of truth for the FFmpeg compositing engine.

```json
{
  "canvas": {
    "width": 1080,
    "height": 1920,
    "fps": 60
  },
  "elements": [
    {
      "id": "character_1",
      "type": "sprite",
      "x": 100,
      "y": 500,
      "scale": 1.2
    },
    {
      "id": "subtitles",
      "type": "text",
      "x": 540,
      "y": 1400,
      "font_size": 48
    }
  ]
}
```

By decoupling the layout from the rendering logic, you eliminate the need to hardcode coordinates in Python scripts.

## Building Custom UI Frontends

You can build your own Web, Desktop, or Mobile frontends to interact with this framework. The visual editor included in `tools/layout_editor.html` is a vanilla JavaScript implementation, but developers can construct complex React or Vue apps.

**Implementation Steps:**
1. Create a drag-and-drop UI to place elements on a 9:16 (1080x1920) canvas.
2. Serialize the X, Y, Scale, and properties of all elements upon save.
3. Export the serialized state into the `layout_config.json` schema.
4. Pass the JSON into the framework execution context. The FFmpeg engine will parse it and render the layers sequentially.
