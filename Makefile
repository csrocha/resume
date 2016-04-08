all: cv.pdf

cv.pdf: cv.tex csrocha.en.tex bu1.bib

bu1.bib: cv.tex
	pdflatex $<

bu%.bbl: bu%.aux
	bibtex bu$*.aux

clean:
	rm -f *.bbl *.aux *.blg *.bak *.log *.out

%.pdf: %.tex
	pdflatex $<

