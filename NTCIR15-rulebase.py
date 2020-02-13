from NTCIR15Util import arg_parse, get_match_utterance
import sys
import re
import kanjize


# 情報表示関数
def info_print(text, exit=None, info=""):
    if SHOW_INFO_PRINT:
        if info == "":
            print("{}".format(text), file=sys.stderr)
        else:
            print("{}:\n\t{}".format(info, text), file=sys.stderr)
        if exit is not None:
            sys.exit(exit)


def error_print(text, exit=None):
    if SHOW_ERROR_PRINT:
        info_print(text, exit=exit, info="ERROR")


# 最終結果だけ見たければINFOをFalseに
# ERRORは基本Trueのままにしておくこと
SHOW_ERROR_PRINT = True         # エラー表示切り替え
SHOW_INFO_PRINT = True        # インフォ(途中出力とか)表示切り替え

args = sys.argv
questions, utterances = arg_parse(args)

# 賛成/反対のマクロ
AGREE_SIGHN = "賛成"
NON_AGREE_SIGHN = "反対"
NULL_AGREE_SIGHN = "不明"

# 発言での宣言と、実際の議事録だよりの略称対応辞書
PARTY_DIC = {
    "自民党": ["都議会自由民主党","自民党"],
    "民主党": ["都議会民主党"],
    "公明党": ["都議会公明党"],
    "ネット": ["生活者ネットワーク"],
    "ネット・み": ["生活者ネットワーク・みらい"],
    "無（1/2の会）": ["1/2の会"],
    "無（行革110番）": ["行革110番"],
    "無（自治市民）": ["自治市民"],
    "日本共産党": ["日本共産党"],
    "無（市民の会）": ["市民の会"],
    "都ファースト": ["都民ファースト"],
    "民進党": ["民進党"],
    "立憲・民主": ["立憲民主党・民主クラブ"],
    "民進・立憲": ["民進党・立憲民主党"],
    "東京改革": ["東京改革"],
    "東京みらい": ["東京みらい"],
    "かがやけ": ["かがやけ"],
    "維新・あた": ["維新・あたらしい"],
    "みんな": ["みんなの党Tokyo"],
    "みんなの党": ["都議会会派みんなの党"],
    "維新の党": ["維新の党"],
    "日本維新": ["日本維新"],
    "無（維新の会）": ["維新の会"],
    "結いと維新": ["結いと維新"]
}


sum_correct = 0
sum_incorrect = 0
sum_null_ans = 0
sum_d_len = 0
warn_list = []
warn_list_vose = []


questions_pathes = questions.keys()

