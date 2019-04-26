from pathlib import Path

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
        r")"
    )

    fgn_pt = regex.compile(
        r"(?P<last>"
        r"^(\p{Script_extensions=Katakana})+$"
        r")"
    )

    all_kana_pt = regex.compile(
        r"^(\p{Hiragana}|\p{Katakana})+$"
    )

    kata_pt = regex.compile(
        r"\p{Katakana}"
    )

    def __init__(self, name):
        self.last, self.first, self.kana_last, self.kana_first, self.is_fgn = self._init_name(name)

    def _init_name(self, name):
        ja_match = FullName.ja_pt.search(name)
        fgn_match = FullName.fgn_pt.match(name)

        if ja_match:
            return (
                ja_match.group("last"),
                ja_match.group("first"),
                self._kata_to_hira(ja_match.group("kana_last")),
                self._kata_to_hira(ja_match.group("kana_first")),
                False
            )
        elif fgn_match:
            return (
                fgn_match.group("last"), "",
                self._kata_to_hira(fgn_match.group("last")), "",
                True
            )
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

    @staticmethod
    def _kata_to_hira(text):
        return "".join([chr(ord(ch) - 96) if FullName.kata_pt.match(ch) else ch for ch in text])

    def __str__(self):
        return self.last + self.first + "(" + self.kana_last + " " + self.kana_first + ")"


def formatting(li):
    return "".join(list(map(lambda text: text + "\r\n", li)))


def make_dic(url_ja, begin_id, end_id, dic_name="dic.txt", tag_get="dt"):
    url = parse.quote_plus(url_ja, "/:?=&")
    html = request.urlopen(url)
    soup = BeautifulSoup(html, "html.parser")

    begin_tag = soup.find(id=begin_id).parent
    end_tag = soup.find(id=end_id).parent
    tag_list = begin_tag.find_next_siblings()
    tag_list = tag_list[:tag_list.index(end_tag)]
    tag_list = BeautifulSoup("".join([str(tag) for tag in tag_list]), "html.parser").find_all(tag_get)

    full_list = list()
    last_list = list()
    first_list = list()

    for tag in tag_list:
        try:
            n = FullName(tag.text)

            full_list.append(n.get_kana() + "\t" + n.get_name() + "\t" + "人名")

            if n.is_fgn:
                continue

            if not n.is_all_kana_last():
                last_list.append(n.kana_last + "\t" + n.last + "\t" + "姓")

            if not n.is_all_kana_first():
                first_list.append(n.kana_first + "\t" + n.first + "\t" + "名")
        except NameError:
            continue

    full_list = list(dict.fromkeys(full_list))
    last_list = list(dict.fromkeys(last_list))
    first_list = list(dict.fromkeys(first_list))
    
    path = Path("dic/")
    if not path.exists():
        path.mkdir()
    path /= Path(dic_name)

    with path.open("w", encoding="utf-8", newline="\r\n") as file:
        file.write(formatting(full_list))
        file.write(formatting(last_list))
        file.write(formatting(first_list))

    print(str(path) + " ->")
    print("人名: " + str(len(full_list)))
    print("姓　: " + str(len(last_list)))
    print("名　: " + str(len(first_list)))
    print()


def main():
    make_dic(
        "https://ja.wikipedia.org/wiki/THE_IDOLM@STERの登場人物",
        "765（ナムコ）プロダクション所属アイドル", "765プロダクション社員",
        dic_name="765pro.txt", tag_get="h3"
    )

    make_dic(
        "https://ja.wikipedia.org/wiki/アイドルマスター_シンデレラガールズ",
        "登場キャラクター", "他プロダクション",
        dic_name="cinderella.txt"
    )

    make_dic(
        "https://ja.wikipedia.org/wiki/アイドルマスター_ミリオンライブ!の登場人物",
        "765THEATER_ALLSTARS", "765PRO_ALLSTARS",
        dic_name="millionlive.txt"
    )

    make_dic(
        "https://ja.wikipedia.org/wiki/アイドルマスター_SideM",
        "登場キャラクター", "その他の登場人物",
        dic_name="sidem.txt"
    )

    make_dic(
        "https://ja.wikipedia.org/wiki/アイドルマスター_シャイニーカラーズ",
        "登場人物", "CD",
        dic_name="shinycolors.txt"
    )


if __name__ == "__main__":
    main()

