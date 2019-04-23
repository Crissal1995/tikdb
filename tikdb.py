import os, glob, pathlib, shutil
import tarfile, zipfile
import urllib.request

# todo: improve scraping from titledb
# parse bytes but cannot make them unicode chars
# so for now no jap games

# setup temp folder
layers = 0
tmpfold = "tikdb_tmpfold"
try:
    os.mkdir(tmpfold)
except OSError:
    print("[WARNING] Temp folder already created...")
    shutil.rmtree(tmpfold,True)
    os.mkdir(tmpfold)
os.chdir(tmpfold) # cwd: tmpfold
layers = 1

# setup agent crawlers
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1941.0 Safari/537.36')]
urllib.request.install_opener(opener)

# utility
def find_all(string, substr):
    start = 0
    while True:
        start = string.find(substr, start)
        if start == -1: return
        yield start
        start += len(substr)

# download title db
def parse_titledb():
    url = 'https://wiiubrew.org/wiki/Title_database'
    content_bytes = urllib.request.urlopen(url).read()
    content = str(content_bytes)
    content = content.replace(':','').replace('-','').replace("\\'","'")
    indeces = list(find_all(content,'000500'))
    titles = []; names = []; regions = []
    for i in range(len(indeces)):
        index = indeces[i]
        titleid = content[index:index+16]
        start_name = content.find('<td>',index+16) + 4
        end_name = content.find('\\n',start_name)
        name = content[start_name:end_name]
        # fix name from utf8 chars - temporary solution
        idx = name.find('\\x')
        while idx != -1:
            name = name[:idx] + name[idx+4:]
            if name == '': break
            elif name[0] in range(10):
                name = name[1:]
            idx = name.find('\\x')
        regs = ['EUR','USA','JAP','JPN','ALL','all']
        reg_idx = None
        if i+1 == len(indeces):
            next_idx = index
        else:
            next_idx = indeces[i+1]
        for j in range(len(regs)):
            result = content.find(regs[j],index,next_idx)
            if result != -1:
                reg_idx = j
                break
        if reg_idx == None:
            region = 'None'
        else:
            region = regs[reg_idx]
        titles.append(titleid)
        names.append(name)
        regions.append(region)
    return titles, names, regions

print('Parsing titledb...')
titles, names, regions = parse_titledb()
print('Titledb parsed')

# download ticket db
def download_tickets():
    def download_tickets_from_vault():
        vaultdb = "vault.tar.gz"
        url = "http://vault.titlekeys.ovh/" + vaultdb
        urllib.request.urlretrieve(url,vaultdb)
        tar = tarfile.open(vaultdb)
        tar.extractall()
        os.chdir('ticket') # cwd: tmpfold/ticket
        return 2
    
    return download_tickets_from_vault()

print('Downloading tickets...')
layers = download_tickets()
print('Tickets downloaded')

# make region folders
regs = ['EUR','USA']
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
    idx_tdb = titles.index(tik_name)
    name = names[idx_tdb]
    region = regions[idx_tdb]
    # fix double region for Japan
    if region == 'JAP':
        region = 'JPN'
    if region in regs: # if not 'jpn', 'all' or 'none' then work
        reg_path = pathlib.Path(region)
        name_path = reg_path / name
        title_path = name_path / tik_name
        try: os.mkdir(name_path)
        except OSError: pass
        os.mkdir(title_path)
        os.rename(tik, title_path / 'title.tik')
    else: # otherwise delete ticket
        os.remove(tik)

# all tickets moved into folders, time to zip
def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

print('Creating zip file, please wait...')
zipf = zipfile.ZipFile('tikdb.zip', 'w', zipfile.ZIP_DEFLATED)
for reg in regs:
    zipdir(reg,zipf)
zipf.close()
print('Zip file created')

# move zip into root and clean up
root = '../' * layers
shutil.move('tikdb.zip', root + 'tikdb.zip')
os.chdir(root)
shutil.rmtree(tmpfold,True)

print('Done')