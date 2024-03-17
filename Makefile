ppenaf.pdf: pplayout.tex ppenaf.tex ppdefault.tex parallel.tex hyph-en.tex
	lualatex ppenaf.tex # for microtype
	./coords-to-headings.py # parallel.aux -> ppenaf.headings.csv

parallel.tex: parallel.py paragraphs.txt ppenafnt.csv highlights.txt
	./parallel.py

ppenaf.headings.csv: parallel.tex ppenaf.coords
	./coords-to-headings.py

build:
	make ppenaf.pdf
	# ./coords-to-headings.py # parallel.aux -> ppenaf.headings.csv
	lualatex ppenaf.tex
	make ppenaf-book.pdf

# Make book signatures - the 28 here is 28 x 1/72" ≅ 10mm
# See also https://softwarerecs.stackexchange.com/questions/438/software-to-put-pages-of-a-pdf-file-in-book-order
%-book.pdf: %.pdf
	# pdfbook2 --no-crop --paper=a4paper --outer-margin=28 --inner-margin=0 --top-margin=0 --bottom-margin=0 --signature=40 $<
	# pdfbook2 --no-crop --paper=a4paper --outer-margin=18 --inner-margin=0 --top-margin=15 --bottom-margin=14 --signature=4 $<
	pdfbook2 --no-crop --paper=a4paper --outer-margin=0 --inner-margin=0 --top-margin=0 --bottom-margin=0 --signature=4 --short-edge $<
	# pdfbook2 --paper=a4paper --outer-margin=18 --inner-margin=0 --top-margin=15 --bottom-margin=14 --signature=4 $<



