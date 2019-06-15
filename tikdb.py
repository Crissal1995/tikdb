import os, glob, pathlib, shutil
import re
import tarfile, zipfile
import requests

# setup struct for tids
base_titleid = '0005000'
titleids = {'game': base_titleid + '0',
            'demo': base_titleid + '2',
            'dlc': base_titleid + 'C',
            'update': base_titleid + 'E' }

# setup temp folder
root = os.getcwd()
tmpfold = "tikdb_tmpfold"
try: 
    os.mkdir(tmpfold)
except FileExistsError:
    print("[WARNING] Temp folder was already created")
    shutil.rmtree(tmpfold,True)
    os.mkdir(tmpfold)
os.chdir(tmpfold) # cwd: tmpfold

# download titledb
def parse_titledb():
    url = 'https://raw.githubusercontent.com/Crissal1995/tikdb/master/titledbs/wiiubrew'
    r = requests.get(url)
    if r.status_code != 200:
        raise requests.HTTPError('Cannot connect to title database!')
    text = r.text
    _titles = []; _names = []; _regions = []
    # compiling regex for speed
    title_pattern = re.compile(base_titleid + r'\w-\w{8}', re.I)
    name_pattern = re.compile(r'(?<=<td>)[^\n]*')
    fix_name_pattern = re.compile(r'[\\/:"*?<>|]+')
    reg_pattern = re.compile(r'(?<=<td>)(EUR)|(JAP)|(JPN)|(USA)|(ALL)', re.I)
    # first search
    result = title_pattern.search(text,0)
    while result is not None:
        start_title, end_title = result.span()
        # search for the next title (end limiter)
        next_title_result = title_pattern.search(text,end_title)
        if next_title_result is None: next_title_start = len(text)
        else: next_title_start, _ = next_title_result.span()
        # parse title
        title = text[start_title:end_title].upper().replace('-','')
        # check if title is valid, otherwise skip it
        if title[:8] not in titleids.values():
            result = next_title_result
            continue
        # parse name
        result = name_pattern.search(text,end_title,next_title_start)
        if result is None: 
            result = next_title_result
            continue
        start_name, end_name = result.span()
        name = text[start_name:end_name]
        # parse region
        result = reg_pattern.search(text,end_name,next_title_start)
        if result is None: 
            result = next_title_result
            continue
        start_reg, end_reg = result.span()
        region = text[start_reg:end_reg].upper()
        # fix name for win folders
        name = fix_name_pattern.sub('',name)
        # fix JAP region
        if region == 'JAP': region = 'JPN'
        # save title parsed
        _titles.append(title)
        _names.append(name)
        _regions.append(region)
        # get another title
        result = next_title_result
    return _titles, _names, _regions

# fix names (different names for same game+upd+dlc)
def fix_names(_titles, _names, _regions):
    for index, _ in enumerate(_names):
        titleid = _titles[index]
        type_titleid = titleid[:8]
        gameid = titleid[8:]
        if type_titleid in [titleids['dlc'],titleids['update']]:
            try: game_idx = _titles.index(titleids['game'] + gameid)
            except ValueError: continue # no game linked to upd/dlc
            _names[index] = _names[game_idx]
            _regions[index] = _regions[game_idx]

print('Parsing titledb...')
titles, names, regions = parse_titledb()
fix_names(titles, names, regions)
print('Titledb parsed')

# download ticket db
def download_tickets():
    def download_tickets_from_vault():
        vaultdb = "vault.tar.gz"
        url = "http://vault.titlekeys.ovh/" + vaultdb
        try:
            r = requests.get(url)
        except requests.exceptions.ConnectionError:
            raise requests.HTTPError('Cannot connect to {}, the site don\'t exist!'.format(url))
        if r.status_code != 200:
            raise requests.HTTPError('Cannot download {}!'.format(vaultdb))            
        open(vaultdb, 'wb').write(r.content)
        tar = tarfile.open(vaultdb)
        tar.extractall()
        tar.close()
        os.remove(vaultdb)
        # search for tickets
        for dirpath, _, files in os.walk(os.getcwd()):
            tiks = glob.glob(os.path.join(dirpath,'*.tik'))
            if tiks: # len(tiks) > 0
                os.chdir(dirpath)
                return
        # if here, no tik found
        raise ValueError('Cannot find any tik files in {}!'.format(vaultdb))
    
    try:
        download_tickets_from_vault()
    except ValueError:
        print('Cannot download tickets!')
        quit(1)

print('Downloading tickets...')
download_tickets()
print('Tickets downloaded')

# make region folders
regs = ['EUR','USA','JPN']
for reg in regs:
    try: os.mkdir(reg)
    except FileExistsError:
        print('[WARNING] {} folder was already created'.format(reg))
        shutil.rmtree(reg, ignore_errors=True)
        os.mkdir(reg)

# find matches
def match_tiks():
    def doit(region_game: str, game_name: str, tik_upper: str, tik_original: str):
        os.chdir(region_game) # (tiks)/(REG)/
        try: os.mkdir(game_name) # same game can have multiple folders (dlcs and updates)
        except FileExistsError: pass
        os.chdir(game_name) # (tiks)/REG/game_name/
        try: os.mkdir(tik_upper)
        except FileExistsError: return
        os.chdir('../..') # (tiks)/
        title_path = os.path.normpath(region_game + '/' + game_name + '/' + tik_upper)
        shutil.copyfile(tik_original, os.path.join(title_path, 'title.tik') )

    for tik in glob.glob('*.tik'):
        tik_name = tik.replace('.tik','').upper()
        try: index = titles.index(tik_name)
        except ValueError: continue
        name = names[index]
        region = regions[index]
        if region == 'ALL': # 'ALL' region
            for region in regs:
                doit(region, name, tik_name, tik)
        else: # single region
            doit(region, name, tik_name, tik)

print('Matching titles...')
match_tiks()
print('Titles matched')

def zip_all(_zipname: str):
    def zipdir(path, ziph):
        for directory, _, files in os.walk(path):
            for file in files:
                ziph.write(os.path.join(directory, file))
    try: 
        import zlib
        comp = zipfile.ZIP_DEFLATED
    except ImportError:
        comp = zipfile.ZIP_STORED
    zipf = zipfile.ZipFile(_zipname, 'w', compression=comp)
    for _reg in regs:
        zipdir(_reg,zipf)
    zipf.close()

print('Creating zip file...')
zipname = 'tikdb.zip'
zip_all(zipname)
print('Zip file created')

print('Cleaning...')
# move zip into root and clean up
shutil.move(zipname, os.path.join(root, zipname))
os.chdir(root)
shutil.rmtree(tmpfold, ignore_errors=True)
print('Done - Goodbye!')