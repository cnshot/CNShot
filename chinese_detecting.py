#!/usr/bin/python
#coding:utf-8

from mmseg import seg_txt

def isChinesePhase(t, min_word_count=1, thredhold=0.3):
    word_count = 0
    chinese_word_count = 0

    for i in seg_txt(t):
        if len(i)>0:
            word_count += 1
            if u"一" <= i.decode("utf-8", "ignore")[0] <= u"龥": 
                chinese_word_count += 1

    return (word_count > min_word_count and float(chinese_word_count)/word_count > thredhold)

if __name__ == '__main__':
    import sys

    s=["Python格式中最有特色的东西，有了它风格统一，而且减少了不毕要的块包围符号",
       "La murène poivrée est capable de chasser une proie sur une plage à marée haute et de bondir entièrement hors de l’eau.",
       "ウィキペディアはオープンコンテントの百科事典です。基本方針に賛同していただけるなら、誰でも記事を編集したり新しく作成したりできます。ガイドブックを読んでから、サンドボックスで練習してみましょう。質問は利用案内でどうぞ。",
       "开普敦为南非人口排名第二大城市，为西开普省省会，亦为南非立法首都，因为南非国会及很多政府部门亦座落于该市。"]

    if len(sys.argv) > 1:
        s=sys.argv[1:]

    for i in s:
        print i
        if isChinesePhase(i):
            print "Chinese"
        else:
            print "Not Chinese"
