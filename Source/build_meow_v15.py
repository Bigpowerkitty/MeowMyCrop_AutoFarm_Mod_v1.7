import os, struct, hashlib, shutil, json, zipfile, re
from pathlib import Path
import pefile, dnfile
from dncil.cil.body.reader import read_method_body_from_bytes

SRC = Path('/mnt/data/Assembly-CSharp.dll')
V14ROOT = Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.4')
ROOT = Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.5')
MODDIR = ROOT / 'ModFiles'
TOOLSDIR = ROOT / 'Tools'
SOURCEDIR = ROOT / 'Source'
if ROOT.exists(): shutil.rmtree(ROOT)
shutil.copytree(V14ROOT, ROOT)
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
v14_hashes=json.loads((V14ROOT/'hashes.json').read_text(encoding='utf-8-sig'))['variants']
(ROOT/'hashes.json').write_text(json.dumps({'original':orig_hash,'variants':hashes,'legacy_v14':v14_hashes},indent=2),encoding='utf-8')

# Static validation.
def validate(path,speed):
    raw=path.read_bytes(); pe=pefile.PE(data=raw); dn=dnfile.dnPE(str(path))
    parsed={}
    for typ,name in [('DataManager','Update'),('Player','ClickStealBtn'),('Plant','Grow'),('FlowerPot','CheckAutoHarvest'),('FlowerPot','AutoReplantAfterHarvest')]:
        rva,_=method_info(dn,typ,name); off=pe.get_offset_from_rva(rva)
        b=read_method_body_from_bytes(raw[off:off+5000]); assert b.code_size>0, (path,typ,name)
        parsed[(typ,name)]=b
    auto_toks=[i.operand.value for i in parsed[('FlowerPot','CheckAutoHarvest')].instructions if hasattr(i.operand,'value')]
    assert T['Player.ClickStealBtn'] in auto_toks and T['FlowerPot.HarvestFlower'] in auto_toks
    steal_toks=[i.operand.value for i in parsed[('Player','ClickStealBtn')].instructions if hasattr(i.operand,'value')]
    for tok in [T['StealResultMessage.Obtain'],T['Player.ShowStealResult'],T['DataManager.RemoveFruit'],T['FruitLostMessage.Obtain'],T['Debug.Log']]:
        assert tok in steal_toks, (path,tok)
    assert any(str(i.opcode)=='ldc.r4' and abs(float(i.operand)-float(speed))<1e-6 for i in parsed[('Plant','Grow')].instructions)
for s in speeds: validate(MODDIR/f'Assembly-CSharp_{s}x.dll',s)

# Update manager from v1.4.
ps1=(V14ROOT/'Tools'/'ModManager.ps1').read_text(encoding='utf-8-sig')
def map_block(name,m):
    lines=[f'${name} = @{{']
    for k in ['1','2','5','10','20','50']: lines.append(f'    "{k}" = "{m[k]}"')
    lines.append('}')
    return '\n'.join(lines)
ps1=re.sub(r'\$variantHashes = @\{.*?\n\}',map_block('variantHashes',hashes),ps1,count=1,flags=re.S)
# Insert legacy v1.4 map before legacy v1.3.
idx=ps1.find('$legacyV13Hashes = @{')
ps1=ps1[:idx]+map_block('legacyV14Hashes',v14_hashes)+'\n\n'+ps1[idx:]
# Add detector.
needle='function Detect-Legacy-V13-Speed([string]$Hash) {'
pos=ps1.find(needle); end=ps1.find('\n}\n',pos)+3
block=ps1[pos:end]
block14=block.replace('Detect-Legacy-V13-Speed','Detect-Legacy-V14-Speed').replace('$legacyV13Hashes','$legacyV14Hashes')
ps1=ps1[:pos]+block14+'\n'+ps1[pos:]
# Variables/checks/default.
ps1=ps1.replace('$legacyV13Speed = Detect-Legacy-V13-Speed $currentHash', '$legacyV13Speed = Detect-Legacy-V13-Speed $currentHash\n    $legacyV14Speed = Detect-Legacy-V14-Speed $currentHash')
ps1=ps1.replace('($legacyV13Speed -eq 0) -and (-not $isLegacyV10)', '($legacyV13Speed -eq 0) -and ($legacyV14Speed -eq 0) -and (-not $isLegacyV10)')
# Insert v1.4 upgrade check before v1.3.
needle='    if ($legacyV13Speed -gt 0) {'
insert14='''    if ($legacyV14Speed -gt 0) {
        Write-Host "Detected v1.4 (${legacyV14Speed}x). v1.5 removes the one-fruit skip and guarantees automatic steal/lost events." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.4 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.5.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.4 backup hash is unexpected. It was not overwritten for safety.' }
    }
'''
ps1=ps1.replace(needle,insert14+needle,1)
ps1=ps1.replace('$defaultSpeed = if ($installedSpeed -gt 0) { $installedSpeed } elseif ($legacyV13Speed -gt 0) { $legacyV13Speed } elseif ($legacyV12Speed -gt 0) { $legacyV12Speed } else { 10 }', '$defaultSpeed = if ($installedSpeed -gt 0) { $installedSpeed } elseif ($legacyV14Speed -gt 0) { $legacyV14Speed } elseif ($legacyV13Speed -gt 0) { $legacyV13Speed } elseif ($legacyV12Speed -gt 0) { $legacyV12Speed } else { 10 }')
# Targeted version and messages.
ps1=ps1.replace('MOD Manager v1.4', 'MOD Manager v1.5')
ps1=ps1.replace('known v1.0/v1.2/v1.3/v1.4 MOD file', 'known v1.0/v1.2/v1.3/v1.4/v1.5 MOD file')
ps1=ps1.replace("'Detected v1.0 MOD. It can be upgraded directly to v1.4.'", "'Detected v1.0 MOD. It can be upgraded directly to v1.5.'")
ps1=ps1.replace("then install v1.4.'", "then install v1.5.'")
ps1=ps1.replace('v1.4 will enable automatic offline steal and automatic being-stolen events.', 'v1.5 will guarantee automatic offline steal and automatic being-stolen events.')
ps1=ps1.replace('v1.4 will repair input handling and add automatic offline steal/loss events.', 'v1.5 will repair input handling and guarantee automatic offline steal/loss events.')
ps1=ps1.replace("'Meow My Crop! AutoFarm MOD v1.4'", "'Meow My Crop! AutoFarm MOD v1.5'")
ps1=ps1.replace("'AutomaticBeingStolen=Once per mature crop cycle when more than one fruit exists'", "'AutomaticBeingStolen=Once per mature crop cycle, including one-fruit crops'")
ps1=ps1.replace("$verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MOD v1.4 installed' }", "$verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MOD v1.5 installed' }")
ps1=ps1.replace('Automatic steal + automatic being-stolen: once per mature crop cycle', 'Automatic steal + automatic being-stolen: guaranteed once per mature crop cycle')
(TOOLSDIR/'ModManager.ps1').write_text('\ufeff'+ps1,encoding='utf-8')

