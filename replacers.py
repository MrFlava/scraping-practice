import re

REPLACE_DEFAULT = ''
REPLACE_BIRTH_PLACE_ELEMENTS_LIST = [' ', '[', ']', '|', ',']

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
    '<!--Pleasedonotaddanymoreoccupationstothelist', 'itislongenoughalready-->',
    '[[',
    ']]',
    'recordproducer',
    'artist<ref>Citeweb',
    'first=Robert',
    'author-link=RobertChristgau',
    'title=JohnLennon!Biography',
    'Songs',
    'Albums',
    'Death',
    'Facts',
    'url=https://www.britannica.com/biography/John-Lennon',
    'access-date=18February2024',
    'website=Britannica',
    'archive-date=19January2024',
    'archive-url=https://web.archive.org/web/20240119065307/https://www.britannica.com/biography/John-Lennon',
    'url-status=live</ref>',
    'peaceactivist',
    'last=Christgau',
    '&',
    'musicandfilmproducer',
    'Hlist',
    'radiopersonality',
    'tourmanager',
    'Recordingartist',
    'filmproducer',
    'musicalarranger',
    'Artistsandrepertoire',
    'ARrepresentative',
    'occupationhadbeenastheownerofLukesGuitars',
    'aguitarshopin[[Ramsgate]]', 'England',
    "sellingnewandusedmusicalinstruments.<ref>[http://lukes-guitar-shop.tripod.com/WebsiteofLukesGuitars].''Lukes-guitar-shop.tripod.com''",
    'Retrieved10March2017.</ref>',
    'aguitarshopinRamsgate',
    'Cityworker',
    'autoracer',
    'Christianminister',
    'filmdirector',
    'occupations=',
    'Musician;songwriter'
]

OCCUPATION_REPLACEMENTS = {
    '[[minister(christianity)|minister]]': 'minister',
    '|': ',',
    'recordproducer': 'record producer',
    'artist<ref>citeweb': 'artist',
    'peaceactivist': 'peace activist',
    'musicandfilmproducer': 'music and film producer',
    'radiopersonality': 'radio personality',
    'tourmanager': 'tour manager',
    'recordingartist': 'Recording artist',
    'filmproducer': 'Film producer',
    'musicalarranger': 'musical arranger',
    'artistsandrepertoire': 'Artists and repertoire',
    'arrepresentative': 'AR representative',
    'cityworker': 'City worker',
    'autoracer': 'auto racer',
    'christianminister': 'Christian minister',
    'filmdirector': 'film director',
    "[[philanthropyofmichaeljackson', 'philanthropist]]": 'philanthropist',
    'musician;songwriter': 'Musician-songwriter',
    'hlist': REPLACE_DEFAULT,
    'flatlist': REPLACE_DEFAULT,
    'occupation=': REPLACE_DEFAULT,
    'occupations=': REPLACE_DEFAULT,
}

DEATH_DATE_ELEMENTS_LIST = [
    '  ',
    'death date and age',
    'Death date and age',
    'death_date',
    '=',
    '{{',
    '}}',
    '|mf=yes',
    'dfyes',
    '[[PhilanthropyofMichaelJackson', 'philanthropist]]'
]

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
    '<!--LinksnotneededperMOS:OVERLINK-->',
    'Atseaoffthecoastof',
    '<!--"US"doesnottakefullstops/pointsinBritishEnglish;Harrison\'shousewasjustinsideLAcitylimits-->',
    '<ref>LosAngelesSentinel,September29,2004ObituaryofJamesLewis</ref>',
    '{{',
    '}}',
    'nowrap',
    'sfnStanton2003p102',
    '<refname"Obit"/><refname"Obit3"/>',
    '<!--InBritishEnglish,"US"ispreferredover"U.S."-->'
]

