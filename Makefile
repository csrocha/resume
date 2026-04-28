all: cv.en.pdf cv.es.pdf

cv.en.pdf: cv.tex csrocha.en.tex

cv.es.pdf: cv.tex csrocha.es.tex

bu1.bib: cv.tex
	pdflatex $<

bu%.bbl: bu%.aux
	bibtex bu$*.aux

clean:
	rm -f *.bbl *.aux *.blg *.bak *.log *.out cv_output.*

%.pdf: %.tex
	pdflatex $<

# Generate a targeted CV:
#   make TARGET="Senior ML Engineer en startup fintech" LANG=en
#   make TARGET="CTO en empresa de salud digital" LANG=es PDF=--pdf
TARGET ?= Software Engineer
LANG   ?= en
PDF    ?=

cv_output.tex:
	python generate_cv.py --target "$(TARGET)" --lang $(LANG) $(PDF) --output cv_output

