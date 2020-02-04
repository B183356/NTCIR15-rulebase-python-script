import json
from datetime import datetime

""" 
関数

get_match_utterance
change_code
"""


# --------------------

"""
会期の始まりと終わりを与えると、それにマッチしたUtteranceを持ってくる関数
    mes :
        string, MeetingStartDate、会期の始まりの日付
    med : 
        string, MeetingEndDate、会期の終わりの日付。
"""
def get_match_utterance(msd, med, utter_json, cc=False, vose=False) :

    tmp     = [ int(t) for t in msd.split("/") ]
    startdate = datetime(tmp[0],tmp[1],tmp[2])

    tmp     = [ int(t) for t in med.split("/") ]
    enddate = datetime(tmp[0],tmp[1],tmp[2])
    
    utter_json
    match_utterances = []

    for u in utter_json :
        
        udate = [ int(ud) for ud in u["Date"].split("/") ]
        udate = datetime(udate[0],udate[1],udate[2])

        if ( udate >= startdate and udate <= enddate ) : match_utterances.append(u)    

    if cc:
        change_code(match_utterances)
    if vose:
        for mu in match_utterances :
            print("matched : " + mu["ProceedingTitle"] + ". held in " + mu["Date"])
    return match_utterances

"""
get_match_utteranceとかで取ってきたutteranceを整形する関数。
主に \n と\u3000 の整形を行う。
    uterrances :
        dictionaly, 会議録の一記事。
"""
def change_code(utterances):
    for u in utterances :
        for up in u["Proceeding"]:
            up["Utterance"] = up["Utterance"].replace("\n","\n").replace("\u3000","")
    return

def grep_speaker(susets, name, mklist=False):
    greped = []
    for ss in susets :
        #print("name is " + name + ", speaker is " + ss["Speaker"])
        
        if name in ss["Speaker"] :
            #print("matched!")
            greped.append(ss)

    if not mklist : return greped
    
    speaches = [ g["Utterance"] for g in greped]

    return speaches

def grep_string(susets, textlist):
    greped = []
    for ss in susets :
        for text in textlist :
            if text in ss["Utterance"] :
                greped.append(ss)
                break

    return greped

def get_key_from_value(d, val):
    keys = [k for k, v in d.items() if v == val]
    if keys:
        return keys[0]
    return None

if __name__ == "__main__" :
    with open("/Users/Sawayama/NTCIR15/tokyo-proceedings-JSON/honkaigi/teireikai/utterances_tokyo_proceeding_withURL.json","r") as f:
        j = json.load(f)
    
    # get_match_utterance関数のテスト
    l = get_match_utterance("2001/9/19", "2001/10/5", j, cc=True)

#print( l[0]["Proceeding"][0]["Utterance"] )
    proceedings = [ u["Proceeding"] for u in l ] # 全ての会議録のProceedingの集合,proceedings[0] は、一つ目の記事のProceeding全体

    all_utterances = []
    for procs in proceedings:
        for sus in procs :
            all_utterances.append(sus["Utterance"])
    """
    for au in all_utterances:
#print(pros[0][0]["Utterance"])
        if ("反対" in au or "賛成" in au) : print(au)
    """

    susets = l[0]["Proceeding"]

    ss = grep_speaker(susets, "三田")


    for s in ss :
        print(s["Utterance"])

    
    ss = grep_speaker(susets, "三田",mkdict=True)
    print(ss)