# Update command launchers.
for fname in ['1_INSTALL_MOD.cmd','2_CHANGE_SPEED.cmd','3_UNINSTALL_MOD.cmd']:
    p=ROOT/fname; txt=p.read_text(encoding='ascii')
    txt=txt.replace('v1.4','v1.5')
    if fname=='1_INSTALL_MOD.cmd':
        txt=txt.replace('Automatic steal and automatic being-stolen are enabled.', 'Automatic steal/lost events now also work for one-fruit crops.')
    p.write_text(txt,encoding='ascii',newline='')

readme='''Meow My Crop!（喵了个菜！）AutoFarm MOD v1.5
================================================

本版针对你上传的日志修复：
- 安装日志显示 v1.4 的 50x DLL 已正确安装，游戏日志也没有崩溃或 IL 异常。
- v1.4 只有在成熟果实总数 > 1 时才执行偷菜/被偷菜；单果实作物会整轮跳过。
- v1.5 去掉这个限制，只要成熟后至少有 1 个果实，每轮都保证发生一次偷菜和一次被偷菜。

功能流程（每个成熟周期一次）
--------------------------
1. 自动模拟偷到 1 个当前作物果实，调用游戏原生 ShowStealResult，出现偷菜收获效果。
2. 自动记录 1 个被偷果实，并发送 FruitLostMessage，更新丢失果实统计。
3. 奖励与损失互相抵消，然后正常自动收获剩余等价收益。
4. 自动补种之前手动选择的同一种作物。

这样处理不会调用联网房间、不会寻找远程玩家，也不会因作物只有 1 个果实而失败。
Player.log 中会固定出现：
PlantNetworkModule: Player 0 stole 1 from slot -1

其他功能
--------
- 1x / 2x / 5x / 10x / 20x / 50x 生长速度。
- 自动内部按键输送，不移动、不抢占鼠标。
- F6：暂停/恢复自动按键输送；真实键盘和鼠标仍有效。
- F8：手动测试一次偷菜＋被偷菜事件。
- 指定作物种一次后，自动收获并持续补种同一种。

安装
----
1. 完全退出游戏。
2. 双击 1_INSTALL_MOD.cmd。
3. 可直接覆盖 v1.4；安装器会识别当前 50x 等倍率并默认保留。
4. 安装完成后进入游戏，手动种一次作物，等到第一次成熟。

验证
----
成熟后应同时看到偷菜获得果实效果、自动收获和自动补种。
运行 5_OPEN_PLAYER_LOG.cmd，搜索：
Player 0 stole 1

说明
----
本包基于你提供的 Assembly-CSharp.dll 生成，并完成 PE、元数据、补丁方法体、关键调用和六种倍率 DLL 的静态校验。当前环境不能直接启动 Windows 游戏实机运行。
'''
(ROOT/'README_CN.txt').write_text('\ufeff'+readme,encoding='utf-8')
notes=f'''v1.5 implementation notes
- Fixes v1.4's >1 fruit gate. Any mature crop with >=1 fruit triggers the pair.
- Player.ClickStealBtn now performs a fully local synthetic cycle:
  * dispatch StealResultMessage for Steam stolen-fruit stats without double reward,
  * call Player.ShowStealResult directly for visible local reward,
  * call DataManager.RemoveFruit(1) to represent being stolen,
  * dispatch FruitLostMessage for lost-fruit stats,
  * write a UnityEngine.Debug.Log line to Player.log.
- CheckAutoHarvest calls the pair before normal harvest/replant.
- No remote player, lobby, or network request is required.

SHA256 variants:
{json.dumps(hashes,indent=2)}
'''
(SOURCEDIR/'PATCH_NOTES.txt').write_text(notes,encoding='utf-8')
shutil.copy2('/mnt/data/build_meow_v15.py',SOURCEDIR/'build_meow_v15.py')

# ZIP with one top-level folder.
zip_path=Path('/mnt/data/MeowMyCrop_AutoFarm_Mod_v1.5.zip')
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(ROOT.rglob('*')):
        if f.is_file(): z.write(f,Path(ROOT.name)/f.relative_to(ROOT))
print(json.dumps({'root':str(ROOT),'zip':str(zip_path),'hashes':hashes},ensure_ascii=False,indent=2))
