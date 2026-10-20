import urllib.request, struct, json, pathlib, xml.etree.ElementTree as ET

base=pathlib.Path('/opt/ui-skill-lab-20261020/android-validation')
root=ET.parse(base/'evidence/android-repository.xml').getroot()
packages=[]
for p in root.findall('remotePackage'):
    if p.get('path') not in ['ndk;27.0.12077973','platforms;android-36','build-tools;35.0.0','cmdline-tools;latest','platform-tools']:
        continue
    for a in p.findall('./archives/archive'):
        if a.findtext('host-os') not in [None,'linux']:
            continue
        packages.append({'package':p.get('path'),'url':'https://dl.google.com/android/repository/'+a.findtext('./complete/url'),'size':int(a.findtext('./complete/size')),'sha1':a.findtext('./complete/checksum'),'license':p.find('uses-license').get('ref')})

def part(url,start,end):
    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
    with urllib.request.urlopen(req,timeout=45) as r:
        if r.status!=206: raise RuntimeError(f'Expected 206, got {r.status}, aborting full download')
        return r.read()

for p in packages:
    try:
        tail=part(p['url'],p['size']-65536,p['size']-1)
        i=tail.rfind(b'PK\x05\x06')
        e=struct.unpack_from('<4s4H2LH',tail,i)
        cdsize,offset=e[5],e[6]
        cd=part(p['url'],offset,offset+cdsize-1)
        pos=0; total=0; count=0
        while cd[pos:pos+4]==b'PK\x01\x02':
            v=struct.unpack_from('<4s6H3L5H2L',cd,pos)
            total+=v[9]; count+=1
            pos+=46+v[10]+v[11]+v[12]
        p.update(uncompressed_bytes=total,zip_entries=count,central_directory_bytes=cdsize)
    except Exception as exc:
        p['probe_error']=str(exc)
    print(json.dumps(p),flush=True)
(base/'evidence/package-budget.json').write_text(json.dumps(packages,indent=2)+'\n')
for l in root.findall('license'):
    (base/'evidence'/f"{l.get('id')}.txt").write_text(l.text or '')
