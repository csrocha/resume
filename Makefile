all: cv.en.pdf cv.es.pdf

cv.en.pdf: cv.tex csrocha.en.tex

cv.es.pdf: cv.tex csrocha.es.tex

bu1.bib: cv.tex
	pdflatex $<

bu%.bbl: bu%.aux
	bibtex bu$*.aux

clean:
	rm -f *.bbl *.aux *.blg *.bak *.log *.out

%.pdf: %.tex
	pdflatex $<

