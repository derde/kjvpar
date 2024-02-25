#! /usr/bin/python3

import re
import copy
import sys

def index(dicty,i):
    keys=list(dicty.keys())
    return dicty[keys[i]]

rightmargin=21400
maxchunk=5
minchunk=2  # look ahead this far
debug=False

alltemplates={
    'parallel.html': {
        'new':        '<!-- Begin -->',
        'newbook':    '<table>',
        'newchapter': '<tr>',
        'swlang':     '',
        'newlang':    '<td>',
        'book':       '<H1>%(book)s</H1>\n',
        'chapter':    '<h2>%(chapter)s</h2> ',
        'versei':     '<p><sup>%(v)s</sup> %(text)s</p>\n',
        'verseii':    '<p><sup>%(v)s</sup> %(text)s</p>\n',
        'verse':      '<p><sup>%(v)s</sup> %(text)s</p>\n',
        'endlang':    '</td>',
        'endchapter': '</tr>',
        'endbook':    '</table>',
        'end':        '<!-- End -->',
        'italics':    '<i>%(italics)s</i>',
        'authorship': '<b>%(authorship)s</b><br>',
        'attribution': '<b>%(attribution)s</b><br>',
    },
    'parallel.tex': {
        'new':        '\\PPnew',
        'newbook':    '\\PPnewbook',
        'newchapter': '\\PPnewchapter\\PPnewchapter%(zz)s', #  synchronise left/right
        'swlang':     '\\PPswlang',   # switch between languages
        'newlang':    '\\PPnewlang\\PPnewlang%(zz)s',   # column
        'book':       '\\PPbook{%(book)s}\n',
        'chapter':    '\\PPchapter{%(chapter)s}',
        'versei':     '\\PPversei{%(v)s}{%(text)s}\n',
        'verseii':    '\\PPverseii{%(v)s}{%(text)s}\n',
        'verse':      '\\PPverse{%(v)s}\\PPverseref{%(reference)s}{%(text)s}\n',
        'endlang':    '\\PPendlang%(zz)s\\PPendlang',   # /column
        'endchapter': '\\PPendchapter\\PPendchapter%(zz)s',
        'endbook':    '\\PPendbook\n',
        'end':        '\\PPend',
        'italics':    '{\\em %(italics)s}',
        'authorship': '\\PPpsalmauthor{%(authorship)s}',
        'attribution': '\\PPpostscript{%(attribution)s}',
    }
}

# Rough guess at text width 
class TextWidth:
    width = {'A': 772, 'B': 693, 'C': 718, 'D': 797, 'E': 668, 'F': 620, 'G': 796, 'H': 852, 'I': 378, 'J': 534, 'K': 731, 'L': 608, 'M': 1004, 'N': 826, 'O': 838, 'P': 664, 'Q': 847, 'R': 744, 'S': 597, 'T': 687, 'U': 816, 'V': 763, 'W': 1067, 'X': 726, 'Y': 717, 'Z': 659, 'a': 583, 'b': 636, 'c': 534, 'd': 646, 'e': 562, 'f': 374, 'g': 586, 'h': 658, 'i': 347, 'j': 296, 'k': 612, 'l': 340, 'm': 974, 'n': 650, 'o': 623, 'p': 641, 'q': 629, 'r': 448, 's': 456, 't': 389, 'u': 652, 'v': 597, 'w': 898, 'x': 584, 'y': 607, 'z': 529}
    def __init__(self):
        self.default = self.width['x']  # default letter width?
        self.space = self.default//5*4  # default spacec width
        self.width[' '] = self.space
        self.width['.'] = self.width['j']//2
        self.width[','] = self.width['j']//2
    def measure(self,text):
        w=0
        for c in text:
           w+=self.width.get(c,self.space) 
        return w
    def wordwidths(self,words):
        'An array of word widths'
        o=[]
        for word in words.split():
            o.append(self.measure(word)+self.space)
        return o
    def wrap(self,text,margin=rightmargin,indent=0):
        "Do wordwrap and count lines"
        x=indent
        lines=1
        for width in self.wordwidths(text):
            if x+width>margin:
                lines+=1 # this word goes on the next line
                x=0  # carriage return
            x+=width # place word on line
        return lines

    
