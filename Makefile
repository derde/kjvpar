ppenaf.pdf: pplayout.tex ppenaf.tex ppdefault.tex parallel.tex
	xelatex ppenaf.tex

parallel.tex: parallel.py paragraphs.txt
	./parallel.py
