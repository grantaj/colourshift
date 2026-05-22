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
	$(PANDOC) $(SRC) \
	  --standalone \
	  --mathjax \
	  --citeproc \
	  --toc \
	  --bibliography=$(BIB) \
	  --lua-filter=$(FILTER) \
	  --template=$(TPL) \
	  --resource-path=. \
	  --extract-media=$(OUTDIR)/assets \
	  -o $(OUT)
	cp $(CSS) $(OUTDIR)/style.css
	touch $(OUTDIR)/.nojekyll
	@echo "Built -> $(OUT)"

clean:
	rm -rf $(OUTDIR) docs

.PHONY: all clean