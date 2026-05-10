import discord
from discord import app_commands
from discord.ext import commands


FONT_STYLES = {
    "bold": {
        "upper": "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙",
        "lower": "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳",
        "digits": "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
    },
    "italic": {
        "upper": "𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍",
        "lower": "𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧",
        "digits": "0123456789",
    },
    "bold_italic": {
        "upper": "𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁",
        "lower": "𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛",
        "digits": "0123456789",
    },
    "script": {
        "upper": "𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵",
        "lower": "𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏",
        "digits": "0123456789",
    },
    "bold_script": {
        "upper": "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩",
        "lower": "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃",
        "digits": "0123456789",
    },
    "gothic": {
        "upper": "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
        "lower": "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷",
        "digits": "0123456789",
    },
    "bold_gothic": {
        "upper": "𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅",
        "lower": "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟",
        "digits": "0123456789",
    },
    "double": {
        "upper": "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ",
        "lower": "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫",
        "digits": "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡",
    },
    "sans": {
        "upper": "𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹",
        "lower": "𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝗏𝗐𝗑𝗒𝗓",
        "digits": "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫",
    },
    "sans_bold": {
        "upper": "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭",
        "lower": "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇",
        "digits": "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵",
    },
    "sans_italic": {
        "upper": "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡",
        "lower": "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻",
        "digits": "0123456789",
    },
    "sans_bold_italic": {
        "upper": "𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕",
        "lower": "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯",
        "digits": "0123456789",
    },
    "monospace": {
        "upper": "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉",
        "lower": "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣",
        "digits": "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿",
    },
    "circled": {
        "upper": "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ",
        "lower": "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ",
        "digits": "⓪①②③④⑤⑥⑦⑧⑨",
    },
    "squared": {
        "upper": "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉",
        "lower": "abcdefghijklmnopqrstuvwxyz",
        "digits": "0123456789",
    },
    "negative_circled": {
        "upper": "🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩",
        "lower": "abcdefghijklmnopqrstuvwxyz",
        "digits": "0123456789",
    },
    "negative_squared": {
        "upper": "🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🆅🆆🆇🆈🆉",
        "lower": "abcdefghijklmnopqrstuvwxyz",
        "digits": "0123456789",
    },
}

SMALL_CAPS = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ғ",
    "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ",
    "m": "ᴍ", "n": "ɴ", "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ",
    "s": "s", "t": "ᴛ", "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x",
    "y": "ʏ", "z": "ᴢ",
}

PARENTHESIZED = {
    "a": "⒜", "b": "⒝", "c": "⒞", "d": "⒟", "e": "⒠", "f": "⒡",
    "g": "⒢", "h": "⒣", "i": "⒤", "j": "⒥", "k": "⒦", "l": "⒧",
    "m": "⒨", "n": "⒩", "o": "⒪", "p": "⒫", "q": "⒬", "r": "⒭",
    "s": "⒮", "t": "⒯", "u": "⒰", "v": "⒱", "w": "⒲", "x": "⒳",
    "y": "⒴", "z": "⒵",
    "1": "⑴", "2": "⑵", "3": "⑶", "4": "⑷", "5": "⑸",
    "6": "⑹", "7": "⑺", "8": "⑻", "9": "⑼", "0": "⓪",
}

SUPERSCRIPT = {
    "a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ", "e": "ᵉ", "f": "ᶠ",
    "g": "ᵍ", "h": "ʰ", "i": "ⁱ", "j": "ʲ", "k": "ᵏ", "l": "ˡ",
    "m": "ᵐ", "n": "ⁿ", "o": "ᵒ", "p": "ᵖ", "q": "q", "r": "ʳ",
    "s": "ˢ", "t": "ᵗ", "u": "ᵘ", "v": "ᵛ", "w": "ʷ", "x": "ˣ",
    "y": "ʸ", "z": "ᶻ",
    "A": "ᴬ", "B": "ᴮ", "C": "ᶜ", "D": "ᴰ", "E": "ᴱ", "F": "ᶠ",
    "G": "ᴳ", "H": "ᴴ", "I": "ᴵ", "J": "ᴶ", "K": "ᴷ", "L": "ᴸ",
    "M": "ᴹ", "N": "ᴺ", "O": "ᴼ", "P": "ᴾ", "Q": "Q", "R": "ᴿ",
    "S": "ˢ", "T": "ᵀ", "U": "ᵁ", "V": "ⱽ", "W": "ᵂ", "X": "ˣ",
    "Y": "ʸ", "Z": "ᶻ",
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
}

