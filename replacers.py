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
    ' '
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
    '<!--Links not needed per MOS:OVERLINK-->',
    '<ref>{{Cite web|url=http://historicplacesla.org/reports/302ad891-d563-49ee-a301-',
    '<!--Links not needed per MOS:OVERLINK--> ',
]
DEATH_PLACE_ELEMENTS = dict()

for element in DEATH_PLACE_ELEMENTS_LIST:
    DEATH_PLACE_ELEMENTS[element] = REPLACE_DEFAULT
