# Accessible Document Metadata

Incorporating proper metadata is essential for accessible documents. By
including critical metadata such as titles, authors, language, and tags, you
improve usability for people with disabilities while meeting compliance
standards like **ADA Title II** and **Section 508**.

The `folge-cli metadata` command derives this metadata from your guide JSON and
embeds it into **every** output format — PDF, DOCX, HTML, PPTX, EPUB, ODT, and
more.

```bash
# Generate a Pandoc-compatible metadata.yaml for all formats
folge-cli metadata guide.json -o metadata.yaml

# Embed metadata into an existing PDF and allow text copying
folge-cli metadata guide.json --apply-pdf output/guide.pdf

# Check metadata against accessibility best practices
folge-cli metadata guide.json --check --strict
```

---

## Required Metadata

### 1. Title (not to be confused with the file name)

The document title is one of the most crucial metadata elements for
accessibility. Screen readers rely on the title to identify the document's
purpose, ensuring users know what they are opening.

**Best practices:**

- Use clear, concise language that reflects the document's content
- Avoid generic titles like "Document 1" or "Untitled"
- Set the title from the document's actual title, not its file name

The pipeline uses the guide's `title` field (with `project.name` as a
fallback). `--check --strict` flags generic titles:

```bash
folge-cli metadata guide.json --check --strict
# - Title 'Document 1' is generic - use a clear, specific document title
```

### 2. Author

Identifying the author provides readers and content managers important context.

**Best practices:**

- Include the individual, department, or organization responsible for the document

The author is read from `project.author` in `config.yaml`, overridden by
`--author`, or taken from the guide's `metadata.author`.

```yaml
project:
  author: "Department of Accessible Technology"
```

### 3. Subject

The subject provides a brief summary of the document's content, helping users
understand its purpose.

**Best practices:**

- Provide a concise description that outlines the document's key themes or objectives

The subject is derived from the guide's `description` (with
`project.description` as a fallback), or overridden with `--subject`.

### 4. Keywords

Keywords improve searchability and help users quickly locate the document based
on relevant terms.

**Best practices:**

- Include relevant keywords that accurately reflect the document's content and purpose

Keywords come from `project.keywords` in `config.yaml`, the guide's
`metadata.keywords`, or `--keywords`, and are augmented with the most frequent
meaningful words from step titles.

### 5. Language Specification

Specifying the document's language ensures screen readers interpret the text
correctly, applying appropriate pronunciation and intonation.

**Best practices:**

- Define the document's primary language in the metadata settings
- For multilingual documents, specify different language attributes for applicable sections

The language is taken from the guide's `language` field (default `en`) and is
written both to Pandoc's `lang` metadata and to the PDF `/Lang` entry.

### 6. Document Structure Tags

Digital tags provide essential structure for screen readers, guiding users
through headings, lists, tables, and other content elements.

**Best practices:**

- Ensure each element of the document is tagged accurately

Tags are applied by the pipeline's Pandoc Lua filters
(`pdf-accessibility.lua`, `docx-accessibility.lua`, `accessibility.lua`) and
WeasyPrint's tagged-PDF output. `folge-cli validate-pdf` verifies the result.

### 7. Bookmarks (documents of 10 pages or more)

Bookmarks create an interactive table of contents, allowing users to jump
directly to key sections of the document.

**Best practices:**

- Generate bookmarks based on heading levels to improve navigation
- Use descriptive bookmark labels that match the document's structure

WeasyPrint generates an outline from the heading structure automatically. The
metadata report flags when a guide is large enough (10+ pages) to require
bookmarks.

### 11. Security Settings — allow copying of text

Overly restrictive security settings can block assistive technologies from
accessing document content.

**Best practices:**

- Avoid security restrictions that prevent text copying, text extraction, or
  screen reader access

With `--apply-pdf`, `folge-cli metadata` strips any restrictive security
handler from the PDF so text copying is always allowed:

```bash
folge-cli metadata guide.json --apply-pdf output/guide.pdf
# Copy allowed : True
```

---

## How It Works

1. `folge-cli metadata` reads the guide JSON (or the enriched output) and
   `config.yaml`.
2. It writes a Pandoc-compatible `metadata.yaml`:

   ```yaml
   ---
   title: 'BrailleBlaster: Headings, Lists, and Emphasis'
   author: Michael Ryan Hunsaker, M.Ed., Ph.D.
   subject: Automated documentation publishing with vision enrichment
   keywords:
   - accessibility
   - documentation
   - headings
   lang: en
   ---
   ```

3. `publish` passes it to every Pandoc target via `--metadata-file`, embedding
   the same metadata into DOCX/ODT core properties, HTML `<meta>` tags, EPUB
   OPF metadata, and PDFs.
4. For PDFs, `--apply-pdf` writes the Info dictionary and `/Lang` entry with
   PyMuPDF and ensures the security permissions allow text copying.

## Metadata Sources

| Element | Source | Fallback |
|---------|--------|----------|
| Title | Guide `title` | `project.name` |
| Author | `metadata.author` / `--author` | `project.author` |
| Subject | Guide `description` / `--subject` | `project.description` |
| Keywords | `metadata.keywords` / `--keywords` | `project.keywords` + derived from step titles |
| Language | Guide `language` / `--language` | `en` |
| Tags | Pandoc Lua filters + WeasyPrint | always on |
| Bookmarks | Heading outline (WeasyPrint) | 10+ pages |
| Security | PyMuPDF `--apply-pdf` | copying allowed |
