# Step 1: Export from Folge

**What it does:** Extracts your guide content and screenshots from Folge.

**Why it matters:** This is your source of truth. All subsequent processing depends on this export.

## How to Export

1. Open your guide in Folge
2. Click **Export** > **JSON**
3. Save the file as `guide.json` in the project root
4. Export all screenshots
5. Save all images to the `images/` directory with consistent naming (e.g., `001.png`, `002.png`)

## Output

| File | Location |
|------|----------|
| `guide.json` | Project root |
| `*.png` screenshots | `images/` directory |

## Guide JSON Structure

The exported `guide.json` contains:

| Field | Description |
|-------|-------------|
| `guide_id` | Unique identifier for the guide |
| `title` | Guide title |
| `description` | Optional description |
| `language` | Language code (e.g., `en`) |
| `steps` | Array of step objects |
| `steps[].step_id` | Unique integer ID for each step |
| `steps[].title` | Step heading |
| `steps[].body` | Instructional text |
| `steps[].image` | Filename of the associated screenshot |

!!! warning "Important"
    Do **not** modify `guide.json` after export. It must remain unchanged as your source of truth. The pipeline's deterministic merge depends on this file being exactly as Folge produced it.

## Image Naming

Use consistent numbering for your screenshots. The pipeline matches images to steps by filename:

- `001.png` corresponds to step 1
- `002.png` corresponds to step 2
- And so on

The filenames must match what is referenced in `guide.json`'s `steps[].image` field.
