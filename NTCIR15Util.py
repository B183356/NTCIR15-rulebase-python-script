import json
from datetime import datetime
import os
import sys

"""
NTCIR15-rulebase.pyで使った関数群

get_match_utterance
change_code
"""


# --------------------

"""
デバッグプリント用
"""


def error_print(text, exit=None):
    print("ERROR:\n\t{}".format(text), file=sys.stderr)
    if exit is not None:
        sys.exit(exit)


def info_print(text, exit=None, info="INFO"):
    print("WARNING:\n\t{}".format(text), file=sys.stderr)
    if exit is not None:
        sys.exit(exit)


"""
コマンドライン引数解決
"""


def arg_parse(args):
    dir_specific = False
    questions_dict = {}

    # ディレクトリ指定モード(指定ディレクトリ内の全ファイルを統合してそれぞれに対して実行)
    if "-d" in args:
        dir_specific = True
        args.remove("-d")

    # エラー、警告表示
    if len(args) < 3:
        error_print("コマンドライン引数が不足", exit=1)
    if len(args) >= 4:
        info_print("コマンドライン引数が過剰です。不要な部分\n\t\t> {}\n\t以降は無視されます。".format(args[3]), info="WARNING")

    # 単一ファイル指定モード
    if not dir_specific:
        questions_path = args[1]
        utterances_path = args[2]

        with open(questions_path, "r") as f:
            questions = json.load(f)
            questions = [questions]
            questions_dict[questions_path] = questions

    # ディレクトリ指定モード
    else:
        questions_dir_path = args[1]
        utterances_path = args[2]

        question_file_list = os.listdir(questions_dir_path)
        questions = []

        for question_file in question_file_list:
            path = os.path.join(questions_dir_path, question_file)

            with open(path, "r") as f:
                q = json.load(f)
                # questions.append(q)
                questions_dict[path] = q

    with open(utterances_path, "r") as f:
        utterances = json.load(f)

    return(questions_dict, utterances)


"""
会期の始まりと終わりを与えると、それにマッチしたUtteranceを持ってくる関数
    mes :
        string, MeetingStartDate、会期の始まりの日付
    med :
        string, MeetingEndDate、会期の終わりの日付。
"""


def get_match_utterance(msd, med, utter_json, cc=False, vose=False):

    tmp = [int(t) for t in msd.split("/")]
    startdate = datetime(tmp[0], tmp[1], tmp[2])

    tmp = [int(t) for t in med.split("/")]
    enddate = datetime(tmp[0], tmp[1], tmp[2])

    utter_json
    match_utterances = []

    for u in utter_json:

        udate = [int(ud) for ud in u["Date"].split("/")]
        udate = datetime(udate[0], udate[1], udate[2])

        if (udate >= startdate and udate <= enddate):
            match_utterances.append(u)

    if cc:
        change_code(match_utterances)
    if vose:
        for mu in match_utterances:
            print("matched : " + mu["ProceedingTitle"] + ". held in " + mu["Date"])
    return match_utterances


"""
get_match_utteranceとかで取ってきたutteranceを整形する関数。
主に \n と\u3000 の整形を行う。
    uterrances :
        dict, 会議録の一記事。
"""


def change_code(utterances):
    for u in utterances:
        for up in u["Proceeding"]:
            up["Utterance"] = up["Utterance"].replace("\n", "\n").replace("\u3000", " ")
    return


"""
発言と発言者のセットのリストと発言者名を与えると、与えた発言者名の発言だけ抜き出す関数
"""


def grep_speaker(susets, name, mklist=False):
    greped = []

    for ss in susets:
        if name in ss["Speaker"]:
            greped.append(ss)

    if not mklist:
        return greped

    speaches = [g["Utterance"] for g in greped]

    return speaches


"""
発言の中に、textlist中の単語が入っているものだけを抽出。or検索とand検索は指定すること、デフォルトはor
"""


def grep_string(susets, textlist, mode="or", check=True):
    if check:
        if type(textlist) is str:
            textlist = [textlist]
        elif hasattr(textlist, "__iter__"):         # listとかdict_keysとか
            for t in textlist:
                if type(t) is str:
                    pass
                else:
                    error_print("grep_string()の検索リスト中の要素: {} はstrオブジェクトではありません。".format(t), exit=1)
            pass
        else:
            error_print("grep_string()の検索語句がstrまたはiterableなオブジェクトではありません。\n\t\t> type(textlist)={}".format(type(textlist)), exit=1)

    greped = []

    for ss in susets:
        all_in = True
        if mode == "or":
            for text in textlist:
                if text in ss["Utterance"]:
                    greped.append(ss)
                    break
        elif mode == "and":
            for text in textlist:
                if text not in ss["Utterance"]:
                    all_in = False
            if all_in:
                greped.append(ss)
            
        else:
            error_print("grep_string()のmodeが不正。\n\t\t> mode={}".format(mode), exit=1)

    return greped


"""
辞書型オブジェクトdとその値の一つvalを与えたとき、そのvalを持つkeyを一つ返す関数。
今回の用途的にvalは単一にしかならない。
"""


def get_key_from_value(d, val):
    keys = [k for k, v in d.items() if v == val]
    if keys:
        return keys[0]
    return None
