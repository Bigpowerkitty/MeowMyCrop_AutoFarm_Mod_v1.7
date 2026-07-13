import os, struct, hashlib, shutil, json, zipfile, re
from pathlib import Path
import pefile, dnfile
from dncil.cil.body.reader import read_method_body_from_bytes

SRC = Path('/mnt/data/Assembly-CSharp.dll')
V15ROOT = Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.5')
ROOT = Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.6')
MODDIR = ROOT / 'ModFiles'
TOOLSDIR = ROOT / 'Tools'
SOURCEDIR = ROOT / 'Source'
if ROOT.exists(): shutil.rmtree(ROOT)
shutil.copytree(V15ROOT, ROOT)
for p in (MODDIR, TOOLSDIR, SOURCEDIR): p.mkdir(parents=True, exist_ok=True)

class IL:
    def __init__(self): self.items=[]
    def label(self,name): self.items.append(('label',name))
    def b(self,*xs): self.items.append(('bytes',bytes(xs)))
    def raw(self,bs): self.items.append(('bytes',bytes(bs)))
    def token(self,opcode,token): self.items.append(('bytes',bytes([opcode])+struct.pack('<I',token)))
    def i4(self,v): self.items.append(('bytes',b'\x20'+struct.pack('<i',v)))
    def i1(self,v): self.items.append(('bytes',b'\x1f'+struct.pack('<b',v)))
    def r4(self,v): self.items.append(('bytes',b'\x22'+struct.pack('<f',float(v))))
    def branch(self,opcode,label): self.items.append(('branch',opcode,label))
    def assemble(self):
        labels={}; pos=0
        for item in self.items:
            if item[0]=='label': labels[item[1]]=pos
            elif item[0]=='bytes': pos += len(item[1])
            elif item[0]=='branch': pos += 5
        out=bytearray(); pos=0
        for item in self.items:
            if item[0]=='label': continue
            if item[0]=='bytes': out.extend(item[1]); pos += len(item[1]); continue
            _,op,label=item
            rel=labels[label]-(pos+5)
            out.append(op); out.extend(struct.pack('<i',rel)); pos += 5
        return bytes(out)

def fat_body(code,max_stack=8,local_sig=0,init_locals=False):
    flags=0x3003 | (0x10 if init_locals else 0)
    body=struct.pack('<HHII',flags,max_stack,len(code),local_sig)+code
    body += b'\x00'*((4-len(body)%4)%4)
    return body

T={
 'Input.GetKeyDown':0x0A0000EB,
 'Time.frameCount':0x0A000282,
 'PlayerManager.Instance':0x0A000284,
 'PlayerManager.get_LocalPlayer':0x06000168,
 'Player.ClickStealBtn':0x06000402,
 'Player.ShowStealResult':0x0600040B,
 'DataManager.Instance':0x0A000028,
 'DataManager.SaveGameData':0x06000124,
 'DataManager.RemoveFruit':0x06000132,
 'DataManager.debugMode':0x040001C4,
 'MessageManager.Instance':0x060001D4,
 'MessageManager.Dispatch':0x060001D8,
 'KeyClickMessage.Obtain':0x06000229,
 'Player.isLocal':0x040002AE,
 'Player.flowerPot':0x040002B2,
 'Object.op_Equality':0x0A00004D,
 'FlowerPot.player':0x04000076,
 'FlowerPot.GetTotalFruitCount':0x06000057,
 'FlowerPot.HarvestFlower':0x06000050,
 'FlowerPot.PlantFlower':0x0600004F,
 'FlowerPot.plantPrefab':0x04000075,
 'FlowerPot.currentPlantConfig':0x0400007A,
 'FlowerPot.get_CurrentPlantConfigId':0x0600004B,
 'StealResultMessage.Obtain':0x0600026D,
 'FruitLostMessage.Obtain':0x06000216,
 'String.Format3':0x0A0001C6,
 'Debug.Log':0x0A0000ED,
 'Type.UInt64':0x01000109,
 'Type.Int32':0x010000E7,
 'US.PlayerStole':0x70002CD7,
 'Plant.get_IsMature':0x060003D3,
 'Plant.get_Player':0x060003D1,
 'Object.op_Inequality':0x0A00002A,
 'Player.get_BuffMultiplier':0x060003EF,
 'Plant.plantData':0x0400029F,
 'PlantSaveData.growthValue':0x040002D1,
 'Plant.SendGrowthProgressMessage':0x060003E1,
 'Plant.config':0x0400029D,
 'tPlantConfigExtension.GetStageIndex':0x0600098C,
 'Plant.SetStage':0x060003E0,
 'BaseCannedItem.ExchangeButton':0x0400043D,
 'BaseCannedItem._isExchanging':0x0400043A,
 'BaseCannedItem._cachedPoolConfig':0x0400043C,
 'BaseCannedItem.ExchangeCannedItem':0x060005AA,
 'BaseCannedItem.GetRequiredFruitIds':0x060005A6,
 'BaseCannedItem.CheckInventorySufficient':0x060005AC,
 'BaseCannedItem.UpdateTextColors':0x060005B1,
 'tPoolConfig.Count':0x040006C0,
 'List.get_Count':0x0A0000D4,
 'Selectable.set_interactable':0x0A000456,
 'tClothConfig.ctor':0x06000964,
 'tClothConfig.Rarity':0x0400068B,
}