YEARS_ACTIVE_ELEMENTS_LIST = [
    '  ',
    '<ref>{{cite web| url = https://www.allmusic.com/artist/bob-dylan-mn0000066915/biography| title = Bob Dylan biography| author = Erlewine, Stephen Thomas| author-link=Stephen Thomas Erlewine|date = December 12, 2019| access-date = January 6, 2020| website=[[AllMusic]]',
    '|',
    '=',
    'years_active',
    '<ref>{{Cite web lastDaley firstLauren dateAugust 2, 2007 titleLast Man Standing: Jerry Lee at the Z urlhttps://www.southcoasttoday.com/article/20070802/entertain/708020326 access-dateSeptember 30, 2020 quote"He made his public debut in 1949 at 14, sitting in with a local country/western band in a Ford dealership parking lot." newspaperSouth Coast Today archive-dateOctober 11, 2020 archive-urlhttps://web.archive.org/web/20201011020956/https://www.southcoasttoday.com/article/20070802/entertain/708020326 url-statuslive }}</ref>',
    '<ref name"songsofsamcooke.com" />',
    '<!-- YYYY–YYYY (or –present) -->',
    '{{',
    '}}',
    'hlist',
    '19751980',
    '<ref name"Muse">cite book first1François last1Allard first2Richardlast2LecocqtitleMichael Jackson: All the Songs: The Story Behind Every Track year2018chapterDiana Ross: Godmother and Musepublisher[[Octopus Books]] isbn9781788401234 chapter-urlhttps://books.google.com/books?id4qJfDwAAQBAJ&pgPT378access-dateNovember 11, 2019 archive-dateAugust 1, 2020archive-urlhttps://web.archive.org/web/20200801014854/https://books.google.com/books?id4qJfDwAAQBAJ&pgPT378 url-statuslive</ref>',
    '1959–19931997–present',
    '&ndash;',
    'c. ',
    '(music career)<br />',
    'sfnMason2004p17',
    ' 1965–19771997–present',
    '<ref name"GQ">cite webauthorCharlie Burtonurlhttps://www.gq-magazine.co.uk/article/jacksons-legacy-jackson-5titleInside the Jackson machinedateFebruary 7, 2018access-dateOctober 24, 2019</ref>',
    '<ref name"GQ">cite webauthorCharlie Burtonurlhttps://www.gq-magazine.co.uk/article/jacksons-legacy-jackson-5titleInside the Jackson machinedateFebruary 7, 2018access-dateOctober 24, 2019archive-dateOctober 7, 2022archive-urlhttps://web.archive.org/web/20221007005527/https://www.gq-magazine.co.uk/article/jacksons-legacy-jackson-5url-statuslive</ref>',
    'ndash',
    '1966–19982003–20042013–2022',
    '1960–19791986–present',
    "<!--STOP editing this without a reliable source; Phillips's professional career began with Mamas and Papas in 1965 by all accounts. She was 13 years old in 1957, and living in Mexico at that time-->",
    '1965–as of2015altpresent',
]