SUBSCRIPT = {
    "a": "ₐ", "e": "ₑ", "h": "ₕ", "i": "ᵢ", "j": "ⱼ", "k": "ₖ",
    "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ", "r": "ᵣ",
    "s": "ₛ", "t": "ₜ", "u": "ᵤ", "v": "ᵥ", "x": "ₓ",
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋", "=": "₌", "(": "₍", ")": "₎",
}

UPSIDE_DOWN = str.maketrans({
    "a": "ɐ", "b": "q", "c": "ɔ", "d": "p", "e": "ǝ", "f": "ɟ",
    "g": "ƃ", "h": "ɥ", "i": "ᴉ", "j": "ɾ", "k": "ʞ", "l": "ʃ",
    "m": "ɯ", "n": "u", "o": "o", "p": "d", "q": "b", "r": "ɹ",
    "s": "s", "t": "ʇ", "u": "n", "v": "ʌ", "w": "ʍ", "x": "x",
    "y": "ʎ", "z": "z",
    "A": "∀", "B": "ᗺ", "C": "Ɔ", "D": "ᗡ", "E": "Ǝ", "F": "Ⅎ",
    "G": "פ", "H": "H", "I": "I", "J": "ſ", "K": "ꓘ", "L": "˥",
    "M": "W", "N": "N", "O": "O", "P": "Ԁ", "Q": "Q", "R": "ᴚ",
    "S": "S", "T": "⊥", "U": "∩", "V": "Λ", "W": "M", "X": "X",
    "Y": "⅄", "Z": "Z",
    "0": "0", "1": "Ɩ", "2": "ᄅ", "3": "Ɛ", "4": "ㄣ", "5": "ϛ",
    "6": "9", "7": "ㄥ", "8": "8", "9": "6",
    "!": "¡", "?": "¿", ".": "˙", ",": "'", "'": ",", '"': "„",
    "(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{",
})

MIRROR = str.maketrans({
    "a": "ɒ", "b": "d", "c": "ɔ", "d": "b", "e": "ɘ", "f": "ʇ",
    "g": "ǫ", "h": "ʜ", "i": "i", "j": "ꞁ", "k": "ʞ", "l": "l",
    "m": "m", "n": "ᴎ", "o": "o", "p": "q", "q": "p", "r": "ɿ",
    "s": "ꙅ", "t": "ƚ", "u": "υ", "v": "v", "w": "w", "x": "x",
    "y": "γ", "z": "z",
    "A": "A", "B": "ᗺ", "C": "Ɔ", "D": "ᗡ", "E": "Ǝ", "F": "ꟻ",
    "G": "Ꭾ", "H": "H", "I": "I", "J": "Ⴑ", "K": "ꓘ", "L": "⅃",
    "M": "M", "N": "И", "O": "O", "P": "ꟼ", "Q": "Ϙ", "R": "Я",
    "S": "Ƨ", "T": "T", "U": "U", "V": "V", "W": "W", "X": "X",
    "Y": "Y", "Z": "Z",
})

LEET = str.maketrans({
    "a": "4", "A": "4", "e": "3", "E": "3", "i": "1", "I": "1",
    "o": "0", "O": "0", "s": "5", "S": "5", "t": "7", "T": "7",
    "b": "8", "B": "8", "g": "9", "G": "9",
})

