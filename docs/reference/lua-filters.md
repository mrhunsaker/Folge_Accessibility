# Lua Filters Reference

Pandoc Lua filters inject accessibility metadata into output formats during conversion.

## accessibility.lua (HTML)

Adds ARIA attributes for screen readers.

### Image Handler

```lua
function Image(img)
```

| Attribute | Value | Purpose |
|-----------|-------|---------|
| `aria-description` | `longdesc` value | Extended description for screen readers |
| `accessibility-description` | `longdesc` value | Redundant for compatibility |
| `title` | Caption text | Tooltip and accessible name |
| `alt` | Caption or empty | Fallback alt text |

### Link Handler

```lua
function Link(link)
```

Sets `aria-label` from the link's `title` attribute.

### Div Handler

```lua
function Div(div)
```

For divs with class `image-description`, `ocr-text`, or `ui-controls`:

| Attribute | Value |
|-----------|-------|
| `aria-hidden` | `true` |
| `role` | `note` |

These divs are marked as supplementary notes, not primary content.

### Header Handler

```lua
function Header(header)
```

Sets `aria-level` to the heading level (1-6).

---

## docx-accessibility.lua (DOCX)

Identical to the HTML filter. Injects the same ARIA attributes into the DOCX OpenXML structure.

---

## pdf-accessibility.lua (PDF)

Enhanced filter for PDF/UA compliance. Adds explicit PDF tags and metadata.

### Image Handler

```lua
function Image(img)
```

| Attribute | Value | Purpose |
|-----------|-------|---------|
| `pdf-alt` | First 150 chars of `longdesc` | Short Alt entry |
| `pdf-tag` | `Figure` | Explicit PDF structure tag |
| `pdf-longdesc` | Full `longdesc` | Expanded `/E` description |
| `alt` | Caption or empty | Fallback alt text |

### Header Handler

```lua
function Header(header)
```

Sets `pdf-tag` to `H1`, `H2`, etc. based on heading level.

### Para Handler

```lua
function Para(para)
```

Sets `pdf-tag` to `P` for all paragraphs.

### List Handler

```lua
function List(list)
```

Sets `pdf-tag` to `L` for all lists (bullet and numbered).

### BlockQuote Handler

```lua
function BlockQuote(block)
```

Sets `pdf-tag` to `BlockQuote`.

### CodeBlock Handler

```lua
function CodeBlock(code)
```

Sets `pdf-tag` to `Code`.

### Table Handler

```lua
function Table(table)
```

Sets `pdf-tag` to `Table`.

### Meta Handler

```lua
function Meta(meta)
```

Injects PDF/UA metadata:

```lua
meta["pdf-metadata"] = {
    producer = "Folge Vision Pipeline - PDF/UA Compliant",
    creator = "Documentation Team",
    subject = "Accessible Software Documentation",
    keywords = "documentation,accessibility,software,PDF/UA,WCAG,ARIA",
    pdf_version = "1.7",
    tagged = true,
    conforms_to = "PDF/UA-1"
}
```

## Custom Filters

To create a custom filter, follow the Pandoc Lua filter API:

```lua
function MyElement(element)
    element.attributes["my-attribute"] = "my-value"
    return element
end
```

Place the `.lua` file in the project root and reference it with `--lua-filter=my-filter.lua`.
