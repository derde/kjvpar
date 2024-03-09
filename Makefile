ppenaf.pdf: pplayout.tex ppenaf.tex ppdefault.tex parallel.tex hyph-en.tex
	lualatex ppenaf.tex # for microtype

parallel.tex: parallel.py paragraphs.txt ppenafnt.csv highlights.txt
	./parallel.py

ppenaf.headings.csv: parallel.tex ppenaf.coords
	./coords-to-headings.py

build:
	./parallel.py
	lualatex ppenaf.tex
	./coords-to-headings.py
	lualatex ppenaf.tex
