import os, struct, hashlib, shutil, json, zipfile, re
from pathlib import Path
import pefile, dnfile
from dncil.cil.body.reader import read_method_body_from_bytes

SCRIPT_DIR = Path(__file__).resolve().parent
SRC = Path(os.environ.get('MEOW_SRC', SCRIPT_DIR / 'Assembly-CSharp.original.dll')).resolve()
BASE_ROOT = Path(os.environ.get('MEOW_BASE_ROOT', SCRIPT_DIR.parent)).resolve()
ROOT = Path(os.environ.get('MEOW_OUTPUT_ROOT', SCRIPT_DIR.parent.parent / 'MeowMOD_v1.8_build')).resolve()
MODDIR = ROOT / 'ModFiles'
TOOLSDIR = ROOT / 'Tools'
SOURCEDIR = ROOT / 'Source'
EXPECTED_ORIGINAL_SHA256 = 'ad00d6dd37d0ee222e5506e9a4b697c5b5bf10fa3673843cde68b9760654e954'
if not SRC.is_file():
    raise FileNotFoundError(f'Original Assembly-CSharp.dll not found: {SRC}')
if hashlib.sha256(SRC.read_bytes()).hexdigest() != EXPECTED_ORIGINAL_SHA256:
    raise RuntimeError('Unsupported Assembly-CSharp.dll. Refusing to patch a changed game build.')
if ROOT == BASE_ROOT:
    raise RuntimeError('MEOW_OUTPUT_ROOT must differ from the template package directory.')
if ROOT.exists(): shutil.rmtree(ROOT)
shutil.copytree(BASE_ROOT, ROOT)
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
 'RealtimeClock.ElapsedMilliseconds':0x060007F5,
 'PlayerPrefs.GetInt':0x0A00044D,
 'PlayerPrefs.SetInt':0x0A00044E,
 'PlayerPrefs.Save':0x0A000614,
 'String.Format1':0x0A000057,
 'String.Format2':0x0A000068,
 'Debug.Log':0x0A0000ED,
 'Type.Int32':0x010000E7,
 'DataManager.SaveGameData':0x06000124,
 'MessageManager.Instance':0x060001D4,
 'MessageManager.Subscribe':0x060001D5,
 'MessageManager.Dispatch':0x060001D8,
 'KeyClickMessage.Obtain':0x06000229,
 'MarkDirtyMessage.Obtain':0x0600023C,
 'CannedUI.UpdateDisplay':0x060005F0,
 'CannedUI.Refresh':0x060005F1,
 'CannedUI._lastUpdateTime':0x0400046A,
 'Time.get_time':0x0A00003D,
 'Player.isLocal':0x040002AE,
 'Player.steamId':0x040002AF,
 'Player.flowerPot':0x040002B2,
 'Player.stealButton':0x040002C0,
 'Object.op_Equality':0x0A00004D,
 'SteamLobbySystem.Instance':0x0A0000A3,
 'SteamLobbySystem.IsNoStealing':0x06000545,
 'SendStealRequestMessage.Obtain':0x060002A9,
 'GameObject.get_gameObject':0x0A0000B9,
 'GameObject.SetActive':0x0A0000AA,
 'Behaviour.get_isActiveAndEnabled':0x0A000246,
 'FlowerPot.player':0x04000076,
 'FlowerPot.GetTotalFruitCount':0x06000057,
 'FlowerPot.HarvestFlower':0x06000050,
 'FlowerPot.PlantFlower':0x0600004F,
 'FlowerPot.RemovePlant':0x06000054,
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
 'BaseCannedItem.UpdateDisplayInternal':0x060005A7,
 'BaseCannedItem.GetRequiredFruitIds':0x060005A6,
 'BaseCannedItem.CheckInventorySufficient':0x060005AC,
 'BaseCannedItem.UpdateTextColors':0x060005B1,
 'BaseCannedItem.UpdateButtonState':0x060005B0,
 'BaseCannedItem.GetPoolConfig':0x060005AF,
 'BaseCannedItem._cachedRequiredFruitIds':0x0400043E,
 'SteamInventoryManager.Instance':0x0A0002A3,
 'SteamInventoryManager.HasItem':0x0600047F,
 'SteamInventoryManager.GetItemsByDefinitionId':0x06000482,
 'SteamInventoryManager.GetFirstCachedInstance':0x06000484,
 'SteamInventoryItem.get_InstanceId':0x0600044B,
 'SteamInventoryItem.get_DefinitionId':0x0600044D,
 'SteamInventoryItem.get_Quantity':0x0600044F,
 'SteamInventoryItem.ctor.Details':0x06000452,
 'SteamInventoryItem.GetInstanceIdValue':0x06000454,
 'Type.SteamInventoryItem':0x020000B6,
 'IEnumerable.GetEnumerator':0x0A000022,
 'IEnumerator.MoveNext':0x0A00000D,
 'IEnumerator.get_Current':0x0A000010,
 'SteamInventoryItemList.get_Count':0x0A0002EF,
 'SteamInventoryItemList.get_Item':0x0A0002F0,
 'NullableSteamItemInstanceId.ctor':0x0A00031D,
 'Type.NullableSteamItemInstanceId':0x1B00009F,
 'Type.SteamInventoryRefreshedMessage':0x0200007D,
 'Type.SteamInventoryExchangedMessage':0x0200007B,
 'SteamInventoryExchangedMessage.success':0x0400025D,
 'SteamInventoryExchangedMessage.consumeItemId':0x0400025E,
 'Type.SteamItemDropMessage':0x0200007E,
 'SteamItemDropMessage.itemDetails':0x0400026A,
 'Type.FruitUpdateMessage':0x0200003B,
 'Type.MarkDirtyMessage':0x02000043,
 'Type.LanguageChangedMessage':0x02000040,
 'DataManager.GetFruitInventoryCount':0x0600012F,
 'List.get_Item':0x0A0000D5,
 'List.Contains':0x0A00016C,
 'PlayerManager.Instance':0x0A000284,
 'PlayerManager.get_LocalPlayer':0x06000168,
 'ConfigManager.Instance':0x0A00004B,
 'ConfigManager.tables':0x040001B6,
 'Tables.get_TbPlantConfig':0x060008FC,
 'TbPlantConfig.GetOrDefault':0x06000954,
 'tPoolConfig.Count':0x040006C0,
 'tPoolConfig.TokenId':0x040006BD,
 'List.get_Count':0x0A0000D4,
 'Selectable.set_interactable':0x0A000456,
 'Selectable.get_interactable':0x0A0004BA,
 'ExchangeState.BuilderCreate':0x0A0000F4,
 'ExchangeState.Builder':0x040007E6,
 'ExchangeState.This':0x040007E7,
 'ExchangeState.State':0x040007E5,
 'ExchangeState.Start':0x2B00010E,
 'tClothConfig.ctor':0x06000964,
 'tClothConfig.Rarity':0x0400068B,
 # Existing user strings reused as private PlayerPrefs keys / labels.
 'KEY_STEAL':0x70002999,          # "steal_request"
 'KEY_STEAL_DONE':0x700029B5,     # "steal_result"; per-crop-cycle marker
 'KEY_AUTOKEY':0x700050F8,        # "total_key_clicks"
 'KEY_AUTOFARM':0x70006CA1,       # "FarmingCat"
 'KEY_AUTOCAN':0x700017F6,        # "Canned"
 'KEY_AUTOCAN_TARGET':0x70000474, # "growTrigger"; current missing fruit id
 'KEY_AUTOCAN_COUNT':0x700088DE,  # "requiredGrowthValue"; required inventory count
 'KEY_AUTOCAN_APPLIED':0x700088C6,# "stageSprite"; safely applied crop id
 'KEY_AUTOCAN_LAST_FRAME':0x70000356, # "inventory_exchange"; F8 latch: 0 armed, 1 blocked, 2 success/drop re-armed
 'KEY_AUTOCAN_REFRESH_FRAME':0x70003F50, # private same-event broadcast de-dup key
 'KEY_STOLEN_COUNT':0x7000511A,    # "total_stolen_fruits"; MOD-local PlayerPrefs counter
 'KEY_LOST_COUNT':0x7000521C,      # "total_lost_fruits"; MOD-local PlayerPrefs counter
 'KEY_SPEED':0x70007284,           # "UI_SPEEDUP_STAGE2"; installed multiplier
 'FMT_AUTOSTEAL':0x7000851E,       # replaced in-place with "[AutoSteal] {0}/100"
 'FMT_AUTOBEING':0x7000845C,       # replaced in-place with "[AutoBeingStolen] {0}/100"
 'FMT_STATE':0x70006979,           # "{0}: {1}"
}