GENRES_ELEMENTS = {
    "ContemporaryfolkmusicFolk": "Contemporary folk music",
    "rockmusic": "Rock music",
    "Gospelmusicgospel": "Gospel music",
    "Countrymusiccountry": "Country music",
    "traditionalpop": "Traditional pop",
    "blues": "Blues",
    "rockmusicrock": "Rock music",
    "RockmusicRock": "Rock music",
    "Popmusicpop": "Pop music",
    "RockMusicRock": "Rock music",
    "Rockandroll": "Rock & Roll",
    "Artrock": "Art rock",
    "glamrock": "Glam rock",
    "popmusicpop": "Pop music",
    "PopmusicPop": "Pop music",
    "Electronicmusicelectronic": "Electronic music",
    "classicalmusicclassical": "Classical music",
    "SoulmusicSoul": "Soul music",
    "rockabilly": "Rockabilly",
    "R&B": "R&B",
    "RhythmandbluesR&B": "R&B",
    "Blue-eyedsoulsoul": "Blue-eyed soul",
    "nowrapNewOrleansR&B": "New Orleans R&B",
    "rhythmandblues": "Rhythm and blues",
    "SoulmusicSoulrhythmandbluesR&Bfunk": "Soul, R&B, Funk",
    "SoulmusicSoulRhythmandbluesR&BGospelmusicgospel": "Soul, R&B, Gospel",
    "Rockandrollrhythmandbluessoulmusicsoulpopmusicpop": "Rock and roll,R&B, Soul, Pop music",
    "RockabillyrockandrollPopmusicpopcountryrock": "Rokabilly, Rock and roll, Pop music, Country rock",
    "jazz": "Jazz",
    "countrymusiccountry": "Country music",
    "ChansonFrenchchanson": "French chanson",
    "disco": "Disco",
    "Doo-wopRhythmandbluesR&B": "Doo-Wop, R&B",
    "softrock": "Soft rock",
    "folkrock": "Folk rock",
    "bluesrock": "Blues rock",
    "blue-eyedsoul": "Blue-eyed soul",
    "ska": "Ska music",
    "rocksteady": "Rocksteady",
    "Reggae": "Reggae",
    "folkmusicfolk": "Folk music",
    "Poprock": "Pop-rock",
    "CountrymusicCountry": "Country music",
    "RhythmandbluesR": "R&B",
    "RockandrollrockabillyWesternswing": "Rock and roll, Rockabilly, Western swing",
    "SoulmusicSoulRhythmandbluesR&BGospelmusicgospelfunk": "Soul music, R&B, Gospel, Funk",
    "Rockandrollrockabillypopmusicpop": "Rock and roll, Rockabilly, Pop music",
    "RockmusicRockpopmusicpopCountrymusiccountryrockandrollrockabilly": "Rock music, Pop, Country, Rock and Roll, Rockabilly",
    "Psychedelicrockbluesrocksoulmusicsoulblues": "Psychedelic rock, Blues rock, Soul music, Blues",
    "RockmusicRockPopmusicpopExperimentalmusicexperimental": "Rock music, Pop music, Experimental music",
    "Rockandrollrhythmandbluesgospelmusicgospelsoulmusicsoul": "Rock and roll, R&B, Gospel, Soul",
    "CountrymusicCountryrockandrollcountryrock": "Country music, Rock and roll, Country rock",
    "RockmusicRockprogressiverockbluesexperimentalmusicexperimentaljazzjazzfusionfusionclassicalmusicclassicalPopmusicpopavant-gardemusicavant-gardedoo-wopcomedymusiccomedyelectronicmusicelectronicmusiqueconcrète": "Rock, Progressive rock, Blues, Experimental music, Experimental jazz, Jazz fuzion, Classical music",
}

# python
# helper used to build replacement dicts from existing *LIST constants
def _normalize_key(s: str) -> str:
    return s.strip().lower()

def _build_replacements_from_list(list_items, replacements=None, default=REPLACE_DEFAULT):
    replacements = replacements or {}
    out = {}
    for item in list_items:
        key = _normalize_key(item)
        out[item] = replacements.get(key, default)
    return out

# specific replacements for years active (previously handled with many elifs)
YEARS_ACTIVE_REPLACEMENTS = {
    '19751980': '1980',
    '1959–19931997–present': '1959–1993 1997–present',
    '&ndash;': '-',
    ' 1965–19771997–present': '1965-1977 1997-present',
    'ndash': '-',
    '1960–19791986–present': '1960–1979 1986–present',
    '1966–19982003–20042013–2022': '1966–1998 2003–2004 2013–2022',
    '1965–as of2015altpresent': '1965-present',
}

# build the dicts using the helper (works for occupation, years active, birth/death/place lists)
REPLACE_BIRTH_PLACE_ELEMENTS = _build_replacements_from_list(REPLACE_BIRTH_PLACE_ELEMENTS_LIST)
REPLACE_OCCUPATION_ELEMENTS = _build_replacements_from_list(REPLACE_OCCUPATION_ELEMENTS_LIST, OCCUPATION_REPLACEMENTS)
DEATH_DATE_ELEMENTS = _build_replacements_from_list(DEATH_DATE_ELEMENTS_LIST)
DEATH_PLACE_ELEMENTS = _build_replacements_from_list(DEATH_PLACE_ELEMENTS_LIST)
YEARS_ACTIVE_ELEMENTS = _build_replacements_from_list(YEARS_ACTIVE_ELEMENTS_LIST, YEARS_ACTIVE_REPLACEMENTS)

