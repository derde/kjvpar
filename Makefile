ppenaf.pdf: pplayout.tex ppenaf.tex ppdefault.tex parallel.tex hyph-en.tex
	xelatex ppenaf.tex

parallel.tex: parallel.py paragraphs.txt ppenafnt.csv highlights.txt
	./parallel.py