class Verse:
    def __init__(self,line,bibleparser):
        self.textwidth=TextWidth()
        bookname,ref,text =bibleparser.decodeline(line)
        self.bookname=bookname
        self.ref=ref
        self.text=text
        self.newbook=(ref[1]==1 and ref[2]==1)
        self.newchapter=(ref[2]==1)
        self.endchapter=False
        self.endbook=False
        self.newparagraph=self.newchapter  # this might fail for Job 34 or so
        self.next=None # chained sequence of verses in a snippet
        self.bibleparser=bibleparser

    # Get the linecount for this snippet and its friends
    def linecount0(self,linewidth=43):
        ntext=re.sub(r'[<>\[\]]','',self.text)
        lines=0
        while len(ntext)>linewidth:
            trim=ntext[:linewidth]
            line,carry=trim.rsplit(' ',1)
            lines+=1
            ntext=carry+ntext[linewidth:]
        lines+=1 # min(len(ntext)/linewidth+0.5,1.0) # fuzzyness
        lines=max(1,lines)
        if self.next:
            lines+=self.next.linecount()
        return lines

    # Get the linecount for this snippet and its friends
    def linecount(self,margin=rightmargin):
        ntext=re.sub(r'[<>\[\]]','',self.text)
        lines=self.textwidth.wrap(ntext,margin,margin//20)
        if self.next:
            lines+=self.next.linecount(margin)
        return lines

    def getreferencename(self):
        bookname,chapters=self.bibleparser.getbookname(self.ref[0])
        if chapters==1:
            return bookname+' '+str(self.ref[2])
        return bookname+' '+str(self.ref[1])+':'+str(self.ref[2])

    def pairs(self):
        return {
            'text':self.text,
            'book':self.bookname,
            'chapter':self.ref[1],
            'verse':self.ref[2],
        }
    def __str__(self):
        return f'{self.bookname} {self.ref[1]}:{self.ref[2]}'

class BibleParser:
    def __init__(self,settings):
        self.settings=settings
        self.booknames=[]
        self.books={}
        self.counters={}
        self.canonref={} # this language reference->kjv canonical reference
        self.allverses={}
        self.checkrefs={}
        self.snippets=[]
        self.setup()
    def getbookname(self,booknumber):
        # FIXME: Language-specific adjustments have to happen
        c2=(booknumber,2,1)
        if c2 not in self.allverses:
            chapters=1
        else:
            chapters=2
        booknames=self.settings.get('booknames',self.booknames)
        return booknames[booknumber],chapters

    def setup(self):
        sourcefile=open(self.settings['source'],'r')
        textre=re.compile(r'^(.*?) (\d+):(\d+) (.*)')
        for line in sourcefile:
            m=textre.search(line)
            if m: self.register(line)
        self.markchapterends()

    def markchapterends(self):
        "Go through the chapters, and mark the ends of the chapters and books"
        lastverse=None
        for ref,verse in self.allverses.items():
            if lastverse and verse.newbook:
                lastverse.endbook=True
            if lastverse and verse.newchapter:
                lastverse.endchapter=True
            lastverse=verse
        lastverse.endbook=True
        lastverse.endchapter=True

    def register(self,line):
        verse = Verse(line,self)
        self.allverses[verse.ref]=verse

    def addsnippet(self,snippet):
        lastverse=None
        verse0=None
        for ref in snippet:
            verse=self.allverses[ref]
            if not verse0: verse0=verse
            if lastverse: lastverse.next=verse # chain it
            lastverse=verse
        self.snippets.append(verse0)
        return len(snippet)

    def checkreference(self,ref):
        if ref in self.checkrefs:
            self.checkrefs.pop(ref)
        else:
            lang=self.settings['lang']
            sys.stderr.write(f"{lang}: Reference f{ref} used twice!")
        return len(self.checkrefs)

    def linetoref(self,line):
        if not line:
            return None
        mbookname,ref,mtext=self.decodeline(line)
        return ref

    def decodeline(self,line):
        m=re.search('(.*) (\d+):(\d+)\s*(.*)',line)
        if not m: return
        bookname,mchapter,mverse,mtext = m.groups()
        bookindex=self.bookindex(bookname)
        chapter=int(mchapter)
        verse=int(mverse)
        ref=(bookindex,chapter,verse)
        return bookname,ref,mtext

    def registerparagraphbreaks(self,paragraphs):
        for ref in paragraphs:
            verse=self.allverses[ref]
            verse.newparagraph=True

    def moreparagraphbreaks(self,other,margin):
        # Have paragraph syncs every few verses
        runlength=0
        leftlines=0
        rightlines=0
        linematchbreak=0
        runlengthcount=0
        shouldbreaksoon=0
        for i in range(len(self.snippets)):
            verse=self.snippets[i]
            # Compare line counts between translations:
            leftlines+=verse.linecount(margin)
            rightlines+=other.snippets[i].linecount()
            #if i<len(self.snippets)-1:
            #    leftnext=self.snippets[i+1].linecount()
            #    rightnext=other.snippets[i+1].linecount()
            if verse.newparagraph:
                runlength=0
                shouldbreaksoon=0
            runlength+=1
            if runlength>maxchunk or (shouldbreaksoon and runlength > 1):
                # Don't break if we are about to do a paragraph break soon anyway:
                breakingsoon=False
                for j in range(1+i,1+i+minchunk):
                    if j>=len(self.snippets):
                        break
                    if self.snippets[j].newparagraph:
                        breakingsoon=True
                if not breakingsoon:
                    if shouldbreaksoon:
                        linematchbreak+=1
                        if debug: verse.text='*'+verse.text # Mangle output for debug
                    else:
                        runlengthcount+=1
                        if debug: verse.text='"'+verse.text # Mangle output for debug
                    verse.newparagraph=True
                    runlength=0
                    leftlines=0
                    rightlines=0
                    shouldbreaksoon=0
            else:
                mismatchlr = (runlength>1 and abs((rightlines)-(leftlines))>0)
                if mismatchlr:
                    shouldbreaksoon+=1
        sys.stderr.write(f'paragraph breaks: linematchbreak={linematchbreak}, runlengthcount={runlengthcount}\n')

    def getparagraphranges(self):
        # Return list of snippet ranges for paragraphs
        o=[]
        last=0
        for i in range(len(self.snippets)):
            if self.snippets[i].newparagraph:
                if i: o.append((last,i))
                last=i
        o.append((last,len(self.snippets)))
        return o

    def getsnippetverses(self,sniprange):
        'A paragraph that we are going to emit'
        i0,i1 = sniprange
        verselist=[]
        for i in range(i0,i1):
            verse=self.snippets[i]
            verselist.append(verse)
            while verse.next:
                verse=verse.next
                verselist.append(verse)
        return verselist

    def bookindex(self,bookname,autoregister=True):
        "Find position of book by name in this language, and if it's new, just add it to the list"
        # books=list(self.books.keys())
        if autoregister and not bookname in self.booknames:
            self.booknames.append(bookname)
        return self.booknames.index(bookname)
                

def italicise(m):
    global templates
    r={'italics': m.group(1)}
    return templates['italics'] % r
def authorship(m):
    global templates
    r={'authorship': m.group(1)}
    return templates['authorship'] % r
def attribution(m):
    global templates
    r={'attribution': m.group(1)}
    return templates['attribution'] % r


def readparagraphs(paragraphs,filename,language):
    "language: look up paragraph book names in this language"
    fd=open(filename,'r')
    for line in fd:
        m=re.search(' \d+:',line) 
        i,ii=m.span(0)
        bookname=line[:i]
        chapter=0
        for bit in line[i:].strip().split():
            m=re.search('^(\d+):(\d+)|(\d+)$',bit)
            mchapter,mverse,mmverse = m.groups()
            if mchapter:
                n=int(mchapter)
                chapter=n
                verse=int(mverse)
            else:
                verse=int(mmverse)
            bookindex=language.bookindex(bookname)
            ref=(bookindex,chapter,verse)
            paragraphs[ref]=True
    fd.close()

# Read from a parallel spec file
def iterateparallel(csvfeed,en,af):
    concurrent=None
    for line in csvfeed:
        if len(line)==0: continue
        if len(line)<3: line.extend(['','',''])
        cmd,lineEN,lineAF=line[:3]
        if lineEN and lineAF:
            if concurrent:
                yield concurrent
            concurrent={'en':[],'af':[]}
        refEN=en.linetoref(lineEN)
        refAF=af.linetoref(lineAF)
        if refEN: concurrent['en'].append(refEN)
        if refAF: concurrent['af'].append(refAF)
    yield concurrent

# Read the parallel file and sequence the verses
def buildparallelsequence(filename, en, af):
    # FIXME: Hack code
    import csv
    fd=csv.reader(open(filename,'r'))
    countEN=0
    countAF=0
    snippets=0
    for enaf in iterateparallel(fd,en,af):
        countEN += en.addsnippet(enaf['en'])
        countAF += af.addsnippet(enaf['af'])
        snippets+=1
    print(f'CHECK: snippets={snippets}, verses[en]={countEN}, verses[af]={countAF}')

if __name__=="__main__":
    paragraphs={}
    paragraphsAF={}
    ensettings={
        'zz':'EN',
        'lang':'King James Version 1611/1769',
        'source': 'text/kingjamesbibleonline.txt',
        'errata':'text/kingjamesbibleonline.errata' }
    zusettings={
        'zz':'ZU',
        'lang':'Zulu 1959',
        'source': 'text/zulu1959.txt' }
    afsettings={
        'zz':'AF',
        'lang':'Afrikaans 1935/1953',
        'source': 'text/af1953.txt',
        'errata':'text/af1953.errata',
        'BOOKNAMES': [ 'GÉNESIS', 'EXODUS', 'LEVÍTIKUS', 'NÚMERI', 'DEUTERONÓMIUM', 'JOSUA', 'RIGTERS', 'RUT', 'I SAMUEL', 'II SAMUEL', 'I KONINGS', 'II KONINGS', 'I KRONIEKE', 'II KRONIEKE', 'ESRA', 'NEHEMÍA', 'ESTER', 'JOB', 'PSALMS', 'SPREUKE', 'PREDIKER', 'HOOGLIED', 'JESAJA', 'JEREMIA', 'KLAAGLIEDERE', 'ESÉGIËL', 'DANIËL', 'HOSÉA', 'JOËL', 'AMOS', 'OBÁDJA', 'JONA', 'MIGA', 'NAHUM', 'HÁBAKUK', 'SEFÁNJA', 'HAGGAI', 'SAGARÍA', 'MALEÁGI', 'MATTHÉÜS', 'MARKUS', 'LUKAS', 'JOHANNES', 'HANDELINGE', 'ROMEINE', 'I KORINTHIËRS', 'II KORINTHIËRS', 'GALÁSIËRS', 'EFÉSIËRS', 'FILIPPENSE', 'KOLOSSENSE', 'I THESSALONICENSE', 'II THESSALONICENSE', 'I TIMÓTHEÜS', 'II TIMÓTHEÜS', 'TITUS', 'FILÉMON', 'HEBREËRS', 'JAKOBUS', 'I PETRUS', 'II PETRUS', 'I JOHANNES', 'II JOHANNES', 'III JOHANNES', 'JUDAS', 'OPENBARING', ],
        'booknames': [ 'Génesis', 'Exodus', 'Levítikus', 'Númeri', 'Deuteronómium', 'Josua', 'Rigters', 'Rut', 'I Samuel', 'II Samuel', 'I Konings', 'II Konings', 'I Kronieke', 'II Kronieke', 'Esra', 'Nehemía', 'Ester', 'Job', 'Psalms', 'Spreuke', 'Prediker', 'Hooglied', 'Jesaja', 'Jeremia', 'Klaagliedere', 'Eségiël', 'Daniël', 'Hoséa', 'Joël', 'Amos', 'Obádja', 'Jona', 'Miga', 'Nahum', 'Hábakuk', 'Sefánja', 'Haggai', 'Sagaría', 'Maleági', 'Matthéüs', 'Markus', 'Lukas', 'Johannes', 'Handelinge', 'Romeine', 'I Korinthiërs', 'II Korinthiërs', 'Galásiërs', 'Efésiërs', 'Filippense', 'Kolossense', 'I Thessalonicense', 'II Thessalonicense', 'I Timótheüs', 'II Timótheüs', 'Titus', 'Filémon', 'Hebreërs', 'Jakobus', 'I Petrus', 'II Petrus', 'I Johannes', 'II Johannes', 'III Johannes', 'Judas', 'Openbaring', ],
         }

    en = BibleParser(ensettings)
    zu = BibleParser(zusettings)
    af = BibleParser(afsettings)
    allversions=[en,af]
    paragraphs={}
    readparagraphs(paragraphs,'paragraphs.txt',en)
    en.registerparagraphbreaks(paragraphs)
    zu.registerparagraphbreaks(paragraphs)
    buildparallelsequence('ppenafnt.csv',en,af)
    en.moreparagraphbreaks(af,22000)
    
    # Plan: iterate through sequence in english
    # Afrikaans: paragraphs move a little bit

    di=0
    for filename,templates in alltemplates.items():
        fd=open(filename,'w')
        fd.write(templates['new'])
        for sniprange in en.getparagraphranges():
            peek=en.getsnippetverses(sniprange)
            if peek[0].newbook:
                fd.write(templates['newbook'])
            endbook=False
            for vv in allversions:
                if vv!=allversions[0]:
                    fd.write(templates['swlang'] % vv.settings)
                fd.write(templates['newlang'] % vv.settings)
                verses=vv.getsnippetverses(sniprange)
                for verse in verses:
                    if verse.newbook:
                        fd.write(templates['book'] % verse.pairs())
                    if verse.newchapter:
                        fd.write(templates['chapter'] % verse.pairs())
                    # Epistle postscripts
                    text=verse.text
                    if text.find('<<[')>=0:
                        text = re.sub('<<\[(.*?)\]>>',attribution,text,0)
                    # Psalm titles
                    if text.find('<<')>=0:
                        text = re.sub('<<(.*?)>>',authorship,text,0)
                    # Regular italics
                    if text.find('[')>=0:
                        text = re.sub(r'\[([^\]]*?)\]',italicise,text,0)
                    v=verse.ref[2]
                    reference=verse.getreferencename() # the display of the verse
                    r={'v':v,'text':text, 'reference': reference, 'REFERENCE': reference.upper() }
                    if v==1: versetmpl ='versei'
                    elif v==2: versetmpl ='verseii'
                    else : versetmpl ='verse'
                    fd.write(templates[versetmpl] % r)
                    if verse.endchapter:
                        fd.write(templates['endchapter'] % vv.settings)
                    endbook = endbook or verse.endbook
                fd.write(templates['endlang'] % vv.settings)
            if endbook:
                fd.write(templates['endbook'] % vv.settings)
            pass
        fd.write(templates['end'])
        fd.close()

