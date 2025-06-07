REPLACE_DEFAULT = ''
REPLACE_BIRTH_PLACE_ELEMENTS_LIST = [' ', '[', ']', '|', ',']
REPLACE_BIRTH_PLACE_ELEMENTS = dict()
REPLACE_OCCUPATION_ELEMENTS_LIST = [
    '  ',
    'hlist',
    ' ',
    'occupation=',
    'Flatlist',
    'flatlist',
    '{{',
    '}}',
    '<!--Pleasedonotaddtothislistwithoutfirstdiscussingyourproposalonthetalkpage.-->',
    '[[Minister(Christianity)|minister]]',
    '|',
    '<!--Pleasedonotaddanymoreoccupationstothelist', 'itislongenoughalready-->'
]
REPLACE_OCCUPATION_ELEMENTS = dict()
DEATH_DATE_ELEMENTS_LIST = [
    '  ',
    'death date and age',
    'Death date and age',
    'death_date',
    '=',
    '{{',
    '}}',
    '|mf=yes'
]
DEATH_DATE_ELEMENTS = dict()

for element in REPLACE_BIRTH_PLACE_ELEMENTS_LIST:
        REPLACE_BIRTH_PLACE_ELEMENTS[element] = REPLACE_DEFAULT

for element in REPLACE_OCCUPATION_ELEMENTS_LIST:
    if element == '[[Minister(Christianity)|minister]]':
        REPLACE_OCCUPATION_ELEMENTS[element] = 'minister'
    elif element == '|':
        REPLACE_OCCUPATION_ELEMENTS[element] = ','

    else:
        REPLACE_OCCUPATION_ELEMENTS[element] = REPLACE_DEFAULT

for element in DEATH_DATE_ELEMENTS_LIST:
    DEATH_DATE_ELEMENTS[element] = REPLACE_DEFAULT

DEATH_PLACE_ELEMENTS_LIST = [
    ' ',
    'near',
    'death_place',
    '=',
    '[[',
    ']]',
    '<!-- Per MOS:U.S., "the use or non-use of periods (full stops) should also be consistent with',
    '<!-- "US" does not take full stops/points in British English -->',
    '|',
    '<!-- No need to list boroughs -->',
    '<!-- DO NOT LINK this, see [[MOS:OVERLINK]]. -->',
    '<!-- DO NOT LINK this, see MOS:OVERLINK. -->',
    '<!--Links not needed per MOS:OVERLINK-->',
    '<ref>{{Cite web|url=http://historicplacesla.org/reports/302ad891-d563-49ee-a301-',
    '<!--Links not needed per MOS:OVERLINK--> ',
    '<ref>{{Cite weburlhttp://historicplacesla.org/reports/302ad891-d563-49ee-a301-3a8ec8d687cdtitleReport – HPLA}}</ref>',
    'Georgia (U.S. state)',
    'Georgia(U.S.state)',
    '<ref>{{Citeweburlhttp://historicplacesla.org/reports/302ad891-d563-49ee-a301-3a8ec8d687cdtitleReport–HPLA}}</ref>',
    '<!--LinksnotneededperMOS:OVERLINK-->',
    '<!--DONOTLINKthis,seeMOS:OVERLINK.-->',
    '<!--Noneedtolistboroughs-->',
    '<!--"US"doesnottakefullstops/pointsinBritishEnglish-->',
    "theuseornon-useofperiods(fullstops)shouldalsobeconsistentwithothercountryabbreviationsinthesamearticle(thus\'theUS,UK,andUSSR\',not\'theU.S.,UK,andUSSR\').",
    '<!--LinksnotneededperMOS:OVERLINK-->'

]
DEATH_PLACE_ELEMENTS = dict()

for element in DEATH_PLACE_ELEMENTS_LIST:
    DEATH_PLACE_ELEMENTS[element] = REPLACE_DEFAULT

YEARS_ACTIVE_ELEMENTS_LIST = [
    ' '
    "<ref>{{cite web| url = https://www.allmusic.com/artist/bob-dylan-mn0000066915/biography| title = Bob Dylan biography| author = Erlewine, Stephen Thomas| author-link=Stephen Thomas Erlewine|date = December 12, 2019| access-date = January 6, 2020| website=[[AllMusic]]}}</ref>",
    '|',
    '='
]