# ファイルごとのループ
for q_key in questions_pathes:

    # 議題ごとのループ
    for i, q in enumerate(questions[q_key]):

        party_opinion = {}
        party_rule_dict = {}

        info_print("{:-^64}\n".format(q_key))
        info_print("対象議題番号\t: {}\n".format(q["BillNumber"]))

        # 会期がマッチした会議録を取得してくる
        match_utterance = get_match_utterance(q["MeetingStartDate"], q["MeetingEndDate"], utterances, cc=True, vose=False)

        # SpeakerとUtteranceのセットを取り出す
        for mu in match_utterance:
            su_sets = mu["Proceeding"]

        for j, op in enumerate(su_sets):

            # 意見表明は一名しか行わないと仮定、もし同じ党で二人以上意見表明した場合には後の人が優先される

            utterance = op["Utterance"]
            speaker = op["Speaker"]

            utterance_split = utterance.split("。")
            express = ""

            # 代表、立場、賛成反対のどちらか、といった単語が全て一文で入っていれば、これは意見表明だろうという判定
            # つまり二文以上に渡って意見表明していると取得できない
            for us in utterance_split:
                if us.find("代表") >= 0 and us.find("立場") >= 0 and (us.find("賛成") >= 0 or us.find("反対") >= 0):
                    express = us
                    continue
            if express == "":
                continue

            party_formal_name = ""
            party_unformal_name = ""

            # 意見表明者の所属政党は、SpeakerListから取得できないので発言の口上部分から抽出する
            for key in PARTY_DIC.keys():
                pns = PARTY_DIC[key]

                for pn in pns:
                    if express.find(pn) >= 0:
                        party_formal_name = pn
                        party_unformal_name = key
                        break
                if not party_formal_name == "":
                    break

            if party_formal_name == "":
                warn_list.append(express)
                warn_list_vose.append(utterance)
                continue    # 議長などの発言

            info_print("{} : {} : の発言\n\t{}".format(party_unformal_name, speaker, express))

            party_rule_dict[party_unformal_name] = {}
            party_rule_dict[party_unformal_name]["Name"] = party_unformal_name

            # どの議案に対して 賛成/反対 かを判定

            # 賛否のデフォルト値を決定,すべてに〜などで指定されているもの、基本的に発言者のデフォルトは賛成と仮定
            default = AGREE_SIGHN

            all_assertion_iter = [itera.span() for itera in re.finditer("全て|すべて|他", express)]

            if not bool(all_assertion_iter):
                max_iter = -1
            else:
                max_iter = max([itera[1] for itera in all_assertion_iter])

            if max_iter >= 0:
                ag_iter = express[max_iter:].find(AGREE_SIGHN)
                nag_iter = express[max_iter:].find(NON_AGREE_SIGHN)
                if (ag_iter < 0) and (nag_iter < 0):
                    error_print("defaultが不明な発言。\n\t\t{}".format(express), exit=1)
                if nag_iter >= 0 and nag_iter < ag_iter:
                    default = NON_AGREE_SIGHN

            party_rule_dict[party_unformal_name]["Default"] = default

            # ルールを追加していく

            party_rule_dict[party_unformal_name]["Rules"] = []

            # どの議案に対して、賛成/反対かを判定するために「〇〇号」という正規表現で文のイテレータを抽出
            agenda_number_iter = re.finditer("[一二三四五六七八九〇零十百千万]*号", express)
            agenda_number_iter = [gou.span() for gou in agenda_number_iter]

            if not bool(agenda_number_iter):
                continue     # 全て賛成/反対のみの主張であれば、次の発言へ

            from_flag = False
            tmp = {}

            for i, state in enumerate(agenda_number_iter):
                istmp = []

                if not from_flag:
                    tmp = {}

                # から~ までルール(FromTo)

                # 〇〇号から~といった内容が既に発言されている場合
                if from_flag:

                    # 文の途中(続く発言内容に「〇〇号には~」というものが含まれている場合)
                    if i + 1 < len(agenda_number_iter):
                        # どの議案番号まで 賛成/反対 か
                        if (express[agenda_number_iter[i][1]: agenda_number_iter[i + 1][0]].find("まで") >= 0) or (express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find("に") >= 0):
                            tmp["Operand"].append(express[agenda_number_iter[i][0]: agenda_number_iter[i][1]])
                            if express[agenda_number_iter[i][1]: agenda_number_iter[i + 1][0]].find(AGREE_SIGHN) >= 0:
                                tmp["Assertion"] = AGREE_SIGHN
                                is_assertion = AGREE_SIGHN
                            elif express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find(NON_AGREE_SIGHN) >= 0:
                                tmp["Assertion"] = NON_AGREE_SIGHN
                                is_assertion = NON_AGREE_SIGHN
                            else:
                                # 賛成/反対が直後で明言されていない場合には、おそらく以降の議案の後でまとめて立場を表明するので、一時的に穴埋め
                                # e.g. 1号議案から5号議案、7号議案には反対
                                is_assertion = "エラー"
                                tmp["Assertion"] = "エラー"

                            # 〇〇号から〇〇号についてのルールを辞書に格納し、フラグを解除
                            party_rule_dict[party_unformal_name]["Rules"].append(tmp)
                            from_flag = False

                            # もし、いままで立場の明言を保留しているものがあり、賛成/反対を明言していればここで埋める。
                            for rule in party_rule_dict[party_unformal_name]["Rules"]:
                                if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                                    rule["Assertion"] = is_assertion
                            continue
                    # 文の終わり(続く発言内容に「〇〇号には~」というものが含まれていない場合)
                    else:
                        if (express[agenda_number_iter[i][1]:].find("まで") >= 0) or (express[agenda_number_iter[i][1]:].find("に") >= 0):
                            tmp["Operand"].append(express[agenda_number_iter[i][0]: agenda_number_iter[i][1]])
                            if express[agenda_number_iter[i][1]:].find(AGREE_SIGHN) >= 0:
                                tmp["Assertion"] = AGREE_SIGHN
                            elif express[agenda_number_iter[i][1]:].find(NON_AGREE_SIGHN) >= 0:
                                tmp["Assertion"] = NON_AGREE_SIGHN
                            else:
                                # 以降に賛否が続かないのは立場表明的におかしい
                                tmp["Assertion"] = "エラー"

                            # 会派ごとのルール辞書に格納
                            party_rule_dict[party_unformal_name]["Rules"].append(tmp)
                            from_flag = False
                            continue

                # 〇〇号から~という発言を受けておらず、まだ以降に「〇〇号には〜」という発言が残されている可能性がある場合の処理
                if i+1 < len(agenda_number_iter):

                    # 賛成ないし反対という発言のある場所を示すイテレータ
                    a_na_iter = [express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find(AGREE_SIGHN), express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find(NON_AGREE_SIGHN)]
                    a_na_iter = [anaf for anaf in a_na_iter if anaf >= 0]

                    # 賛成/反対が両方ある場合、前の方にあるものを優先
                    if bool(a_na_iter):
                        a_na_iter = min(a_na_iter)

                    # tmpでFromTo用のルールを保持
                    if express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find("から") >= 0:
                        from_flag = True
                        tmp["Rule"] = "FromTo"
                        tmp["Operand"] = []
                        tmp["Operand"].append(express[agenda_number_iter[i][0]: agenda_number_iter[i][1]])
                        continue

                    # Isルール e.g. 〇〇号には賛成、〇〇号には反対

                    # 〇〇号に賛成、などの処理
                    elif express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find(AGREE_SIGHN) >= 0 and express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find(AGREE_SIGHN) == a_na_iter:
                        party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[agenda_number_iter[i][0]: agenda_number_iter[i][1]], "Assertion": AGREE_SIGHN})
                        is_assertion = AGREE_SIGHN

                        # 保留していた意見を埋める
                        for rule in party_rule_dict[party_unformal_name]["Rules"]:
                            if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                                rule["Assertion"] = is_assertion
                        continue

                    # 〇〇号に反対、などの処理
                    elif express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find(NON_AGREE_SIGHN) >= 0 and express[agenda_number_iter[i][1]: agenda_number_iter[i+1][0]].find(NON_AGREE_SIGHN) == a_na_iter:
                        party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[agenda_number_iter[i][0]: agenda_number_iter[i][1]], "Assertion": NON_AGREE_SIGHN})
                        is_assertion = NON_AGREE_SIGHN

                        # 保留していた意見を埋める
                        for rule in party_rule_dict[party_unformal_name]["Rules"]:
                            if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                                rule["Assertion"] = is_assertion
                        continue

                    # Fromでもない、Isでもないとき、意見を保留しているものである
                    else:
                        party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[agenda_number_iter[i][0]: agenda_number_iter[i][1]], "Assertion": "エラー"})

                # 〇〇号から~という発言を受けておらず、以降に「〇〇号には〜」という発言が残されていない場合の処理
                else:
                    # 賛成ないし反対が表明されている場所をfindする
                    a_na_iter = [express[agenda_number_iter[i][1]:].find(AGREE_SIGHN), express[agenda_number_iter[i][1]:].find(NON_AGREE_SIGHN)]
                    a_na_iter = [anaf for anaf in a_na_iter if anaf >= 0]

                    # 賛成/反対が両方ある場合、前の方にあるものを優先
                    if bool(a_na_iter):
                        a_na_iter = min(a_na_iter)

                    # 賛成の場合
                    if express[agenda_number_iter[i][1]:].find(AGREE_SIGHN) >= 0 and express[agenda_number_iter[i][1]:].find(AGREE_SIGHN) == a_na_iter:
                        party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[agenda_number_iter[i][0]: agenda_number_iter[i][1]], "Assertion": AGREE_SIGHN})
                        is_assertion = AGREE_SIGHN
                        for rule in party_rule_dict[party_unformal_name]["Rules"]:
                            if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                                rule["Assertion"] = is_assertion
                        continue
                    # 反対の場合
                    elif express[agenda_number_iter[i][1]:].find(NON_AGREE_SIGHN) >= 0 and express[agenda_number_iter[i][1]:].find(NON_AGREE_SIGHN) == a_na_iter:
                        party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[agenda_number_iter[i][0]: agenda_number_iter[i][1]], "Assertion": NON_AGREE_SIGHN})
                        is_assertion = NON_AGREE_SIGHN
                        for rule in party_rule_dict[party_unformal_name]["Rules"]:
                            if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                                rule["Assertion"] = is_assertion
                        continue

                    # 末尾に「〇〇号は継続審査としたい」などはっきりしない意見表明があるとここに到達する
                    info_print("WARNING : はっきりしない立場表明があります", info="WARNING")
                    pass

            # 誰かの発言ごとに意見を抽出して表示
            info_print(party_rule_dict[party_unformal_name])
            info_print("")

        # 対象の議題番号を数比較するために数字に変換
        billnumber_orig = q["BillNumber"]
        billnumber = kanjize.kanji2int(re.search(r"[一二三四五六七八九〇零十百千万]+", billnumber_orig).group())

        # 立場表明した(=ルールの格納された)会派の一覧を取得
        pn_list = party_rule_dict.keys()

        # それぞれの会派ごとにルールを解決する
        for key in pn_list:

            d = party_rule_dict[key]
            pname = d["Name"]

            # 全て/他 などで指定された、デフォルト意見を決定
            p_assertion = d["Default"]

            # 全指定しかない場合
            if not bool(d["Rules"]):
                # 意見辞書に格納
                party_opinion[pname] = p_assertion
                continue

            # 全体指定以外のルールを解決する
            for r in d["Rules"]:

                # エラーが残っていたらとりあえず警告を出すだけに止める
                if r["Assertion"] == "エラー":
                    info_print("よくわからない立場表明が存在。 \n\t\t> {}".format(r["Assertion"]), info="WARNING")

                # FromTo ルールについての判定
                if r["Rule"] == "FromTo":
                    from_number = kanjize.kanji2int(r["Operand"][0][:-1])
                    to_number = kanjize.kanji2int(r["Operand"][1][:-1])

                    # 対象議題が、FromToの中に入っていた場合には会派の意見を書き換え
                    if from_number <= billnumber and billnumber <= to_number:
                        p_assertion = r["Assertion"]

                # Is ルールについての判定
                elif r["Rule"] == "Is":
                    is_assertion_number = kanjize.kanji2int(r["Operand"][:-1])

                    # 一致していたら会派の意見を書き換え
                    if is_assertion_number == billnumber:
                        p_assertion = r["Assertion"]

                # デバッグ用
                else:
                    error_print("不正なRuleが格納されています。もしくはRuleが有りません。\n\t\t> {}".format(r["Rule"]), exit=1)

                # 最終的な意見を会派ごとの意見辞書に反映
                party_opinion[pname] = p_assertion
                continue

        # ProsConsPartyListを確認し、立場表明を行なっていない会派があれば不明として意見辞書に反映
        for l in q["ProsConsPartyList"]:
            if l not in party_opinion.keys():
                party_opinion[l] = NULL_AGREE_SIGHN

        # ----------評価出力(議題ごと)----------

        info_print("{:-^16}".format("各政党立場表明"))
        info_print("")

        correct_ans = q["ProsConsPartyList"]
        d_len = len(correct_ans)
        correct = 0
        incorrect = 0
        null_ans = 0

        info_print("{:-^64}".format(""))
        info_print("{}:{}:{}".format("党名".center(16), "予想".center(16), "正解".center(16)))
        info_print("{:-^64}".format(""))
        for k in correct_ans.keys():
            if party_opinion.get(k) is None:
                error_print("評価キーが元辞書に有りません。",exit=1)

            if party_opinion[k] == correct_ans[k]:
                correct += 1
            elif party_opinion[k] == NULL_AGREE_SIGHN:
                incorrect += 1
                null_ans += 1
            else:
                incorrect += 1

            info_print("{}:{}:{}".format(k.center(16), party_opinion[k].center(16), correct_ans[k].center(16)))

        info_print("{:-^64}".format(""))
        info_print("\n\n{:-^16}\n".format("評価"))
        info_print("正解\t\t: {}".format(correct))
        info_print("有効不正解\t: {}".format(incorrect-null_ans))
        info_print("無回答\t\t: {}".format(null_ans))
        info_print("")
        info_print("正答率\t\t\t: {} / {},  {:.2f} %".format(correct, d_len, correct / d_len * 100))
        info_print("有効回答率\t\t: {} / {},  {:.2f} %".format(d_len - null_ans, d_len, (d_len - null_ans)/d_len * 100))
        info_print("正答率(有効回答)\t: {} / {},  {:.2f} %".format(correct, d_len - null_ans, correct / (d_len-null_ans) * 100))
        info_print("\n")

        sum_correct += correct
        sum_incorrect += incorrect
        sum_null_ans += null_ans
        sum_d_len += d_len

# ----------評価出力(全体)----------

print("\n\n{:-^64}\n".format("総合評価"))

print("正解\t\t: {}".format(sum_correct))
print("有効不正解\t: {}".format(sum_incorrect-sum_null_ans))
print("無回答\t\t: {}".format(sum_null_ans))
print("")
print("正答率\t\t\t: {} / {},  {:.2f} %".format(sum_correct, sum_d_len, sum_correct / sum_d_len * 100))
print("有効回答率\t\t: {} / {},  {:.2f} %".format(sum_d_len - sum_null_ans, sum_d_len, (sum_d_len - sum_null_ans)/sum_d_len * 100))
print("正答率(有効回答)\t: {} / {},  {:.2f} %".format(sum_correct, sum_d_len - sum_null_ans, sum_correct / (sum_d_len-sum_null_ans) * 100))
print("\n")
