#! /usr/bin/python3

import re
import copy
import sys

def index(dicty,i):
    keys=list(dicty.keys())
    return dicty[keys[i]]

maxchunk=5
minchunk=2

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
        'newchapter': '\\PPnewchapter', #  synchronise left/right
        'swlang':     '\\PPswlang',   # switch between languages
        'newlang':    '\\PPnewlang\\PPnewlang%(zz)s',   # column
        'book':       '\\PPbook{%(book)s}',
        'chapter':    '\\PPchapter{%(chapter)s}',
        'versei':     '\\PPversei{%(v)s}{%(text)s}\n',
        'verseii':    '\\PPverseii{%(v)s}{%(text)s}\n',
        'verse':      '\\PPverse{%(v)s}{%(text)s}\n',
        'endlang':    '\\PPendlang%(zz)s\\PPendlang',   # /column
        'endchapter': '\\PPendchapter',
        'endbook':    '\\PPendbook',
        'end':        '\\PPend',
        'italics':    '{\\em %(italics)s}',
        'authorship': '\\PPpsalmauthor{%(authorship)s}',
        'attribution': '\\PPpostscript{%(attribution)s}',
    }
}
    
class Verse:
    def __init__(self,line,bibleparser):
        bookname,ref,text =bibleparser.decodeline(line)
        self.bookname=bookname
        self.ref=ref
        self.text=text
        self.newbook=(ref[1]==1 and ref[2]==1)
        self.newchapter=(ref[2]==1)
        self.endchapter=False
        self.endbook=False
        self.newparagraph=self.newchapter  # this might fail for Job 34 or so
        self.next=None # chained sequence of verses
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

    def moreparagraphbreaks(self):
        # Have paragraph syncs every few verses
        runlength=0
        for i in range(len(self.snippets)):
            verse=self.snippets[i]
            if verse.newparagraph: runlength=0
            runlength+=1
            if runlength>maxchunk:
                foundnew=False
                for j in range(1+i,1+i+minchunk):
                    if j>=len(self.snippets):
                        break
                    if self.snippets[j].newparagraph:
                        foundnew=True
                if not foundnew:
                    verse.newparagraph=True
                    runlength=0

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
        'errata':'text/af1953.errata' }

    en = BibleParser(ensettings)
    zu = BibleParser(zusettings)
    af = BibleParser(afsettings)
    allversions=[en,af]
    paragraphs={}
    readparagraphs(paragraphs,'paragraphs.txt',en)
    en.registerparagraphbreaks(paragraphs)
    zu.registerparagraphbreaks(paragraphs)
    buildparallelsequence('ppenafnt.csv',en,af)
    en.moreparagraphbreaks()
    
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
                    r={'v':v,'text':text,}
                    if v==1: versetmpl ='versei'
                    elif v==2: versetmpl ='verseii'
                    else : versetmpl ='verse'
                    fd.write(templates[versetmpl] % r)
                    if verse.endchapter:
                        fd.write(templates['endchapter'])
                    endbook = endbook or verse.endbook
                fd.write(templates['endlang'] % vv.settings)
            if endbook:
                fd.write(templates['endbook'])
            pass
        fd.write(templates['end'])
        fd.close()

