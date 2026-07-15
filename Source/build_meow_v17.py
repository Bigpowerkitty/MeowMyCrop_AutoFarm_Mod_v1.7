import os, struct, hashlib, shutil, json, zipfile, re
from pathlib import Path
import pefile, dnfile
from dncil.cil.body.reader import read_method_body_from_bytes

SRC = Path('/mnt/data/Assembly-CSharp.dll')
V16ROOT = Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.6')
ROOT = Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.7')
MODDIR = ROOT / 'ModFiles'
TOOLSDIR = ROOT / 'Tools'
SOURCEDIR = ROOT / 'Source'
if ROOT.exists(): shutil.rmtree(ROOT)
shutil.copytree(V16ROOT, ROOT)
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
 'PlayerPrefs.GetInt':0x0A00044D,
 'PlayerPrefs.SetInt':0x0A00044E,
 'PlayerPrefs.Save':0x0A000614,
 'String.Format2':0x0A000068,
 'Debug.Log':0x0A0000ED,
 'Type.Int32':0x010000E7,
 'DataManager.SaveGameData':0x06000124,
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
 'Type.UInt64':0x01000109,
 'US.PlayerStole':0x70002CD7,
 'Player.ShowStealResult':0x0600040B,
 'DataManager.Instance':0x0A000028,
 'DataManager.RemoveFruit':0x06000132,
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
 'Player.ClickStealBtn':0x06000402,
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
 # Existing user strings reused as private PlayerPrefs keys / labels.
 'KEY_STEAL':0x70002999,          # "steal_request"
 'KEY_STEAL_DONE':0x700029B5,     # "steal_result"; per-crop-cycle marker
 'KEY_AUTOKEY':0x700050F8,        # "total_key_clicks"
 'KEY_AUTOFARM':0x70006CA1,       # "FarmingCat"
 'KEY_AUTOCAN':0x700017F6,        # "Canned"
 'FMT_STATE':0x70006979,           # "{0}: {1}"
}

# PlayerPrefs toggle helper. Defaults are enabled (1), and state persists.
def emit_toggle(il,keycode,key_token,label_token,after_label):
    il.i4(keycode); il.token(0x28,T['Input.GetKeyDown']); il.branch(0x39,after_label)
    # SetInt(key, 1 - GetInt(key, 1))
    il.token(0x72,key_token)
    il.b(0x17)
    il.token(0x72,key_token); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.b(0x59)
    il.token(0x28,T['PlayerPrefs.SetInt'])
    il.token(0x28,T['PlayerPrefs.Save'])
    # Debug.Log(String.Format("{0}: {1}", label, boxed-state))
    il.token(0x72,T['FMT_STATE'])
    il.token(0x72,label_token)
    il.token(0x72,key_token); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.token(0x8C,T['Type.Int32'])
    il.token(0x28,T['String.Format2'])
    il.token(0x28,T['Debug.Log'])
    il.label(after_label)

def emit_enabled_check(il,key_token,enabled_label,disabled_label=None):
    il.token(0x72,key_token); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt'])
    if disabled_label is None:
        il.branch(0x3A,enabled_label)
    else:
        il.branch(0x39,disabled_label)
        il.branch(0x38,enabled_label)


