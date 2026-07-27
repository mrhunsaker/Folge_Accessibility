# Step 1: Export from Folge

**What it does:** Extracts your guide content and screenshots from [Folge](https://folge.me).

**Why it matters:** This is your source of truth. All subsequent processing depends on this export.

## How to Export

1. Open your guide in Folge
2. Click **Export** > **JSON**
3. Save the file as `guide.json` in the project root
4. Export all screenshots
5. Save all images to the `images/` directory (Folge uses names like `step-0.png`, `step-1.png`, etc.)

## Output

| File | Location |
|------|----------|
| `guide.json` | Project root |
| `step-*.png` screenshots | `images/` directory |

## Guide JSON Structure

The exported `guide.json` from Folge has this structure:

### Top Level

| Field | Type | Description |
|-------|------|-------------|
| `guide` | object | Guide metadata |
| `guide.id` | string | Unique identifier for the guide (Folge UUID) |
| `guide.title` | string | Guide title |
| `guide.description` | string | Optional description (may be empty) |
| `steps` | array | Array of step objects |

### Step Objects

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the step (Folge UUID) |
| `index` | integer | Step position in the guide |
| `parentId` | string or null | Parent step ID (for nested steps) |
| `title` | string | Step heading |
| `description` | string | Instructional text (HTML) |
| `screenshotFilename` | string | Image filename (e.g., `step-0.png`) |
| `screenshotRelativePath` | string | Full relative path (e.g., `images/step-0.png`) |
| `indexString` | string | Display index (e.g., `1.`) |
| `textblocks` | array | Additional text blocks |
| `includeInToc` | boolean | Whether to include in table of contents |
| `settings` | object | Step display settings |
| `nested` | integer | Nesting depth (0 = top level) |

### Step Settings

| Field | Type | Description |
|-------|------|-------------|
| `forceToANewPage` | boolean | Force page break before this step |
| `multiImageStep` | boolean | Step contains multiple images |
| `focusedView` | boolean | Use focused/cropped view |
| `contentBlock` | boolean | Display as content block |
| `focusedViewSettings` | object | Crop coordinates and scale |
| `substepBlocksSettings` | array | Which blocks to show (title, image, description) |

### Example: Minimal Step

```json
{
  "id": "QatJX1vxONIm_nySDUIyv",
  "index": 1,
  "parentId": null,
  "title": "Open Settings",
  "description": "<p>Click the Settings button in the sidebar.</p>",
  "screenshotFilename": "step-0.png",
  "indexString": "1.",
  "nested": 0,
  "screenshotRelativePath": "images/step-0.png"
}
```

## How the Pipeline Uses This

The merge step transforms the Folge format into the enriched format:

- `guide.id` becomes `guide_id` in the enriched output
- `guide.title` becomes `title`
- `steps[].id` becomes `steps[].step_id`
- `steps[].description` becomes `steps[].body`
- `steps[].screenshotFilename` becomes `steps[].image`

This normalization happens automatically during the merge step — you do not
need to rename any fields.

!!! warning "Important"
    Do **not** modify `guide.json` after export. It must remain unchanged as your source of truth. The pipeline's deterministic merge depends on this file being exactly as Folge produced it.

## Image Naming

Folge exports screenshots with names like `step-0.png`, `step-1.png`, etc.
The pipeline matches images to steps by the `screenshotFilename` field:

- `step-0.png` corresponds to the step with `"screenshotFilename": "step-0.png"`
- `step-1.png` corresponds to the step with `"screenshotFilename": "step-1.png"`
- And so on

The filenames must match what is referenced in `guide.json`'s `steps[].screenshotFilename` field.
