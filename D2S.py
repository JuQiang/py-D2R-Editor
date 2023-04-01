from ItemQuality import ItemQuality
from ItemStat import ItemStat
from Item import Item
from Corpse import Corpse
import os

class D2S(object):
    index = 0
    buf = []

    def __init__(self,file_name):
        self.init_buffer_by_file(file_name)

        self.cost_txt = self.get_txt("itemstatcost.txt", 1)
        self.armor_txt = self.get_txt("armor.txt", 18)
        self.misc_txt = self.get_txt("misc.txt", 14)
        self.weapons_txt = self.get_txt("weapons.txt", 3)
        self.item_txt = {**self.armor_txt, **self.misc_txt, **self.weapons_txt}

    def get_1_byte(self):
        return self.get_bits(8)

    def get_2_bytes(self):
        return self.get_bits(16)

    def get_4_bytes(self):
        return self.get_bits(32)

    def get_string(self,len):
        s = []
        for i in range(0, len):
            s.append(self.get_1_byte())

        return bytes(s).decode().replace("\x00", "")

    def access_bit(self,data, num):
        base = int(num // 8)
        shift = int(num % 8)
        return (data[base] >> shift) & 0x1

    def get_bits(self,length):
        r = 0
        for i in range(length,0,-1):
            r = (r << 1) | self.buf[self.index+i - 1]

        self.index += length
        return r

    def get_bits2(self,array):
        r = 0
        for i in range(len(array), 0, -1):
            r = (r << 1) | array[i - 1]

        self.index += len(array)
        return r

    def decode_by_huffman(self):
        mappings = {"111101000": '\0', "01": ' ', "11011111": '0', "0011111": '1',
                    "001100": '2', "1011011": '3', "01011111": '4', "01101000": '5',
                    "1111011": '6', "11110": '7', "001000": '8', "01110": '9',
                    "01111": 'a', "1010": 'b', "00010": 'c', "100011": 'd',
                    "000011": 'e', "110010": 'f', "01011": 'g', "11000": 'h',
                    "0111111": 'i', "011101000": 'j', "010010": 'k', "10111": 'l',
                    "10110": 'm', "101100": 'n', "1111111": 'o', "10011": 'p',
                    "10011011": 'q', "00111": 'r', "0100": 's', "00110": 't',
                    "10000": 'u', "0111011": 'v', "00000": 'w', "11100": 'x',
                    "0101000": 'y', "00011011": 'z'}

        code_key = ""
        for i in range(0, 10):
            code_key += str(self.buf[self.index + i])
            key = ''.join(list(reversed(code_key)))
            if key in mappings.keys():
                return mappings[key], i + 1

        raise Exception("Key not found in huffman tree.")

    def get_txt(self,fname, id_col):
        txt = {}
        lines = open(fname).readlines()
        cols = lines[0].split("\t")
        for i in range(1, len(lines)):
            stats = lines[i].split("\t")
            id = stats[id_col]
            txt[id] = {}
            for j in range(0, len(stats)):
                txt[id][cols[j]] = stats[j]

        return txt

    def init_buffer_by_file(self, file_name):
        fsize = os.path.getsize(file_name)

        f = open(file_name, "rb")
        content = f.read(fsize)
        f.close()

        self.buf = [self.access_bit(content, i) for i in range(len(content) * 8)]

    def get_item_stat_list(self):
        stat_list = []

        id = self.get_bits(9)
        while id != 0x1ff:
            property = self.cost_txt.get(str(id), None)
            if property is None:
                raise Exception("Property not found for id:{}".format(id))
            stat_list.append(self.get_item_stat(property, id))

            if id in [52, 17, 48, 50]:
                property = self.cost_txt.get(str(id+1), None)
                stat_list.append(self.get_item_stat(property, id + 1))
            elif id in [54, 57]:
                property = self.cost_txt.get(str(id+1), None)
                stat_list.append(self.get_item_stat(property, id + 1))
                property = self.cost_txt.get(str(id+2), None)
                stat_list.append(self.get_item_stat(property, id + 2))
            id = self.get_bits(9)

        return stat_list

    def get_item_stat(self,property, id):
        item_stat = ItemStat()

        item_stat.Id = id
        item_stat.Stat = property["Stat"]
        save_param_bit_count = self.get_int(property["Save Param Bits"])
        encode = self.get_int(property["Encode"])

        if save_param_bit_count != 0:
            save_param = self.get_bits(save_param_bit_count)
            if int(property["descfunc"]) == 14:
                item_stat.SkillTab = save_param & 7
                item_stat.SkillLevel = (save_param >> 3) & 0x1fff

            match encode:
                case 2 | 3:
                    item_stat.SkillLevel = save_param & 0x3f
                    item_stat.SkillId = (save_param >> 6) & 0x3ff
                case _:
                    item_stat.Param = save_param

        save_bits = self.get_bits(self.get_int(property["Save Bits"]))
        save_bits -= self.get_int(property["Save Add"])
        if encode == 3:
            item_stat.MaxCharges = (save_bits >> 8) & 0xff
            item_stat.Value = save_bits & 0xff
        else:
            item_stat.Value = save_bits

        return item_stat

    def get_int(self,value: str):
        return 0 if value.strip() == "" else int(value)

    def parse(self):
        self.index = 0

        self.Signature = self.get_4_bytes()
        self.Version = self.get_4_bytes()
        self.FileSize = self.get_4_bytes()
        self.CheckSum = self.get_4_bytes()
        self.ActiveWeapon = self.get_4_bytes()
        self.ChacterName = self.get_string(16)
        chacter_status = list(reversed(bin(self.get_1_byte()).replace("0b", "")))
        for i in range(0,8-len(chacter_status)):
            chacter_status.append("0")
        self.StatusIsHardCore = (chacter_status[2]=="1")
        self.StatusIsDead = (chacter_status[3] == "1")
        self.StatusIsExpansion = (chacter_status[5] == "1")
        self.StatusIsLadder = (chacter_status[6] == "1")

        self.ChacterProgression = self.get_1_byte()
        always_zero = self.get_1_byte()
        always_zero = self.get_1_byte()
        self.ChacterClass = self.get_1_byte()
        _0x10 = self.get_1_byte()
        _0x1E = self.get_1_byte()
        self.Level = self.get_1_byte()
        self.CreatedTimestamp = self.get_4_bytes()
        self.LastPlayedTimestamp = self.get_4_bytes()
        _0XFFFFFFFF = self.get_4_bytes()
        self.Skills = []
        for i in range(0,16):
            self.Skills.append(self.get_bits(4 * 8))
        self.LeftSkill = self.get_4_bytes()
        self.RightSkill = self.get_4_bytes()
        self.LeftSwapSkill = self.get_4_bytes()
        self.RightSwapSkill = self.get_4_bytes()
        self.ChacterMenuAppereance = self.get_bits(32 * 8)
        self.Difficulty = self.get_bits(3 * 8)
        self.MapId = self.get_4_bytes()
        _0x00 = self.get_2_bytes()
        self.MercDead = self.get_2_bytes()
        self.MercSeed = self.get_4_bytes()
        self.MercNameId = self.get_2_bytes()
        self.MercType = self.get_2_bytes()
        self.MercExperience = self.get_4_bytes()
        _0x00 = self.get_bits(28 * 8)
        self.ChacterMenuAppereanceD2R = self.get_bits(48 * 8)
        self.ChacterNameD2R = self.get_string(16)
        _0x00 = self.get_bits(52 * 8)
        self.Quest = self.get_bits(298 * 8)
        self.Waypoint = self.get_bits(80 * 8)
        self.NPC = self.get_bits(52 * 8)
        gf_0x6667 = self.get_2_bytes()

        self.index = (int((self.index - 1) / 8) + 1) * 8

        self.Attributes = {}
        while True:
            attr_id = self.get_bits(9)
            if attr_id == 0x1ff:
                break

            attr_id = str(attr_id)
            offset = int(self.cost_txt[attr_id]["CSvBits"])
            attr_value = self.get_bits(offset)

            val_shift = self.cost_txt[attr_id]["ValShift"]
            val_shift = 0 if val_shift == "" else int(val_shift)

            attr_value = attr_value >> val_shift

            self.Attributes[self.cost_txt[attr_id]["Stat"]] = attr_value

        self.index = (int((self.index - 1) / 8) + 1) * 8

        if_0x6669 = self.get_2_bytes()
        self.Skills = self.get_bits(30 * 8)
        jm_0x4d4a = self.get_2_bytes()
        item_count = self.get_2_bytes()

        self.ItemList = []
        for j in range(0, item_count):
            self.ItemList.append(self.get_item())

        self.CorpseHeader = self.get_2_bytes()
        self.CorpseCount =  self.get_2_bytes()
        self.CorpseList = []

        for i in range(0,self.CorpseCount):
            self.CorpseList.append(self.get_corpse())

        if self.StatusIsExpansion:
            self.MercenaryItemList = []
            merc_header = self.get_2_bytes()
            if self.MercSeed !=0:
                jm_0x4d4a = self.get_2_bytes()
                item_count = self.get_2_bytes()

                for j in range(0, item_count):
                    self.MercenaryItemList.append(self.get_item())

        golem_header = self.get_2_bytes()
        golem_exist = (self.get_1_byte() == 1)
        if golem_exist:
            self.GolemItem = self.get_item()
        return self

    def get_corpse(self):
        c = Corpse()
        always0 = self.get_4_bytes()
        c.X = self.get_4_bytes()
        c.Y = self.get_4_bytes()
        jm_0x4d4a = self.get_2_bytes()
        item_count = self.get_2_bytes()

        c.ItemList = []
        for j in range(0, item_count):
            c.ItemList.append(self.get_item())

        return c

    def get_item(self):
        item = Item()

        flags = self.buf[self.index:self.index + 32]
        item.IsIdentified = flags[4]
        item.IsSocketed = flags[11]
        item.IsNew = flags[13]
        item.IsEar = flags[16]
        item.IsStarteritem = flags[17]
        item.IsCompact = flags[21]
        item.IsEthereal = flags[22]
        item.IsPersonalized = flags[24]
        item.IsRuneword = flags[26]

        self.index += 32

        item_version = self.get_bits(3)
        item.Version = bin(item_version).replace("0b", "")
        item.Mode = self.get_bits(3)
        item.Location = self.get_bits(4)
        item.Column = self.get_bits(4)
        item.Row = self.get_bits(4)
        item.Page = self.get_bits(3)

        if item.IsEar:
            item.FileIndex = self.get_bits(3)
            item.EarLevel = self.get_bits(7)
            item.PlayerName = self.get_string(self.buf[self.index:self.index + 15 * 8])
        else:
            item_code = ""
            for i in range(0, 4):
                code, index_seek = self.decode_by_huffman()
                item_code += code
                self.index += index_seek
            item.Code = item_code.strip()

            item.NumberOfSockedItems = self.get_bits(1 if item.IsCompact else 3)

        if item.IsCompact != 1:
            item.Id = self.get_4_bytes()
            item.Level = self.get_bits(7)
            item.Quality = self.get_bits(4)
            item.HasMultipleGraphics = self.get_bits(1)
            if item.HasMultipleGraphics == 1:
                item.GraphicId = self.get_bits(3)
            item.IsAutoAffix = self.get_bits(1)
            if item.IsAutoAffix == 1:
                item.AutoAffixId = self.get_bits(11)

            item.MagicPrefixId = [0] * 3
            item.MagicSuffixId = [0] * 3

            match item.Quality:
                case ItemQuality.Inferior.value | ItemQuality.Superior.value:
                    item.FileIndex = self.get_bits(3)
                case ItemQuality.Magic.value:
                    item.MagicPrefixId[0] = self.get_bits(11)
                    item.MagicSuffixId[0] = self.get_bits(11)
                case ItemQuality.Rare.value | ItemQuality.Craft.value:
                    item.RarePrefixId = self.get_bits(8)
                    item.RareSuffixId = self.get_bits(8)
                    for i in range(0, 3):
                        flag = self.get_bits(1)
                        if flag == 1:
                            item.MagicPrefixId[i] = self.get_bits(11)
                        flag = self.get_bits(1)
                        if flag == 1:
                            item.MagicSuffixId[i] = self.get_bits(11)
                case ItemQuality.Set.value | ItemQuality.Unique.value:
                    item.FileIndex = self.get_bits(12)

            propertyLists = 0
            if item.IsRuneword:
                item.RunnwordId = self.get_bits(12)
                propertyLists |= (1 << (self.get_bits(4) + 1))
            if item.IsPersonalized:
                item.PlayerName = self.get_string(self.buf, 15)
            if item.Code.strip() == "tbk" or item.Code.strip() == "ibk":
                item.MagicSuffixId[0] = self.get_bits(5)

            item.HasRealmdata = self.get_bits(1)
            if item.HasRealmdata:
                self.get_bits(96)

            item.IsArmor = item.Code in self.armor_txt.keys()
            item.IsWeapon = item.Code in self.weapons_txt.keys()
            txt = self.item_txt[item.Code]

            if item.IsArmor:
                id = list(x for x in self.cost_txt.keys() if self.cost_txt[x]["Stat"] == "armorclass")[0]
                item.Armor = self.get_bits(11) - self.get_int(self.cost_txt[id]["Save Add"])
            if item.IsArmor or item.IsWeapon:
                id = list(x for x in self.cost_txt.keys() if self.cost_txt[x]["Stat"] == "maxdurability")[0]
                max_durability_stat = self.cost_txt[id]
                offset = self.get_int(max_durability_stat["Save Bits"]) + self.get_int(max_durability_stat["Save Add"])
                item.MaxDurability = self.get_bits(offset)
                if item.MaxDurability > 0:
                    item.Durability = self.get_bits(self.get_int(max_durability_stat["Save Bits"]))+self.get_int(max_durability_stat["Save Add"])
                    self.get_bits(1)

            item.IsStackable = self.get_int(txt["stackable"])
            if item.IsStackable:
                item.Quantity = self.get_bits(9)
            if item.IsSocketed:
                item.TotalNumberofSockets = self.get_bits(4)

            if item.Quality == ItemQuality.Set.value:
                item.SetitemMask = self.get_bits(5)
                propertyLists |= item.SetitemMask

            item.StatLists = []
            item.StatLists.append(self.get_item_stat_list())

            i = 1
            while i <= 64:
                if (propertyLists & i) != 0:
                    item.StatLists.append(self.get_item_stat_list())
                i *= 2

        self.index = (int((self.index - 1) / 8) + 1) * 8
        item_socked_items = []
        for i in range(0, item.NumberOfSockedItems):
            item_socked_items.append(self.get_item())
        item.IsMisc = (self.misc_txt.get(item.Code,"") != "")

        return item

    def print(self):
        print("Signature = {}".format(self.Signature))
        print("FileSize = {}".format(self.FileSize))
        print("Version = {}".format(self.Version))
        print("Is Hardcore = {}".format(self.StatusIsHardCore))
        print("Is Dead = {}".format(self.StatusIsDead))
        print("Is Expansion = {}".format(self.StatusIsExpansion))
        print("Level = {}".format(self.Level))
        print("Player Name = {}".format(self.ChacterNameD2R))
        print("Player Attributes")
        for key in self.Attributes.keys():
            print("\t{} = {}".format(key,self.Attributes[key]))
        print("Item List")
        for item in self.ItemList:
            print("\tCode = {}, Page = {}, Row = {}, Column = {}".format(item.Code, item.Page,item.Row,item.Column))
            if hasattr(item,"StatLists"):
                print("\tStat Lists")
                for stat_lsits in item.StatLists:
                    for stat in stat_lsits:
                        print("\t\tId = {0}, Stat = {1}, Param = {2}, Value = {3}".format(stat.Id,stat.Stat,stat.Param,stat.Value))
