"""Spelling word lists.

Level N uses words with N + 1 letters (level 1 = 2 letters ... level 10 = 11 letters).
Each entry is (english_word, japanese_meaning). The Japanese meaning is shown as a
hint when the game language is set to Japanese, so the game doubles as English
practice for Japanese-speaking kids.

easy   = ages 4+  : animals, food, toys, everyday things
medium = ages 8+  : school, nature, adventure, hobbies
hard   = ages 12+ : science, maths, history, abstract ideas
"""
import random

WORDS = {
    "easy": {
        2: [("hi", "こんにちは"), ("up", "うえ"), ("go", "いく"), ("no", "いいえ"),
            ("me", "わたし"), ("we", "わたしたち"), ("ox", "おうし")],
        3: [("cat", "ねこ"), ("dog", "いぬ"), ("sun", "たいよう"), ("hat", "ぼうし"),
            ("pig", "ぶた"), ("bus", "バス"), ("cow", "うし"), ("egg", "たまご")],
        4: [("fish", "さかな"), ("frog", "かえる"), ("duck", "あひる"), ("cake", "ケーキ"),
            ("ball", "ボール"), ("star", "ほし"), ("moon", "つき"), ("bear", "くま")],
        5: [("apple", "りんご"), ("horse", "うま"), ("train", "でんしゃ"), ("happy", "うれしい"),
            ("house", "いえ"), ("tiger", "トラ"), ("candy", "あめ"), ("bunny", "うさちゃん")],
        6: [("banana", "バナナ"), ("monkey", "サル"), ("flower", "はな"), ("rabbit", "うさぎ"),
            ("cookie", "クッキー"), ("turtle", "カメ"), ("orange", "オレンジ"), ("rocket", "ロケット")],
        7: [("chicken", "にわとり"), ("giraffe", "キリン"), ("penguin", "ペンギン"),
            ("rainbow", "にじ"), ("dolphin", "イルカ"), ("pumpkin", "かぼちゃ"),
            ("monster", "かいじゅう"), ("unicorn", "ユニコーン")],
        8: [("elephant", "ゾウ"), ("dinosaur", "きょうりゅう"), ("sandwich", "サンドイッチ"),
            ("birthday", "たんじょうび"), ("kangaroo", "カンガルー"), ("treasure", "たからもの"),
            ("princess", "おひめさま"), ("pancakes", "パンケーキ")],
        9: [("butterfly", "ちょうちょ"), ("crocodile", "ワニ"), ("fireworks", "はなび"),
            ("pineapple", "パイナップル"), ("chocolate", "チョコレート"), ("spaceship", "うちゅうせん"),
            ("dragonfly", "トンボ"), ("snowflake", "ゆきのけっしょう")],
        10: [("strawberry", "いちご"), ("playground", "あそびば"), ("watermelon", "すいか"),
             ("helicopter", "ヘリコプター"), ("toothbrush", "はブラシ"), ("television", "テレビ"),
             ("motorcycle", "バイク")],
        11: [("caterpillar", "いもむし"), ("grandmother", "おばあちゃん"),
             ("grandfather", "おじいちゃん"), ("marshmallow", "マシュマロ"),
             ("hummingbird", "ハチドリ"), ("fingerpaint", "ゆびえのぐ")],
    },
    "medium": {
        2: [("it", "それ"), ("be", "〜である"), ("do", "する"), ("us", "わたしたちを"),
            ("to", "〜へ"), ("if", "もし"), ("so", "だから")],
        3: [("map", "ちず"), ("owl", "フクロウ"), ("fox", "キツネ"), ("ant", "アリ"),
            ("axe", "おの"), ("gym", "たいいくかん"), ("zoo", "どうぶつえん")],
        4: [("game", "ゲーム"), ("jump", "とぶ"), ("wolf", "オオカミ"), ("kite", "たこ"),
            ("snow", "ゆき"), ("rain", "あめ"), ("gold", "きん"), ("ship", "ふね")],
        5: [("robot", "ロボット"), ("pizza", "ピザ"), ("ocean", "うみ"), ("earth", "ちきゅう"),
            ("magic", "まほう"), ("music", "おんがく"), ("beach", "ビーチ"), ("shark", "サメ")],
        6: [("planet", "わくせい"), ("castle", "おしろ"), ("jungle", "ジャングル"),
            ("wizard", "まほうつかい"), ("pirate", "かいぞく"), ("garden", "にわ"),
            ("island", "しま"), ("school", "がっこう")],
        7: [("volcano", "かざん"), ("library", "としょかん"), ("science", "かがく"),
            ("history", "れきし"), ("captain", "せんちょう"), ("compass", "コンパス"),
            ("mystery", "なぞ"), ("octopus", "タコ")],
        8: [("computer", "コンピューター"), ("mountain", "やま"), ("football", "サッカー"),
            ("skeleton", "がいこつ"), ("squirrel", "リス"), ("aquarium", "すいぞくかん"),
            ("airplane", "ひこうき"), ("triangle", "さんかくけい")],
        9: [("astronaut", "うちゅうひこうし"), ("adventure", "ぼうけん"), ("detective", "たんてい"),
            ("telescope", "ぼうえんきょう"), ("hurricane", "ハリケーン"), ("lightning", "いなずま"),
            ("waterfall", "たき"), ("dangerous", "きけんな")],
        10: [("basketball", "バスケットボール"), ("skateboard", "スケートボード"),
             ("dictionary", "じしょ"), ("experiment", "じっけん"), ("friendship", "ゆうじょう"),
             ("volleyball", "バレーボール"), ("earthquake", "じしん")],
        11: [("electricity", "でんき"), ("imagination", "そうぞうりょく"),
             ("rattlesnake", "ガラガラヘビ"), ("grasshopper", "バッタ"),
             ("fingerprint", "しもん"), ("spectacular", "すばらしい")],
    },
    "hard": {
        2: [("pi", "えんしゅうりつ"), ("ax", "おの"), ("oh", "おお"), ("ox", "おうし"),
            ("id", "みぶんしょう")],
        3: [("wry", "ひねくれた"), ("gnu", "ヌー"), ("awe", "いけい"), ("sly", "ずるい"),
            ("zen", "ぜん"), ("yak", "ヤク")],
        4: [("myth", "しんわ"), ("quiz", "クイズ"), ("jazz", "ジャズ"), ("lynx", "オオヤマネコ"),
            ("echo", "こだま"), ("zinc", "あえん")],
        5: [("rhyme", "いん"), ("pixel", "ピクセル"), ("quest", "たんきゅう"), ("glyph", "もじきごう"),
            ("fjord", "フィヨルド"), ("nymph", "ようせい"), ("vivid", "あざやかな"), ("crypt", "ちかしつ")],
        6: [("zenith", "てんちょう"), ("sphinx", "スフィンクス"), ("quartz", "すいしょう"),
            ("rhythm", "リズム"), ("oxygen", "さんそ"), ("galaxy", "ぎんが"), ("puzzle", "パズル")],
        7: [("eclipse", "にっしょく"), ("gravity", "じゅうりょく"), ("phoenix", "ふしちょう"),
            ("quantum", "りょうし"), ("diagram", "ずひょう"), ("rhombus", "ひしがた"),
            ("algebra", "だいすう")],
        8: [("molecule", "ぶんし"), ("symphony", "こうきょうきょく"), ("hologram", "ホログラム"),
            ("parallel", "へいこう"), ("asteroid", "しょうわくせい"), ("mosquito", "か"),
            ("sapphire", "サファイア")],
        9: [("ecosystem", "せいたいけい"), ("democracy", "みんしゅしゅぎ"),
            ("algorithm", "アルゴリズム"), ("orchestra", "オーケストラ"), ("labyrinth", "めいきゅう"),
            ("satellite", "えいせい"), ("chemistry", "かがく")],
        10: [("hypothesis", "かせつ"), ("atmosphere", "たいき"), ("laboratory", "けんきゅうじょ"),
             ("revolution", "かくめい"), ("philosophy", "てつがく"), ("microscope", "けんびきょう")],
        11: [("equilibrium", "へいこう"), ("archaeology", "こうこがく"),
             ("mathematics", "すうがく"), ("temperature", "おんど"),
             ("personality", "せいかく"), ("independent", "どくりつした")],
    },
}


def word_length(level):
    return level + 1


def pick_words(difficulty, level, count=3, rng=random):
    """Return `count` distinct (WORD, meaning) tuples for the level, upper-cased."""
    pool = WORDS[difficulty][word_length(level)]
    chosen = rng.sample(pool, min(count, len(pool)))
    return [(w.upper(), m) for w, m in chosen]