def normalize_genre_string(genre_unparsed: str) -> str:
    genre_str = (genre_unparsed
                 .replace('Flatlist', '')
                 .replace('flatlist', '')
                 .replace('Hlist', '')
                 .replace('hlist', '')
                 .replace('genre', '')
                 .replace('=', '')
                 .replace('*', '')
                 .replace('[', '')
                 .replace(']', '')
                 .replace('{', '')
                 .replace('}', '')
                 .replace('|', ' ')
                 .replace(' ', '')
                 .replace('<ref>CitewebtitleJerryLeeLewisurlhttps://www.rockhall.com/inductees/jerry-lee-lewisaccess-dateSeptember4,2016websiteRockandRollHallofFameandMuseumarchive-dateOctober1,2021archive-urlhttps://web.archive.org/web/20211001212832/https://www.rockhall.com/inductees/jerry-lee-lewisurl-statuslive', '')
                 .replace('<ref>citeweblastSilvafirstCarlytitleRodStewartAnnouncesHe"sSwitchingMusicGenresurlhttps://www.msn.com/en-us/entertainment/news/rod-stewart-announces-he-s-switching-music-s/ar-AA1cB3el?liBBnb2ghwebsiteParadedate15June2023access-date9July2023viaMSN', '')
                 .replace('<ref>citeweburlhttps://www.allmusic.com/artist/roy-orbison-mn0000852007titleRoyOrbisonSongs,Albums,Reviews,Bio&MorewebsiteAllMusic', '')
                 .replace('<ref>JazzNorthernSoulhttps://lithub.com/dusty-springfield-reluctant-queen-of-blue-eyed-soul/DustySpringfieldqueenofblue-eyed-soulRetrieved12April2022</ref>', '')
                 .replace("<ref>citeweblastSilvafirstCarlytitleRodStewartAnnouncesHe'sSwitchingMusicGenresurlhttps://www.msn.com/en-us/entertainment/news/rod-stewart-announces-he-s-switching-music-s/ar-AA1cB3el?liBBnb2ghwebsiteParadedate15June2023access-date9July2023viaMSN", '')
                 .replace("<ref>citeweburlhttps://www.latimes.com/archives/la-xpm-1995-02-13-ca-31549-story.htmltitleBobMarleyFestivalSpreadsSome'RastamanVibration':Anniversary:Jamaicaconcertmarksthe50thbirthdayofthelatereggaeiconandpoet-musician.authorFreed,Kennethdate13February1995newspaperLosAngelesTimesaccess-date1August2019archive-date2August2019archive-urlhttps://web.archive.org/web/20190802064134/https://www.latimes.com/archives/la-xpm-1995-02-13-ca-31549-story.htmlurl-statuslive", '')
                 .replace('<refname"auto2">Citeweburlhttps://www.allmusic.com/artist/johnny-cash-mn0000816890titleJohnnyCash&#124;Biography,Albums,StreamingLinkswebsiteAllMusic', '')
                 .replace('<refname"Snapes-2019">citeweburlhttps://www.theguardian.com/music/2019/jul/08/stevie-wonder-kidney-transplant-british-summertime-festival-hyde-park-londontitleStevieWondertoundergokidneytransplantworkTheGuardianlocationLondonlastSnapesfirstLauradateJuly8,2019access-dateJuly26,2020', '')
                 )
    if genre_str.startswith('Rockmusicrock<refname"bio-allmusic1"'):
        genre_str = re.sub(r"['\"]", "", genre_str)
        genre_str = genre_str.replace('<refnamebio-allmusic1/><refnameconcertarchives>citeweburlhttps://www.concertarchives.org/bands/billy-joel--5workConcertArchivestitleBillyJoelsConcertHistoryaccess-dateOctober18,2020archive-dateNovember8,2020archive-urlhttps://web.archive.org/web/20201108053223/https://www.concertarchives.org/bands/billy-joel--5url-statuslive', "")

    if genre_str.startswith('<!--Donotaddslikeart/prog/jazz/experimental/symphonicrock.'):
        genre_str = genre_str.replace('<!--Donotaddslikeart/prog/jazz/experimental/symphonicrock.ThisinfoboxwouldbeenormousifeverystyleZappaeverplayedwasincluded.-->', '')

    return genre_str

