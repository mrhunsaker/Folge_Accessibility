-- pagebreak.lua
-- Converts \newpage LaTeX raw blocks to format-appropriate page breaks.
--
-- For HTML output (weasyprint): CSS page-break-before
-- For DOCX output: Word page break via OpenXML
-- For PPTX output: remove (H2 headings already create slides)
-- For everything else (xelatex): pass through as-is

function RawBlock(raw)
  if raw.format == "latex" or raw.format == "tex" then
    if raw.text:match("\\newpage") then
      if FORMAT == "html" or FORMAT == "html5" then
        return pandoc.RawBlock("html", '<div style="page-break-before: always;"></div>')
      elseif FORMAT == "docx" then
        return pandoc.RawBlock("openxml",
          '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
      elseif FORMAT == "pptx" then
        return nil
      end
    end
  end
  return nil
end
