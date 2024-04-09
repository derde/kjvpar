#! /usr/bin/python3

import re
import sys

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
    # \zref@newlabel{zPPEN25917}{\default{}\page{3}\abspage{3}}
    # \zref@newlabel{jPPEN25917}{\posx{4159018}\posy{32177230}} % -> y0
    # \zref@newlabel{kPPEN25917}{\posx{8691775}\posy{30932046}} % -> y1
    page_re=re.compile(r'newlabel\{([z])(PP...*?)\}.*\\page\{(\d+)\}')
    posy_re=re.compile(r'newlabel\{([jk])(PP...*?)\}.*\\posx\{(\d+)\}\\posy\{(\d+)\}')
    refinfo = {}
    for line in coords:
        page_m=page_re.search(line)
        posy_m=posy_re.search(line)
        if page_m:
            j,ppref,page = page_m.groups()
            refinfo[ppref]={'page': page}
        if posy_m:
            try:
                j,ppref,x,y = posy_m.groups()
                if j=='j':
                    refinfo[ppref]['x0']=int(x)
                    refinfo[ppref]['y0']=int(y)
                elif j=='k':
                    refinfo[ppref]['x1']=int(x)
                    refinfo[ppref]['y1']=int(y)
                else:
                    sys.stderr.write("bad ref "+ppref+'\n')
                refinfo['zz']=ppref[5:7]
                if 'y1' in refinfo[ppref] and 'y0' in refinfo[ppref]:
                    yield (ppref,refinfo[ppref])
            except KeyError:
                sys.stderr.write(f'Missing ref on page {page}\n')

data={}        
toc={'EN': [], 'AF': [] }
lasty={'EN': 0, 'AF': 0 }
fp=open('ppenaf.pararaphs.csv','w')
fp.write('bcv,ref,dy,meh\n')
for ppref,ref in iteraterefs(coords):
    zz=ppref[5:7]
    y=ref['y0']
    page=ref['page']
    bcv=ref2bcv[ppref] # book,chapter,verse
    p=data.setdefault(page,ref)
    p['page']=int(page)
    lang=ref2lang[ppref]
    rightname = lang+'right'
    leftname = lang+'left'
    if leftname not in p: p[leftname]=bcv
    p[rightname]=bcv
    
    # Calculate space before this paragraph
    space = lasty[zz] - ref['y0']
    lasty[zz]=ref['y1']

    dy = ref['y0']-ref['y1']
    fp.write(bcv+','+ppref+','+str(dy)+','+str(space)+'\n')

    if bcv.endswith(' 1:1'):
        book=bcv[:-4]
        toc[lang].append('\\PPtoc{'+book+'}{'+str(ref['page'])+'}\n')
fp.close()

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
    for lang in 'EN','AF': # Order matters ... as displayed
        if lang+'left' not in p: continue
        if lang+'right' not in p: continue
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
                    p[rangekey]=f'{BOOKLEFT} {chapterleft}\\,–\\,{chapterright}'
            else:
                # If we have multiple books, ignore all but the last in the title
                if chapterright in ('','1'):
                    rangeleftleft=''
                else:
                    rangeleftleft='1\\,–\\,'
                p[rangekey]=f'{BOOKRIGHT} {rangeleftleft}{chapterright}'.strip() # strip because 1-chapter book is blank chapter

    try:
        fo.write('%(page)s,%(ENleft)s,%(AFleft)s,%(ENright)s,%(AFright)s,%(ENrange)s,%(AFrange)s\n' % p)
    except KeyError:
        sys.stderr.write('Headings error on page %(page)s\n' % p)
    
    for lang in 'EN','AF':
        # for k in 'left','right','range':
        for k in ( 'range', ):
            try:
                ft.write('\\ppsave{%s}{%s}{%s}\n' % (lang+k, p['page'], p[lang+k]) )
            except KeyError:
                sys.stderr.write('Page range error on page %(page)s\n' % p)

for lang in 'EN','AF':
    tocs=''.join(toc[lang])
    ft.write('\\newcommand{\\PPtoc'+lang+'}{\n'+tocs+'}\n')

ft.close()
fo.close()

