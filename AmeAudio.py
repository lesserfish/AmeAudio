from pkgutil import iter_importers
from re import I
import string
from gtts import gTTS
from pydub import AudioSegment
import xml.etree.ElementTree as ET
import requests
import hashlib


#GLOBAL VARIABLES:

OUT_DELAY = 2000
IN_DELAY = 1000
INPUTPATH = "input.txt"
DICTPATH = "Dict/JMdict.xml"
TMPAUDIO = "tmp/tmp.mp3"
TMPPRONUNCIATION = "tmp/a.mp3"
TMPTTS = "tmp/b.mp3"
IGNORE_KANJI = False
IGNORE_KANA = False
AUDIO_WEBSITE = "http://assets.languagepod101.com/dictionary/japanese/audiomp3.php?kana={0}&kanji={1}"
AUDIO_ERR_MD5 = "Config/missingaudio.md5"
MANUAL_CHOICE = True
NUM_CHOICES = 3
OUTPUT_DIR = "./Out/"
REPEAT = 2


class IEntry:
    def __init__(self, kanji : str, kana : str):
        self.Kanji = kanji
        self.Kana = kana
    def PrintEntry(self):
        print("Kanji: " + self.Kanji)
        print("Kana: " + self.Kana)
        print("Meaning: " + str(self.Meanings))
    Kanji = ""
    Kana = ""
    Meanings = []

def ReadInput(filepath : string):
    Entries = []
    fp = open(filepath, "r")
    Lines = fp.readlines()
    fp.close()

    for line in Lines:
        spline = line.split("|")
        
        kanji = spline[0].split()[0]
        kana = ""
        if len(spline) >= 2:
            kana = spline[1].split()[0]

        Entries.append(IEntry(kanji, kana))
    return Entries

def GetMeaning(root , ientry : IEntry):
    output = ientry
    
    

    dentries = root.findall("entry")

    meanings = []
    for dentry in dentries:
        kele = dentry.find("k_ele")

        if kele is None:
            continue
        keb = kele.find("keb")

        if keb is None:
            continue
        
        rele = dentry.find("r_ele")

        if rele is None:
            continue
        
        reb = rele.find("reb")

        if reb is None:
            continue

        kanji = keb.text.split()[0]
        kana = reb.text.split()[0]

        if (kanji == ientry.Kanji or IGNORE_KANJI) and (kana == ientry.Kana or IGNORE_KANA or ientry.Kana == ""):

            sense = dentry.find("sense")
            if(sense is None):
                continue

            gloss = sense.findall("gloss")
            for meaning in gloss:
                meanings.append(meaning.text)

            output.Meanings = meanings
            if IGNORE_KANA or ientry.Kana == "":
                output.Kana = kana
            
            return output
    
    print("Error parsing the word: " + ientry.Kanji)
    return None

def DownloadPronunciation(ientry : IEntry, output : str):
    fullpath = AUDIO_WEBSITE.format(ientry.Kana, ientry.Kanji)
    audio = requests.get(fullpath)
    audiomd5 = hashlib.md5(audio.content).digest()

    missingmd5 = open(AUDIO_ERR_MD5, "rb").read()

    if(missingmd5 == audiomd5):
        print("Audio is not available for the word: " + ientry.Kanji + " : " + ientry.Kana)
        tts = gTTS(ientry.Kanji, lang='ja')
        tts.save(output)
    else:
        fp = open(output, "wb")
        fp.write(audio.content)
        fp.close()

def GenerateTTS(ientry :IEntry, output : str):
    choices = []
    
    if MANUAL_CHOICE:
        print("Meanings for the word " + ientry.Kanji + ": ")
        i = 0
        for entry in ientry.Meanings:
            print(str(i) + " : " + entry)
            i = i + 1
        choice = input("Write the number of the selected meanings, separated by a comma: ")
        choice = choice.replace(" ", "")
        choicelist = choice.split(',')
        for c in choicelist:
            choices.append(int(c))
    else:
        minimum = min(NUM_CHOICES, len(ientry.Meanings))
        for i in range(0, minimum):
            choices.append(i)
    
    sentence = ""

    faudio = AudioSegment.empty()
    silence = AudioSegment.silent(duration=IN_DELAY)
    i = 1
    for choice in choices:
        sentence = str(i) + ". " + ientry.Meanings[choice]
        tts = gTTS(sentence, lang='en')
        tts.save(TMPAUDIO)
        segment = AudioSegment.from_mp3(TMPAUDIO)
        faudio = faudio + segment + silence
        i = i + 1

    faudio.export(output, format="mp3")

def MergeAudio(APath : str, BPath : str, output : str):
    Aaudio = AudioSegment.from_mp3(APath)
    BAudio = AudioSegment.from_mp3(BPath)
    silence = AudioSegment.silent(duration=OUT_DELAY)
    faudio = Aaudio + silence + BAudio

    faudio = faudio * REPEAT
    faudio.export(output, format="mp3")


def Main():

    Entries = ReadInput(INPUTPATH)
    tree = ET.parse(DICTPATH)
    root = tree.getroot()
    
    print("Reading from dictionary....")
    i = 1
    for entry in Entries:
        print(str(i) + " / " + str(len(Entries)))
        entry = GetMeaning(root, entry)
        i = i + 1

    i = 1
    for entry in Entries:
        print(str(i) + " / " + str(len(Entries)))
        if len(entry.Meanings) == 0:
            continue
        DownloadPronunciation(entry, TMPPRONUNCIATION)
        GenerateTTS(entry, TMPTTS)

        output = OUTPUT_DIR + entry.Kanji + ".mp3"
        MergeAudio(TMPPRONUNCIATION, TMPTTS, output)
        i = i + 1

Main()