#! /usr/bin/python3
import re
# Fri Mar 08 16:43:15 ~/src/kjvpar $ grep PPsq25928 parallel.tex ppenaf.coords

# oparallel.tex:\PPendlangEN\PPendlang\PPswlang\PPnewlang\PPnewlangAF\PPverse{4}{Matthéüs
# 1:4}{PPsq25928}{en Ram die vader van Ammínadab, en Ammínadab die vader van
# Nagson, en Nagson die vader van Salmon,}
parallelfd=open('parallel.tex','r')

# ppenaf.coords:PPsq25928,Matthéüs 1:4,x=210.59714pt, y=391.37599pt,3
coords=open('ppenaf.coords','r')

ref2verse={'AF':{},'EN':{}}
ref2lang={}
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
parallelfd.close()

def iteraterefs(coords):
    # Find first and last reference on each page
    pages = {}
    coords_re=re.compile(r'(PP.*?),(.*?),x=(.*?)pt, y=(.*?)pt,(\d+)')
    for line in coords:
        coords_m = coords_re.search(line)
        if not coords_m: continue
        ppref,bibref,x,y,page = coords_m.groups()
        yield (ppref,bibref,x,y,page)

data={}        
for ppref,bibref,x,y,page in iteraterefs(coords):
    p=data.setdefault(page,{})
    p['page']=int(page)
    lang=ref2lang[ppref]
    rightname = lang+'right'
    leftname = lang+'left'
    if leftname not in p: p[leftname]=bibref
    p[rightname]=bibref

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
        bookleft=bookleft.upper()
        bookright=bookright.upper()
        rangekey=lang+'range'
        if bookleft+chapterleft==bookright+chapterright:
            p[rangekey]=f'{bookleft} {chapterleft}'.strip()
        else:
            if bookleft==bookright: 
                if chapterleft==chapterright:
                    p[rangekey]=f'{bookleft} {chapterleft}'.strip()
                else:
                    p[rangekey]=f'{bookleft} {chapterleft} - {chapterright}'
            else:
                # If we have multiple books, ignore all but the last in the title
                if chapterright in ('','1'):
                    rangeleftleft=''
                else:
                    rangeleftleft='1 - '
                p[rangekey]=f'{bookright} {rangeleftleft}{chapterright}'.strip() # strip because 1-chapter book is blank chapter

    fo.write('%(page)s,%(ENleft)s,%(AFleft)s,%(ENright)s,%(AFright)s,%(ENrange)s,%(AFrange)s\n' % p)
    
    for lang in 'EN','AF':
        # for k in 'left','right','range':
        for k in ( 'range', ):
            ft.write('\\ppsave{%s}{%s}{%s}\n' % (lang+k, p['page'], p[lang+k]) )

ft.close()
fo.close()