MORSE = {
    "a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.",
    "g": "--.", "h": "....", "i": "..", "j": ".---", "k": "-.-", "l": ".-..",
    "m": "--", "n": "-.", "o": "---", "p": ".--.", "q": "--.-", "r": ".-.",
    "s": "...", "t": "-", "u": "..-", "v": "...-", "w": ".--", "x": "-..-",
    "y": "-.--", "z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}

SPECIAL_STYLES = [
    "small_caps",
    "vaporwave",
    "upside_down",
    "mirror",
    "parenthesized",
    "superscript",
    "subscript",
    "strikethrough",
    "underline",
    "slash",
    "double_underline",
    "sparkle",
    "hearts",
    "stars",
    "spaced",
    "clap",
    "leet",
    "morse",
]

ALL_STYLE_NAMES = sorted(list(FONT_STYLES.keys()) + SPECIAL_STYLES)


def make_translate_table(style_name: str) -> dict[int, str]:
    style = FONT_STYLES[style_name]
    table = {}

    for normal, fancy in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", style["upper"]):
        table[ord(normal)] = fancy

    for normal, fancy in zip("abcdefghijklmnopqrstuvwxyz", style["lower"]):
        table[ord(normal)] = fancy

    for normal, fancy in zip("0123456789", style["digits"]):
        table[ord(normal)] = fancy

    return table


def add_combining_mark(text: str, mark: str) -> str:
    return "".join(char + mark if char != " " else char for char in text)


def convert_font(text: str, style: str) -> str:
    style = style.lower().strip()

    if style in FONT_STYLES:
        return text.translate(make_translate_table(style))

    if style == "small_caps":
        return "".join(SMALL_CAPS.get(char.lower(), char) for char in text)

    if style == "vaporwave":
        converted = []
        for char in text:
            if char == " ":
                converted.append("　")
            elif 33 <= ord(char) <= 126:
                converted.append(chr(ord(char) + 0xFEE0))
            else:
                converted.append(char)
        return "".join(converted)

    if style == "upside_down":
        return text.translate(UPSIDE_DOWN)[::-1]

    if style == "mirror":
        return text.translate(MIRROR)

    if style == "parenthesized":
        return "".join(PARENTHESIZED.get(char.lower(), char) for char in text)

    if style == "superscript":
        return "".join(SUPERSCRIPT.get(char, char) for char in text)

    if style == "subscript":
        return "".join(SUBSCRIPT.get(char, char) for char in text)

    if style == "strikethrough":
        return add_combining_mark(text, "\u0336")

    if style == "underline":
        return add_combining_mark(text, "\u0332")

    if style == "slash":
        return add_combining_mark(text, "\u0338")

    if style == "double_underline":
        return add_combining_mark(text, "\u0333")

    if style == "sparkle":
        return f"✧･ﾟ: *✧･ﾟ:* {text} *:･ﾟ✧*:･ﾟ✧"

    if style == "hearts":
        return f"♡ {text} ♡"

    if style == "stars":
        return f"★ {text} ★"

    if style == "spaced":
        return " ".join(text)

    if style == "clap":
        return " 👏 ".join(text.split())

    if style == "leet":
        return text.translate(LEET)

    if style == "morse":
        converted_words = []
        for word in text.lower().split():
            converted_letters = []
            for char in word:
                converted_letters.append(MORSE.get(char, char))
            converted_words.append(" ".join(converted_letters))
        return " / ".join(converted_words)

    return text


async def font_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    current = current.lower()
    matches = [style for style in ALL_STYLE_NAMES if current in style.lower()]

    return [
        app_commands.Choice(name=style.replace("_", " ").title(), value=style)
        for style in matches[:25]
    ]


class FontGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="font",
            description="Convert text into fun Discord-safe Unicode styles.",
        )

    @app_commands.command(name="list", description="View available font styles.")
    async def list_fonts(self, interaction: discord.Interaction):
        style_text = "\n".join(f"`{style}`" for style in ALL_STYLE_NAMES)

        embed = discord.Embed(
            title="Available Font Styles",
            description=style_text,
            color=discord.Color.purple(),
        )

        embed.add_field(
            name="How to use",
            value=(
                "`/font preview style:gothic text:Hello world`\n"
                "`/font say style:vaporwave text:Hello world`"
            ),
            inline=False,
        )

        embed.set_footer(
            text="These are Unicode styles, so some may look different depending on device."
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="preview", description="Preview text in a font style.")
    @app_commands.describe(
        style="Start typing a style name.",
        text="The text you want to convert.",
    )
    @app_commands.autocomplete(style=font_autocomplete)
    async def preview(
        self,
        interaction: discord.Interaction,
        style: str,
        text: app_commands.Range[str, 1, 500],
    ):
        style = style.lower().strip()

        if style not in ALL_STYLE_NAMES:
            await interaction.response.send_message(
                "That font style does not exist. Use `/font list` to see all styles.",
                ephemeral=True,
            )
            return

        converted = convert_font(text, style)

        embed = discord.Embed(
            title=f"Font Preview: {style.replace('_', ' ').title()}",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Original", value=text, inline=False)
        embed.add_field(name="Converted", value=converted, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="say", description="Send a message using a font style.")
    @app_commands.describe(
        style="Start typing a style name.",
        text="The text you want Dei to send.",
    )
    @app_commands.autocomplete(style=font_autocomplete)
    async def say(
        self,
        interaction: discord.Interaction,
        style: str,
        text: app_commands.Range[str, 1, 1000],
    ):
        style = style.lower().strip()

        if style not in ALL_STYLE_NAMES:
            await interaction.response.send_message(
                "That font style does not exist. Use `/font list` to see all styles.",
                ephemeral=True,
            )
            return

        converted = convert_font(text, style)

        await interaction.response.send_message("Sent!", ephemeral=True)
        await interaction.channel.send(
            converted,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class Fonts(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.font_group = FontGroup()
        self.bot.tree.add_command(self.font_group)

    async def cog_unload(self):
        self.bot.tree.remove_command(
            self.font_group.name,
            type=self.font_group.type,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Fonts(bot))