def make_update_body():
    il=IL()
    # F6 toggles internal automatic key delivery. Physical input remains untouched.
    il.i4(287); il.token(0x28,T['Input.GetKeyDown']); il.branch(0x39,'after_toggle')
    il.b(0x02,0x25); il.token(0x7B,T['DataManager.debugMode']); il.b(0x16,0xFE,0x01); il.token(0x7D,T['DataManager.debugMode'])
    il.label('after_toggle')
    # F8 runs the same guaranteed local steal/lost simulation once.
    il.i4(289); il.token(0x28,T['Input.GetKeyDown']); il.branch(0x39,'after_manual')
    il.token(0x28,T['PlayerManager.Instance']); il.b(0x25); il.branch(0x3A,'has_pm')
    il.b(0x26); il.branch(0x38,'after_manual')
    il.label('has_pm')
    il.token(0x6F,T['PlayerManager.get_LocalPlayer']); il.b(0x25); il.branch(0x3A,'has_player')
    il.b(0x26); il.branch(0x38,'after_manual')
    il.label('has_player'); il.token(0x6F,T['Player.ClickStealBtn'])
    il.label('after_manual')
    # Internal A-key message every 6 frames; does not move/capture mouse.
    il.b(0x02); il.token(0x7B,T['DataManager.debugMode']); il.branch(0x3A,'after_auto_key')
    il.token(0x28,T['Time.frameCount']); il.b(0x1C,0x5D); il.branch(0x3A,'after_auto_key')
    il.token(0x28,T['MessageManager.Instance']); il.i1(65)
    il.token(0x28,T['KeyClickMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.label('after_auto_key')
    # Preserve original S quick-save.
    il.i1(115); il.token(0x28,T['Input.GetKeyDown']); il.branch(0x39,'return')
    il.b(0x02); il.token(0x28,T['DataManager.SaveGameData'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=4)

def make_steal_body():
    # Guaranteed offline pair for any mature crop with >=1 fruit.
    # StealResultMessage is dispatched while isLocal=false so Steam stats receive it
    # without Player.HandleMessage granting the fruit twice. Then ShowStealResult is
    # called directly for the visible +1 reward. RemoveFruit(-1) simulates one fruit
    # lost from the local crop; FruitLostMessage updates the lost-fruit statistic.
    il=IL()
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.b(0x14); il.token(0x28,T['Object.op_Equality']); il.branch(0x39,'has_pot'); il.b(0x2A)
    il.label('has_pot')
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.token(0x6F,T['FlowerPot.GetTotalFruitCount']); il.b(0x16); il.branch(0x3D,'has_fruit'); il.b(0x2A)
    il.label('has_fruit')
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.token(0x28,T['FlowerPot.get_CurrentPlantConfigId']); il.b(0x0A) # local0 configId

    # Temporarily mark local player as remote while dispatching the result: Steam stats
    # see it, but Player.HandleMessage does not call ShowStealResult a second time.
    il.b(0x02,0x16); il.token(0x7D,T['Player.isLocal'])
    il.token(0x28,T['MessageManager.Instance'])
    il.b(0x16,0x6E,0x17,0x17,0x06,0x15)
    il.token(0x28,T['StealResultMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.b(0x02,0x17); il.token(0x7D,T['Player.isLocal'])

    # Visible local steal reward (+1), then subtract one to represent being stolen.
    il.b(0x02,0x06,0x17); il.token(0x28,T['Player.ShowStealResult'])
    il.token(0x28,T['DataManager.Instance']); il.b(0x06,0x17); il.token(0x6F,T['DataManager.RemoveFruit'])

    # Lost-fruit event/stat.
    il.token(0x28,T['MessageManager.Instance']); il.b(0x17,0x16,0x6E)
    il.token(0x28,T['FruitLostMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])

    # Always-visible Unity Player.log line.
    il.token(0x72,T['US.PlayerStole'])
    il.b(0x16,0x6E); il.token(0x8C,T['Type.UInt64'])
    il.b(0x17); il.token(0x8C,T['Type.Int32'])
    il.b(0x15); il.token(0x8C,T['Type.Int32'])
    il.token(0x28,T['String.Format3']); il.token(0x28,T['Debug.Log'])
    il.b(0x2A)
    return fat_body(il.assemble(),max_stack=8,local_sig=0x11000022,init_locals=True)

def make_check_auto_harvest_body():
    # Runs once per SecondMessage. Any mature crop with at least one fruit gets one
    # automatic steal + one automatic lost event before normal harvest/replant.
    il=IL()
    il.b(0x02); il.token(0x7B,T['FlowerPot.player']); il.b(0x14); il.token(0x28,T['Object.op_Equality']); il.branch(0x39,'has_player'); il.b(0x2A)
    il.label('has_player')
    il.b(0x02); il.token(0x7B,T['FlowerPot.player']); il.token(0x7B,T['Player.isLocal']); il.branch(0x3A,'local_player'); il.b(0x2A)
    il.label('local_player')
    il.b(0x02); il.token(0x28,T['FlowerPot.GetTotalFruitCount']); il.b(0x16); il.branch(0x3D,'has_fruit'); il.b(0x2A)
    il.label('has_fruit')
    il.b(0x02); il.token(0x7B,T['FlowerPot.player']); il.token(0x6F,T['Player.ClickStealBtn'])
    il.b(0x02); il.token(0x28,T['FlowerPot.HarvestFlower']); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=3)

def make_auto_replant_body():
    il=IL()
    il.b(0x02); il.token(0x7B,T['FlowerPot.currentPlantConfig']); il.branch(0x3A,'has_config'); il.b(0x2A)
    il.label('has_config')
    il.b(0x02,0x02); il.token(0x7B,T['FlowerPot.plantPrefab'])
    il.b(0x02); il.token(0x7B,T['FlowerPot.currentPlantConfig']); il.b(0x16)
    il.token(0x28,T['FlowerPot.PlantFlower']); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=4)

def make_grow_body(speed):
    il=IL()
    il.b(0x02); il.token(0x28,T['Plant.get_IsMature']); il.branch(0x39,'not_mature'); il.b(0x2A)
    il.label('not_mature')
    il.r4(1.0); il.b(0x0A)
    il.b(0x04); il.branch(0x39,'after_buff')
    il.b(0x02); il.token(0x28,T['Plant.get_Player']); il.b(0x14); il.token(0x28,T['Object.op_Inequality']); il.branch(0x39,'after_buff')
    il.b(0x02); il.token(0x28,T['Plant.get_Player']); il.token(0x6F,T['Player.get_BuffMultiplier']); il.b(0x0A)
    il.label('after_buff')
    il.b(0x02); il.token(0x7B,T['Plant.plantData']); il.b(0x25); il.token(0x7B,T['PlantSaveData.growthValue'])
    il.b(0x03,0x06,0x5A); il.r4(float(speed)); il.b(0x5A,0x58)
    il.token(0x7D,T['PlantSaveData.growthValue'])
    il.b(0x02); il.token(0x28,T['Plant.SendGrowthProgressMessage'])
    il.b(0x02); il.token(0x7B,T['Plant.config'])
    il.b(0x02); il.token(0x7B,T['Plant.plantData']); il.token(0x7B,T['PlantSaveData.growthValue'])
    il.b(0x69); il.token(0x28,T['tPlantConfigExtension.GetStageIndex']); il.b(0x0B)
    il.b(0x02,0x07); il.token(0x28,T['Plant.SetStage']); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=4,local_sig=0x11000030,init_locals=True)


def make_auto_can_update_button_body():
    # Start can exchange automatically whenever the original sufficiency test passes.
    il=IL()
    il.b(0x02); il.token(0x7B,T['BaseCannedItem.ExchangeButton']); il.b(0x14)
    il.token(0x28,T['Object.op_Equality']); il.branch(0x39,'has_button'); il.b(0x2A)
    il.label('has_button')
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._isExchanging']); il.branch(0x39,'check_inventory')
    il.b(0x02); il.token(0x7B,T['BaseCannedItem.ExchangeButton']); il.b(0x16)
    il.token(0x6F,T['Selectable.set_interactable']); il.b(0x2A)
    il.label('check_inventory')
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.GetRequiredFruitIds']); il.b(0x0A)
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig']); il.branch(0x39,'set_false')
    il.b(0x06); il.token(0x6F,T['List.get_Count']); il.b(0x16); il.branch(0x3E,'set_false')
    il.b(0x02,0x06,0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig'])
    il.token(0x7B,T['tPoolConfig.Count']); il.token(0x6F,T['BaseCannedItem.CheckInventorySufficient'])
    il.b(0x0B); il.branch(0x38,'apply_state')
    il.label('set_false'); il.b(0x16,0x0B)
    il.label('apply_state')
    il.b(0x02); il.token(0x7B,T['BaseCannedItem.ExchangeButton']); il.b(0x07)
    il.token(0x6F,T['Selectable.set_interactable'])
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.UpdateTextColors'])
    il.b(0x07); il.branch(0x39,'return')
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.ExchangeCannedItem'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=4,local_sig=0x11000131,init_locals=True)

def make_legendary_cloth_config_body():
    # Construct the original config and locally override Rarity to Legendary (4).
    il=IL()
    il.b(0x02); il.token(0x73,T['tClothConfig.ctor']); il.b(0x25,0x1A)
    il.token(0x7D,T['tClothConfig.Rarity']); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=3)

def method_info(dn,type_name,method_name):
    for td in dn.net.mdtables.TypeDef:
        if str(td.TypeName)==type_name:
            for mi in td.MethodList:
                if str(mi.row.Name)==method_name:
                    return mi.row.Rva, mi.row.struct.get_file_offset()
    raise KeyError((type_name,method_name))

def patch(speed,outfile):
    raw=bytearray(SRC.read_bytes())
    pe=pefile.PE(data=bytes(raw),fast_load=False)
    text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text')
    rsrc=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.rsrc')
    reloc=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.reloc')
    old_text_raw=text.SizeOfRawData
    insert_at=text.PointerToRawData+old_text_raw
    insert_size=0x1000
    assert text.VirtualAddress+old_text_raw+insert_size <= rsrc.VirtualAddress
    raw[insert_at:insert_at]=b'\0'*insert_size
    def w32(off,val): raw[off:off+4]=struct.pack('<I',val)
    th=text.get_file_offset(); rh=rsrc.get_file_offset(); reh=reloc.get_file_offset()
    w32(th+8,text.Misc_VirtualSize+insert_size)
    w32(th+16,text.SizeOfRawData+insert_size)
    w32(rh+20,rsrc.PointerToRawData+insert_size)
    w32(reh+20,reloc.PointerToRawData+insert_size)
    dn=dnfile.dnPE(str(SRC))
    cursor=0
    def place(body):
        nonlocal cursor
        cursor=(cursor+3)&~3
        off=insert_at+cursor; rva=text.VirtualAddress+old_text_raw+cursor
        raw[off:off+len(body)]=body; cursor += len(body)
        return rva
    entries=[
        ('DataManager','Update',make_update_body()),
        ('Player','ClickStealBtn',make_steal_body()),
        ('Plant','Grow',make_grow_body(speed)),
        ('FlowerPot','CheckAutoHarvest',make_check_auto_harvest_body()),
        ('FlowerPot','AutoReplantAfterHarvest',make_auto_replant_body()),
        ('BaseCannedItem','UpdateButtonState',make_auto_can_update_button_body()),
        ('tClothConfig','DeserializetClothConfig',make_legendary_cloth_config_body()),
    ]
    for typ,name,body in entries:
        rva=place(body); _,fieldoff=method_info(dn,typ,name); w32(fieldoff,rva)
    assert cursor < insert_size
    outfile.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

speeds=[1,2,5,10,20,50]
hashes={}
for s in speeds:
    out=MODDIR/f'Assembly-CSharp_{s}x.dll'
    hashes[str(s)]=patch(s,out)
orig_hash=hashlib.sha256(SRC.read_bytes()).hexdigest()
v15_hashes=json.loads((V15ROOT/'hashes.json').read_text(encoding='utf-8-sig'))['variants']
(ROOT/'hashes.json').write_text(json.dumps({'original':orig_hash,'variants':hashes,'legacy_v15':v15_hashes},indent=2),encoding='utf-8')

# Static validation.
def validate(path,speed):
    raw=path.read_bytes(); pe=pefile.PE(data=raw); dn=dnfile.dnPE(str(path))
    parsed={}
    for typ,name in [('DataManager','Update'),('Player','ClickStealBtn'),('Plant','Grow'),('FlowerPot','CheckAutoHarvest'),('FlowerPot','AutoReplantAfterHarvest'),('BaseCannedItem','UpdateButtonState'),('tClothConfig','DeserializetClothConfig')]:
        rva,_=method_info(dn,typ,name); off=pe.get_offset_from_rva(rva)
        b=read_method_body_from_bytes(raw[off:off+5000]); assert b.code_size>0, (path,typ,name)
        parsed[(typ,name)]=b
    auto_toks=[i.operand.value for i in parsed[('FlowerPot','CheckAutoHarvest')].instructions if hasattr(i.operand,'value')]
    assert T['Player.ClickStealBtn'] in auto_toks and T['FlowerPot.HarvestFlower'] in auto_toks
    steal_toks=[i.operand.value for i in parsed[('Player','ClickStealBtn')].instructions if hasattr(i.operand,'value')]
    for tok in [T['StealResultMessage.Obtain'],T['Player.ShowStealResult'],T['DataManager.RemoveFruit'],T['FruitLostMessage.Obtain'],T['Debug.Log']]:
        assert tok in steal_toks, (path,tok)
    assert any(str(i.opcode)=='ldc.r4' and abs(float(i.operand)-float(speed))<1e-6 for i in parsed[('Plant','Grow')].instructions)
    can_toks=[i.operand.value for i in parsed[('BaseCannedItem','UpdateButtonState')].instructions if hasattr(i.operand,'value')]
    for tok in [T['BaseCannedItem.CheckInventorySufficient'],T['BaseCannedItem.ExchangeCannedItem'],T['Selectable.set_interactable']]:
        assert tok in can_toks, (path,tok)
    rarity_body=parsed[('tClothConfig','DeserializetClothConfig')]
    rarity_toks=[i.operand.value for i in rarity_body.instructions if hasattr(i.operand,'value')]
    assert T['tClothConfig.ctor'] in rarity_toks and T['tClothConfig.Rarity'] in rarity_toks
    assert any(str(i.opcode)=='ldc.i4.4' for i in rarity_body.instructions)
for s in speeds: validate(MODDIR/f'Assembly-CSharp_{s}x.dll',s)

# Update manager from v1.5.
ps1=(V15ROOT/'Tools'/'ModManager.ps1').read_text(encoding='utf-8-sig')
def map_block(name,m):
    lines=[f'${name} = @{{']
    for k in ['1','2','5','10','20','50']: lines.append(f'    "{k}" = "{m[k]}"')
    lines.append('}')
    return '\n'.join(lines)
ps1=re.sub(r'\$variantHashes = @\{.*?\n\}',map_block('variantHashes',hashes),ps1,count=1,flags=re.S)
idx=ps1.find('$legacyV14Hashes = @{')
ps1=ps1[:idx]+map_block('legacyV15Hashes',v15_hashes)+'\n\n'+ps1[idx:]
needle='function Detect-Legacy-V14-Speed([string]$Hash) {'
pos=ps1.find(needle); end=ps1.find('\n}\n',pos)+3
block=ps1[pos:end]
block15=block.replace('Detect-Legacy-V14-Speed','Detect-Legacy-V15-Speed').replace('$legacyV14Hashes','$legacyV15Hashes')
ps1=ps1[:pos]+block15+'\n'+ps1[pos:]
ps1=ps1.replace('$legacyV14Speed = Detect-Legacy-V14-Speed $currentHash', '$legacyV14Speed = Detect-Legacy-V14-Speed $currentHash\n    $legacyV15Speed = Detect-Legacy-V15-Speed $currentHash')
ps1=ps1.replace('($legacyV14Speed -eq 0) -and (-not $isLegacyV10)', '($legacyV14Speed -eq 0) -and ($legacyV15Speed -eq 0) -and (-not $isLegacyV10)')
needle='    if ($legacyV14Speed -gt 0) {'
insert15='''    if ($legacyV15Speed -gt 0) {
        Write-Host "Detected v1.5 (${legacyV15Speed}x). v1.6 adds automatic can opening and local Legendary/orange decoration rarity." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.5 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.6.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.5 backup hash is unexpected. It was not overwritten for safety.' }
    }
'''
ps1=ps1.replace(needle,insert15+needle,1)
ps1=ps1.replace('$defaultSpeed = if ($installedSpeed -gt 0) { $installedSpeed } elseif ($legacyV14Speed -gt 0) { $legacyV14Speed }', '$defaultSpeed = if ($installedSpeed -gt 0) { $installedSpeed } elseif ($legacyV15Speed -gt 0) { $legacyV15Speed } elseif ($legacyV14Speed -gt 0) { $legacyV14Speed }')
ps1=ps1.replace('MOD Manager v1.5', 'MOD Manager v1.6')
ps1=ps1.replace('known v1.0/v1.2/v1.3/v1.4/v1.5 MOD file', 'known v1.0/v1.2/v1.3/v1.4/v1.5/v1.6 MOD file')
ps1=ps1.replace('upgraded directly to v1.5', 'upgraded directly to v1.6')
ps1=ps1.replace('then install v1.5', 'then install v1.6')
ps1=ps1.replace('v1.5 will guarantee', 'v1.6 will preserve')
ps1=ps1.replace('v1.5 will repair', 'v1.6 will repair')
ps1=ps1.replace("'Meow My Crop! AutoFarm MOD v1.5'", "'Meow My Crop! AutoFarm MOD v1.6'")
ps1=ps1.replace("'AutomaticBeingStolen=Once per mature crop cycle, including one-fruit crops',", "'AutomaticBeingStolen=Once per mature crop cycle, including one-fruit crops',\n        'AutomaticCanOpening=Enabled whenever a can has sufficient required fruit',\n        'DecorationRarityOverride=Local Legendary/orange display and classification',")
ps1=ps1.replace("$verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MOD v1.5 installed' }", "$verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MOD v1.6 installed' }")
old_success="Show-Result \"$verb successfully.`nKeyboard/mouse growth input repaired.`nGrowth speed: ${speed}x`n`nF6: pause/resume automatic key delivery`nAutomatic steal + automatic being-stolen: guaranteed once per mature crop cycle`nF8: manual diagnostic trigger`n`nSelect a crop and plant it once; later harvests will replant the same crop automatically.\""
new_success="Show-Result \"$verb successfully.`nKeyboard/mouse growth input repaired.`nGrowth speed: ${speed}x`n`nAutomatic can opening: enabled`nDecoration rarity: local Legendary/orange override`nF6: pause/resume automatic key delivery`nAutomatic steal + automatic being-stolen: guaranteed once per mature crop cycle`nF8: manual diagnostic trigger`n`nOpen the can page once. Every can with enough fruit will be opened automatically until materials run out.\""
ps1=ps1.replace(old_success,new_success)
(TOOLSDIR/'ModManager.ps1').write_text('\ufeff'+ps1,encoding='utf-8')

for fname in ['1_INSTALL_MOD.cmd','2_CHANGE_SPEED.cmd','3_UNINSTALL_MOD.cmd']:
    p=ROOT/fname; txt=p.read_text(encoding='ascii')
    txt=txt.replace('v1.5','v1.6')
    if fname=='1_INSTALL_MOD.cmd':
        txt=txt.replace('Automatic steal/lost events now also work for one-fruit crops.', 'Adds automatic can opening and local Legendary/orange decoration rarity.')
    p.write_text(txt,encoding='ascii',newline='')

readme='''Meow My Crop!（喵了个菜！）AutoFarm MOD v1.6
================================================

新增功能
--------
1. 自动开罐
   - 打开一次“罐头/开罐”页面即可。
   - 只要当前罐头所需果实足够，MOD 会自动执行游戏内部的开罐流程。
   - 每次交换完成后继续检查并开下一罐，直到材料不足。
   - 普通罐头和活动罐头都会套用自动逻辑。

2. 橙色（Legendary）装饰品质
   - 游戏加载装饰配置时，本地统一把 Rarity 覆盖为 Legendary（枚举值 4）。
   - 开罐获得的装饰会在本地界面按橙色品质显示和分类。
   - 已拥有装饰的本地品质显示也会变为橙色。

重要说明
--------
罐头兑换调用 Steam Inventory，服务器实际发放的物品 definitionId 仍由 Steam/游戏服务器决定。
本 MOD 只覆盖客户端的装饰品质显示与本地分类，不能把服务器库存中的普通物品真正改造成可交易的传奇物品。

保留功能
--------
- 指定作物种一次后自动收获并持续补种同一种。
- 1x / 2x / 5x / 10x / 20x / 50x 生长速度。
- 自动内部按键输送，不移动、不抢占鼠标。
- 自动偷菜与自动被偷菜，每个成熟周期一次。
- F6：暂停/恢复自动按键输送。
- F8：手动测试一次偷菜＋被偷菜事件。

安装
----
1. 完全退出游戏。
2. 解压后双击 1_INSTALL_MOD.cmd。
3. 可直接覆盖 v1.5；安装器会识别当前倍率并默认保留。
4. 进入游戏并打开一次罐头页面，自动开罐即开始工作。

注意
----
自动开罐会持续消耗满足条件的果实，直到不足。
本包基于你提供的 Assembly-CSharp.dll 生成，并完成 PE、元数据、补丁方法体、关键调用和六种倍率 DLL 的静态校验。当前环境不能直接启动 Windows 游戏实机运行。
'''
(ROOT/'README_CN.txt').write_text('\ufeff'+readme,encoding='utf-8')
notes=f'''v1.6 implementation notes
- Preserves all v1.5 farming, growth, steal/lost and internal-key patches.
- BaseCannedItem.UpdateButtonState calls ExchangeCannedItem whenever the original inventory-sufficiency check is true.
- tClothConfig.DeserializetClothConfig constructs the original config and then sets Rarity=4 (Legendary) locally.
- Steam Inventory remains authoritative for the actual item definition; this patch changes local display/classification only.

SHA256 variants:
{json.dumps(hashes,indent=2)}
'''
(SOURCEDIR/'PATCH_NOTES.txt').write_text(notes,encoding='utf-8')
shutil.copy2('/mnt/data/build_meow_v16.py',SOURCEDIR/'build_meow_v16.py')

zip_path=Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.6.zip')
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(ROOT.rglob('*')):
        if f.is_file(): z.write(f,Path(ROOT.name)/f.relative_to(ROOT))
print(json.dumps({'root':str(ROOT),'zip':str(zip_path),'hashes':hashes},ensure_ascii=False,indent=2))