# PlayerPrefs toggle helper. Defaults are enabled (1), and state persists.
def emit_toggle(il,keycode,key_token,label_token,after_label,reset_token=None,refresh_can=False):
    il.i4(keycode); il.token(0x28,T['Input.GetKeyDown']); il.branch(0x39,after_label)
    # SetInt(key, 1 - GetInt(key, 1))
    il.token(0x72,key_token)
    il.b(0x17)
    il.token(0x72,key_token); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.b(0x59)
    il.token(0x28,T['PlayerPrefs.SetInt'])
    if reset_token is not None:
        # A deliberate feature-key toggle re-arms one automatic attempt.
        il.token(0x72,reset_token); il.b(0x16); il.token(0x28,T['PlayerPrefs.SetInt'])
    if refresh_can:
        # Enabling F8 while the can page is already open must immediately
        # re-evaluate its recipe instead of waiting for an unrelated message.
        emit_clear_auto_can_state(il)
    il.token(0x28,T['PlayerPrefs.Save'])
    # Debug.Log(String.Format("{0}: {1}", label, boxed-state))
    il.token(0x72,T['FMT_STATE'])
    il.token(0x72,label_token)
    il.token(0x72,key_token); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.token(0x8C,T['Type.Int32'])
    il.token(0x28,T['String.Format2'])
    il.token(0x28,T['Debug.Log'])
    if refresh_can:
        il.token(0x28,T['MessageManager.Instance']); il.b(0x16)
        il.token(0x28,T['MarkDirtyMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.label(after_label)

def emit_enabled_check(il,key_token,enabled_label,disabled_label=None):
    il.token(0x72,key_token); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt'])
    if disabled_label is None:
        il.branch(0x3A,enabled_label)
    else:
        il.branch(0x39,disabled_label)
        il.branch(0x38,enabled_label)


def emit_clear_auto_can_state(il):
    for key in (T['KEY_AUTOCAN_TARGET'],T['KEY_AUTOCAN_COUNT'],T['KEY_AUTOCAN_APPLIED']):
        il.token(0x72,key); il.b(0x16); il.token(0x28,T['PlayerPrefs.SetInt'])


def emit_pref_state_log(il,label_token,value_token):
    # Sparse diagnostics only when a supply target is claimed or applied.
    il.token(0x72,T['FMT_STATE']); il.token(0x72,label_token)
    il.token(0x72,value_token); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.token(0x8C,T['Type.Int32']); il.token(0x28,T['String.Format2']); il.token(0x28,T['Debug.Log'])


def emit_increment_counter_and_log(il,key_token,format_token):
    # PlayerPrefs counter = counter + 1, then emit the exact acceptance log.
    il.token(0x72,key_token)
    il.token(0x72,key_token); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.b(0x17,0x58); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.token(0x72,format_token)
    il.token(0x72,key_token); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.token(0x8C,T['Type.Int32']); il.token(0x28,T['String.Format1']); il.token(0x28,T['Debug.Log'])


def make_start_body(speed):
    il=IL()
    # Materialize all four default-on switches without overwriting an existing
    # persisted value. Unlike v1.7, F8 is no longer forced on at every launch.
    for key in (T['KEY_STEAL'],T['KEY_AUTOKEY'],T['KEY_AUTOFARM'],T['KEY_AUTOCAN']):
        il.token(0x72,key); il.token(0x72,key); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt'])
        il.token(0x28,T['PlayerPrefs.SetInt'])
    # Record the selected DLL multiplier as part of the persistent MOD config.
    il.token(0x72,T['KEY_SPEED']); il.i4(speed); il.token(0x28,T['PlayerPrefs.SetInt'])
    # Only transient can-operation state is reset between processes.
    il.token(0x72,T['KEY_AUTOCAN_LAST_FRAME']); il.b(0x16); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.token(0x72,T['KEY_AUTOCAN_REFRESH_FRAME']); il.i4(-1); il.token(0x28,T['PlayerPrefs.SetInt'])
    emit_clear_auto_can_state(il)
    il.token(0x28,T['PlayerPrefs.Save'])
    # Preserve the original DataManager.Start subscription exactly, then notify
    # any can widgets that already subscribed earlier in Unity's Start order.
    il.token(0x28,T['MessageManager.Instance']); il.b(0x02); il.token(0x6F,T['MessageManager.Subscribe'])
    il.token(0x28,T['MessageManager.Instance']); il.b(0x16)
    il.token(0x28,T['MarkDirtyMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.b(0x2A)
    return fat_body(il.assemble(),max_stack=3)


def emit_can_page_refresh(il):
    # Re-run the active can widgets' normal recipe/UI refresh. This is needed
    # after a hidden can page becomes active: BaseCannedItem.Start may have run
    # before the page was active, so its one-time UpdateButtonState call could
    # not claim an automatic supply target.
    il.token(0x28,T['MessageManager.Instance']); il.b(0x16)
    il.token(0x28,T['MarkDirtyMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])


def make_canned_ui_on_enable_body():
    il=IL()
    # Preserve the original visual refresh, then immediately re-evaluate the
    # recipe after this page has become active.
    il.b(0x02); il.token(0x28,T['CannedUI.UpdateDisplay'])
    il.b(0x02); il.token(0x28,T['CannedUI.Refresh'])
    emit_can_page_refresh(il)
    il.b(0x2A)
    return fat_body(il.assemble(),max_stack=2)


def make_canned_ui_update_body():
    il=IL()
    # Preserve the original one-second UI cadence. Each visible-page refresh
    # also asks active can widgets to re-check shortages, so an initialization
    # order race cannot leave the shared supply target permanently empty.
    il.token(0x28,T['Time.get_time'])
    il.b(0x02); il.token(0x7B,T['CannedUI._lastUpdateTime']); il.b(0x59)
    il.r4(1.0); il.branch(0x44,'return')  # blt.un
    il.b(0x02); il.token(0x28,T['CannedUI.UpdateDisplay'])
    emit_can_page_refresh(il)
    il.b(0x02); il.token(0x28,T['Time.get_time']); il.token(0x7D,T['CannedUI._lastUpdateTime'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=3)


def make_update_body():
    il=IL()
    # Four independent, persistent switches.
    emit_toggle(il,286,T['KEY_STEAL'],T['KEY_STEAL'],'after_f5')     # F5
    emit_toggle(il,287,T['KEY_AUTOKEY'],T['KEY_AUTOKEY'],'after_f6') # F6
    emit_toggle(il,288,T['KEY_AUTOFARM'],T['KEY_AUTOFARM'],'after_f7') # F7
    emit_toggle(il,289,T['KEY_AUTOCAN'],T['KEY_AUTOCAN'],'after_f8',T['KEY_AUTOCAN_LAST_FRAME'],True) # F8

    # Internal A-key message every game frame, independently gated by F6 setting.
    il.token(0x72,T['KEY_AUTOKEY']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'after_auto_key')
    il.token(0x28,T['MessageManager.Instance']); il.i1(65)
    il.token(0x28,T['KeyClickMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.label('after_auto_key')

    # Crop replacement is deliberately performed here, outside inventory-change
    # callbacks. This avoids re-entering HarvestFlower while it is still adding
    # fruit and dispatching UI messages.
    il.token(0x72,T['KEY_AUTOCAN']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3A,'can_enabled')
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'after_auto_supply')
    emit_clear_auto_can_state(il); il.branch(0x38,'after_auto_supply')
    il.label('can_enabled')
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'after_auto_supply')
    # A target that has reached its stored requirement is complete.
    il.b(0x02); il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.token(0x6F,T['DataManager.GetFruitInventoryCount'])
    il.token(0x72,T['KEY_AUTOCAN_COUNT']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3F,'target_missing')
    emit_clear_auto_can_state(il); il.branch(0x38,'after_auto_supply')

    il.label('target_missing')
    il.token(0x28,T['PlayerManager.Instance']); il.token(0x6F,T['PlayerManager.get_LocalPlayer']); il.b(0x25); il.branch(0x3A,'has_supply_player'); il.b(0x26); il.branch(0x38,'after_auto_supply')
    il.label('has_supply_player')
    il.token(0x7B,T['Player.flowerPot']); il.b(0x25); il.branch(0x3A,'has_supply_pot'); il.b(0x26); il.branch(0x38,'after_auto_supply')
    il.label('has_supply_pot')
    # Replace once per target, or again if the player manually changed crops.
    il.b(0x25); il.token(0x28,T['FlowerPot.get_CurrentPlantConfigId'])
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x40,'replace_supply_crop')
    il.token(0x72,T['KEY_AUTOCAN_APPLIED']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x40,'replace_supply_crop')
    il.b(0x26); il.branch(0x38,'after_auto_supply')
    il.label('replace_supply_crop')
    # Resolve and validate the target plant config before removing the current
    # crop. A stale/non-plant fruit id now clears the task without data loss.
    il.token(0x28,T['ConfigManager.Instance']); il.token(0x7B,T['ConfigManager.tables']); il.token(0x6F,T['Tables.get_TbPlantConfig'])
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.token(0x6F,T['TbPlantConfig.GetOrDefault'])
    il.b(0x25); il.branch(0x3A,'valid_supply_config')
    il.b(0x26,0x26); emit_clear_auto_can_state(il); il.branch(0x38,'after_auto_supply')
    il.label('valid_supply_config'); il.b(0x0A)
    il.b(0x25); il.token(0x28,T['FlowerPot.RemovePlant'])
    il.b(0x25,0x7B); il.raw(struct.pack('<I',T['FlowerPot.plantPrefab']))
    il.b(0x06,0x16); il.token(0x28,T['FlowerPot.PlantFlower'])
    il.token(0x72,T['KEY_AUTOCAN_APPLIED']); il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.token(0x28,T['PlayerPrefs.SetInt'])
    emit_pref_state_log(il,T['KEY_AUTOCAN_APPLIED'],T['KEY_AUTOCAN_APPLIED'])
    il.label('after_auto_supply')

    # Preserve original S quick-save.
    il.i1(115); il.token(0x28,T['Input.GetKeyDown']); il.branch(0x39,'return')
    il.b(0x02); il.token(0x28,T['DataManager.SaveGameData'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=6,local_sig=0x11000160,init_locals=True)


def make_steal_body():
    # Preserve the original remote-player/manual online steal path byte-for-byte
    # in behavior. Only the local player enters the F5-controlled offline logic.
    # The two persisted 0..100 counters then stop independently at their limits.
    il=IL()
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.b(0x14); il.token(0x28,T['Object.op_Equality']); il.branch(0x39,'has_pot'); il.b(0x2A)
    il.label('has_pot')
    il.b(0x02); il.token(0x7B,T['Player.isLocal']); il.branch(0x3A,'local_auto')
    il.token(0x28,T['SteamLobbySystem.Instance']); il.token(0x6F,T['SteamLobbySystem.IsNoStealing']); il.branch(0x39,'remote_send'); il.b(0x2A)
    il.label('remote_send')
    il.token(0x28,T['MessageManager.Instance']); il.b(0x02); il.token(0x7B,T['Player.steamId'])
    il.token(0x28,T['SendStealRequestMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.b(0x02); il.token(0x7B,T['Player.stealButton']); il.token(0x6F,T['GameObject.get_gameObject'])
    il.b(0x16); il.token(0x6F,T['GameObject.SetActive']); il.b(0x2A)
    il.label('local_auto')
    il.token(0x72,T['KEY_STEAL']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3A,'enabled'); il.b(0x2A)
    il.label('enabled')
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.token(0x6F,T['FlowerPot.GetTotalFruitCount']); il.b(0x16); il.branch(0x3D,'has_fruit'); il.b(0x2A)
    il.label('has_fruit')
    il.b(0x02); il.token(0x7B,T['Player.flowerPot']); il.token(0x28,T['FlowerPot.get_CurrentPlantConfigId']); il.b(0x0A)

    # Automatic steal reward, capped independently at 100.
    il.token(0x72,T['KEY_STOLEN_COUNT']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.i4(100); il.branch(0x3C,'skip_auto_steal')
    il.b(0x02,0x16); il.token(0x7D,T['Player.isLocal'])
    il.token(0x28,T['MessageManager.Instance'])
    il.b(0x16,0x6E,0x17,0x17,0x06,0x15)
    il.token(0x28,T['StealResultMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    il.b(0x02,0x17); il.token(0x7D,T['Player.isLocal'])

    il.b(0x02,0x06,0x17); il.token(0x28,T['Player.ShowStealResult'])
    emit_increment_counter_and_log(il,T['KEY_STOLEN_COUNT'],T['FMT_AUTOSTEAL'])
    il.label('skip_auto_steal')

    # Automatic being-stolen loss, capped independently at 100.
    il.token(0x72,T['KEY_LOST_COUNT']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.i4(100); il.branch(0x3C,'skip_auto_lost')
    il.token(0x28,T['DataManager.Instance']); il.b(0x06,0x17); il.token(0x6F,T['DataManager.RemoveFruit'])

    il.token(0x28,T['MessageManager.Instance']); il.b(0x17,0x16,0x6E)
    il.token(0x28,T['FruitLostMessage.Obtain']); il.token(0x6F,T['MessageManager.Dispatch'])
    emit_increment_counter_and_log(il,T['KEY_LOST_COUNT'],T['FMT_AUTOBEING'])
    il.label('skip_auto_lost')
    il.token(0x28,T['PlayerPrefs.Save'])
    il.b(0x2A)
    return fat_body(il.assemble(),max_stack=7,local_sig=0x11000022,init_locals=True)


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
    # Normal F7 auto-farm, or an active F8 can-supply target, may harvest.
    il.token(0x72,T['KEY_AUTOFARM']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3A,'harvest')
    il.token(0x72,T['KEY_AUTOCAN']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'return')
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'return')
    il.label('harvest')
    il.b(0x02); il.token(0x28,T['FlowerPot.HarvestFlower'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=3)


def make_auto_replant_body():
    il=IL()
    il.token(0x72,T['KEY_AUTOFARM']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3A,'farm_enabled')
    il.token(0x72,T['KEY_AUTOCAN']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'return')
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3A,'farm_enabled')
    il.label('return'); il.b(0x2A)
    il.label('farm_enabled')
    il.b(0x02); il.token(0x7B,T['FlowerPot.currentPlantConfig']); il.branch(0x3A,'has_config'); il.b(0x2A)
    il.label('has_config')
    il.b(0x02,0x02); il.token(0x7B,T['FlowerPot.plantPrefab'])
    il.b(0x02); il.token(0x7B,T['FlowerPot.currentPlantConfig']); il.b(0x16)
    il.token(0x28,T['FlowerPot.PlantFlower'])
    # The newly planted local crop begins a fresh one-shot steal/lost cycle.
    il.token(0x72,T['KEY_STEAL_DONE']); il.b(0x16); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.b(0x2A)
    return fat_body(il.assemble(),max_stack=4)


def make_grow_body(speed):
    il=IL()
    il.b(0x02); il.token(0x28,T['Plant.get_IsMature']); il.branch(0x39,'not_mature'); il.b(0x2A)
    il.label('not_mature')
    # Only the local player's growing crop may reset the global one-shot marker.
    # Remote/non-local crops can no longer repeatedly unlock one mature crop.
    il.b(0x02); il.token(0x28,T['Plant.get_Player']); il.b(0x25); il.branch(0x3A,'has_cycle_player')
    il.b(0x26); il.branch(0x38,'after_cycle_reset')
    il.label('has_cycle_player')
    il.token(0x7B,T['Player.isLocal']); il.branch(0x39,'after_cycle_reset')
    il.b(0x02); il.token(0x7B,T['Plant.plantData']); il.token(0x7B,T['PlantSaveData.growthValue'])
    il.r4(0.0); il.branch(0x40,'after_cycle_reset')
    il.token(0x72,T['KEY_STEAL_DONE']); il.b(0x16); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.label('after_cycle_reset')
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


def make_first_cached_instance_body():
    # The original implementation only checks definitionIdIndex[0]. Steam can
    # leave that first id stale while later ids still point at valid inventory
    # entries, causing HasItem() to say true but the exchange lookup to return
    # null. Reuse the game's filtered list helper and select its first valid
    # SteamInventoryItem instead. No item is created or modified here.
    il=IL()
    il.b(0x02,0x03); il.token(0x28,T['SteamInventoryManager.GetItemsByDefinitionId'])
    # Keep the boxed non-generic IEnumerator on the evaluation stack so the
    # original local signature remains valid. Local 1 is SteamInventoryItem and
    # local 2 is the nullable return value.
    il.token(0x6F,T['IEnumerable.GetEnumerator'])
    il.label('scan')
    il.b(0x25); il.token(0x6F,T['IEnumerator.MoveNext']); il.branch(0x39,'no_item')
    il.b(0x25); il.token(0x6F,T['IEnumerator.get_Current'])
    il.token(0x74,T['Type.SteamInventoryItem']); il.b(0x0B)
    # All three facts must match the requested consumable item: definition,
    # positive quantity and a real Steam instance id. Steam's invalid instance
    # sentinel is UInt64.MaxValue, so reject both zero and that sentinel.
    il.b(0x07); il.token(0x6F,T['SteamInventoryItem.get_DefinitionId']); il.b(0x03); il.branch(0x40,'scan')
    il.b(0x07); il.token(0x6F,T['SteamInventoryItem.get_Quantity']); il.b(0x16); il.branch(0x3E,'scan')
    il.b(0x07); il.token(0x6F,T['SteamInventoryItem.GetInstanceIdValue']); il.branch(0x39,'scan')
    il.b(0x07); il.token(0x6F,T['SteamInventoryItem.GetInstanceIdValue'])
    il.b(0x15,0x6E); il.branch(0x3B,'scan')
    il.b(0x26,0x07); il.token(0x6F,T['SteamInventoryItem.get_InstanceId'])
    il.token(0x73,T['NullableSteamItemInstanceId.ctor']); il.b(0x2A)
    il.label('no_item')
    il.b(0x26,0x12,0x02,0xFE,0x15); il.raw(struct.pack('<I',T['Type.NullableSteamItemInstanceId']))
    il.b(0x08,0x2A)
    return fat_body(il.assemble(),max_stack=3,local_sig=0x110000E2,init_locals=True)


def make_auto_can_update_button_body():
    # Keep the original button/manual operation. Inventory callbacks only select
    # a missing-fruit target; DataManager.Update performs replacement safely on
    # the next frame after any active HarvestFlower call has returned. Automatic
    # exchange is globally guarded before the async call: the game's failed-
    # exchange completion synchronously calls this method again after clearing
    # _isExchanging, so an unguarded call here recursively exhausts the stack.
    il=IL()
    il.b(0x02); il.token(0x7B,T['BaseCannedItem.ExchangeButton']); il.b(0x14)
    il.token(0x28,T['Object.op_Equality']); il.branch(0x39,'has_button'); il.b(0x2A)
    il.label('has_button')
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._isExchanging']); il.branch(0x39,'check_inventory')
    # Preserve state 2 when a success/drop message arrives before the original
    # async completion clears busy. Every other busy/in-flight callback becomes
    # state 1, which blocks automatic retry after a failure.
    il.token(0x72,T['KEY_AUTOCAN_LAST_FRAME']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.b(0x18); il.branch(0x3B,'busy_button')
    il.token(0x72,T['KEY_AUTOCAN_LAST_FRAME']); il.b(0x17); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.label('busy_button')
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
    # MessageManager broadcasts to can widgets on hidden tabs too. Only the
    # currently active/enabled widget may claim the shared supply/opening task.
    il.b(0x02); il.token(0x28,T['Behaviour.get_isActiveAndEnabled']); il.branch(0x39,'return')
    il.b(0x07); il.branch(0x39,'supply')
    il.token(0x72,T['KEY_AUTOCAN']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'return')

    # A failed or in-flight exchange locks only the automatic caller. The manual
    # Unity Button continues to use the untouched ExchangeCannedItem entry.
    # State 1 means blocked/in-flight/failed. State 2 is written only by a
    # successful exchange or real item drop and permits one verified re-arm.
    # Older timestamp values are neither state and cannot become permanent locks.
    il.token(0x72,T['KEY_AUTOCAN_LAST_FRAME']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.b(0x17); il.branch(0x3B,'return')

    # The player-facing requirement is recipe fruit only. Do not add a second
    # MOD-side Steam-item gate here: the original ExchangeCannedItem path owns
    # all internal Steam exchange details. Claim the shared latch before entering
    # that original path so an internal failure cannot recurse or flood requests.
    # This also blocks a second BaseCannedItem widget in the same callback batch.
    # A failure keeps the latch set through its original busy completion callback;
    # only a confirmed success/drop marker or explicit F8 toggle re-arms it.
    emit_clear_auto_can_state(il)
    il.token(0x72,T['KEY_AUTOCAN_LAST_FRAME']); il.b(0x17); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.ExchangeCannedItem'])
    il.branch(0x38,'return')

    il.label('supply')
    il.token(0x72,T['KEY_AUTOCAN']); il.b(0x17); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'return')
    il.b(0x06); il.token(0x6F,T['List.get_Count']); il.b(0x16); il.branch(0x3E,'return')

    # Release a completed/stale target before claiming the next missing fruit.
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x39,'find_missing')
    il.token(0x28,T['DataManager.Instance']); il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.token(0x6F,T['DataManager.GetFruitInventoryCount'])
    il.token(0x72,T['KEY_AUTOCAN_COUNT']); il.b(0x16); il.token(0x28,T['PlayerPrefs.GetInt']); il.branch(0x3F,'return')
    emit_clear_auto_can_state(il)
    il.label('find_missing')
    # Use local 1 as a full Int32 index and scan every recipe fruit instead of
    # assuming recipes contain at most two. Signature 0x11000132 begins with
    # List<Int32>, Int32; its extra original locals remain initialized/unused.
    il.b(0x16,0x0B)
    il.label('scan_missing')
    il.b(0x07,0x06); il.token(0x6F,T['List.get_Count']); il.branch(0x3C,'return')
    il.token(0x28,T['DataManager.Instance']); il.b(0x06,0x07); il.token(0x6F,T['List.get_Item'])
    il.token(0x6F,T['DataManager.GetFruitInventoryCount'])
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig']); il.token(0x7B,T['tPoolConfig.Count']); il.branch(0x3F,'missing_found')
    il.b(0x07,0x17,0x58,0x0B); il.branch(0x38,'scan_missing')
    il.label('missing_found')
    il.token(0x72,T['KEY_AUTOCAN_TARGET']); il.b(0x06,0x07); il.token(0x6F,T['List.get_Item']); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.label('store_requirement')
    emit_pref_state_log(il,T['KEY_AUTOCAN_TARGET'],T['KEY_AUTOCAN_TARGET'])
    il.token(0x72,T['KEY_AUTOCAN_COUNT']); il.b(0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig']); il.token(0x7B,T['tPoolConfig.Count']); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.token(0x72,T['KEY_AUTOCAN_APPLIED']); il.b(0x16); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.label('return'); il.b(0x2A)
    return fat_body(il.assemble(),max_stack=4,local_sig=0x11000132,init_locals=True)


def make_auto_can_handle_message_body():
    # Preserve original UI messages. Only a successful exchange or a real Steam
    # item drop matching this can's TokenId can write state 2. Generic inventory
    # refreshes and failed exchange messages remain unhandled and never re-arm.
    il=IL()
    il.b(0x03); il.token(0x75,T['Type.FruitUpdateMessage']); il.branch(0x39,'mark_dirty')
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.UpdateDisplayInternal'])
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.UpdateButtonState']); il.b(0x17,0x2A)
    il.label('mark_dirty')
    il.b(0x03); il.token(0x75,T['Type.MarkDirtyMessage']); il.branch(0x39,'language')
    il.b(0x02,0x02); il.token(0x6F,T['BaseCannedItem.GetPoolConfig']); il.token(0x7D,T['BaseCannedItem._cachedPoolConfig'])
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.UpdateDisplayInternal'])
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.UpdateButtonState']); il.b(0x17,0x2A)
    il.label('language')
    il.b(0x03); il.token(0x75,T['Type.LanguageChangedMessage']); il.branch(0x39,'exchange_succeeded')
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.UpdateDisplayInternal']); il.b(0x17,0x2A)
    il.label('exchange_succeeded')
    # Hidden can tabs must not consume the global success/drop re-arm event.
    il.b(0x02); il.token(0x28,T['Behaviour.get_isActiveAndEnabled']); il.branch(0x39,'unhandled')
    il.b(0x03); il.token(0x75,T['Type.SteamInventoryExchangedMessage']); il.branch(0x39,'item_drop')
    il.b(0x03); il.token(0x75,T['Type.SteamInventoryExchangedMessage']); il.token(0x7B,T['SteamInventoryExchangedMessage.success']); il.branch(0x39,'unhandled')
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig']); il.branch(0x39,'unhandled')
    il.b(0x03); il.token(0x75,T['Type.SteamInventoryExchangedMessage']); il.token(0x7B,T['SteamInventoryExchangedMessage.consumeItemId'])
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig']); il.token(0x7B,T['tPoolConfig.TokenId']); il.branch(0x40,'unhandled')
    il.branch(0x38,'rearm')

    il.label('item_drop')
    il.b(0x03); il.token(0x75,T['Type.SteamItemDropMessage']); il.branch(0x39,'unhandled')
    # A repeated/stale drop callback must not overwrite state 1 while an
    # exchange is in flight. Only an idle widget may use a real drop to retry.
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._isExchanging']); il.branch(0x3A,'unhandled')
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig']); il.branch(0x39,'unhandled')
    il.b(0x03); il.token(0x75,T['Type.SteamItemDropMessage']); il.token(0x7B,T['SteamItemDropMessage.itemDetails'])
    il.token(0x73,T['SteamInventoryItem.ctor.Details']); il.token(0x6F,T['SteamInventoryItem.get_DefinitionId'])
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig']); il.token(0x7B,T['tPoolConfig.TokenId']); il.branch(0x40,'unhandled')
    # Accept only a drop that is actually present in the refreshed internal
    # Steam cache; stale callbacks cannot re-arm a failed exchange.
    il.token(0x28,T['SteamInventoryManager.Instance'])
    il.b(0x02); il.token(0x7B,T['BaseCannedItem._cachedPoolConfig']); il.token(0x7B,T['tPoolConfig.TokenId'])
    il.b(0x17); il.token(0x6F,T['SteamInventoryManager.HasItem']); il.branch(0x39,'unhandled')
    il.label('rearm')
    # The message is broadcast to every matching can widget. Only the first
    # listener in this frame may write state 2/call UpdateButtonState.
    il.token(0x72,T['KEY_AUTOCAN_REFRESH_FRAME']); il.i4(-1); il.token(0x28,T['PlayerPrefs.GetInt'])
    il.token(0x28,T['Time.frameCount']); il.branch(0x3B,'handled')
    il.token(0x72,T['KEY_AUTOCAN_REFRESH_FRAME']); il.token(0x28,T['Time.frameCount']); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.token(0x72,T['KEY_AUTOCAN_LAST_FRAME']); il.b(0x18); il.token(0x28,T['PlayerPrefs.SetInt'])
    il.b(0x02); il.token(0x6F,T['BaseCannedItem.UpdateButtonState'])
    il.label('handled'); il.b(0x17,0x2A)
    il.label('unhandled'); il.b(0x16,0x2A)
    return fat_body(il.assemble(),max_stack=3)


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
    # Install exact log format strings by equal-length in-place #US replacement.
    # Heap offsets and metadata tables remain unchanged.
    for token,old,new in (
        (T['FMT_AUTOSTEAL'],'General information','[AutoSteal] {0}/100'),
        (T['FMT_AUTOBEING'],'This is a general message','[AutoBeingStolen] {0}/100'),
    ):
        assert len(old)==len(new)
        heap_offset=token & 0x00FFFFFF
        entry_offset=dn.net.user_strings.file_offset+heap_offset
        encoded_old=old.encode('utf-16-le'); encoded_new=new.encode('utf-16-le')
        assert raw[entry_offset]==len(encoded_old)+1
        content_offset=entry_offset+1
        assert raw[content_offset:content_offset+len(encoded_old)]==encoded_old
        raw[content_offset:content_offset+len(encoded_new)]=encoded_new
    cursor=0
    def place(body):
        nonlocal cursor
        cursor=(cursor+3)&~3
        off=insert_at+cursor; rva=text.VirtualAddress+old_text_raw+cursor
        raw[off:off+len(body)]=body; cursor += len(body)
        return rva
    entries=[
        ('DataManager','Start',make_start_body(speed)),
        ('DataManager','Update',make_update_body()),
        ('CannedUI','OnEnable',make_canned_ui_on_enable_body()),
        ('CannedUI','Update',make_canned_ui_update_body()),
        ('Player','ClickStealBtn',make_steal_body()),
        ('Plant','Grow',make_grow_body(speed)),
        ('FlowerPot','CheckAutoHarvest',make_check_auto_harvest_body()),
        ('FlowerPot','AutoReplantAfterHarvest',make_auto_replant_body()),
        ('BaseCannedItem','UpdateButtonState',make_auto_can_update_button_body()),
        ('BaseCannedItem','HandleMessage',make_auto_can_handle_message_body()),
        ('tClothConfig','DeserializetClothConfig',make_legendary_cloth_config_body()),
    ]
    for typ,name,body in entries:
        rva=place(body); _,fieldoff=method_info(dn,typ,name); w32(fieldoff,rva)
    # Leave ExchangeCannedItem's original UI/busy/await/completion lifecycle
    # byte-for-byte intact. Only UpdateButtonState's F8 path is rate-limited.
    assert cursor < insert_size
    outfile.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

speeds=[1,2,5,10,20,50,500]
hashes={}
for s in speeds:
    out=MODDIR/f'Assembly-CSharp_{s}x.dll'
    hashes[str(s)]=patch(s,out)
orig_hash=hashlib.sha256(SRC.read_bytes()).hexdigest()
base_manifest=json.loads((BASE_ROOT/'hashes.json').read_text(encoding='utf-8-sig'))
latest_v17_hashes=base_manifest['variants']
original_instance_v17_hashes=base_manifest['legacy_v17_original_instance']
pre_accel_v17_hashes={
    '1':'1d47232d1f9d31fe91f127316cefa888d976d9100e04886e1bab257bc2e93c7d',
    '2':'c41d61989e1bb3d2f2e8e7582cd8adc3181c26e2375c78efa4e523d6a4f8ae8b',
    '5':'6085f4fa43687758feb30a6be5eea5ff9dccf9b613a559af7f16c12eb822d04c',
    '10':'c46f0b0bc8ee810badb351657cc514b3da7cd5a37b9e787986e8603ec4b25dd9',
    '20':'9e0270b96bd1f22ec5acf8d02c8ac70e1af086a5373ed970c5985f678d2b97c4',
    '50':'cbce1e4ea53e8b7b41ead71b87a08a7c299fe7e2f6f0e019037ff4f8dcc303b0',
}
every_frame_v17_hashes={
    '1':'3338b9e8457156d869cfbfb82998b08e37d9f192c10b3b166770f9372e91af4c',
    '2':'3cf4a1355d6b1db4ad2112cb79328692dbd9b370fc51454d1f77365badd7c91c',
    '5':'52dbf0e1ebf010cb9ff1ec7a04e4cf6eea7f55d229b1b8df16150379d75d82a7',
    '10':'746e1fb4c0ce92bbd1e61e8347415c0cd4965b1a69cc3c4e0ee41e3d8fb6baf6',
    '20':'a1822fea9c384655de53a957b8d8aff702be64bc8f382f9cb2f34ec00cc1f962',
    '50':'4ea6d68c7a69dbe9218a5f2dc06c77cdc0c8e593ed541d38c92846922766826b',
    '500':'55c2904d9cf97281c428af5e0f36dd8fa3787e2d4f79283b5748ce13e273511c',
}
autosupply_v1_hashes={
    '1':'32ae37be641f5c0f025bc35ecddf008f0b2199de8ba52fdd2b9f84cc1c4214b6',
    '2':'fc677753a35ada8be0811e48d622b18a5952de4f0aa67cac876d06aab20e6459',
    '5':'bba527cb7bdac8df0b02b30af0cae0c064a2b69390d5cfd3b72eab874a025d00',
    '10':'cfc80ce7d8158dfdce217b6cb69423559f86735c2c0add0c5a0e730eecfd353d',
    '20':'723d9fe46ab6700501281d32863fc36b0f12a920419f3597da4f16876ea9a8a0',
    '50':'61c23795d9e53f9e51c2b68cdc3152c621938b91ca4f1d30be00394d55ba715f',
    '500':'99d8afdc70dbc5b7e8692ffb296d069a6ba3572c5f8948ac76d1a22d7b1bff21',
}
autosupply_reentry_hashes={
    '1':'0ff08cd4ffc52b5b6ca60ac7d4ac588d9088f981789cd33ec1fdabb0233c96b4',
    '2':'65bb1d0b5239c0400697e6e1253245ca73ea90e0ff7f113d1ba00d99e5e7dc17',
    '5':'1aa5ef1b53740718b55f7f074f0409ea34d9ef19cddd9ec7c461250191cd99a3',
    '10':'1e6e870dc1290fc0c91f7e40d64685717cb628a8ba5afa41f3ba65cbd06a0948',
    '20':'02baf004ccae110f9d014c7eb288de62d6665a4dd5c02081e11192c9d874b4fd',
    '50':'14ec38d2c8fa6160d85ab7c157dc1a72b51c7573cd668167205105efc4bd6669',
    '500':'1d842c602f728fa1fa8e0a2ee5c2d2710a4c21583b826e01db7d512fd855b0ff',
}
autocan_guard_hashes={
    '1':'fd6acf0ea9d49185c835a0294199b99079c4c1a2c26ea1c74eee9c1e7616fba8',
    '2':'a8a2785d186e21edbe7efdf072f838bcc2e086f1255305a229609d30778b1bd1',
    '5':'527a38fbbbf0aa39a7c15a1285ebda6390f057d191be322fe5018132fa5b3efe',
    '10':'99c8e58ec7f0cacbf083b0a56e2a665443455d086aa1760e0df2d1024803ccd3',
    '20':'6a1cd0cf479f5c22810d8564a011ffa8bb534a9075db492a1e46fb32a6048f35',
    '50':'ac836311c52e12bef8f8b25461a8a46cb57d4f68d5a99761066a41f54ab037c4',
    '500':'4fd4bcb0d316faed686a4bcee791985d4193be451fcbf8d04722f2921c274625',
}
autocan_refresh_access_hashes={
    '1':'d48644adb5a4d1c8d7d1181c7ceda3666e93375cadf647170ef5e7ffd7273a93',
    '2':'998de791e226b9b1b5112a87b0ae79de83140ea3f6b42df212887959f18cee6e',
    '5':'204d6ab316ff23c43bce5b10f63fde17b52eabddff0fd476fa8856f52799d97f',
    '10':'6f6f536d24e21ed3e8c8c9ef06a970ddb2c7264c971d3942abaf04c1f388f85f',
    '20':'d62fb064e7fdab0843f626b9ebdccbd66c47ed803a857ef6af66f2bf43509e25',
    '50':'781910d8659a1ffeecf786bc62aa70dbdd36229dc84dee0ebea799ccefd812f6',
    '500':'568c54de3303c7d682390c2eab20f6cd3edcbc94cf30364fc1fa280dcf48021c',
}
autocan_entry_guard_hashes={
    '1':'9c9d444b8c93062141ccb39faeb43062b2dc24bb5592ed548ab9395d3b40d1c8',
    '2':'23a21b956de51d235521d0410713bd38b3c8037f0f5335a46b70262abd11f947',
    '5':'b15e23dddf75562f2a92af8aec465014eb675910949559034a05f891286be289',
    '10':'b4fd13873a14894dd4be0eef14c1b0b1f67a01681ad9bc1f86a2bbcc6fa02630',
    '20':'53c40fec9eaed6a2d95463d17acfd9db06c2cba6cecd8b1b4c23a9a1f6206237',
    '50':'d6752629abd9989831f4cd29bd255c9e251526e610c34c937be68a0fac233cc8',
    '500':'9c4b45c40c80e53695fb366a805c42bfd9112f0e5e39b1cacbc1abe4a6c61088',
}
autocan_shared_entry_guard_hashes={
    '1':'ff653e8e5d968e5ddc0b8d42780797c095da8f3b2a92196d8c10eadef1c35524',
    '2':'470b13e6e8ddbd17abe023f7f1ead06f22f54efd609826523cdc416084128a7a',
    '5':'6a63f18e03fe174613bd5d31cce01202e29cae3dccf7197dde69d15bbec80c75',
    '10':'d2102968e191366f430ae887f46983ca7c80c2aac92698022e5e916f4f8a2a7c',
    '20':'b6e8618e5c5e8563fdcd5b8b35f66bccc66c0844607423d7641d5e7c74fba94f',
    '50':'992423c9355046eb5938bef362256144ed71b9a2edac8f72908adb0d252824ce',
    '500':'08f5c5f0947b1ab1a22820e1289151883ef86fdb688211be92b0fac77ea600a4',
}
autocan_filtered_instance_hashes={
    '1':'cc12ddf63d2c21ddc4b0cd827418919be7b922f213eaa95f4b9def5f912bfb40',
    '2':'42b02b802015268adde12808cbf21f437f810afaf6df3288bb6ac4ef1235ad15',
    '5':'92eb78bceb77ecc02bce0e5f4e647baa435c0a1d7e2ca3be19bf334bff120685',
    '10':'245617b29afbb45003e5fb2f86d94e6d7f2e8ceef5df71af75935b6f34ebe48a',
    '20':'97686f780cd1baec33a27ddf84e6ad08c2bf657fe24863e381cda2230467741a',
    '50':'840cba40ceeeb1953a13b4eae1f7a29a4d2f30cf3f7aa0288e667238c2c4c626',
    '500':'6d811e5f02d54a5d6f9297ea8060283a814da3c5692c54096a1a75707fb9bfba',
}
autocan_event_lock_hashes={
    '1':'8ee562eee6206caf87da9961091c446d9ddd21e87cc919ec5a5a5b99531c9088',
    '2':'fb1def44c9f5f4641ea7686b64ed7a7eb2daa452a76631f21a51e3aa708d11e0',
    '5':'012c5b46bfda7b1a2fb0e28a0695fb0b6377678385cab6401baa72a73f2ff73d',
    '10':'81061028735edab8e72fcb1a0a14a5215c5885da6ab3090ebd8c72edaeb1a346',
    '20':'eab0a06465f2eeb00a09db135a69e4f90ad7b5839b0c48180e06e95088a99db9',
    '50':'f431d55e3bc80f76997ed6f6e34d4b79c777a28127e3107e11b564db2839b372',
    '500':'af497907fc473705ca9a94e3922c9ed23fef325e4a16afce5fdb7d6cc691bf41',
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
manifest=dict(base_manifest)
manifest['original']=orig_hash
manifest['legacy_v17_latest']=latest_v17_hashes
manifest['variants']=hashes
(ROOT/'hashes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

# Static validation: all methods parse, switch checks and key calls are present.
def validate(path,speed):
    raw=path.read_bytes(); pe=pefile.PE(data=raw); dn=dnfile.dnPE(str(path))
    parsed={}
    targets=[('DataManager','Start'),('DataManager','Update'),('CannedUI','OnEnable'),('CannedUI','Update'),('Player','ClickStealBtn'),('Plant','Grow'),('FlowerPot','CheckAutoHarvest'),('FlowerPot','AutoReplantAfterHarvest'),('SteamInventoryManager','GetFirstCachedInstance'),('BaseCannedItem','ExchangeCannedItem'),('BaseCannedItem','UpdateButtonState'),('BaseCannedItem','HandleMessage'),('<ExchangeCannedItem>d__13','MoveNext'),('tClothConfig','DeserializetClothConfig')]
    for typ,name in targets:
        rva,_=method_info(dn,typ,name); off=pe.get_offset_from_rva(rva)
        b=read_method_body_from_bytes(raw[off:off+10000]); assert b.code_size>0, (path,typ,name)
        parsed[(typ,name)]=b
    def toks(k): return [i.operand.value for i in parsed[k].instructions if hasattr(i.operand,'value')]
    start=toks(('DataManager','Start'))
    for tok in [T['KEY_STEAL'],T['KEY_AUTOKEY'],T['KEY_AUTOFARM'],T['KEY_AUTOCAN'],T['KEY_SPEED'],T['KEY_AUTOCAN_LAST_FRAME'],T['KEY_AUTOCAN_REFRESH_FRAME'],T['KEY_AUTOCAN_TARGET'],T['KEY_AUTOCAN_COUNT'],T['KEY_AUTOCAN_APPLIED'],T['PlayerPrefs.GetInt'],T['PlayerPrefs.SetInt'],T['PlayerPrefs.Save'],T['MessageManager.Instance'],T['MessageManager.Subscribe'],T['MarkDirtyMessage.Obtain'],T['MessageManager.Dispatch']]: assert tok in start
    for key in [T['KEY_STEAL'],T['KEY_AUTOKEY'],T['KEY_AUTOFARM'],T['KEY_AUTOCAN']]: assert start.count(key)==2
    for key in [('CannedUI','OnEnable'),('CannedUI','Update')]:
        page=toks(key)
        for tok in [T['CannedUI.UpdateDisplay'],T['MessageManager.Instance'],T['MarkDirtyMessage.Obtain'],T['MessageManager.Dispatch']]: assert tok in page
    page_update=toks(('CannedUI','Update'))
    for tok in [T['Time.get_time'],T['CannedUI._lastUpdateTime']]: assert tok in page_update
    update=toks(('DataManager','Update'))
    assert update.count(T['PlayerPrefs.SetInt'])>=10
    assert update.count(T['PlayerPrefs.GetInt'])>=9
    for key in [T['KEY_STEAL'],T['KEY_AUTOKEY'],T['KEY_AUTOFARM'],T['KEY_AUTOCAN'],T['KEY_AUTOCAN_TARGET'],T['KEY_AUTOCAN_COUNT'],T['KEY_AUTOCAN_APPLIED'],T['KEY_AUTOCAN_LAST_FRAME']]: assert key in update
    for tok in [T['KeyClickMessage.Obtain'],T['MarkDirtyMessage.Obtain'],T['FlowerPot.RemovePlant'],T['FlowerPot.PlantFlower']]: assert tok in update
    steal=toks(('Player','ClickStealBtn'))
    for tok in [T['PlayerPrefs.GetInt'],T['PlayerPrefs.SetInt'],T['PlayerPrefs.Save'],T['KEY_STEAL'],T['KEY_STOLEN_COUNT'],T['KEY_LOST_COUNT'],T['FMT_AUTOSTEAL'],T['FMT_AUTOBEING'],T['String.Format1'],T['StealResultMessage.Obtain'],T['Player.ShowStealResult'],T['DataManager.RemoveFruit'],T['FruitLostMessage.Obtain'],T['Debug.Log'],T['SteamLobbySystem.Instance'],T['SteamLobbySystem.IsNoStealing'],T['Player.steamId'],T['SendStealRequestMessage.Obtain'],T['Player.stealButton'],T['GameObject.get_gameObject'],T['GameObject.SetActive']]: assert tok in steal, (path,tok)
    assert steal.count(T['KEY_STOLEN_COUNT'])==4 and steal.count(T['KEY_LOST_COUNT'])==4
    assert sum(1 for i in parsed[('Player','ClickStealBtn')].instructions if str(i.opcode)=='bge')==2
    assert dn.net.user_strings.get(T['FMT_AUTOSTEAL'] & 0x00FFFFFF).value=='[AutoSteal] {0}/100'
    assert dn.net.user_strings.get(T['FMT_AUTOBEING'] & 0x00FFFFFF).value=='[AutoBeingStolen] {0}/100'
    auto=toks(('FlowerPot','CheckAutoHarvest'))
    for tok in [T['PlayerPrefs.GetInt'],T['PlayerPrefs.SetInt'],T['KEY_AUTOFARM'],T['KEY_STEAL'],T['KEY_STEAL_DONE'],T['Player.ClickStealBtn'],T['FlowerPot.HarvestFlower']]: assert tok in auto
    replant=toks(('FlowerPot','AutoReplantAfterHarvest'))
    for tok in [T['PlayerPrefs.GetInt'],T['PlayerPrefs.SetInt'],T['KEY_AUTOFARM'],T['KEY_STEAL_DONE'],T['FlowerPot.PlantFlower']]: assert tok in replant
    grow=toks(('Plant','Grow'))
    for tok in [T['KEY_STEAL_DONE'],T['PlayerPrefs.SetInt'],T['Plant.get_Player'],T['Player.isLocal'],T['PlantSaveData.growthValue']]: assert tok in grow
    assert any(str(i.opcode)=='ldc.r4' and abs(float(i.operand)-float(speed))<1e-6 for i in parsed[('Plant','Grow')].instructions)
    can=toks(('BaseCannedItem','UpdateButtonState'))
    assert parsed[('BaseCannedItem','UpdateButtonState')].local_var_sig_tok.value==0x11000132
    for tok in [T['PlayerPrefs.GetInt'],T['PlayerPrefs.SetInt'],T['KEY_AUTOCAN'],T['KEY_AUTOCAN_TARGET'],T['KEY_AUTOCAN_COUNT'],T['KEY_AUTOCAN_APPLIED'],T['KEY_AUTOCAN_LAST_FRAME'],T['BaseCannedItem.CheckInventorySufficient'],T['BaseCannedItem.ExchangeCannedItem'],T['Selectable.set_interactable'],T['Behaviour.get_isActiveAndEnabled']]: assert tok in can
    for tok in [T['SteamInventoryManager.HasItem'],T['SteamInventoryManager.GetFirstCachedInstance'],T['Type.NullableSteamItemInstanceId']]: assert tok not in can
    assert T['RealtimeClock.ElapsedMilliseconds'] not in can and 0x0A00003D not in can and 0x0600046C not in can
    assert T['FlowerPot.RemovePlant'] not in can and T['FlowerPot.PlantFlower'] not in can
    assert not any(str(i.opcode)=='blt.un' for i in parsed[('BaseCannedItem','UpdateButtonState')].instructions)
    assert can.count(T['KEY_AUTOCAN_LAST_FRAME'])==4 and can.count(T['PlayerPrefs.SetInt'])>=8
    can_ins=parsed[('BaseCannedItem','UpdateButtonState')].instructions
    exchange_i=next(i for i,x in enumerate(can_ins) if getattr(x.operand,'value',None)==T['BaseCannedItem.ExchangeCannedItem'])
    assert [str(x.opcode) for x in can_ins[exchange_i-4:exchange_i+1]]==['ldstr','ldc.i4.1','call','ldarg.0','callvirt']
    assert getattr(can_ins[exchange_i-4].operand,'value',None)==T['KEY_AUTOCAN_LAST_FRAME']
    assert getattr(can_ins[exchange_i-2].operand,'value',None)==T['PlayerPrefs.SetInt']
    assert can.count(T['List.get_Item'])==2 and can.count(T['List.get_Count'])>=3
    assert any(str(i.opcode)=='add' for i in can_ins)
    first_rva,_=method_info(dn,'SteamInventoryManager','GetFirstCachedInstance')
    first_body=parsed[('SteamInventoryManager','GetFirstCachedInstance')]
    first_off=pe.get_offset_from_rva(first_rva)
    assert first_rva==0x126DC and first_body.code_size==78
    assert hashlib.sha256(raw[first_off:first_off+90]).hexdigest()=='2bce2ef45876d35b9592705367b3c9fdef90dd1eed1ccedaaf68cb4174e9f759'
    entry=toks(('BaseCannedItem','ExchangeCannedItem'))
    assert parsed[('BaseCannedItem','ExchangeCannedItem')].code_size==43
    assert entry==[T['ExchangeState.BuilderCreate'],T['ExchangeState.Builder'],T['ExchangeState.This'],T['ExchangeState.State'],T['ExchangeState.Builder'],T['ExchangeState.Start']]
    handle=toks(('BaseCannedItem','HandleMessage'))
    for tok in [T['Type.SteamInventoryExchangedMessage'],T['SteamInventoryExchangedMessage.success'],T['SteamInventoryExchangedMessage.consumeItemId'],T['Type.SteamItemDropMessage'],T['SteamItemDropMessage.itemDetails'],T['SteamInventoryItem.ctor.Details'],T['SteamInventoryItem.get_DefinitionId'],T['BaseCannedItem.UpdateButtonState'],T['BaseCannedItem._isExchanging'],T['Behaviour.get_isActiveAndEnabled'],T['SteamInventoryManager.Instance'],T['SteamInventoryManager.HasItem'],T['PlayerPrefs.GetInt'],T['PlayerPrefs.SetInt'],T['Time.frameCount'],T['KEY_AUTOCAN_REFRESH_FRAME'],T['KEY_AUTOCAN_LAST_FRAME']]: assert tok in handle
    assert T['Type.SteamInventoryRefreshedMessage'] not in handle
    assert handle.count(T['PlayerPrefs.SetInt'])==2 and handle.count(T['KEY_AUTOCAN_LAST_FRAME'])==1 and handle.count(T['KEY_AUTOCAN_REFRESH_FRAME'])==2
    async_body=parsed[('<ExchangeCannedItem>d__13','MoveNext')]
    async_by_offset={ins.offset:ins for ins in async_body.instructions}
    original_gate={0x2D:'ldloc.1',0x2E:'ldfld',0x33:'ldnull',0x34:'call',0x39:'brfalse.s',0x3B:'ldloc.1',0x3C:'ldfld',0x41:'callvirt',0x46:'brtrue.s',0x48:'leave'}
    for off,opcode in original_gate.items(): assert str(async_by_offset[off].opcode)==opcode, (path,hex(off),str(async_by_offset[off].opcode),opcode)
    rarity=parsed[('tClothConfig','DeserializetClothConfig')]
    rt=toks(('tClothConfig','DeserializetClothConfig'))
    assert T['tClothConfig.ctor'] in rt and T['tClothConfig.Rarity'] in rt
    assert any(str(i.opcode)=='ldc.i4.4' for i in rarity.instructions)
for s in speeds: validate(MODDIR/f'Assembly-CSharp_{s}x.dll',s)

# Build the v1.8 package from the latest published v1.7 installer template.
# The historical v1.7 generator below is retained only as unreachable archival
# reference; this block completes the package and exits before that code.
def map_block_v18(name,m):
    lines=[f'${name} = @{{']
    for key in ['1','2','5','10','20','50','500']:
        lines.append(f'    "{key}" = "{m[key]}"')
    lines.append('}')
    return '\n'.join(lines)

ps1=(BASE_ROOT/'Tools'/'ModManager.ps1').read_text(encoding='utf-8-sig')
new_variant_block=map_block_v18('variantHashes',hashes)
ps1=re.sub(r'\$variantHashes = @\{.*?\n\}',new_variant_block,ps1,count=1,flags=re.S)
legacy_latest_block=map_block_v18('legacyV17LatestHashes',latest_v17_hashes)
if '$legacyV17LatestHashes = @{' in ps1:
    ps1=re.sub(r'\$legacyV17LatestHashes = @\{.*?\n\}',legacy_latest_block,ps1,count=1,flags=re.S)
else:
    ps1=ps1.replace(new_variant_block,new_variant_block+'\n\n'+legacy_latest_block,1)
legacy_original_instance_block=map_block_v18('legacyV17OriginalInstanceHashes',original_instance_v17_hashes)
if '$legacyV17OriginalInstanceHashes = @{' in ps1:
    ps1=re.sub(r'\$legacyV17OriginalInstanceHashes = @\{.*?\n\}',legacy_original_instance_block,ps1,count=1,flags=re.S)
else:
    ps1=ps1.replace(legacy_latest_block,legacy_latest_block+'\n\n'+legacy_original_instance_block,1)

detect_head='function Detect-Legacy-V17-Speed([string]$Hash) {'
legacy_loop='''
    foreach ($key in $legacyV17LatestHashes.Keys) {
        if ($legacyV17LatestHashes[$key] -eq $Hash) { return [int]$key }
    }'''
if legacy_loop.strip() not in ps1:
    ps1=ps1.replace(detect_head,detect_head+legacy_loop,1)
legacy_original_instance_loop='''
    foreach ($key in $legacyV17OriginalInstanceHashes.Keys) {
        if ($legacyV17OriginalInstanceHashes[$key] -eq $Hash) { return [int]$key }
    }'''
if legacy_original_instance_loop.strip() not in ps1:
    ps1=ps1.replace(legacy_loop,legacy_loop+legacy_original_instance_loop,1)

old_uninstall='''    if ($Mode -eq 'Uninstall') {
        if (-not (Test-Path -LiteralPath $backup)) { throw 'Backup file not found. Use Steam Verify Integrity to restore the original game file.' }
        $backupHash = Get-Hash $backup
        if ($backupHash -ne $originalHash) { throw 'The backup hash is not the expected original version. It was not restored for safety.' }
        Copy-Item -LiteralPath $backup -Destination $target -Force
        if ((Get-Hash $target) -ne $originalHash) { throw 'Uninstall copy verification failed.' }
        Remove-Item -LiteralPath (Join-Path $root 'MeowMyCrop_Mod_Settings.txt') -ErrorAction SilentlyContinue
        Show-Result 'MOD uninstalled successfully. The original Assembly-CSharp.dll was restored.' 'Meow My Crop MOD' 'Success'
        exit 0
    }'''
safe_uninstall='''    if ($Mode -eq 'Uninstall') {
        if ($currentHash -eq $originalHash) {
            Remove-Item -LiteralPath (Join-Path $root 'MeowMyCrop_Mod_Settings.txt') -ErrorAction SilentlyContinue
            Show-Result 'The supported original Assembly-CSharp.dll is already installed. No game file was overwritten.' 'Meow My Crop MOD' 'Success'
            exit 0
        }
        $isKnownManagedMod = ($installedSpeed -gt 0) -or ($legacyV12Speed -gt 0) -or ($legacyV13Speed -gt 0) -or ($legacyV14Speed -gt 0) -or ($legacyV15Speed -gt 0) -or ($legacyV16Speed -gt 0) -or ($legacyV17Speed -gt 0) -or $isLegacyV10
        if (-not $isKnownManagedMod) { throw 'The current Assembly-CSharp.dll is not a known MeowMOD file. It may belong to a game update or another MOD, so it was not overwritten.' }
        if (-not (Test-Path -LiteralPath $backup)) { throw 'Backup file not found. Use Steam Verify Integrity to restore the original game file.' }
        $backupHash = Get-Hash $backup
        if ($backupHash -ne $originalHash) { throw 'The backup hash is not the expected original version. It was not restored for safety.' }
        Copy-Item -LiteralPath $backup -Destination $target -Force
        if ((Get-Hash $target) -ne $originalHash) { throw 'Uninstall copy verification failed.' }
        Remove-Item -LiteralPath (Join-Path $root 'MeowMyCrop_Mod_Settings.txt') -ErrorAction SilentlyContinue
        Show-Result 'MOD uninstalled successfully. The original Assembly-CSharp.dll was restored.' 'Meow My Crop MOD' 'Success'
        exit 0
    }'''
if old_uninstall not in ps1:
    raise AssertionError('v1.7 uninstall block changed unexpectedly')
ps1=ps1.replace(old_uninstall,safe_uninstall,1)

unknown_guard='''    if (($currentHash -ne $originalHash) -and ($installedSpeed -eq 0) -and ($legacyV12Speed -eq 0) -and ($legacyV13Speed -eq 0) -and ($legacyV14Speed -eq 0) -and ($legacyV15Speed -eq 0) -and ($legacyV16Speed -eq 0) -and ($legacyV17Speed -eq 0) -and (-not $isLegacyV10)) {
        throw 'This Assembly-CSharp.dll is neither the supported original file nor a known v1.0/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7 MOD file. The game may have updated or another MOD may already modify it.'
    }'''
installed_v18_backup_guard='''    if ($installedSpeed -gt 0) {
        if (-not (Test-Path -LiteralPath $backup)) { throw 'MeowMOD v1.8 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'MeowMOD v1.8 backup hash is unexpected. It was not overwritten for safety.' }
    }'''
if unknown_guard not in ps1:
    raise AssertionError('v1.7 unknown-file guard changed unexpectedly')
ps1=ps1.replace(unknown_guard,unknown_guard+'\n'+installed_v18_backup_guard,1)

backup_copy='''            Copy-Item -LiteralPath $target -Destination $backup -Force
            Write-Host "Original backup created: $backup" -ForegroundColor Yellow'''
verified_backup_copy='''            Copy-Item -LiteralPath $target -Destination $backup -Force
            if ((Get-Hash $backup) -ne $originalHash) { throw 'Original backup verification failed. The MOD was not installed.' }
            Write-Host "Original backup created and verified: $backup" -ForegroundColor Yellow'''
if backup_copy not in ps1:
    raise AssertionError('v1.7 first-install backup block changed unexpectedly')
ps1=ps1.replace(backup_copy,verified_backup_copy,1)

ps1=ps1.replace('known v1.0/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7 MOD file',
                'known v1.0/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7/v1.8 MOD file')
ps1=ps1.replace('upgraded directly to v1.7','upgraded directly to v1.8')
ps1=ps1.replace('then install v1.7','then install v1.8')
ps1=ps1.replace('v1.7 will preserve','v1.8 will preserve')
ps1=ps1.replace('v1.7 will repair','v1.8 will repair')
ps1=ps1.replace('Meow My Crop! MOD Manager v1.7','Meow My Crop! MOD Manager v1.8')
ps1=ps1.replace('Enter 1-7 [default: 4 / ${DefaultSpeed}x]',
                'Enter 1-7, or press Enter to keep ${DefaultSpeed}x')
ps1=ps1.replace('Detected earlier v1.7 (${legacyV17Speed}x). Updating to the repaired safe automatic can logic.',
                'Detected v1.7 (${legacyV17Speed}x). Updating to v1.8 with independent 100-count limits and saved F8 state.')
ps1=ps1.replace('v1.7 adds four independent persistent feature switches.',
                'v1.8 adds independent 100-count limits, exact counter logs, and full recipe shortage scanning.')
ps1=ps1.replace('v1.6 adds automatic can opening and local Legendary/orange decoration rarity.',
                'v1.8 includes automatic can opening and local Legendary/orange decoration rarity.')
ps1=ps1.replace('v1.5 removes the one-fruit skip and guarantees automatic steal/lost events.',
                'v1.8 preserves automatic steal/lost events without the one-fruit skip.')
ps1=ps1.replace("'Meow My Crop! AutoFarm MOD v1.7'","'Meow My Crop! MeowMOD v1.8'")
ps1=ps1.replace("$verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MOD v1.7 installed' }",
                "$verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MeowMOD v1.8 installed' }")
settings_anchor="        'All four switches default to enabled on first run',"
settings_extra="""        'All four switches default to enabled on first run',
        'AutomaticStealLimit=100 (saved independently)',
        'AutomaticBeingStolenLimit=100 (saved independently)',
        'CounterLogs=[AutoSteal] n/100 and [AutoBeingStolen] n/100',
        'AutoCanRecipeScan=All required fruit entries',
        'GrowthMultiplier=Saved in MOD PlayerPrefs config',"""
ps1=ps1.replace(settings_anchor,settings_extra,1)
old_success='Show-Result "$verb successfully.`nGrowth speed: ${speed}x`n`nIndependent persistent switches (default ON):`nF5 = steal + being-stolen`nF6 = internal automatic key delivery`nF7 = automatic harvest + replant`nF8 = automatic can opening + missing-fruit crop supply`n`nWhen a can lacks fruit, the current wrong crop is removed and the required crop is planted with synchronized visuals. Manual keyboard/mouse input and the manual can button remain usable."'
new_success='Show-Result "$verb successfully.`nGrowth speed: ${speed}x`n`nF5 = automatic steal + being-stolen (each stops at saved 100)`nF6 = internal automatic key delivery`nF7 = automatic harvest + replant`nF8 = automatic can opening + full missing-fruit scan`n`nF5 logs: [AutoSteal] n/100 and [AutoBeingStolen] n/100.`nManual online stealing, keyboard/mouse input, and the manual can button remain usable."'
ps1=ps1.replace(old_success,new_success)
(TOOLSDIR/'ModManager.ps1').write_text('\ufeff'+ps1,encoding='utf-8')

for fname in ['1_INSTALL_MOD.cmd','2_CHANGE_SPEED.cmd','3_UNINSTALL_MOD.cmd']:
    p=ROOT/fname; txt=p.read_text(encoding='ascii')
    txt=txt.replace('v1.7','v1.8')
    txt=txt.replace('Adds four independent persistent feature switches: F5/F6/F7/F8.',
                    'Adds saved 100 limits, full can shortage analysis, and F5/F6/F7/F8 controls.')
    p.write_text(txt,encoding='ascii',newline='')

readme_cn='''MeowMOD v1.8 —《喵了个菜！ / Meow My Crop!》
===================================================

功能与按键
----------
F5：自动偷菜＋自动被偷菜
    - 两项各自独立累计，分别达到 100 后停止，不会出现 101。
    - 每个本地成熟作物周期最多触发一次，远程作物不会重置一次锁。
    - 数量和开关写入 Unity PlayerPrefs，退出游戏后保留。
    - Player.log 精确记录：[AutoSteal] n/100、[AutoBeingStolen] n/100。
    - 联机时手动点击远程玩家偷菜仍走原版网络流程，不受 F5 影响。

F6：自动按键输送
    - 每个游戏帧内部发送一次 A 键成长消息。
    - 不移动、不捕获鼠标，不阻断真实键盘或鼠标输入。

F7：自动种植收获
    - 控制普通自动收获与自动补种。
    - 关闭后仍可手动种植、收获；F6、F8 不受影响。

F8：自动开罐
    - 检测当前罐头配方的全部所需果实，不再只检查前两项。
    - 缺料时锁定缺少的果实；盆中作物不对则自动铲除、换种、收获补料。
    - 材料满足后调用原版开罐入口，并保留失败锁与成功后单次重放行，防止递归和重复请求。
    - 关闭 F8 后手动“开罐”按钮仍走原版路径。
    - F8 状态现在会跨重启保存，不再每次进入游戏强制开启。

配置与倍率
------------
- F5/F6/F7/F8 首次默认开启，之后分别保存。
- 保存 1x / 2x / 5x / 10x / 20x / 50x / 500x 的已安装倍率。
- 保存自动偷菜、自动被偷菜的累计统计。
- 安装器会识别当前 v1.7 并保留原倍率升级；原版备份与卸载恢复逻辑保留。

安装
----
1. 完全退出游戏。
2. 解压 ZIP，双击 1_INSTALL_MOD.cmd。
3. 选择生长倍率；安装后用 F5～F8 独立控制功能。

重要说明
--------
- 本 MOD 直接替换 MeowMyCrop_Data\\Managed\\Assembly-CSharp.dll，不是 BepInEx 插件。
- 装饰会在客户端本地按橙色 Legendary 品质显示和分类；Steam 服务器库存品质不会被篡改。
- 构建已完成 PE、元数据、方法体、关键调用、原版手动开罐路径和哈希静态校验；仍需在 Windows 游戏内查看 Player.log 完成运行验证。
'''
(ROOT/'README_CN.txt').write_text('\ufeff'+readme_cn,encoding='utf-8')

readme_en='''# MeowMOD v1.8 for Meow My Crop!

- F5: local automatic steal and being-stolen simulation, independently persisted and capped at 100 each. Exact logs: `[AutoSteal] n/100` and `[AutoBeingStolen] n/100`.
- F6: internal A-key growth delivery without moving or capturing the mouse.
- F7: automatic harvest and replant.
- F8: automatic can shortage detection, complete recipe scanning, crop replacement, supply harvest, and guarded automatic opening.
- F5 through F8 are independent and persisted. The selected 1x/2x/5x/10x/20x/50x/500x growth multiplier is persisted too.
- The original remote/manual online steal path and original manual can-opening path remain available.

Run `1_INSTALL_MOD.cmd` after fully closing the game. Local Legendary/orange decoration rarity is a client display/classification override only; it does not alter Steam server inventory rarity.
'''
(ROOT/'README.md').write_text(readme_en,encoding='utf-8')

notes='''MeowMOD v1.8 implementation notes
- Rebuilt from the supported original Assembly-CSharp.dll SHA256 ad00d6dd37d0ee222e5506e9a4b697c5b5bf10fa3673843cde68b9760654e954.
- F5 local automation has independent persisted total_stolen_fruits and total_lost_fruits counters, each capped at 100.
- Exact counter log strings are installed by equal-length #US replacement without moving metadata offsets.
- Original remote/manual online Player.ClickStealBtn behavior is preserved outside the local F5 branch.
- Per-crop duplicate protection resets only for a newly growing local crop; remote crops cannot unlock it.
- F8 is no longer forced enabled at process start. All four toggle values and the selected multiplier are persisted.
- Auto-can shortage analysis scans the complete required-fruit list.
- SteamInventoryManager.GetFirstCachedInstance, BaseCannedItem.ExchangeCannedItem, and its async state machine retain the supported original behavior.
- Automatic opening still uses active-widget filtering, a three-state retry latch, event de-duplication, and the original manual button path.
- Legendary/orange decoration rarity remains a local display/classification override only.

SHA256 variants:
'''+json.dumps(hashes,indent=2)+'\n'
(SOURCEDIR/'PATCH_NOTES.txt').write_text(notes,encoding='utf-8')

for obsolete in ['build_meow_v15.py','build_meow_v16.py','build_meow_v17.py']:
    p=SOURCEDIR/obsolete
    if p.exists(): p.unlink()
cache_dir=SOURCEDIR/'__pycache__'
if cache_dir.exists(): shutil.rmtree(cache_dir)

zip_path=Path(os.environ.get('MEOW_ZIP', ROOT.parent/'MeowMOD_v1.8.zip')).resolve()
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(ROOT.rglob('*')):
        if f.is_file(): z.write(f,f.relative_to(ROOT))
print(json.dumps({'root':str(ROOT),'zip':str(zip_path),'hashes':hashes},ensure_ascii=False,indent=2))
raise SystemExit(0)

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
ps1=ps1[:idx]+map_block('legacyV17AutoCanEventLockHashes',autocan_event_lock_hashes)+'\n\n'+map_block('legacyV17AutoCanFilteredInstanceHashes',autocan_filtered_instance_hashes)+'\n\n'+map_block('legacyV17AutoCanSharedEntryGuardHashes',autocan_shared_entry_guard_hashes)+'\n\n'+map_block('legacyV17AutoCanEntryGuardHashes',autocan_entry_guard_hashes)+'\n\n'+map_block('legacyV17AutoCanRefreshAccessHashes',autocan_refresh_access_hashes)+'\n\n'+map_block('legacyV17AutoCanGuardHashes',autocan_guard_hashes)+'\n\n'+map_block('legacyV17AutoSupplyReentryHashes',autosupply_reentry_hashes)+'\n\n'+map_block('legacyV17AutoSupplyV1Hashes',autosupply_v1_hashes)+'\n\n'+map_block('legacyV17EveryFrameHashes',every_frame_v17_hashes)+'\n\n'+map_block('legacyV17Hashes',pre_accel_v17_hashes)+'\n\n'+map_block('legacyV17Fast2Hashes',fast2_v17_hashes)+'\n\n'+map_block('legacyV17Fast4Hashes',fast4_v17_hashes)+'\n\n'+map_block('legacyV16Hashes',v16_hashes)+'\n\n'+ps1[idx:]
needle='function Detect-Legacy-V15-Speed([string]$Hash) {'
pos=ps1.find(needle); end=ps1.find('\n}\n',pos)+3
block=ps1[pos:end]
block16=block.replace('Detect-Legacy-V15-Speed','Detect-Legacy-V16-Speed').replace('$legacyV15Hashes','$legacyV16Hashes')
block17=block.replace('Detect-Legacy-V15-Speed','Detect-Legacy-V17-Speed').replace('$legacyV15Hashes','$legacyV17Hashes')
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17AutoCanEventLockHashes.Keys) {\n        if ($legacyV17AutoCanEventLockHashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17AutoCanFilteredInstanceHashes.Keys) {\n        if ($legacyV17AutoCanFilteredInstanceHashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17AutoCanSharedEntryGuardHashes.Keys) {\n        if ($legacyV17AutoCanSharedEntryGuardHashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17AutoCanEntryGuardHashes.Keys) {\n        if ($legacyV17AutoCanEntryGuardHashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17AutoCanRefreshAccessHashes.Keys) {\n        if ($legacyV17AutoCanRefreshAccessHashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17AutoCanGuardHashes.Keys) {\n        if ($legacyV17AutoCanGuardHashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17AutoSupplyV1Hashes.Keys) {\n        if ($legacyV17AutoSupplyV1Hashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17AutoSupplyReentryHashes.Keys) {\n        if ($legacyV17AutoSupplyReentryHashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17EveryFrameHashes.Keys) {\n        if ($legacyV17EveryFrameHashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17Fast2Hashes.Keys) {\n        if ($legacyV17Fast2Hashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
block17=block17.replace('    return 0\n}', "    foreach ($key in $legacyV17Fast4Hashes.Keys) {\n        if ($legacyV17Fast4Hashes[$key] -eq $Hash) { return [int]$key }\n    }\n    return 0\n}")
ps1=ps1[:pos]+block17+'\n'+block16+'\n'+ps1[pos:]
ps1=ps1.replace('$legacyV15Speed = Detect-Legacy-V15-Speed $currentHash', '$legacyV15Speed = Detect-Legacy-V15-Speed $currentHash\n    $legacyV16Speed = Detect-Legacy-V16-Speed $currentHash\n    $legacyV17Speed = Detect-Legacy-V17-Speed $currentHash')
ps1=ps1.replace('($legacyV15Speed -eq 0) -and (-not $isLegacyV10)', '($legacyV15Speed -eq 0) -and ($legacyV16Speed -eq 0) -and ($legacyV17Speed -eq 0) -and (-not $isLegacyV10)')
needle='    if ($legacyV15Speed -gt 0) {'
insert_upgrades='''    if ($legacyV17Speed -gt 0) {
        Write-Host "Detected earlier v1.7 (${legacyV17Speed}x). Updating to the repaired safe automatic can logic." -ForegroundColor Yellow
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
    - 每个游戏帧自动发送一次 A 键成长消息（60 FPS 下约每秒 60 次），不再使用间隔帧。
    - 关闭后停止 MOD 内部自动发送 A 键成长消息。
    - 不影响你的真实键盘、鼠标输入，也不会抢鼠标。

F7：自动种植收获
    - 关闭后停止自动收获和自动补种。
    - 作物仍可通过真实输入或 F6 自动按键继续生长。
    - 你仍可以手动收获、手动种植。

F8：自动开罐
    - 每次进入游戏都会自动开启；本局按 F8 可以关闭，下次进入游戏会再次自动开启。
    - 进入罐头页时立即检查配方缺料；页面可见期间每秒重检，避免初始化顺序导致换种任务丢失。
    - 关闭后停止自动连续开罐。
    - 缺少开罐果实时，自动锁定一种缺料果实。
    - 如果盆中不是目标作物，则自动铲除并种植所需作物，再自动收获补料。
    - 在罐头页面按 F8 开启时会立即重检当前配方，并清除旧目标；无需等待下一次收获或库存刷新。
    - 只有当前可见并启用的罐头页面可以领取自动补料与开罐任务；隐藏页面不会抢占任务。
    - 换种后目标作物、成长阶段、进度和动画会立即按真实状态刷新。
    - 补料期间即使 F7 暂停，F8 仍会完成目标作物的收获和补种。
    - F8 只以当前配方果实是否充足作为自动开罐条件，不增加“开罐券”或其他玩家侧门槛。
    - 果实充足后调用游戏原版开罐入口；内部兑换失败时会锁住自动重试，避免递归、连发或卡死。
    - F8 是连续模式：每次成功只放行一个新尝试；只要配方果实仍充足就会继续。按 F8 关闭即可停止。
    - 罐头页面的手动“开罐”按钮使用游戏原版入口，不受 MOD 自动重试锁限制。

开关规则
--------
- F5～F7 首次运行默认开启，并继续保存你的开关状态。
- F8 每次进入游戏都会重置为开启；本局仍可按 F8 临时关闭。
- 每个开关互不影响。
- 状态通过 Unity PlayerPrefs 保存；F8 的保存值会在下次进入游戏时自动改为开启。
- 按键后 Player.log 会出现下列状态名和 0/1：
  steal_request：F5，0=关闭，1=开启
  total_key_clicks：F6，0=关闭，1=开启
  FarmingCat：F7，0=关闭，1=开启
  Canned：F8，0=关闭，1=开启

保留功能
--------
- 指定作物种一次后自动收获并持续补种同一种作物。
- 1x / 2x / 5x / 10x / 20x / 50x / 500x（极高速）生长速度。
- 离线自动偷菜和自动被偷菜。
- 自动开罐。
- 装饰在本地按橙色 Legendary 品质显示和分类。

安装
----
1. 完全退出游戏。
2. 解压后双击 1_INSTALL_MOD.cmd。
3. 安装完成后进入游戏，使用 F5～F8 分别开关四项功能。

重要说明
--------
罐头奖励仍由 Steam Inventory 决定。橙色品质修改是客户端本地显示与分类覆盖，不能把 Steam 服务器库存里的普通物品真正改造成可交易的传奇物品。
'''
(ROOT/'README_CN.txt').write_text('\ufeff'+readme,encoding='utf-8')
notes=f'''v1.7 implementation notes
- Adds four independent persistent PlayerPrefs switches, all default enabled:
  F5 steal/lost, F6 internal key delivery, F7 auto harvest/replant, F8 auto can opening.
- F8 is reset to enabled in DataManager.Start on every game launch. It can still be disabled for the current session; the next launch enables it again and clears stale auto-can task/latch state.
- CannedUI dispatches a normal MarkDirty recipe check on page enable and once per second while visible, closing the initialization-order gap that could leave the auto-supply target empty.
- SteamInventoryManager.GetFirstCachedInstance is restored byte-for-byte to the original game implementation; the stricter MOD scan could reject internal definition 100002 and break manual and automatic opening.
- Player.log records growTrigger when a missing recipe fruit is selected and stageSprite when the target crop is planted.
- Player.ClickStealBtn itself is gated, so the steal/lost feature is fully paused when disabled.
- F5 steal/lost remains independent when F7 auto-farm is paused: a per-crop marker prevents repeated events on the same mature crop.
- F7 gates normal harvesting and replanting; an active F8 supply target can still harvest/replant until its shortage is filled.
- F8 locks one missing recipe fruit at a time and stores its required inventory count.
- Toggling F8 clears any stale supply target and dispatches the game's normal MarkDirty message so an already-open can page immediately re-evaluates its recipe.
- BaseCannedItem automation is gated by Behaviour.isActiveAndEnabled, so hidden can tabs cannot claim the shared supply/opening latch.
- Inventory callbacks only select/release targets. Crop removal and planting run on the next DataManager.Update frame, after HarvestFlower has returned, preventing callback re-entry.
- No private FlowerPot animation method is called. PlantFlower/Plant.Start and Grow/SetStage provide the real crop, stage, progress and animation visuals.
- F8-off, completed and stale targets clear target/count/applied state so a changed can page cannot remain permanently locked.
- Auto-can off preserves button interactability and manual opening.
- The manual ExchangeCannedItem entry remains byte-for-byte original and is never blocked by MOD automatic retry locking.
- The F8 guard is a three-state latch: 0 armed, 1 in-flight/failed, 2 re-armed by a matching successful exchange or real Steam item drop. Generic refresh, FruitUpdate and MarkDirty never re-arm failure state 1.
- A Steam item-drop callback can re-arm only when the visible can is idle and the refreshed internal inventory actually contains the matching item; stale/repeated callbacks cannot overwrite an in-flight lock.
- Successful exchange/drop broadcast de-dup uses a private PlayerPrefs key backed by the otherwise log-only string token 0x70003F50; only one can widget may consume each event in a frame.
- GetFirstCachedInstance scans all indexed candidates and requires DefinitionId equality, Quantity > 0 and a GetInstanceIdValue that is neither zero nor UInt64.MaxValue before returning an instance.
- The original async MoveNext state machine, UI interactable gate, busy state, await path and visual completion lifecycle remain byte-for-byte intact.
- SteamInventoryManager keeps its original refresh routine; BaseCannedItem does not use generic SteamInventoryRefreshedMessage to unlock automatic retry and calls no private manager method.
- F8 is intentionally continuous: each confirmed success can authorize exactly one next attempt while the recipe fruit remains sufficient.
- Removes the invalid cross-type CheckAutoRefresh call that caused repeated MethodAccessException errors when opening the can page.
- Automatic opening is gated only by recipe fruit sufficiency and calls the untouched original exchange entry; no extra player-facing coupon check is introduced.
- Existing v1.6 Legendary/orange local rarity override is preserved.
- F6 internal A-key delivery sends exactly once per game frame with no interval-frame gate.
- Adds a 500x extreme growth variant while retaining the original 1x through 50x choices.
- Installer recognizes all earlier v1.7 hashes, including the 500x every-frame build, and preserves the selected growth multiplier during upgrade.

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
