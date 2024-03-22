#! /usr/bin/python3
import re
# Fri Mar 08 16:43:15 ~/src/kjvpar $ grep PPsq25928 parallel.tex ppenaf.coords

# oparallel.tex:\PPendlangEN\PPendlang\PPswlang\PPnewlang\PPnewlangAF\PPverse{4}{Matthéüs
# 1:4}{PPsq25928}{en Ram die vader van Ammínadab, en Ammínadab die vader van
# Nagson, en Nagson die vader van Salmon,}
parallelfd=open('parallel.tex','r')

# ppenaf.coords:PPsq25928,Matthéüs 1:4,x=210.59714pt, y=391.37599pt,3
coords=open('parallel.aux','r')

ref2verse={'AF':{},'EN':{}}
ref2lang={}
ref2bcv={}
ref2reference={}
pplang_re=re.compile(r'\\PPnewlang([A-Z]+)')

# 1=>4; 2=>Matthéüs 1:4; 3=>PPsq25928; 
ppverse_re=re.compile(r'\\PPversei*\{(.*?)\}\{(.*?)\}\{(PP.*?)\}')

lang='ZZ'
for line in parallelfd:
    pplang_m = pplang_re.search(line)
    if pplang_m: lang=pplang_m.group(1)
    ppverse_m = ppverse_re.search(line)
    if not ppverse_m : continue
    bookchapterverse = ppverse_m.group(2)
    ppref = ppverse_m.group(3) 
    ref2lang[ppref]=lang
    ref=ref2verse[lang]
    ref[ppref]=bookchapterverse
    ref2bcv[ppref]=bookchapterverse
parallelfd.close()

def iteraterefs(coords):
    # Find first and last reference on each page
    page_re=re.compile(r'newlabel\{(.*?)\}.*\\page\{(\d+)\}')
    posy_re=re.compile(r'newlabel\{(.*?)\}.*\\posx\{(\d+)\}\\posy\{(\d+)\}')
    pages = {}
    for line in coords:
        page_m=page_re.search(line)
        posy_m=posy_re.search(line)
        if page_m:
            ppref,page = page_m.groups()
            pages[ppref.strip('z')]=page
        if posy_m:
            ppref,x,y = posy_m.groups()
            page=pages[ppref]
            yield (ppref,x,y,page)

data={}        
toc={'EN': [], 'AF': [] }
for ppref,x,y,page in iteraterefs(coords):
    bcv=ref2bcv[ppref] # book,chapter,verse
    p=data.setdefault(page,{})
    p['page']=int(page)
    lang=ref2lang[ppref]
    rightname = lang+'right'
    leftname = lang+'left'
    if leftname not in p: p[leftname]=bcv
    p[rightname]=bcv

    if bcv.endswith(' 1:1'):
        book=bcv[:-4]
        toc[lang].append('\\PPtoc{'+book+'}{'+page+'}\n')

def decoderef(ref):
    m=re.search(r'^(.*) (\d+):(\d+)',ref)
    if m:
        return m.groups()
    m=re.search(r'^(.*) (\d+)',ref)
    if m:
        return m.group(1),'',m.group(2)

fo=open('ppenaf.headings.csv','w')
ft=open('ppenaf.headings.tex','w')

ft.write(r'''% Store by value
\newcommand{\ppsave}[3]{%
  \expandafter\def\csname PPdb#1@#2\endcsname{#3}%
}

% Define a command to retrieve values by index
\newcommand{\ppget}[2]{%
  \ifcsname PPdb#1@#2\endcsname
    \csname PPdb#1@#2\endcsname
  \fi
}
%
%   % Store values by index
%   \ppsave{entitle}{1}{First value}
%   \ppsave{entitle}{2}{Second value}
%
%   % Retrieve values by index
%   \ppget[entitle}{1} % Output: First value
%   \ppget[entitle}{2} % Output: Second value
''')

fo.write('page,enleft,enright,afleft,afright,entitle,aftitle\n')
for p in data.values():
    for lang in 'EN','AF':
        bookleft,chapterleft,verseleft=decoderef(p[lang+'left'])
        bookright,chapterright,verseright=decoderef(p[lang+'right'])
        BOOKLEFT=bookleft.upper()
        BOOKRIGHT=bookright.upper()
        rangekey=lang+'range'
        if BOOKLEFT+chapterleft==BOOKRIGHT+chapterright:
            p[rangekey]=f'{BOOKLEFT} {chapterleft}'.strip()
        else:
            if BOOKLEFT==BOOKRIGHT: 
                if chapterleft==chapterright:
                    p[rangekey]=f'{BOOKLEFT} {chapterleft}'.strip()
                else:
                    p[rangekey]=f'{BOOKLEFT} {chapterleft} - {chapterright}'
            else:
                # If we have multiple books, ignore all but the last in the title
                if chapterright in ('','1'):
                    rangeleftleft=''
                else:
                    rangeleftleft='1 - '
                p[rangekey]=f'{BOOKRIGHT} {rangeleftleft}{chapterright}'.strip() # strip because 1-chapter book is blank chapter

    fo.write('%(page)s,%(ENleft)s,%(AFleft)s,%(ENright)s,%(AFright)s,%(ENrange)s,%(AFrange)s\n' % p)
    
    for lang in 'EN','AF':
        # for k in 'left','right','range':
        for k in ( 'range', ):
            ft.write('\\ppsave{%s}{%s}{%s}\n' % (lang+k, p['page'], p[lang+k]) )

for lang in 'EN','AF':
    tocs=''.join(toc[lang])
    ft.write('\\newcommand{\\PPtoc'+lang+'}{\n'+tocs+'}\n')

ft.close()
fo.close()

