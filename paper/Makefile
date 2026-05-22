PANDOC = pandoc
SRC    = main.tex
BIB    = references.bib
TPL    = template.html
FILTER = ignore-spacing.lua
CSS    = style.css

OUTDIR = ../docs
OUT    = $(OUTDIR)/index.html

all: $(OUT)

$(OUT): $(SRC) $(BIB) $(TPL) $(CSS) $(FILTER)
	@mkdir -p $(OUTDIR)
	cd $(OUTDIR) && $(PANDOC) ../paper/$(SRC) \
	  --standalone \
	  --mathjax \
	  --citeproc \
	  --toc \
	  --bibliography=../paper/$(BIB) \
	  --lua-filter=../paper/$(FILTER) \
	  --template=../paper/$(TPL) \
	  --resource-path=../paper \
	  --extract-media=assets \
	  -o index.html
	sed -i 's#\.\./docs/assets/#assets/#g' $(OUT)
	cp $(CSS) $(OUTDIR)/style.css
	touch $(OUTDIR)/.nojekyll
	@echo "Built -> $(OUT)"

clean:
	rm -rf $(OUTDIR) docs

.PHONY: all clean