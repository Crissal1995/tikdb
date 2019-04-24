import os, glob, pathlib, shutil
import re
import tarfile, zipfile
import requests
from bs4 import BeautifulSoup

# setup temp folder
root = pathlib.Path(os.getcwd())
tmpfold = root / "tikdb_tmpfold"
try: os.mkdir(tmpfold)
except OSError:
    print("[WARNING] Temp folder already created...")
    shutil.rmtree(tmpfold,True)
    os.mkdir(tmpfold)
os.chdir(tmpfold) # cwd: tmpfold

# download titledb
def parse_titledb():
    url = 'https://wiiubrew.org/wiki/Title_database'
    r = requests.get(url,timeout=60)
    if r.status_code != 200:
        print('Cannot connect to title database! Quitting...')
        shutil.rmtree(tmpfold,True)
        quit()
    soup = BeautifulSoup(r.text, 'html.parser')
    text = re.sub("[\":]+",'',soup.get_text())
    titles = []; names = []; regions = []
    title_pattern = re.compile(r'0005000\w-\w{8}')
    name_pattern = re.compile(r'\S([^\n]*)')
    second_name_pattern = re.compile(r'(?<=\n)\w[^\n\d](^WUP)+', re.I)
    fix_name_pattern = re.compile(r'[\\/:"*?<>|]+')
    reg_pattern = re.compile('(EUR)|(JAP)|(JPN)|(USA)|(ALL)', re.I)
    result = title_pattern.search(text,0)
    while result is not None:
        start_title, end_title = result.span()
        # search for the next title
        next_title_result = title_pattern.search(text,end_title)
        if next_title_result is None: next_title = len(text)
        else: next_title, _ = next_title_result.span()
        title = (text[start_title:end_title]).replace('-','')
        # parse name
        result = name_pattern.search(text,end_title,next_title)
        if result is None: 
            result = title_pattern.search(text,next_title)
            continue
        start_name, end_name = result.span()
        name = text[start_name:end_name]
        # parse region
        result = reg_pattern.search(text,end_name,next_title)
        if result is None: 
            result = title_pattern.search(text,next_title)
            continue
        start_reg, end_reg = result.span()
        region = (text[start_reg:end_reg]).upper()
        # parse possible second line name
        result = second_name_pattern.search(text,end_name,start_reg)
        if result is not None:
            start_sec_name, end_sec_name = result.span()
            name = name + ' ' + text[start_sec_name:end_sec_name]
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

print('Parsing titledb...')
titles, names, regions = parse_titledb()
print('Titledb parsed')

# download ticket db
def download_tickets():
    def download_tickets_from_vault():
        vaultdb = "vault.tar.gz"
        url = "http://vault.titlekeys.ovh/" + vaultdb
        r = requests.get(url)
        open(vaultdb, 'wb').write(r.content)
        tar = tarfile.open(vaultdb)
        tar.extractall()
        os.chdir('ticket') # cwd: tmpfold/ticket
    
    download_tickets_from_vault()

print('Downloading tickets...')
download_tickets()
print('Tickets downloaded')

# make region folders
regs = ['EUR','USA','JPN']
for reg in regs:
    try:
        os.mkdir(reg)
    except OSError:
        print("[WARNING] " + reg + " folder already created...")
        shutil.rmtree(reg,True)
        os.mkdir(reg)

# find matches
for tik in glob.glob('*.tik'):
    tik_name = tik.replace('.tik','').upper()
    try: index = titles.index(tik_name)
    except ValueError: continue # discard ticket [no game/upd/dlc]
    name = names[index]
    region = regions[index]
    if region == 'ALL': # 'all' region
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
        os.rename(tik, title_path / 'title.tik')

# all tickets moved into folders, time to zip
def zipdir(path, ziph):
    for root, _, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

print('Creating zip file, please wait...')
zipname = 'tikdb.zip'
zipf = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
for reg in regs:
    zipdir(reg,zipf)
zipf.close()
print('Zip file created')

# move zip into root and clean up
shutil.move(zipname, root / zipname)
os.chdir(root)
shutil.rmtree(tmpfold,True)
print('Done')