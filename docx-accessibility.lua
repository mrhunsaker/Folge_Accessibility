-- Pandoc Lua filter for injecting accessibility metadata
-- Usage: pandoc input.md --lua-filter=accessibility.lua -o output.html

function Image(img)
  local longdesc = img.attributes["longdesc"]
  if longdesc then
    img.attributes["aria-description"] = longdesc
    if img.caption and #img.caption > 0 then
      img.attributes["title"] = pandoc.utils.stringify(img.caption)
    end
    img.attributes["accessibility-description"] = longdesc
  end
  if not img.attr.attributes["alt"] then
    if img.caption and #img.caption > 0 then
      img.attr.attributes["alt"] = pandoc.utils.stringify(img.caption)
    else
      img.attr.attributes["alt"] = ""
    end
  end
  return img
end

function Link(link)
  if link.title then
    link.attributes["aria-label"] = link.title
  end
  return link
end

function Div(div)
  local classes = div.attributes["class"] or ""
  if classes:find("image%-description") then
    div.attributes["aria-hidden"] = "true"
    div.attributes["role"] = "note"
  end
  if classes:find("ocr%-text") then
    div.attributes["aria-hidden"] = "true"
    div.attributes["role"] = "note"
  end
  if classes:find("ui%-controls") then
    div.attributes["aria-hidden"] = "true"
    div.attributes["role"] = "note"
  end
  return div
end

function Header(header)
  header.attributes["aria-level"] = tostring(header.level)
  return header
end
