from pathlib import Path
import json
import pickle

import regex
from urllib import request, parse
from bs4 import BeautifulSoup


class FullName:
    ja_pt = regex.compile(
        r"(?P<last>"
        r"(\p{Hiragana}|\p{Script_extensions=Katakana}|\p{Han})+"
        r")"
        r"\s?"
        r"(?P<first>"
        r"(\p{Hiragana}|\p{Script_extensions=Katakana}|\p{Han})+"
        r")"
        r"（"
        r"(?P<kana_last>"
        r"(\p{Hiragana}|\p{Script_extensions=Katakana}|\w)+"
        r")"
        r"\s?"
        r"(?P<kana_first>"
        r"(\p{Hiragana}|\p{Script_extensions=Katakana}|\w)*"
        r")")

    fgn_pt = regex.compile(
        r"(?P<last>"
        r"^(\p{Script_extensions=Katakana})+$"
        r")")

    all_kana_pt = regex.compile(
        r"^(\p{Hiragana}|\p{Katakana})+$")

    kata_pt = regex.compile(
        r"\p{Katakana}")

    def __init__(self, name):
        if type(name) is str:
            (self.last, self.first,
             self.kana_last, self.kana_first,
             self.is_fgn) = self._init_name(name)
        elif type(name) is dict:
            self.last, self.first = name["last"], name["first"]
            self.kana_last, self.kana_first = name["kana_last"], name["kana_first"]
            self.is_fgn = name["is_fgn"] if "is_fgn" in name else False

    def _init_name(self, name):
        ja_match = FullName.ja_pt.search(name)
        fgn_match = FullName.fgn_pt.match(name)

        if ja_match:
            return (
                ja_match.group("last"),
                ja_match.group("first"),
                self._kata_to_hira(ja_match.group("kana_last")),
                self._kata_to_hira(ja_match.group("kana_first")),
                False)
        elif fgn_match:
            return (
                fgn_match.group("last"), "",
                self._kata_to_hira(fgn_match.group("last")), "",
                True)
        else:
            raise NameError

    def get_name(self):
        return self.last + self.first

    def get_kana(self):
        return self.kana_last + self.kana_first

    def is_all_kana_last(self):
        return FullName.all_kana_pt.search(self.last)

    def is_all_kana_first(self):
        return FullName.all_kana_pt.search(self.first)

    @classmethod
    def is_name(cls, text):
        ja_match = FullName.ja_pt.search(text)
        fgn_match = FullName.fgn_pt.match(text)
        return ja_match or fgn_match

    @staticmethod
    def _kata_to_hira(text):
        return "".join(
            [chr(ord(ch) - 96) if FullName.kata_pt.match(ch) else ch
             for ch in text])

    def __str__(self):
        return (
            self.last + self.first +
            "(" + self.kana_last + " " + self.kana_first + ")")


