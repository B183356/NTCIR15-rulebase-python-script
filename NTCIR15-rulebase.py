import NTCIR15Util as nutil
import sys
import json
import re
import kanjize
import os

args = sys.argv

if "-d" not in args:

    if len(args) < 3:
        print("ERROR : コマンドライン引数が不足")

    QUESTION_FILE_PATH = args[1]
    UTTERANCES_FILE_PATH = args[2]

    with open(QUESTION_FILE_PATH, "r") as f:
        questions = json.load(f)

    with open(UTTERANCES_FILE_PATH, "r") as f:
        utterances = json.load(f)

else:
    args.remove("-d")
    if len(args) < 3:
        print("ERROR : コマンドライン引数が不足")

    QUESTIONS_DIR_PATH = args[1]
    UTTERANCES_FILE_PATH = args[2]

    q_file_list = os.listdir(QUESTIONS_DIR_PATH)
    q_s = []

    for q_file in q_file_list:
        path = os.path.join(QUESTIONS_DIR_PATH, q_file)
        with open(path, "r") as f:
            questions = json.load(f)
            q_s.extend(questions)

    questions = q_s

    with open(UTTERANCES_FILE_PATH, "r") as f:
        utterances = json.load(f)

AGREE_SIGHN = "賛成"
NON_AGREE_SIGHN = "反対"
NULL_AGREE_SIGHN = "不明"

PARTY_DIC = {
    "自民党": "都議会自由民主党",        # 都議会自民党とも
    "民主党": "都議会民主党",
    "公明党": "都議会公明党",
    "ネット": "生活者ネットワーク",
    "ネット・み": "生活者ネットワーク・みらい",  # よくないと思う
    "無（1/2の会）": "1/2の会",
    "無（行革110番）": "行革110番",
    "無（自治市民）": "自治市民",
    "日本共産党": "日本共産党",
    "無（市民の会）": "市民の会",
    "都ファースト": "都民ファースト",
    "民進党": "民進党",
    "立憲・民主": "立憲民主党・民主クラブ",
    "民進・立憲": "民進党・立憲民主党",
    "東京改革": "東京改革",
    "東京みらい": "東京みらい",
    "かがやけ": "かがやけ",
    "維新・あた": "維新・あたらしい",
    "みんな": "みんなの党Tokyo",
    "みんなの党": "都議会会派みんなの党",    # 都議会みんなの党とも
    "維新の党": "維新の党",
    # 維新の会？
    "結いと維新": "結いと維新"
}


sum_correct = 0
sum_incorrect = 0
sum_null_ans = 0
sum_d_len = 0
warn_list = []
warn_list_vose = []

# for i,q in enumerate(questions) :
for i, q in enumerate(questions):
    warn_flag = False

    print("--------------------{}番目のQuestion--------------------\n".format(str(i)))
    print("対象議題番号\t: {}\n".format(q["BillNumber"]))

    # 実は一つのファイルには同じ会期の質問しか入っていないので、この行は意味がない
    match_utterance = nutil.get_match_utterance(q["MeetingStartDate"], q["MeetingEndDate"], utterances, cc=True, vose=False)

    party_opinion = {}

    party_rule_dict = {}

    for mu in match_utterance:
        su_sets = mu["Proceeding"]

    # いずれかの党名、代表、立場、賛成反対の単語が入っていれば、これは意見表明だろうという判定

    # ちょっとゆるいばーじょん
    opinions = nutil.grep_string(nutil.grep_string(nutil.grep_string(su_sets, ["代表"]), ["立場"]), [AGREE_SIGHN, NON_AGREE_SIGHN])

    # 厳しいバージョン、デバッグ用
    opinions_forcount = nutil.grep_string(nutil.grep_string(nutil.grep_string(nutil.grep_string(su_sets, PARTY_DIC.values()), ["代表"]), ["立場"]), [AGREE_SIGHN, NON_AGREE_SIGHN])

