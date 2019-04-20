%% Setup temp folder
mkdir 'tikdb_temp';
cd 'tikdb_temp';
%% Download vault db (tik)
% download vaultdb to disk
vaultdb_name = 'vault.tar.gz';
vaultdb_url = strcat('http://vault.titlekeys.ovh/',vaultdb_name);
websave(vaultdb_name,vaultdb_url);
% unzip vaultdb
untar(vaultdb_name);
% delete json folder and tar
rmdir 'json' s
delete(vaultdb_name);
% change name to 'ticket' to a region
movefile('ticket','EUR');
% change pwd
cd('EUR');
%% Download wiiubrew titledb
url = 'https://wiiubrew.org/wiki/Title_database';
content = webread(url);
indeces = strfind(content,'000500');
titles = strings(length(indeces),1);
names = strings(length(indeces),1);
for i = 1:length(indeces)
    start_title = indeces(i);
    titles(i,:) = content(start_title:start_title+16);
    start_name = indeces(i) + 28;
    end_name = strfind(content(start_name:start_name+200),'<');
    end_name = end_name(1);
    names(i,:) = content(start_name:start_name+end_name-3);
end
titles = erase(titles,'-');
names = erase(names,':'); % cause issues
%% Operate
tickets = ls('*.tik');
for i = 1:size(tickets,1)
    tik = erase(tickets(i,:),'.tik');
    % get name for parent fold
    index = find(strcmpi(titles,tik));
    pfold = names(index);
    % debug
    disp(strcat('ticket: ',tik));
    disp(strcat('index: ',num2str(index)));
    disp(strcat('pfold: ',pfold));
    disp(newline);
    % create folders for both game and titleid
    mkdir(pfold);
    mkdir(tik);
    % rename ticket to 'title.tik'
    movefile(tickets(i,:), 'title.tik');
    % move title.tik into titleid folder
    movefile('title.tik', tik);
    % move titleid folder into game folder
    movefile(tik, pfold);
end

cd ..
disp('zipping, please wait...');
% zip to put into wiiu usb helper method #2
zip('tikdb.zip','EUR');
%% Delete temp files
movefile('tikdb.zip','../tikdb.zip');
cd ..
rmdir 'tikdb_temp' s