class DicGenerator:
    def __init__(self, url_ja, begin_id, end_id,
                 dic_name="dic", tag_get="dt"):
        self.url_ja = url_ja
        self.begin_id, self.end_id = begin_id, end_id
        self.dic_name = dic_name
        self.tag_get = tag_get

    def make_dic(self):
        name_list = self.get_name_list()

        full_list = list()
        last_list = list()
        first_list = list()

        for name in name_list:
            full_list.append(
                name.get_kana() + "\t" + name.get_name() + "\t" + "人名")

            if name.is_fgn:
                continue

            if not name.is_all_kana_last():
                last_list.append(
                    name.kana_last + "\t" + name.last + "\t" + "姓")

            if not name.is_all_kana_first():
                first_list.append(
                    name.kana_first + "\t" + name.first + "\t" + "名")

        full_list = list(dict.fromkeys(full_list))
        last_list = list(dict.fromkeys(last_list))
        first_list = list(dict.fromkeys(first_list))

        path = Path("dic/")
        if not path.exists():
            path.mkdir()
        path /= Path(self.dic_name + ".txt")

        with path.open("w", encoding="utf-8", newline="\r\n") as file:
            file.write(self.formatting(full_list))
            file.write(self.formatting(last_list))
            file.write(self.formatting(first_list))

        print(
            str(path) + " ->" + "\n" +
            "人名: " + str(len(full_list)) + "\n" +
            "姓　: " + str(len(last_list)) + "\n" +
            "名　: " + str(len(first_list)) + "\n"
        )

    def get_raw_name_list(self):
        dump_path = Path("dump/" + self.dic_name + ".pkl")

        if not Path("dump/").exists():
            Path("dump").mkdir()

        if dump_path.exists():
            with dump_path.open("rb") as f:
                name_list = pickle.load(f)
            print("Load from dump")
        else:
            url = parse.quote_plus(self.url_ja, "/:?=&")
            html = request.urlopen(url)
            soup = BeautifulSoup(html, "html.parser")

            begin_tag = soup.find(id=self.begin_id).parent
            end_tag = soup.find(id=self.end_id).parent
            tag_list = begin_tag.find_next_siblings()
            tag_list = tag_list[:tag_list.index(end_tag)]
            tag_list = BeautifulSoup(
                "".join([str(tag) for tag in tag_list]), "html.parser"
            ).find_all(self.tag_get)

            text_list = [
                tag.text for tag in tag_list if FullName.is_name(tag.text)
            ]

            name_list = [FullName(text) for text in text_list]

            with dump_path.open("wb") as f:
                pickle.dump(name_list, f)
            print("Load from Wikipedia")

        return name_list

    def get_name_list(self, replace_json=None, add_json=None):
        raw_name_list = self.get_raw_name_list()
        name_list = self.replace_name_list(raw_name_list)
        name_list = self.add_name_list(name_list)
        return name_list

    def replace_name_list(self, name_list):
        with Path("json/replace.json").open("r") as f:
            replace_dic = json.load(f)

        new_name_list = name_list
        for before, after in replace_dic.items():
            new_name_list = [name
                             if name.get_name() != before
                             else FullName(after)
                             for name in new_name_list]

        return new_name_list

    def add_name_list(self, name_list):
        with Path("json/add.json").open("r") as f:
            add_dic = json.load(f)

        new_name_list = name_list
        for source, target_list in add_dic.items():
            for i, name in enumerate(new_name_list):
                if name.get_name() == source:
                    index = i + 1
                    break
            else:
                index = -1
            if index < 0:
                continue
            for target in target_list:
                new_name_list.insert(index, FullName(target))
                index += 1

        return new_name_list

    @staticmethod
    def formatting(li):
        return "".join(list(map(lambda text: text + "\r\n", li)))


def main():
    dic_generator_list = [
        DicGenerator(
            "https://ja.wikipedia.org/wiki/THE_IDOLM@STERの登場人物",
            "765（ナムコ）プロダクション所属アイドル", "765プロダクション社員",
            dic_name="765pro", tag_get="h3"),
        DicGenerator(
            "https://ja.wikipedia.org/wiki/アイドルマスター_シンデレラガールズ",
            "登場キャラクター",
            "他シリーズ出身のアイドル達",
            dic_name="cinderella"),
        DicGenerator(
            "https://ja.wikipedia.org/wiki/アイドルマスター_ミリオンライブ!の登場人物",
            "765THEATER_ALLSTARS", "765PRO_ALLSTARS",
            dic_name="millionlive"),
        DicGenerator(
            "https://ja.wikipedia.org/wiki/アイドルマスター_SideM",
            "登場キャラクター", "その他の登場人物",
            dic_name="sidem"),
        DicGenerator(
            "https://ja.wikipedia.org/wiki/アイドルマスター_シャイニーカラーズ",
            "登場人物", "CD",
            dic_name="shinycolors")
    ]

    for dic_generator in dic_generator_list:
        dic_generator.make_dic()


if __name__ == "__main__":
    main()
