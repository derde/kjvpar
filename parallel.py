#! /usr/bin/python3

import re
import copy
import sys

def index(dicty,i):
    keys=list(dicty.keys())
    return dicty[keys[i]]

maxchunk=4

alltemplates={
    'parallel.html': {
        'new':        '<!-- Begin -->',
        'newbook':    '<table>',
        'newchapter': '<tr>',
        'swlang':     '',
        'newlang':    '<td>',
        'book':       '<H1>%(newbook)s</H1>\n',
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
        'newchapter': '\\PPnewchapter', #  synchronise left/right
        'swlang':     '\\PPswlang',   # switch between languages
        'newlang':    '\\PPnewlang\\PPnewlang%(zz)s',   # column
        'book':       '\\PPbook{%(newbook)s}',
        'chapter':    '\\PPchapter{%(chapter)s}',
        'versei':     '\\PPversei{%(v)s}{%(text)s}\n',
        'verseii':    '\\PPverseii{%(v)s}{%(text)s}\n',
        'verse':      '\\PPverse{%(v)s}{%(text)s}\n',
        'endlang':    '\\PPendlang%(zz)s\\PPendlang',   # /column
        'endchapter': '\\PPendchapter',
        'endbook':    '\\PPendbook',
        'end':        '\\PPend',
        'italics':    '{\\em %(italics)s}',
        'authorship': '{\\em %(authorship)s}\\PPpar',
        'attribution': '\\PPpostscript{%(attribution)s}',
    }
}
    
class BibleParser:
    def __init__(self,sourcefile,settings):
        self.settings=settings
        self.booklist=[]
        self.books={}
        self.counters={}
        self.readsource(sourcefile)
        self.chaptersequence=self.allchapters()
    def readsource(self,sourcefile):
        textre=re.compile(r'^(.*?) (\d+):(\d+) (.*)')
        for line in sourcefile:
            m=textre.search(line)
            if m: self.register(m)
    def register(self,m):
        thisbook,thischapter,thisverse,thistext = m.groups()
        chapters=self.books.setdefault(thisbook,{})
        if len(chapters)==0:
            self.booklist.append(thisbook)
        verses=chapters.setdefault(int(thischapter),{})
        verses[int(thisverse)]=thistext
    def registerparagraphbreaks(self,paragraphs):
        self.settings['paragraphs']=paragraphs
        self.allchunks()
    def allchunks(self):
        o=[]
        for chapter in self.chaptersequence:
            chunk=copy.copy(chapter)
            chunk['paragraph']={}
            versecount=len(chapter['verses'])
            for verse,text in chapter['verses'].items():
                ref=(chapter['bookindex'], chapter['chapter'], verse)
                if verse==1 or ref in self.settings['paragraphs'] or len(chunk['paragraph'])>maxchunk:
                    if len(chunk['paragraph']):
                        o.append(chunk) # emit previous complete paragraph
                    chunk=copy.copy(chapter)
                    chunk['paragraph']={}
                    chunk['newchapter']= ( verse==1 )
                    if verse!=1:
                        chunk['newbook']=False
                chunk['paragraph'][verse]=text
                chunk['endchapter']= ( verse==versecount )
            # Emit last paragraph
            if len(chunk):
                o.append(chunk)
                chunk=[]
        self.chunksequence=o

    def bookindex(self,bookname):
        books=list(self.books.keys())
        return books.index(bookname)
                
    def allchapters(self):
        o=[]
        lastd=None
        #for book,chapters in self.books.items():
        bookindex=0
        for booknumber in self.settings['bookseq']:
            self.counters['books']=self.counters.get('books',0)+1
            book=self.booklist[booknumber-1]
            chapters=self.books[book]
            if lastd:
                lastd['endbook']=1
            newbook=book
            bookindex=self.bookindex(book)
            for chapter,verses in chapters.items():
                self.counters['chapters']=self.counters.get('chapters',0)+1
                self.counters['verses']=self.counters.get('verses',0)+1
                if lastd: lastd['endchapter']=1
                lastd={'newbook':newbook, 'bookindex':bookindex, 'book': book, 'chapter': chapter, 'verses': verses, 'self': self, 'endbook':0, }
                o.append(lastd)
                newbook=''
        lastd['endbook']=1
        return o

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
    """language: look up paragraph book names in this language
    """
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
    
bookseq=list(range(40,67)) # 40	Matthew # 66 Revelation
bookseq.append(19) # 19	Psalms
bookseq.append(20) # 20 Proverbs

paragraphs={}
ensettings={'zz':'EN','lang':'King James Version 1611/1769', 'bookseq': bookseq, 'paragraphs': paragraphs }
zusettings={'zz':'ZU','lang':'Zulu 1959',  'bookseq': bookseq, 'paragraphs': paragraphs}
afsettings={'zz':'AF','lang':'Afrikaans 1935/1953',  'bookseq': bookseq, 'paragraphs': paragraphs}
en = BibleParser(open('text/kingjamesbibleonline.txt','r'),ensettings)
zu = BibleParser(open('text/zulu1959.txt','r'),zusettings)
af = BibleParser(open('text/af1953.txt','r'),afsettings)
allversions=[en,af]
readparagraphs(paragraphs,'paragraphs.txt',en)
en.registerparagraphbreaks(paragraphs)
af.registerparagraphbreaks(paragraphs)
zu.registerparagraphbreaks(paragraphs)

for filename,templates in alltemplates.items():
    fd=open(filename,'w')
    fd.write(templates['new'])
    for chunknumber in range( len(en.chunksequence) ):
        peek=en.chunksequence[chunknumber]
        if peek['newbook']:
            fd.write(templates['newbook'])
        if peek['newchapter']:
            fd.write(templates['newchapter'])
        for vv in allversions:
            if vv!=allversions[0]:
                fd.write(templates['swlang'] % vv.settings)
            fd.write(templates['newlang'] % vv.settings)
            c=vv.chunksequence[chunknumber]
            if c['newbook']:
                fd.write(templates['book'] % c)
            if c['newchapter']:
                fd.write(templates['chapter'] % c)
            for v,text in c['paragraph'].items():
                # Epistle postscripts
                if text.find('<<[')>=0:
                    text = re.sub('<<\[(.*?)\]>>',attribution,text,0)
                # Psalm titles
                if text.find('<<')>=0:
                    text = re.sub('<<(.*?)>>',authorship,text,0)
                # Regular italics
                if text.find('[')>=0:
                    text = re.sub(r'\[([^\]]*?)\]',italicise,text,0)
                r={'v':v,'text':text,}
                if v==1: versetmpl ='versei'
                elif v==2: versetmpl ='verseii'
                else : versetmpl ='verse'
                fd.write(templates[versetmpl] % r)
            fd.write(templates['endlang'] % vv.settings)
            if c['endchapter']:
                fd.write(templates['endchapter'])
        if c['endbook']:
            fd.write(templates['endbook'])
    fd.write(templates['end'])
    fd.close()