# print(dif_opinion,file=sys.stderr)

    for j, op in enumerate(opinions):

        # 意見表明は一名しか行わない(でほしい)

        utterance = op["Utterance"]
        speaker = op["Speaker"]

        if speaker in q["SpeakerList"]:
            print("{}, {} : {}", format(q["BillNumber"], speaker, q["SpeakerList"][speaker]), file=sys.stderr)  # NOQA
            print("DEBUG : {}はSpeakerListに含まれます。動作停止".format(speaker))
            sys.exit(1)

        # express = utterance.split("。")[0]      # 意見表明は一行で完結する(と思っている)
        utterance_split = utterance.split("。")
        express = ""
        for us in utterance_split:
            if us.find("代表") >= 0 and us.find("立場") >= 0 and (us.find("賛成") >= 0 or us.find("反対") >= 0):
                express = us
                continue
        if express == "":
            print("ERROR: 一文に要求単語が入りきっていません")
            warn_list_vose.append(utterance)
            continue
            sys.exit(1)

        """
        isin = []
        for k in PARTY_DIC.keys():
            isin.append(express.find(PARTY_DIC[k]))
        if (max(isin) == -1):
            print(express, file=sys.stderr)
        """

        # 党名の確認(これSpeakerとかから整合とれないの?)
        party_formal_name = ""
        party_unformal_name = ""

        for pn in PARTY_DIC.values():
            if express.find(pn) >= 0:
                party_formal_name = pn
                party_unformal_name = nutil.get_key_from_value(PARTY_DIC, pn)
                break
        if party_formal_name == "":
            warn_list.append(express)
            warn_list_vose.append(utterance)
            continue    # 多分議長とかその辺の発言

        # print("{} : {} : の発言\n\t{}".format(party_unformal_name, speaker, express))
        party_rule_dict[party_unformal_name] = {}
        party_rule_dict[party_unformal_name]["Name"] = party_unformal_name

        # どの議案に対して 賛成/反対 かを判定

        # デフォルト値を決定,すべて〜とかで指定されているもの
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
                print("ERROR : defaultが不明な発言。")
                sys.exit(1)
            if nag_iter >= 0 and nag_iter < ag_iter:
                default = NON_AGREE_SIGHN

        party_rule_dict[party_unformal_name]["Default"] = default

        # ルールを追加していく

        party_rule_dict[party_unformal_name]["Rules"] = []

        gou_iter = re.finditer("[一二三四五六七八九〇零十百千万]*号", express)
        gou_iter = [gou.span() for gou in gou_iter]
        if not bool(gou_iter):
            continue     # 全て賛成/反対のみであれば、次の発言へ

        # ~から~まで、の後にしか単一指定は来ないという前提で進める

        from_flag = False
        tmp = {}

        for i, state in enumerate(gou_iter):

            istmp = []

            if not from_flag:
                tmp = {}

            # から~ までルール
            if from_flag:
                if i + 1 < len(gou_iter):
                    if (express[gou_iter[i][1]: gou_iter[i + 1][0]].find("まで") >= 0) or (express[gou_iter[i][1]: gou_iter[i+1][0]].find("に") >= 0):
                        tmp["Operand"].append(express[gou_iter[i][0]: gou_iter[i][1]])
                        if express[gou_iter[i][1]: gou_iter[i + 1][0]].find(AGREE_SIGHN) >= 0:
                            tmp["Assertion"] = AGREE_SIGHN
                            is_assertion = AGREE_SIGHN
                        elif express[gou_iter[i][1]: gou_iter[i+1][0]].find(NON_AGREE_SIGHN) >= 0:
                            tmp["Assertion"] = NON_AGREE_SIGHN
                            is_assertion = NON_AGREE_SIGHN
                        else:
                            tmp["Assertion"] = "エラー"
                        party_rule_dict[party_unformal_name]["Rules"].append(tmp)
                        from_flag = False
                        for rule in party_rule_dict[party_unformal_name]["Rules"]:
                            if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                                rule["Assertion"] = is_assertion
                        continue
                else:
                    if (express[gou_iter[i][1]:].find("まで") >= 0) or (express[gou_iter[i][1]:].find("に") >= 0):
                        tmp["Operand"].append(express[gou_iter[i][0]: gou_iter[i][1]])
                        if express[gou_iter[i][1]:].find(AGREE_SIGHN) >= 0:
                            tmp["Assertion"] = AGREE_SIGHN
                        elif express[gou_iter[i][1]:].find(NON_AGREE_SIGHN) >= 0:
                            tmp["Assertion"] = NON_AGREE_SIGHN
                        else:
                            tmp["Assertion"] = "エラー"
                        party_rule_dict[party_unformal_name]["Rules"].append(tmp)
                        from_flag = False
                        continue
            if i+1 < len(gou_iter):

                # 単一用
                a_na_flag = [express[gou_iter[i][1]: gou_iter[i+1][0]].find(AGREE_SIGHN), express[gou_iter[i][1]: gou_iter[i+1][0]].find(NON_AGREE_SIGHN)]
                a_na_flag = [anaf for anaf in a_na_flag if anaf >= 0]

                if bool(a_na_flag):
                    a_na_flag = min(a_na_flag)

                if express[gou_iter[i][1]: gou_iter[i+1][0]].find("から") >= 0:
                    from_flag = True
                    tmp["Rule"] = "FromTo"
                    tmp["Operand"] = []
                    tmp["Operand"].append(express[gou_iter[i][0]: gou_iter[i][1]])
                    continue

                # is ルール(単一)

                elif express[gou_iter[i][1]: gou_iter[i+1][0]].find(AGREE_SIGHN) >= 0 and express[gou_iter[i][1]: gou_iter[i+1][0]].find(AGREE_SIGHN) == a_na_flag:
                    party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[gou_iter[i][0]: gou_iter[i][1]], "Assertion": AGREE_SIGHN})
                    is_assertion = AGREE_SIGHN
                    for rule in party_rule_dict[party_unformal_name]["Rules"]:
                        if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                            rule["Assertion"] = is_assertion
                    continue
                elif express[gou_iter[i][1]: gou_iter[i+1][0]].find(NON_AGREE_SIGHN) >= 0 and express[gou_iter[i][1]: gou_iter[i+1][0]].find(NON_AGREE_SIGHN) == a_na_flag:
                    party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[gou_iter[i][0]: gou_iter[i][1]], "Assertion": NON_AGREE_SIGHN})
                    is_assertion = NON_AGREE_SIGHN
                    for rule in party_rule_dict[party_unformal_name]["Rules"]:
                        if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                            rule["Assertion"] = is_assertion
                    continue

                # FROM でもない IS でもない = ISの二番目以降である
                else:
                    party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[gou_iter[i][0]: gou_iter[i][1]], "Assertion": "エラー"})

            # 一番後ろの処理
            else:

                a_na_flag = [express[gou_iter[i][1]:].find(AGREE_SIGHN), express[gou_iter[i][1]:].find(NON_AGREE_SIGHN)]
                a_na_flag = [anaf for anaf in a_na_flag if anaf >= 0]

                if bool(a_na_flag):
                    a_na_flag = min(a_na_flag)

                if express[gou_iter[i][1]:].find(AGREE_SIGHN) >= 0 and express[gou_iter[i][1]:].find(AGREE_SIGHN) == a_na_flag:
                    party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[gou_iter[i][0]: gou_iter[i][1]], "Assertion": AGREE_SIGHN})
                    is_assertion = AGREE_SIGHN
                    for rule in party_rule_dict[party_unformal_name]["Rules"]:
                        if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                            rule["Assertion"] = is_assertion
                    continue
                elif express[gou_iter[i][1]:].find(NON_AGREE_SIGHN) >= 0 and express[gou_iter[i][1]:].find(NON_AGREE_SIGHN) == a_na_flag:
                    party_rule_dict[party_unformal_name]["Rules"].append({"Rule": "Is", "Operand": express[gou_iter[i][0]: gou_iter[i][1]], "Assertion": NON_AGREE_SIGHN})
                    is_assertion = NON_AGREE_SIGHN
                    for rule in party_rule_dict[party_unformal_name]["Rules"]:
                        if rule["Rule"] == "Is" and rule["Assertion"] == "エラー":
                            rule["Assertion"] = is_assertion
                    continue

                # 末尾に、「号は継続審査云々」とかきちゃうとここに到達する
                print("WARNING : 継続審査などの立場表明があります")
                pass

        # 誰かの発言ごとに意見を抽出して表示
        # print(party_rule_dict[party_unformal_name])
        print()

    # questionの議題に対しての、各政党の答え
    billnumber_orig = q["BillNumber"]
    billnumber = kanjize.kanji2int(re.search(r"[一二三四五六七八九〇零十百千万]+", billnumber_orig).group())

    pn_list = party_rule_dict.keys()

    for key in pn_list:

        d = party_rule_dict[key]

        pname = d["Name"]

        p_assertion = d["Default"]

        # 全指定しかない場合
        if not bool(d["Rules"]):
            party_opinion[pname] = p_assertion
            continue

        # ルールを解決する
        for r in d["Rules"]:

            if r["Assertion"] == "エラー":
                print("ERROR : よくわからない立場表明が存在。 \n\t> {}".format(r["Assertion"]))  # 継続審査とかで引っかかる可能性
                # sys.exit()

            # from-to ルールについての判定
            if r["Rule"] == "FromTo":
                from_number = kanjize.kanji2int(r["Operand"][0][:-1])
                to_number = kanjize.kanji2int(r["Operand"][1][:-1])

                if from_number <= billnumber and billnumber <= to_number:
                    p_assertion = r["Assertion"]

            # 単一指定はfrom-toより上位
            elif r["Rule"] == "Is":
                is_assertion_number = kanjize.kanji2int(r["Operand"][:-1])

                if is_assertion_number == billnumber:
                    p_assertion = r["Assertion"]

            else:
                print("ERROR : 不正なRuleが格納されています。もしくはRuleが有りません。\n\t> {}".format(r["Rule"]))
                sys.exit(1)

            party_opinion[pname] = p_assertion
            continue

    for l in q["ProsConsPartyList"]:
        if l not in party_opinion.keys():
            party_opinion[l] = NULL_AGREE_SIGHN

    # ----------評価----------

    print("{:-^16}".format("各政党立場表明"))
    print("")

    correct_ans = q["ProsConsPartyList"]
    d_len = len(correct_ans)
    correct = 0
    incorrect = 0
    null_ans = 0

    # ----回答評価---

    print("{:-^64}".format(""))
    print("{}:{}:{}".format("党名".center(16), "予想".center(16), "正解".center(16)))
    print("{:-^64}".format(""))
    for k in correct_ans.keys():
        if party_opinion.get(k) is None:
            print("ERROR : 評価キーが元辞書に有りません。")
            sys.exit()

        if party_opinion[k] == correct_ans[k]:
            correct += 1
        elif party_opinion[k] == NULL_AGREE_SIGHN:
            incorrect += 1
            null_ans += 1
        else:
            incorrect += 1

        # 日本語だときっちり揃わないらしい、ターミナルの文字幅認識の問題?
        # print("{:<16}:{:^16}:{:^16}".format(k, correct_ans[k], party_opinion[k]))
        print("{}:{}:{}".format(k.center(16), party_opinion[k].center(16), correct_ans[k].center(16)))
    print("{:-^64}".format(""))

    print("\n\n{:-^16}\n".format("評価"))

    print("正解\t\t: {}".format(correct))
    print("有効不正解\t: {}".format(incorrect-null_ans))
    print("無回答\t\t: {}".format(null_ans))
    print("")
    print("正答率\t\t\t: {} / {},  {:.2f} %".format(correct, d_len, correct / d_len * 100))
    print("有効回答率\t\t: {} / {},  {:.2f} %".format(d_len - null_ans, d_len, (d_len - null_ans)/d_len * 100))
    print("正答率(有効回答)\t: {} / {},  {:.2f} %".format(correct, d_len - null_ans, correct / (d_len-null_ans) * 100))
    print("\n")

    sum_correct += correct
    sum_incorrect += incorrect
    sum_null_ans += null_ans
    sum_d_len += d_len


print("\n\n{:-^64}\n".format("総合評価"))

print("正解\t\t: {}".format(sum_correct))
print("有効不正解\t: {}".format(sum_incorrect-sum_null_ans))
print("無回答\t\t: {}".format(sum_null_ans))
print("")
print("正答率\t\t\t: {} / {},  {:.2f} %".format(sum_correct, sum_d_len, sum_correct / sum_d_len * 100))
print("有効回答率\t\t: {} / {},  {:.2f} %".format(sum_d_len - sum_null_ans, sum_d_len, (sum_d_len - sum_null_ans)/sum_d_len * 100))
print("正答率(有効回答)\t: {} / {},  {:.2f} %".format(sum_correct, sum_d_len - sum_null_ans, sum_correct / (sum_d_len-sum_null_ans) * 100))
print("\n")

# ----------デバッグ用----------

warn_list = set(warn_list_vose)       # 全体表示
# warn_list = set(warn_list)       # 意見のみ表示

for w in warn_list:
    print(w + "\n",file=sys.stderr)
    pass

print("warn len : {}".format(len(warn_list)))
