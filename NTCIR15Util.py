import json
from datetime import datetime
import os

"""
NTCIR15-rulebase.pyで使った関数群

get_match_utterance
change_code
"""


# --------------------


"""
arg_parse()

コマンドライン引数を解決して問題dictと発言内容dictを返す。
ディレクトリを指定するパターンと、ファイルのみを指定するパターンがあり、-dオプションをつけることでディレクトリ指定になる

    INPUT
        args : array
            sys.argvをそのまま投げることを想定

    OUTPUT
        question_dict : dict
            与えられる問題の諸情報を格納した辞書、
            keyは"ID","Prefecture","Meeting","MeetingStartDate","MeetingEndDate","Proponent",
            "BillClass","BillSubClass","Bill","BillNumber","SpeakerList","ProsConsPartyList"
        utterances : dict
            実際の会議録の情報を格納した辞書、keyは"Date","Prefecture","ProceedingTitle","URL",
            "Proceeding"
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
        print("ERROR:\n\tコマンドライン引数が不足", exit=1)
    if len(args) >= 4:
        print("ERROR:\n\tコマンドライン引数が過剰です。不要な部分\n\t\t> {}\n\t以降は無視されます。".format(args[3]), info="WARNING")

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
get_match_utterance

会期の始まりと終わりを与えると、それにマッチしたUtteranceを持ってくる関数

    INPUT
        mes : string
            MeetingStartDate、会期の始まりの日付
        med : string
            MeetingEndDate、会期の終わりの日付
        utter_json : dict
            json.load()で持って来た辞書型データ
        vose : boolean
            デバッグ用

    OUTPUT
        match_utterances : dict
            [ { "Speaker" : 発言者名, "Utterance" : 発言内容" } , {左同} ... ] という形式の辞書のリスト
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
change_code()

全角ブランクや開業コードの変換を行う、中身を直接弄るので戻り値無し
状況に応じて弄る予定

    INPUT
        uterrances : dict
            会議録の中から抜き出した単体記事

    OUTPUT
        なし
"""


def change_code(utterances):
    for u in utterances:
        for up in u["Proceeding"]:
            up["Utterance"] = up["Utterance"].replace("\n", "\n").replace("\u3000", " ")
    return


"""
grep_speaker()

発言と発言者のセットのリストと発言者名を与えると、与えた発言者名の発言だけ抜き出す関数
発言者と所属会派の対応が取れるならば使えると思って作っておいたが、使うことはなかった

    INPUT
        susets : dict
            SpeakerとUtterancesの辞書のリスト
        name : string
            発言者名
        mklist : boolean
            Trueにするとリストのリスト形式で返してくれる、Falseだと一次元リストに変換してから返す

    OUTPUT
        speaches : dict
            susetsと同じ形式
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
grep_string()

発言の中に、textlist中の単語が入っているものだけを抽出。or検索とand検索は指定すること、デフォルトはor
使わなくなった

    INPUT
        susets : dict
            SpeakerとUtteranceの辞書のリスト
        textlist : [ str, str, ... ]
            この中に格納されているテキストで抽出を行う
        mode : str, "or"/"and"のどちらか
            or検索かand検索かの指定
        check : boolean
            textlistのチェック用、一次元リストで、中身がちゃんとstringか調べるだけ

    OUTPUT
        greped : dict
            susetsと同じ
"""


def grep_string(susets, textlist, mode="or", check=True):
    if check:
        if type(textlist) is str:
            textlist = [textlist]
        elif hasattr(textlist, "__iter__"):
            for t in textlist:
                if type(t) is str:
                    pass
                else:
                    print("ERROR:\n\tgrep_string()の検索リスト中の要素: {} はstrオブジェクトではありません。".format(t), exit=1)
            pass
        else:
            print("ERROR:\n\tgrep_string()の検索語句がstrまたはiterableなオブジェクトではありません。\n\t\t> type(textlist)={}".format(type(textlist)), exit=1)

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
            print("ERROR:\n\tgrep_string()のmodeが不正。\n\t\t> mode={}".format(mode), exit=1)

    return greped