def make_update_body():
    il=IL()
    # Four independent, persistent switches.
    emit_toggle(il,286,T['KEY_STEAL'],T['KEY_STEAL'],'after_f5')     # F5
    emit_toggle(il,287,T['KEY_AUTOKEY'],T['KEY_AUTOKEY'],'after_f6') # F6
    emit_toggle(il,288,T['KEY_AUTOFARM'],T['KEY_AUTOFARM'],'after_f7') # F7
    emit_toggle(il,289,T['KEY_AUTOCAN'],T['KEY_AUTOCAN'],'after_f8') # F8

    # Internal A-key message every game frame, independently gated by F6 setting.
    il.token(0x72,T['KEY_AUTOKEY']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'after_auto_key')
    il.token(0x28,T['MessageManager.Instance']); il.i1(65)
    il.token(0x28,T['KeyClickMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.label('after_auto_key')

    # Preserve original S quick-save.
    il.i1(115); il.token(0x28,T['Input.GetKeyDown']); il.branch(0x39,'return')
    il.b(0x02); il.token(0x28,T['DataManager.SaveGameData'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=5)


def make_steal_body():
    # Full pause gate: when F5 setting is off, even any incidental ClickStealBtn call is ignored.
    il=IL()
    il.token(0x72,T['KEY_STEAL']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3A,'enabled'); il.b(0x2A)
    il.label('enabled')
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.b(0x14); il.token(0x28,T['Object.op_Equality']); il.branch(0x39,'has_pot'); il.b(0x2A)
    il.label('has_pot')
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.token(0x6F,T['FlowerPot.GetTotalFruitCount']); il.b(0x16); il.branch(0x3D,'has_fruit'); il.b(0x2A)
    il.label('has_fruit')
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.token(0x28,T['FlowerPot.get_CurrentPlantConfigId']); il.b(0x0A)

    il.b(0x02,0x16); il.token(0x7D,T['Player.isLocal'])
    il.token(0x28,T['MessageManager.Instance'])
    il.b(0x16,0x6E,0x17,0x17,0x06,0x15)
    il.token(0x28,T['StealResultMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.b(0x02,0x17); il.token(0x7D,T['Player.isLocal'])

    il.b(0x02,0x06,0x17); il.token(0x28,T['Player.ShowStealResult'])
    il.token(0x28,T['DataManager.Instance']); il.b(0x06,0x17); il.token(0x6F,T['DataManager.RemoveFruit'])

    il.token(0x28,T['MessageManager.Instance']); il.b(0x17,0x16,0x6E)
    il.token(0x28,T['FruitLostMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])

    il.token(0x72,T['US.PlayerStole'])
    il.b(0x16,0x6E); il.token(0x8C,T['Type.UInt64'])
    il.b(0x17); il.token(0x8C,T['Type.Int32'])
    il.b(0x15); il.token(0x8C,T['Type.Int32'])
    il.token(0x28,T['String.Format3']); il.token(0x28,T['Debug.Log'])
    il.b(0x2A)
    return fat_body(il.assemble(),max_stack=8,local_sig=0x11000022,init_locals=True)


def make_check_auto_harvest_body():
    # F5 and F7 are independent. A PlayerPrefs marker allows one steal/lost pair
    # per mature crop even when automatic harvesting is paused, avoiding repeats
    # every second while the mature crop remains in the pot.
    il=IL()
    il.b(0x02); il.token(0x7B,T['FlowerPot.player']); il.b(0x14); il.token(0x28,T['Object.op_Equality']); il.branch(0x39,'has_player'); il.b(0x2A)
    il.label('has_player')
    il.b(0x02); il.token(0x7B,T['FlowerPot.player']); il.token(0x7B,T['Player.isLocal']); il.branch(0x3A,'local_player'); il.b(0x2A)
    il.label('local_player')
    il.b(0x02); il.token(0x28,T['FlowerPot.GetTotalFruitCount']); il.b(0x16); il.branch(0x3D,'has_fruit'); il.b(0x2A)
    il.label('has_fruit')
    il.token(0x72,T['KEY_STEAL']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'skip_steal')
    il.token(0x72,T['KEY_STEAL_DONE']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3A,'skip_steal')
    il.b(0x02); il.token(0x7B,T['FlowerPot.player']); il.token(0x6F,T['Player.ClickStealBtn'])
    il.token(0x72,T['KEY_STEAL_DONE']); il.b(0x17); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.label('skip_steal')
    il.token(0x72,T['KEY_AUTOFARM']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'return')
    il.b(0x02); il.token(0x28,T['FlowerPot.HarvestFlower'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=3)


def make_auto_replant_body():
    il=IL()
    il.token(0x72,T['KEY_AUTOFARM']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3A,'farm_enabled'); il.b(0x2A)
    il.label('farm_enabled')
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
    # A growing crop starts a new steal/lost cycle.
    il.token(0x72,T['KEY_STEAL_DONE']); il.b(0x16); il.token(0x28,T['PlayerPrefs.SetInt'])
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
    # Always keep the original button state/manual operation. F8 only gates the
    # automatic call to ExchangeCannedItem.
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
    il.token(0x72,T['KEY_AUTOCAN']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'return')
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.ExchangeCannedItem'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=4,local_sig=0x11000131,init_locals=True)


def make_legendary_cloth_config_body():
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

speeds=[1,2,5,10,20,50,500]
hashes={}
for s in speeds:
    out=MODDIR/f'Assembly-CSharp_{s}x.dll'
    hashes[str(s)]=patch(s,out)
orig_hash=hashlib.sha256(SRC.read_bytes()).hexdigest()
v16_hashes=json.loads((V16ROOT/'hashes.json').read_text(encoding='utf-8-sig'))['variants']
pre_accel_v17_hashes={
    '1':'1d47232d1f9d31fe91f127316cefa888d976d9100e04886e1bab257bc2e93c7d',
    '2':'c41d61989e1bb3d2f2e8e7582cd8adc3181c26e2375c78efa4e523d6a4f8ae8b',
    '5':'6085f4fa43687758feb30a6be5eea5ff9dccf9b613a559af7f16c12eb822d04c',
    '10':'c46f0b0bc8ee810badb351657cc514b3da7cd5a37b9e787986e8603ec4b25dd9',
    '20':'9e0270b96bd1f22ec5acf8d02c8ac70e1af086a5373ed970c5985f678d2b97c4',
    '50':'cbce1e4ea53e8b7b41ead71b87a08a7c299fe7e2f6f0e019037ff4f8dcc303b0',
}
fast2_v17_hashes={
    '1':'33f412d7fe9d5e87f717c7f664b4824f8c9f08a5b1d852d672a7619800ecad7f',
    '2':'0fd5a15099edc859f94aee5ed4e0eb8c4dcb2a930a7b2725061c3f0597a9c2d5',
    '5':'3c798803e2daa63450085f9a96f99d647e0e07c36c62ae3448b66f049639564f',
    '10':'9ebf1d260f3c6444963a2af855a7830ce993bb8cba048282fa5d37b6152334d8',
    '20':'206d4661a30b756f1cc4c8f5510afa55032b7d3522bd00e88315d943dec56332',
    '50':'ec50300f5f1eff5c97bf7819a41099814f3ea8c61eb6420a4a48b0f7d9415808',
}
fast4_v17_hashes={
    '1':'205747ca878c7bc0a556bb5f60a95bd12a0e0573cacc0dab677b36f2bae45d84',
    '2':'3cf164a47412ab6469fd760ba20a0e36c928b06927885f1c9b63d3b5fc0b3fbb',
    '5':'8d874640e02f50b67a9a8a303d3754b76577955651b6a0ac39f4c8c2d266d87a',
    '10':'a77aa04df07e0a1db950d07a93edebff75af99221a69481e55648074be0eedc6',
    '20':'0eb54ffc829a5ba2ed904364427e0dab523ad345ef450b3adf43da045f857e11',
    '50':'281d7846a28544af1153319d805e21c7f619bfe2addfacad3a87b559e147dd32',
}
(ROOT/'hashes.json').write_text(json.dumps({'original':orig_hash,'variants':hashes,'legacy_v17':pre_accel_v17_hashes,'legacy_v17_fast2':fast2_v17_hashes,'legacy_v17_fast4':fast4_v17_hashes,'legacy_v16':v16_hashes},indent=2),encoding='utf-8')

# Static validation: all methods parse, switch checks and key calls are present.
def validate(path,speed):
    raw=path.read_bytes(); pe=pefile.PE(data=raw); dn=dnfile.dnPE(str(path))
    parsed={}
    targets=[('DataManager','Update'),('Player','ClickStealBtn'),('Plant','Grow'),('FlowerPot','CheckAutoHarvest'),('FlowerPot','AutoReplantAfterHarvest'),('BaseCannedItem','UpdateButtonState'),('tClothConfig','DeserializetClothConfig')]
    for typ,name in targets:
        rva,_=method_info(dn,typ,name); off=pe.get_offset_from_rva(rva)
        b=read_method_body_from_bytes(raw[off:off+10000]); assert b.code_size>0, (path,typ,name)
        parsed[(typ,name)]=b
    def toks(k): return [i.operand.value for i in parsed[k].instructions if hasattr(i.operand,'value')]
    update=toks(('DataManager','Update'))
    assert update.count(T['PlayerPrefs.SetInt'])==4
    assert update.count(T['PlayerPrefs.GetInt'])>=9
    for key in [T['KEY_STEAL'],T['KEY_AUTOKEY'],T['KEY_AUTOFARM'],T['KEY_AUTOCAN']]: assert key in update
    assert T['KeyClickMessage.Obtain'] in update
    steal=toks(('Player','ClickStealBtn'))
    for tok in [T['PlayerPrefs.GetInt'],T['KEY_STEAL'],T['StealResultMessage.Obtain'],T['Player.ShowStealResult'],T['DataManager.RemoveFruit'],T['FruitLostMessage.Obtain'],T['Debug.Log']]: assert tok in steal, (path,tok)
    auto=toks(('FlowerPot','CheckAutoHarvest'))
    for tok in [T['PlayerPrefs.GetInt'],T['PlayerPrefs.SetInt'],T['KEY_AUTOFARM'],T['KEY_STEAL'],T['KEY_STEAL_DONE'],T['Player.ClickStealBtn'],T['FlowerPot.HarvestFlower']]: assert tok in auto
    replant=toks(('FlowerPot','AutoReplantAfterHarvest'))
    for tok in [T['PlayerPrefs.GetInt'],T['KEY_AUTOFARM'],T['FlowerPot.PlantFlower']]: assert tok in replant
    grow=toks(('Plant','Grow'))
    assert T['KEY_STEAL_DONE'] in grow and T['PlayerPrefs.SetInt'] in grow
    assert any(str(i.opcode)=='ldc.r4' and abs(float(i.operand)-float(speed))<1e-6 for i in parsed[('Plant','Grow')].instructions)
    can=toks(('BaseCannedItem','UpdateButtonState'))
    for tok in [T['PlayerPrefs.GetInt'],T['KEY_AUTOCAN'],T['BaseCannedItem.CheckInventorySufficient'],T['BaseCannedItem.ExchangeCannedItem'],T['Selectable.set_interactable']]: assert tok in can
    rarity=parsed[('tClothConfig','DeserializetClothConfig')]
    rt=toks(('tClothConfig','DeserializetClothConfig'))
    assert T['tClothConfig.ctor'] in rt and T['tClothConfig.Rarity'] in rt
    assert any(str(i.opcode)=='ldc.i4.4' for i in rarity.instructions)
for s in speeds: validate(MODDIR/f'Assembly-CSharp_{s}x.dll',s)

# Update manager from v1.6.
ps1=(V16ROOT/'Tools'/'ModManager.ps1').read_text(encoding='utf-8-sig')
def map_block(name,m):
    lines=[f'${name} = @{{']
    keys=['1','2','5','10','20','50'] + (['500'] if '500' in m else [])
    for k in keys: lines.append(f'    "{k}" = "{m[k]}"')
    lines.append('}')
    return '\n'.join(lines)
ps1=re.sub(r'\$variantHashes = @\{.*?\n\}',map_block('variantHashes',hashes),ps1,count=1,flags=re.S)
idx=ps1.find('$legacyV15Hashes = @{')
ps1=ps1[:idx]+map_block('legacyV17Hashes',pre_accel_v17_hashes)+'\n\n'+map_block('legacyV17Fast2Hashes',fast2_v17_hashes)+'\n\n'+map_block('legacyV17Fast4Hashes',fast4_v17_hashes)+'\n\n'+map_block('legacyV16Hashes',v16_hashes)+'\n\n'+ps1[idx:]
needle='function Detect-Legacy-V15-Speed([string]$Hash) {'
pos=ps1.find(needle); end=ps1.find('\n}\n',pos)+3
block=ps1[pos:end]
block16=block.replace('Detect-Legacy-V15-Speed','Detect-Legacy-V16-Speed').replace('$legacyV15Hashes','$legacyV16Hashes')
block17=block.replace('Detect-Legacy-V15-Speed','Detect-Legacy-V17-Speed').replace('$legacyV15Hashes','$legacyV17Hashes')
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17Fast2Hashes.Keys) {\n        if ($legacyV17Fast2Hashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17Fast4Hashes.Keys) {\n        if ($legacyV17Fast4Hashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
ps1=ps1[:pos]+block17+'\n'+block16+'\n'+ps1[pos:]
ps1=ps1.replace('$legacyV15Speed = Detect-Legacy-V15-Speed $currentHash', '$legacyV15Speed = Detect-Legacy-V15-Speed $currentHash\n    $legacyV16Speed = Detect-Legacy-V16-Speed $currentHash\n    $legacyV17Speed = Detect-Legacy-V17-Speed $currentHash')
ps1=ps1.replace('($legacyV15Speed -eq 0) -and (-not $isLegacyV10)', '($legacyV15Speed -eq 0) -and ($legacyV16Speed -eq 0) -and ($legacyV17Speed -eq 0) -and (-not $isLegacyV10)')
needle='    if ($legacyV15Speed -gt 0) {'
insert_upgrades='''    if ($legacyV17Speed -gt 0) {
        Write-Host "Detected earlier v1.7 (${legacyV17Speed}x). Updating to accelerated automatic key delivery." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'An earlier v1.7 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'Earlier v1.7 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV16Speed -gt 0) {
        Write-Host "Detected v1.6 (${legacyV16Speed}x). v1.7 adds four independent persistent feature switches." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.6 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.6 backup hash is unexpected. It was not overwritten for safety.' }
    }
'''
ps1=ps1.replace(needle,insert_upgrades+needle,1)
ps1=ps1.replace('$defaultSpeed = if ($installedSpeed -gt 0) { $installedSpeed } elseif ($legacyV15Speed -gt 0) { $legacyV15Speed }', '$defaultSpeed = if ($installedSpeed -gt 0) { $installedSpeed } elseif ($legacyV17Speed -gt 0) { $legacyV17Speed } elseif ($legacyV16Speed -gt 0) { $legacyV16Speed } elseif ($legacyV15Speed -gt 0) { $legacyV15Speed }')
ps1=ps1.replace("    Write-Host '  6 = 50x  (very fast)'", "    Write-Host '  6 = 50x  (very fast)'\n    Write-Host '  7 = 500x (extreme)'")
ps1=ps1.replace("$map = @{ '1'=1; '2'=2; '3'=5; '4'=10; '5'=20; '6'=50 }", "$map = @{ '1'=1; '2'=2; '3'=5; '4'=10; '5'=20; '6'=50; '7'=500 }")
ps1=ps1.replace('Enter 1-6', 'Enter 1-7')
ps1=ps1.replace('a number from 1 to 6', 'a number from 1 to 7')
ps1=ps1.replace('MOD Manager v1.6', 'MOD Manager v1.7')
ps1=ps1.replace('known v1.0/v1.2/v1.3/v1.4/v1.5/v1.6 MOD file', 'known v1.0/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7 MOD file')
ps1=ps1.replace('upgraded directly to v1.6', 'upgraded directly to v1.7')
ps1=ps1.replace('then install v1.6', 'then install v1.7')
ps1=ps1.replace('v1.6 will preserve', 'v1.7 will preserve')
ps1=ps1.replace('v1.6 will repair', 'v1.7 will repair')
ps1=ps1.replace("'Meow My Crop! AutoFarm MOD v1.6'", "'Meow My Crop! AutoFarm MOD v1.7'")
# Replace settings manifest block entries.
ps1=ps1.replace("        'F6=Pause/resume internal automatic key delivery (physical input remains active)',\n        'AutomaticSteal=Once per mature crop cycle',\n        'AutomaticBeingStolen=Once per mature crop cycle, including one-fruit crops',\n        'AutomaticCanOpening=Enabled whenever a can has sufficient required fruit',", "        'F5=Toggle automatic steal + automatic being-stolen (persistent)',\n        'F6=Toggle internal automatic key delivery (persistent; physical input remains active)',\n        'F7=Toggle automatic harvest + replant (persistent)',\n        'F8=Toggle automatic can opening (persistent; manual can button remains usable)',\n        'All four switches default to enabled on first run',")
ps1=ps1.replace("        'F8=Manual diagnostic trigger for one steal/loss pair',\n","")
ps1=ps1.replace("$verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MOD v1.6 installed' }", "$verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MOD v1.7 installed' }")
old_success="Show-Result \"$verb successfully.`nKeyboard/mouse growth input repaired.`nGrowth speed: ${speed}x`n`nAutomatic can opening: enabled`nDecoration rarity: local Legendary/orange override`nF6: pause/resume automatic key delivery`nAutomatic steal + automatic being-stolen: guaranteed once per mature crop cycle`nF8: manual diagnostic trigger`n`nOpen the can page once. Every can with enough fruit will be opened automatically until materials run out.\""
new_success="Show-Result \"$verb successfully.`nGrowth speed: ${speed}x`n`nIndependent persistent switches (default ON):`nF5 = steal + being-stolen`nF6 = internal automatic key delivery`nF7 = automatic harvest + replant`nF8 = automatic can opening`n`nPress the same key again to resume a paused feature. Manual keyboard/mouse input and the manual can button remain usable.\""
ps1=ps1.replace(old_success,new_success)
(TOOLSDIR/'ModManager.ps1').write_text('\ufeff'+ps1,encoding='utf-8')

for fname in ['1_INSTALL_MOD.cmd','2_CHANGE_SPEED.cmd','3_UNINSTALL_MOD.cmd']:
    p=ROOT/fname; txt=p.read_text(encoding='ascii')
    txt=txt.replace('v1.6','v1.7')
    if fname=='1_INSTALL_MOD.cmd':
        txt=txt.replace('Adds automatic can opening and local Legendary/orange decoration rarity.', 'Adds four independent persistent feature switches: F5/F6/F7/F8.')
    p.write_text(txt,encoding='ascii',newline='')

readme='''Meow My Crop!（喵了个菜！）AutoFarm MOD v1.7
================================================

四项功能现在完全分开控制，并会记住开关状态
----------------------------------------------
F5：偷菜＋被偷菜
    - 关闭后不会再自动发生偷菜或被偷菜。
    - 与 F7 独立：即使暂停自动收获，F5 开启时每盆成熟作物仍只触发一次偷菜＋被偷菜。
    - 再按一次恢复。

F6：自动按键输送
    - 关闭后停止 MOD 内部自动发送 A 键成长消息。
    - 不影响你的真实键盘、鼠标输入，也不会抢鼠标。

F7：自动种植收获
    - 关闭后停止自动收获和自动补种。
    - 作物仍可通过真实输入或 F6 自动按键继续生长。
    - 你仍可以手动收获、手动种植。

F8：自动开罐
    - 关闭后停止自动连续开罐。
    - 罐头页面的手动“开罐”按钮仍可正常使用。

开关规则
--------
- 四项功能首次运行都默认开启。
- 每个开关互不影响。
- 状态通过 Unity PlayerPrefs 保存，退出并重开游戏后仍会保持。
- 按键后 Player.log 会出现下列状态名和 0/1：
  steal_request：F5，0=关闭，1=开启
  total_key_clicks：F6，0=关闭，1=开启
  FarmingCat：F7，0=关闭，1=开启
  Canned：F8，0=关闭，1=开启

保留功能
--------
- 指定作物种一次后自动收获并持续补种同一种作物。
- 1x / 2x / 5x / 10x / 20x / 50x 生长速度。
- 离线自动偷菜和自动被偷菜。
- 自动开罐。
- 装饰在本地按橙色 Legendary 品质显示和分类。

安装
----
1. 完全退出游戏。
2. 解压后双击 1_INSTALL_MOD.cmd。
3. 可直接覆盖 v1.6，无需先卸载；安装器会默认保留当前生长倍率。
4. 安装完成后进入游戏，使用 F5～F8 分别开关四项功能。

重要说明
--------
罐头奖励仍由 Steam Inventory 决定。橙色品质修改是客户端本地显示与分类覆盖，不能把 Steam 服务器库存里的普通物品真正改造成可交易的传奇物品。

本包基于你提供的 Assembly-CSharp.dll 生成，并完成 PE、元数据、补丁方法体、关键调用和六种倍率 DLL 的静态校验。当前环境不能直接启动 Windows 游戏实机运行。
'''
(ROOT/'README_CN.txt').write_text('\ufeff'+readme,encoding='utf-8')
notes=f'''v1.7 implementation notes
- Adds four independent persistent PlayerPrefs switches, all default enabled:
  F5 steal/lost, F6 internal key delivery, F7 auto harvest/replant, F8 auto can opening.
- Player.ClickStealBtn itself is gated, so the steal/lost feature is fully paused when disabled.
- F5 steal/lost remains independent when F7 auto-farm is paused: a per-crop marker prevents repeated events on the same mature crop.
- F7 gates harvesting and replanting only.
- Auto-can off preserves button interactability and manual opening.
- Existing v1.6 Legendary/orange local rarity override is preserved.

SHA256 variants:
{json.dumps(hashes,indent=2)}
'''
(SOURCEDIR/'PATCH_NOTES.txt').write_text(notes,encoding='utf-8')
shutil.copy2('/mnt/data/build_meow_v17.py',SOURCEDIR/'build_meow_v17.py')

zip_path=Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.7.zip')
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(ROOT.rglob('*')):
        if f.is_file(): z.write(f,Path(ROOT.name)/f.relative_to(ROOT))
print(json.dumps({'root':str(ROOT),'zip':str(zip_path),'hashes':hashes},ensure_ascii=False,indent=2))
