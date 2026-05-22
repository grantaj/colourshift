local function zap_spacing(tex)
  tex = tex:gsub("\\onehalfspacing", "")
  tex = tex:gsub("\\doublespacing", "")
  tex = tex:gsub("\\singlespacing", "")
  tex = tex:gsub("\\setstretch%s*%b{}", "")
  tex = tex:gsub("\\vspace%*?%b{}", "")
  tex = tex:gsub("\\smallskip", "")
  tex = tex:gsub("\\medskip", "")
  tex = tex:gsub("\\bigskip", "")
  return tex
end

function RawBlock(el)
  if el.format == "latex" then
    local text = zap_spacing(el.text)
    if text == "" then
      return {}
    end
    el.text = text
  end
  return el
end

function RawInline(el)
  if el.format == "latex" then
    local text = zap_spacing(el.text)
    if text == "" then
      return {}
    end
    el.text = text
  end
  return el
end

local function stringify(inlines)
  local acc = {}
  for index = 1, #inlines do
    if inlines[index].text then
      table.insert(acc, inlines[index].text)
    end
  end
  return table.concat(acc)
end

local function has_non_text_inline(inlines)
  for index = 1, #inlines do
    local inline = inlines[index]
    if inline.t ~= "Str" and inline.t ~= "Space" and inline.t ~= "SoftBreak" and inline.t ~= "LineBreak" then
      return true
    end
  end
  return false
end

function Para(el)
  if has_non_text_inline(el.content) then
    return el
  end

  local text = stringify(el.content):gsub("%s+", "")
  if text == "" or text == "1em" then
    return {}
  end
  return el
end

local function collect_images(blocks)
  local images = {}

  for _, block in ipairs(blocks) do
    if block.t == "Para" or block.t == "Plain" then
      for _, inline in ipairs(block.content) do
        if inline.t == "Image" then
          table.insert(images, inline)
        end
      end
    end
  end

  return images
end

function Figure(el)
  local images = collect_images(el.content)

  if #images <= 1 then
    return el
  end

  local caption_blocks = {}
  for _, block in ipairs(el.caption.long) do
    table.insert(caption_blocks, block)
  end

  local content = {
    pandoc.Para(images),
  }

  if #caption_blocks > 0 then
    table.insert(
      content,
      pandoc.Div(caption_blocks, pandoc.Attr("", { "figcaption" }, {}))
    )
  end

  return pandoc.Div(content, pandoc.Attr(el.attr.identifier, { "figure-grid" }, el.attr.attributes))
end