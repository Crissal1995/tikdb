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
root = pathlib.Path(os.getcwd())
tmpfold = root / "tikdb_tmpfold"
try: os.mkdir(tmpfold)
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
    titles = []; names = []; regions = []
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
        titles.append(title)
        names.append(name)
        regions.append(region)
        # get another title
        result = next_title_result
    return titles, names, regions

# fix names (different names for same game+upd+dlc)
def fix_names(titles, names, regions):
    for index, _ in enumerate(names):
        titleid = titles[index]
        type_titleid = titleid[:8]
        gameid = titleid[8:]
        if type_titleid in [titleids['dlc'],titleids['update']]:
            try: game_idx = titles.index(titleids['game'] + gameid)
            except ValueError: continue # no game linked to upd/dlc
            names[index] = names[game_idx]
            regions[index] = regions[game_idx]

print('Parsing titledb...')
titles, names, regions = parse_titledb()
fix_names(titles, names, regions)
print('Titledb parsed')

# download ticket db
def download_tickets():
    def download_tickets_from_vault():
        vaultdb = "vault.tar.gz"
        url = "http://vault.titlekeys.ovh/" + vaultdb
        r = requests.get(url)
        if r.status_code != 200:
            raise requests.HTTPError(f'Cannot download {vaultdb}!')            
        open(vaultdb, 'wb').write(r.content)
        tar = tarfile.open(vaultdb)
        tar.extractall()
        tar.close()
        os.remove(vaultdb)
        # search for tickets
        
        for dirpath, _, files in os.walk(tmpfold):
            tiks = [x for x in files if x[-4:].lower() == '.tik']
            if len(tiks) != 0:
                os.chdir(dirpath)
                return
        # if here, no tik found
        raise ValueError(f'Cannot find any tik files in {vaultdb}!')
    
    download_tickets_from_vault()

print('Downloading tickets...')
download_tickets()
print('Tickets downloaded')

# make region folders
regs = ['EUR','USA','JPN']
for reg in regs:
    try: os.mkdir(reg)
    except FileExistsError:
        print(f"[WARNING] {reg} folder was already created")
        shutil.rmtree(reg,True)
        os.mkdir(reg)

# find matches
def match_tiks():
    for tik in glob.glob('*.tik'):
        tik_name = tik.replace('.tik','').upper()
        try: index = titles.index(tik_name)
        except ValueError: continue # discard ticket [no game/upd/dlc]
        name = names[index]
        region = regions[index]
        if region == 'ALL': # 'ALL' region
            for reg in regs:
                reg_path = pathlib.Path(reg)
                name_path = reg_path / name
                title_path = name_path / tik_name
                try: os.mkdir(name_path) # same game can have multiple folders (dlcs and updates)
                except FileExistsError: pass
                os.mkdir(title_path)
                shutil.copyfile(tik, title_path / 'title.tik')
        else: # single region
            reg_path = pathlib.Path(region)
            name_path = reg_path / name
            title_path = name_path / tik_name
            try: os.mkdir(name_path) # same game can have multiple folders (dlcs and updates)
            except FileExistsError: pass
            os.mkdir(title_path)
            shutil.copyfile(tik, title_path / 'title.tik')

print('Matching titles...')
match_tiks()
print('Titles matched')

# all tickets moved into folders, time to zip
def zipdir(path, ziph):
    for dir, _, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(dir, file)) 

print('Creating zip file...')
zipname = 'tikdb.zip'
try: 
    import zlib
    comp = zipfile.ZIP_DEFLATED
except ImportError:
    comp = zipfile.ZIP_STORED
zipf = zipfile.ZipFile(zipname, 'w', compression=comp)
for reg in regs:
    zipdir(reg,zipf)
zipf.close()
print('Zip file created')

# move zip into root and clean up
shutil.move(zipname, root / zipname)
os.chdir(root)
shutil.rmtree(tmpfold,True)
print('Done')