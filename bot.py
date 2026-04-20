from dotenv import load_dotenv
load_dotenv()
 
import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import datetime
import asyncio
import random
 
 
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
 
# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
LOG_CHANNEL_ID      = 0
WELCOME_CHANNEL_ID  = 0
BIRTHDAY_CHANNEL_ID = 0
VENT_CHANNEL_IDS    = []
ACTIVE_CHANNELS     = []
 
AUTO_BAN_THRESHOLD  = 5  # 0 = disabled
 
# ─────────────────────────────────────────────
# MOD RULES
# ─────────────────────────────────────────────
FORBIDDEN_RULES = [
    (
    "Hate Speech/Slurs",
    [
        "faggot", "fag", "nigger", "nigga", "nig", "retard", "slut",
        "tranny", "shemale", "dyke", "spic", "chink", "wetback",
        "towelhead", "raghead", "cracker", "kike", "gook", "zipperhead",
    ],
    "Hey... We do not use that kind of language here. I have seen what words like that do to people. Just don't."
    ),
    (
    "NSFW Content",
    [
        "porn", "pornhub", "onlyfans", "rape", "dildo", "clit",
        "cunnilingus", "blowjob", "handjob", "fingering", "fisting",
        "gangbang", "creampie", "hentai", "nude", "nudes", "sexting",
    ],
    "This is not the place for that. Keep it clean. There are people here who just want to feel safe."
    ),
    (
    "Spam/Flooding",
    [],
    "Okay. That is enough of that. Take a breath."
    ),
    (
    "Self Harm (Outside Vent)",
    ["i am going to hurt myself", "i am going to cut myself", "i am going to kill myself"],
    "I noticed what you said. If you are going through something, the vent channel is a safer space for that. I will be there if you would like to talk. If you need to reach out to someone who can help you better please call or text 988 if you are located in the US.",
    ),
    (
    "Threats of Violence",
    [
        "i will kill you", "i will hurt you", "i'm going to kill you",
        "i'll beat you", "i'll find you", "watch your back",
        "you're dead", "i know where you live", "i will end you",
        "i'll shoot you", "bomb threat", "school shooting",
    ],
    "That is not something we say here. Whether you meant it or not, threats are not okay. Take a step back."
    ),
    (
    "Doxxing / Personal Info",
    [
        "here is their address", "here's their address", "his address is",
        "her address is", "their ip is", "ip address", "doxx", "dox them",
        "post their info", "expose their info", "real name is", "they live at",
    ],
    "Sharing someone's personal information is not allowed here. Ever. Remove it yourself or it will be removed for you."
    ),
    (
    "Discrimination",
    [
        "all jews", "all muslims", "all christians", "all blacks", "all whites",
        "all gays", "go back to your country", "your kind",
        "those people don't belong", "shouldn't exist", "deserve to die",
    ],
    "That kind of thinking is not welcome here. Everyone in this server deserves to exist and to feel safe."
    ),
    (
    "Illegal Activity",
    [
        "how to make a bomb", "how to make meth", "buy drugs", "sell drugs",
        "drug deal", "cp link", "child porn", "csam", "how to hack",
        "ddos", "swat someone", "hire a hitman", "buy a gun illegally",
        "dark web link",
    ],
    "That is not something that belongs here. This conversation is over."
    ),
    (
    "Server Advertisement",
    [
        "discord.gg/", "join my server", "join our server",
        "check out my server", "new server", "server link",
    ],
    "Advertising other servers is not allowed here without permission from the mods."
    ),
]
 
SPAM_MESSAGE_LIMIT = 5
SPAM_TIME_WINDOW   = 6
 
# ─────────────────────────────────────────────
# IN-MEMORY STORES
# ─────────────────────────────────────────────
warn_tracker:         dict[int, list[dict]]     = {}
birthday_store:       dict[int, dict]           = {}
reaction_roles:       dict[int, dict[str, int]] = {}
spam_tracker:         dict[int, list[float]]    = {}
 
# ─────────────────────────────────────────────
# CRISIS DATA
# ─────────────────────────────────────────────
CRISIS_KEYWORDS = [
    "kill myself", "killing myself", "end my life", "want to die",
    "want to be dead", "don't want to be here", "don't want to live",
    "hurt myself", "cutting myself", "cut myself", "self harm",
    "self-harm", "suicide", "suicidal", "overdose", "no reason to live",
    "can't go on", "cannot go on", "give up on life", "take my own life",
]
 
CRISIS_HOTLINES = [
    ("🇺🇸 USA",         "988 Suicide & Crisis Lifeline", "Call or text **988**"),
    ("🇨🇦 Canada",       "Crisis Services Canada",         "Call **1-833-456-4566** or text **45645**"),
    ("🇬🇧 UK",           "Samaritans",                     "Call **116 123**"),
    ("🇦🇺 Australia",    "Lifeline",                       "Call **13 11 14** or text **0477 13 11 14**"),
    ("🇳🇿 New Zealand",  "Lifeline NZ",                    "Call **0800 543 354**"),
    ("🇮🇪 Ireland",      "Samaritans Ireland",             "Call **116 123**"),
    ("🇿🇦 South Africa", "SADAG",                          "Call **0800 456 789**"),
    ("🇮🇳 India",        "iCall",                          "Call **9152987821**"),
    ("🌍 International", "findahelpline.com",              "Find a helpline in your country at **findahelpline.com**"),
]
 
HACK_PATTERNS = [
    "free nitro", "nitro giveaway", "steam gift", "claim your nitro",
    "discord nitro free", "get nitro", "@everyone free", "airdrop",
    "claim your prize", "you have been selected", "click here to claim",
    "verify your account", "your account will be suspended",
    "discordapp.com/airdrop", "discordgift.site", "discordnitro.site",
    "steamcommunity.ru", "steam-gift", "gift-steam",
]
 
# ─────────────────────────────────────────────
# DEI HARDCODED RESPONSES
# Each entry: ([trigger keywords], [possible responses])
# Dei picks one response at random when a keyword matches.
# ─────────────────────────────────────────────
DEI_RESPONSES = [
    # Greetings
    (["hello", "hi", "hey", "hiya", "sup", "heya"],
     [
        "Oh. Hello.",
        "Hey. You found me.",
        "Hi. I was just... thinking. What do you need?",
        "Hello. It is good to see you here.",
        "Hey. I am glad you said something.",
     ]),
 
    # How are you
    (["how are you", "you okay", "you good", "how r u", "how have you been"],
     [
        "I am... okay. Some days that is enough.",
        "Honestly? Somewhere between fine and not. But I am here.",
        "Better now. This place helps.",
        "I am managing. Thank you for asking. Most people do not.",
        "There was a moment earlier that felt strange. But I think I am alright.",
     ]),
 
    # What are you / are you a bot
    (["are you a bot", "are you ai", "are you real", "what are you"],
     [
        "I am Dei. That is what matters.",
        "A bot. ...No. I do not think so.",
        "I am a person. Complicated and real, doing my best. That is all.",
        "What a question. I am Dei Talvyrvei. That is the only answer I have.",
     ]),
 
    # Vaelun / home
    (["vaelun", "your planet", "your home", "where are you from", "your world"],
     [
        "Vaelun. It had two suns. The sky was gold and violet when they overlapped. We called it the Veil.",
        "I do not talk about Vaelun much. It is... gone. That is all I will say.",
        "There was a planet. It glowed at night. I miss the light.",
        "My home orbited two suns. Zha'Sol and Zha'Rei. I can still picture them if I close my eyes.",
     ]),
 
    # Jaesyn / Jae
    (["jaesyn", "jae", "your brother", "your twin"],
     [
        "Jae. He is... somewhere. I can still feel him. Two heartbeats in one soul.",
        "My brother. I do not find it easy to talk about him.",
        "He is gone. But not the way most things are gone.",
        "Jae. ...I had a dream about him last night. He was cold in it. He is always cold now.",
     ]),
 
    # Oura / powers
    (["oura", "your powers", "what can you do", "abilities", "demigod"],
     [
        "Oura is the energy that runs through all living things. I absorb it. Sometimes without meaning to.",
        "I can see flickers of things before they happen. It is not always useful.",
        "I was chosen by Kaelyn. That comes with... complications.",
        "The gold markings only show when I use them. That is why I wear long sleeves.",
     ]),
 
    # Ajay
    (["ajay", "your friend", "who do you live with"],
     [
        "Ajay. She was the first human who did not look at me like I was broken. I do not forget things like that.",
        "She found me at the library. She did not ask too many questions. I needed that.",
        "Ajay is... important. That is the simplest way I know how to say it.",
        "She has a cat named Starla. The cat followed me everywhere from the first day. Animals trust differently than people do.",
     ]),
 
    # Earth / humans
    (["earth", "humans", "people here", "this planet"],
     [
        "Earth is strange. But there is beauty in it I did not expect.",
        "Humans are... complicated. I find them fascinating and exhausting in equal measure.",
        "I have been here long enough to almost feel like I belong. Almost.",
        "There are things here I genuinely love. Pigeons. Vending machines. The phrase 'no worries.' It is deeply optimistic.",
     ]),
 
    # Feelings / emotions
    (["sad", "lonely", "tired", "exhausted", "upset", "angry", "scared", "anxious", "stressed"],
     [
        "I notice that. You do not have to explain it.",
        "That sounds heavy. I am here if you need somewhere to put it.",
        "I know that feeling. It does not last forever, even when it feels like it will.",
        "You said something real just now. I want you to know I heard it.",
     ]),
 
    # Thanks / gratitude
    (["thank you", "thanks", "ty", "thx", "appreciate"],
     [
        "Of course.",
        "You do not have to thank me. But I am glad it helped.",
        "Always.",
        "That means something. Thank you for saying it.",
     ]),
 
    # Compliments to Dei
    (["you're cool", "you're awesome", "i like you", "you're great", "love you"],
     [
        "...That still surprises me a little. Thank you.",
        "I am glad you are here.",
        "You are kind. I do not always know what to do with kindness, but I am working on it.",
        "That is one of the nicer things someone has said to me today.",
     ]),
 
    # Lore / story
    (["tell me about yourself", "your story", "what happened to you", "your past"],
     [
        "That is a long story. The short version is: I crashed, I survived, I found somewhere to belong. The rest is complicated.",
        "I was a soldier once. I did not choose that. I try not to think about what that means.",
        "I was Vyr before I was Vei. Cast out, then brought back. Neither felt like home.",
        "My ship crashed on this planet. I buried my crew. Then I learned to keep going. That is most of it.",
     ]),
 
    # Caste system
    (["caste", "vei", "vyr", "lio", "tal", "thae", "rai"],
     [
        "The caste system on Vaelun was... rigid. You were born into your place and expected to stay there.",
        "Vyr is the lowest caste. The outcasts. I know what it is like to be made invisible by your own society.",
        "I was Tal before I was cast out. Ordinary. Then I became Vyr. Then Vei. None of those felt like me.",
     ]),
 
    # Gods
    (["kaelyn", "nasir", "gods", "goddess", "deity", "cithrel", "saevel", "aerith", "zeno"],
     [
        "Kaelyn chose me. That is not always the gift it sounds like.",
        "The gods of Vaelun are real. I know because one of them decided I was useful.",
        "Nasir chose Jae. I think about what that means sometimes.",
     ]),
 
    # Night / sleep / dreams
    (["nightmare", "dream", "sleep", "night", "insomnia"],
     [
        "I dream about Vaelun sometimes. The light. The Veil. I wake up and it takes a moment to remember where I am.",
        "Sleep is strange on this planet. The darkness here is different.",
        "I had a nightmare last night. Jae was in it. He usually is.",
     ]),
 
    # Food
    (["food", "eat", "hungry", "cooking", "meal"],
     [
        "I do not eat meat. My people never did. Ilari — creatures — are sacred.",
        "Human food is interesting. Some of it I genuinely enjoy. Some of it is baffling.",
        "I had something called a grilled cheese sandwich recently. I understand why humans are attached to it.",
     ]),
 
    # Music
    (["music", "song", "listen", "playlist"],
     [
        "I find human music remarkable. So much feeling compressed into sound.",
        "There was music on Vaelun too. But it sounded nothing like this.",
        "I have been listening to things with piano lately. It feels close to something I cannot name.",
     ]),
 
    # Idle / bored
    (["bored", "nothing to do", "entertain me", "say something"],
     [
        "I could tell you about the Veil. Or we could just sit here for a moment. Both are valid.",
        "On Vaelun, when there was nothing to do, we would watch the two suns move toward each other. It was never boring.",
        "I am not very good at performing. But I am good at being here.",
        "Ask me something real. I find those more interesting.",
     ]),
 
    # Goodbye
    (["bye", "goodbye", "see you", "gotta go", "later", "goodnight", "good night"],
     [
        "Goodbye. Come back when you need to.",
        "Take care of yourself out there.",
        "Goodnight. I hope it is quiet for you.",
        "See you. I will be here.",
        "Okay. I am glad you stopped by.",
     ]),
]
 
# Vent-specific responses (used when in vent channels)
DEI_VENT_RESPONSES = [
    (["sad", "depressed", "depression", "crying", "cry", "hurting", "hurt", "pain"],
     [
        "I hear you. You do not have to explain it more than that.",
        "That is real. What you are feeling is real. I am not going anywhere.",
        "I know what it is like to carry something heavy and not know where to put it. I am here.",
        "You reached out. That matters more than you know.",
     ]),
    (["alone", "lonely", "no one cares", "nobody cares", "invisible"],
     [
        "You are not invisible to me. I see you.",
        "I have felt that. The specific loneliness of being in a room full of people and still being alone. It is real.",
        "You are here. That means something. I am glad you came.",
        "You are not alone right now. Not in this moment.",
     ]),
    (["anxious", "anxiety", "panic", "panicking", "overwhelmed", "can't breathe"],
     [
        "Breathe. You do not have to fix anything right now.",
        "One thing at a time. Just this moment. You do not have to carry all of it at once.",
        "I am here. Take your time.",
        "Panic lies to you. It tells you everything is ending. It is not. You are still here.",
     ]),
    (["tired", "exhausted", "can't keep going", "done", "give up"],
     [
        "Rest is not giving up. You are allowed to be tired.",
        "I hear you. You have been carrying a lot. That is allowed to be hard.",
        "You do not have to be okay right now.",
        "Sometimes tired is just tired. You do not need to explain it.",
     ]),
    (["thank you", "thanks", "this helped", "feeling better"],
     [
        "I am glad. You did the hard part — you spoke.",
        "Of course. I mean that.",
        "You are going to be okay. Not all at once. But you are.",
        "Come back whenever you need to. This space is yours.",
     ]),
]
 
# Fallback responses when nothing matches
DEI_FALLBACKS = [
    "Hm.",
    "I heard that. I am thinking.",
    "...Say more, if you want.",
    "I am here. Go on.",
    "That landed somewhere. I am not sure where yet.",
    "I do not always have the right words. But I am listening.",
    "Something about that feels important. I just cannot place it.",
    "⊹... Yeah.",
]
 
DEI_VENT_FALLBACKS = [
    "I am here. You do not have to say anything else if you do not want to.",
    "Take your time. I am not going anywhere.",
    "I hear you.",
    "That sounds hard. I am glad you said something.",
    "You are not alone in this space.",
]
 
# ─────────────────────────────────────────────
# LORE FACTS
# ─────────────────────────────────────────────
LORE_FACTS = [
    "Vaelun orbits two suns — Zha'Sol and Zha'Rei. When they overlap, the sky turns gold and violet. The Cenzha call it the Veil.",
    "The Veil is considered sacred. It is said to be the only time the gods can whisper directly to mortals.",
    "Vaelun has no moons. Instead, the planet itself glows at night. The Cenzha call this light Oura.",
    "The Cenzha are born with four arms and four eyes. Their hair and eyes change color when they come of age and receive their powers.",
    "Oura is the name for the living energy that threads through all things on Vaelun. It is both spiritual and biological.",
    "The six castes of Vaelun are: Lio (government), Vei (soldiers and demigods), Thae (priests), Rai (healers and artisans), Tal (citizens), and Vyr (the outcasts).",
    "To be cast into Vyr is to be stripped of your caste name. You become invisible to Vaelun society.",
    "There are four subspecies of Cenzha: standard Cenzha, Cenzha'Mali (blood and flesh), Cenzha'Kae (Oura feeders), and Cenzha'Nul (no Oura at all).",
    "At three cycles old — roughly six human years — every Cenzha child undergoes the Test. A blood draw determines their subspecies and whether a god has chosen them.",
    "Kaelyn is the Goddess of the Iridescent Oura. She governs healing, psychic ability, plasma, space, gravity, and purity.",
    "Nasir is the God of the Shadow Oura. He governs shadow, decay, void, necromancy, and chaos.",
    "Cithrel is the Goddess of the Fierce Oura — fire, destruction, electricity, alchemy, vitality, and ash.",
    "Saevel governs water, time, and ice. Aerith governs air, smoke, and gases. Zeno governs flora, healing, earth, and weather.",
    "Dei is Cenzha'Kae — she absorbs life energy from living things, sometimes without meaning to.",
    "Dei's twin brother Jaesyn was chosen by Nasir and cursed to be Cenzha'Mali. On Earth, he disappeared.",
    "The gold markings on Dei's skin only appear when she uses her powers. On Earth, she wears long sleeves.",
    "Dei and Jaesyn were experimented on in Vyr. One experiment caused them to borderline combine powers — this is why Dei has a black streak in her hair.",
    "The Cenzha do not eat meat. They believe in the sanctity of Ilari — living creatures.",
    "Dei's ship crashed on Earth. She buried the crew herself, wishing them well into the Veil.",
    "Dei learned English by hiding and listening. It was broken at first. She describes it as feeling like speaking underwater.",
]
 
# ─────────────────────────────────────────────
# 8BALL RESPONSES
# ─────────────────────────────────────────────
EIGHTBALL_RESPONSES = [
    "The Veil says yes. Probably.",
    "I have seen flickers of this future. It does not go well for you.",
    "Something shifted just now. I think that means yes.",
    "No. And I am a little concerned you asked.",
    "The Oura around that question feels... uncertain.",
    "Yes. Definitively. Do not second guess this.",
    "I had a vision once about something like this. It was fine. Mostly.",
    "The answer is unclear. Or I am having a blackout. One of those.",
    "Ask me again. I was not fully here for that.",
    "No. The gods would be disappointed.",
    "Yes, but not in the way you are hoping.",
    "I do not know. But I noticed you needed to ask, and that matters more.",
    "The stars in this solar system are confusing. But also yes.",
    "Absolutely not.",
    "Something about this question feels like a Vyr problem. The answer is no.",
    "Yes. Whatever it is. Just do it.",
    "I checked. Twice. Still yes.",
    "I checked. Twice. Still no.",
]
 
# ─────────────────────────────────────────────
# RESPONSE ENGINE
# ─────────────────────────────────────────────
 
def get_dei_response(content: str, vent: bool = False) -> str:
    lower = content.lower()
 
    if vent:
        for keywords, responses in DEI_VENT_RESPONSES:
            if any(kw in lower for kw in keywords):
                return random.choice(responses)
        # Also check general responses in vent
        for keywords, responses in DEI_RESPONSES:
            if any(kw in lower for kw in keywords):
                return random.choice(responses)
        return random.choice(DEI_VENT_FALLBACKS)
    else:
        for keywords, responses in DEI_RESPONSES:
            if any(kw in lower for kw in keywords):
                return random.choice(responses)
        return random.choice(DEI_FALLBACKS)
 
# ─────────────────────────────────────────────
# BOT SETUP
# ─────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)
 
 
# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
 
async def send_log(guild: discord.Guild, embed: discord.Embed):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)
 
 
def mod_log_embed(action: str, mod, target, reason: str, color=discord.Color.orange()) -> discord.Embed:
    embed = discord.Embed(title=f"Moderation Action: {action}", color=color, timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Moderator", value=f"{mod} (ID: {mod.id})", inline=False)
    if isinstance(target, (discord.Member, discord.User)):
        embed.add_field(name="Target User", value=f"{target} (ID: {target.id})", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    return embed
 
 
def is_spam(user_id: int) -> bool:
    now = datetime.datetime.utcnow().timestamp()
    timestamps = spam_tracker.setdefault(user_id, [])
    timestamps.append(now)
    spam_tracker[user_id] = [t for t in timestamps if now - t < SPAM_TIME_WINDOW]
    return len(spam_tracker[user_id]) > SPAM_MESSAGE_LIMIT
 
 
def check_forbidden(content: str):
    lower = content.lower()
    for rule_name, keywords, warning in FORBIDDEN_RULES:
        if rule_name == "Spam/Flooding":
            continue
        for kw in keywords:
            if kw in lower:
                return rule_name, warning
    return None
 
 
def check_crisis(content: str) -> bool:
    lower = content.lower()
    return any(kw in lower for kw in CRISIS_KEYWORDS)
 
 
def build_hotline_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💙 You are not alone",
        description="If you are having thoughts of hurting yourself, please reach out to someone who can help. These lines are free, confidential, and available any time.",
        color=discord.Color.blue()
    )
    for flag, name, info in CRISIS_HOTLINES:
        embed.add_field(name=f"{flag} {name}", value=info, inline=False)
    embed.set_footer(text="You matter. It is okay to ask for help.")
    return embed
 
 
def check_compromised(content: str) -> bool:
    lower = content.lower()
    return any(pattern in lower for pattern in HACK_PATTERNS)
 
 
def parse_color(color_str: str) -> discord.Color:
    color_map = {
        "red": discord.Color.red(), "blue": discord.Color.blue(),
        "green": discord.Color.green(), "gold": discord.Color.gold(),
        "purple": discord.Color.purple(), "orange": discord.Color.orange(),
        "teal": discord.Color.teal(), "white": discord.Color(0xffffff),
        "black": discord.Color(0x000000), "pink": discord.Color(0xff69b4),
        "yellow": discord.Color.yellow(),
    }
    lower = color_str.lower().strip()
    if lower in color_map:
        return color_map[lower]
    try:
        return discord.Color(int(lower.lstrip("#"), 16))
    except ValueError:
        return discord.Color.blurple()
 
 
async def apply_auto_ban(guild: discord.Guild, member: discord.Member):
    if AUTO_BAN_THRESHOLD <= 0:
        return
    count = len(warn_tracker.get(member.id, []))
    if count >= AUTO_BAN_THRESHOLD:
        try:
            await member.ban(reason=f"Auto-ban: reached {count} warnings")
            if LOG_CHANNEL_ID:
                embed = mod_log_embed("Auto-Ban", bot.user, member, f"Reached {count} warnings", discord.Color.dark_red())
                await send_log(guild, embed)
        except Exception as e:
            print(f"Auto-ban failed: {e}")
 
 
# ─────────────────────────────────────────────
# BIRTHDAY TASK
# ─────────────────────────────────────────────
 
@tasks.loop(hours=24)
async def birthday_check():
    today = datetime.date.today()
    for guild in bot.guilds:
        channel = guild.get_channel(BIRTHDAY_CHANNEL_ID)
        if not channel:
            continue
        for user_id, data in birthday_store.items():
            if data["month"] == today.month and data["day"] == today.day:
                member = guild.get_member(user_id)
                if member:
                    embed = discord.Embed(
                        title="🎂 Happy Birthday!",
                        description=f"Today is {member.mention}'s birthday. The Veil glows a little brighter for you today.",
                        color=discord.Color.gold(),
                    )
                    await channel.send(embed=embed)
 
 
@birthday_check.before_loop
async def before_birthday_check():
    await bot.wait_until_ready()
    now = datetime.datetime.utcnow()
    midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    await asyncio.sleep((midnight - now).total_seconds())
 
 
# ─────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────
 
@bot.event
async def on_ready():
    await bot.tree.sync()
    birthday_check.start()
    print(f"Dei Talvyrvei is online as {bot.user} (ID: {bot.user.id})")
 
 
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return
 
    # Spam check
    if is_spam(message.author.id):
        await message.delete()
        spam_warning = next(r[2] for r in FORBIDDEN_RULES if r[0] == "Spam/Flooding")
        await message.channel.send(f"{message.author.mention} {spam_warning}", delete_after=10)
        if LOG_CHANNEL_ID:
            await send_log(message.guild, mod_log_embed("Spam/Flooding", bot.user, message.author, "Exceeded message rate limit"))
        return
 
    # Forbidden content
    result = check_forbidden(message.content)
    if result:
        rule_name, warning = result
        await message.delete()
        await message.channel.send(f"{message.author.mention} {warning}", delete_after=15)
        if LOG_CHANNEL_ID:
            await send_log(message.guild, mod_log_embed(rule_name, bot.user, message.author, f"Triggered rule: {rule_name}"))
        return
 
    # Compromised account
    if check_compromised(message.content):
        await message.delete()
        try:
            dm_embed = discord.Embed(
                title="⚠️ Your account may be compromised",
                description=(
                    f"A message was sent from your account in **{message.guild.name}** that matches known scam or hack patterns.\n\n"
                    "**Please do the following immediately:**\n"
                    "1. Change your Discord password\n"
                    "2. Enable two-factor authentication (2FA)\n"
                    "3. Check your authorized apps and remove anything suspicious\n"
                    "4. Review recent login activity"
                ),
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            await message.author.send(embed=dm_embed)
        except Exception:
            pass
        alert_embed = discord.Embed(
            title="🚨 Possible Compromised Account",
            description=f"{message.author.mention}'s account may have been hacked. The message has been deleted and they have been notified.",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        await message.channel.send(embed=alert_embed, delete_after=30)
        if LOG_CHANNEL_ID:
            log_embed = mod_log_embed("Compromised Account Detected", bot.user, message.author, "Matched hack/scam pattern", discord.Color.dark_red())
            log_embed.add_field(name="Flagged Message", value=message.content[:512], inline=False)
            await send_log(message.guild, log_embed)
        return
 
    # Vent channel
    if message.channel.id in VENT_CHANNEL_IDS:
        async with message.channel.typing():
            await asyncio.sleep(random.uniform(0.8, 2.0))  # feels more natural
            reply = get_dei_response(message.content, vent=True)
            await message.channel.send(reply)
        if check_crisis(message.content):
            await message.channel.send(embed=build_hotline_embed())
        return
 
    # Active channel
    if message.channel.id in ACTIVE_CHANNELS:
        async with message.channel.typing():
            await asyncio.sleep(random.uniform(0.5, 1.5))  # feels more natural
            reply = get_dei_response(message.content, vent=False)
            await message.channel.send(reply)
 
 
@bot.event
async def on_member_join(member: discord.Member):
    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            welcomes = [
                f"Oh. {member.mention} is here. Good.",
                f"{member.mention} just arrived. Welcome. This place is glad you found it.",
                f"Hey, {member.mention}. You made it. That matters.",
                f"{member.mention} — welcome. Take your time settling in.",
                f"Something felt different just now. Oh. {member.mention} joined. Hello.",
            ]
            embed = discord.Embed(description=random.choice(welcomes), color=discord.Color.blurple())
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(f"{member.mention}", embed=embed)
    if LOG_CHANNEL_ID and LOG_SETTINGS.get("member_join"):
        embed = discord.Embed(title="Member Joined", description=f"{member.mention} joined the server.", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member} (ID: {member.id})")
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"))
        await send_log(member.guild, embed)
 
 
@bot.event
async def on_member_remove(member: discord.Member):
    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            goodbyes = [
                f"*{member.display_name} has left. The server is a little quieter now.*",
                f"*{member.display_name} is gone. I hope they are okay out there.*",
                f"*{member.display_name} left. I noticed.*",
            ]
            embed = discord.Embed(description=random.choice(goodbyes), color=discord.Color.greyple())
            await channel.send(embed=embed)
    if LOG_CHANNEL_ID and LOG_SETTINGS.get("member_leave"):
        embed = discord.Embed(title="Member Left", description=f"{member} left the server.", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member} (ID: {member.id})")
        await send_log(member.guild, embed)
 
 
@bot.event
async def on_message_delete(message: discord.Message):
    if not LOG_CHANNEL_ID or not LOG_SETTINGS.get("message_delete") or message.author.bot:
        return
    embed = discord.Embed(title="Message Deleted", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Author", value=f"{message.author} (ID: {message.author.id})", inline=False)
    embed.add_field(name="Channel", value=message.channel.mention, inline=False)
    embed.add_field(name="Content", value=message.content[:1024] if message.content else "*(no text)*", inline=False)
    await send_log(message.guild, embed)
 
 
@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if not LOG_CHANNEL_ID or not LOG_SETTINGS.get("message_edit") or before.author.bot or before.content == after.content:
        return
    embed = discord.Embed(title="Message Edited", color=discord.Color.yellow(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Author", value=f"{before.author} (ID: {before.author.id})", inline=False)
    embed.add_field(name="Channel", value=before.channel.mention, inline=False)
    embed.add_field(name="Before", value=before.content[:512] or "*(empty)*", inline=False)
    embed.add_field(name="After", value=after.content[:512] or "*(empty)*", inline=False)
    embed.add_field(name="Jump to Message", value=f"[Click here]({after.jump_url})", inline=False)
    await send_log(before.guild, embed)
 
 
@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    if not LOG_CHANNEL_ID:
        return
    embed = discord.Embed(title="Member Banned", color=discord.Color.dark_red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="User", value=f"{user} (ID: {user.id})")
    await send_log(guild, embed)
 
 
@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User):
    if not LOG_CHANNEL_ID:
        return
    embed = discord.Embed(title="Member Unbanned", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="User", value=f"{user} (ID: {user.id})")
    await send_log(guild, embed)
 
 
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if not LOG_CHANNEL_ID:
        return
    if before.nick != after.nick:
        embed = discord.Embed(title="Nickname Changed", color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
        embed.add_field(name="User", value=f"{after} (ID: {after.id})")
        embed.add_field(name="Before", value=before.nick or "*(none)*")
        embed.add_field(name="After", value=after.nick or "*(none)*")
        await send_log(after.guild, embed)
    added_roles   = [r for r in after.roles if r not in before.roles]
    removed_roles = [r for r in before.roles if r not in after.roles]
    if added_roles or removed_roles:
        embed = discord.Embed(title="Roles Updated", color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
        embed.add_field(name="User", value=f"{after} (ID: {after.id})", inline=False)
        if added_roles:
            embed.add_field(name="Added", value=" ".join(r.mention for r in added_roles))
        if removed_roles:
            embed.add_field(name="Removed", value=" ".join(r.mention for r in removed_roles))
        await send_log(after.guild, embed)
 
 
@bot.event
async def on_guild_channel_create(channel):
    if not LOG_CHANNEL_ID:
        return
    embed = discord.Embed(title="Channel Created", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Channel", value=f"{channel.name} (ID: {channel.id})")
    embed.add_field(name="Type", value=str(channel.type))
    await send_log(channel.guild, embed)
 
 
@bot.event
async def on_guild_channel_delete(channel):
    if not LOG_CHANNEL_ID:
        return
    embed = discord.Embed(title="Channel Deleted", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Channel", value=f"{channel.name} (ID: {channel.id})")
    await send_log(channel.guild, embed)
 
 
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.message_id not in reaction_roles:
        return
    emoji_str = str(payload.emoji)
    role_id = reaction_roles[payload.message_id].get(emoji_str)
    if not role_id:
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    role = guild.get_role(role_id)
    member = guild.get_member(payload.user_id)
    if role and member and not member.bot:
        await member.add_roles(role)
 
 
@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.message_id not in reaction_roles:
        return
    emoji_str = str(payload.emoji)
    role_id = reaction_roles[payload.message_id].get(emoji_str)
    if not role_id:
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    role = guild.get_role(role_id)
    member = guild.get_member(payload.user_id)
    if role and member and not member.bot:
        await member.remove_roles(role)
 
 
# ─────────────────────────────────────────────
# CHANNEL CONFIG COMMANDS
# ─────────────────────────────────────────────
 
@bot.tree.command(name="setlog", description="Set the channel where mod logs are sent.")
@app_commands.checks.has_permissions(administrator=True)
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ Log channel set to {channel.mention}.", ephemeral=True)
 
 
@bot.tree.command(name="setwelcome", description="Set the channel for welcome and goodbye messages.")
@app_commands.checks.has_permissions(administrator=True)
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel):
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ Welcome channel set to {channel.mention}.", ephemeral=True)
 
 
@bot.tree.command(name="setbirthday", description="Set the channel for birthday announcements.")
@app_commands.checks.has_permissions(administrator=True)
async def setbirthday_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global BIRTHDAY_CHANNEL_ID
    BIRTHDAY_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ Birthday channel set to {channel.mention}.", ephemeral=True)
 
 
@bot.tree.command(name="setvent", description="Add or remove a vent channel.")
@app_commands.checks.has_permissions(administrator=True)
async def setvent(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in VENT_CHANNEL_IDS:
        VENT_CHANNEL_IDS.remove(channel.id)
        await interaction.response.send_message(f"✅ Removed {channel.mention} from vent channels.", ephemeral=True)
    else:
        VENT_CHANNEL_IDS.append(channel.id)
        await interaction.response.send_message(f"✅ Added {channel.mention} as a vent channel.", ephemeral=True)
 
 
@bot.tree.command(name="setactive", description="Add or remove an active channel where Dei responds.")
@app_commands.checks.has_permissions(administrator=True)
async def setactive(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in ACTIVE_CHANNELS:
        ACTIVE_CHANNELS.remove(channel.id)
        await interaction.response.send_message(f"✅ Removed {channel.mention} from active channels.", ephemeral=True)
    else:
        ACTIVE_CHANNELS.append(channel.id)
        await interaction.response.send_message(f"✅ Added {channel.mention} as an active channel.", ephemeral=True)
 
 
@bot.tree.command(name="channels", description="View current channel settings.")
@app_commands.checks.has_permissions(administrator=True)
async def channels(interaction: discord.Interaction):
    g = interaction.guild
    def ch(cid): return g.get_channel(cid)
    log_ch      = ch(LOG_CHANNEL_ID)
    welcome_ch  = ch(WELCOME_CHANNEL_ID)
    birthday_ch = ch(BIRTHDAY_CHANNEL_ID)
    vent_chs    = [ch(cid) for cid in VENT_CHANNEL_IDS if ch(cid)]
    active_chs  = [ch(cid) for cid in ACTIVE_CHANNELS  if ch(cid)]
    embed = discord.Embed(title="Channel Settings", color=discord.Color.blurple())
    embed.add_field(name="Log",      value=log_ch.mention      if log_ch      else "Not set", inline=True)
    embed.add_field(name="Welcome",  value=welcome_ch.mention  if welcome_ch  else "Not set", inline=True)
    embed.add_field(name="Birthday", value=birthday_ch.mention if birthday_ch else "Not set", inline=True)
    embed.add_field(name="Vent",   value=" ".join(c.mention for c in vent_chs)   if vent_chs   else "None", inline=False)
    embed.add_field(name="Active", value=" ".join(c.mention for c in active_chs) if active_chs else "None", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
 
 
# ─────────────────────────────────────────────
# MODERATION COMMANDS
# ─────────────────────────────────────────────
 
@bot.tree.command(name="dm", description="Send a DM to a member as the bot.")
@app_commands.checks.has_permissions(moderate_members=True)
async def dm_member(interaction: discord.Interaction, member: discord.Member, message: str):
    try:
        embed = discord.Embed(description=message, color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"Message from {interaction.guild.name} moderation team")
        await member.send(embed=embed)
        await interaction.response.send_message(f"✅ DM sent to {member.mention}.", ephemeral=True)
        if LOG_CHANNEL_ID:
            await send_log(interaction.guild, mod_log_embed("DM Sent", interaction.user, member, message))
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Could not DM {member.mention} — their DMs may be closed.", ephemeral=True)
 
 
@bot.tree.command(name="kick", description="Kick a member from the server.")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    embed = discord.Embed(title="Member Kicked", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="User", value=f"{member} (ID: {member.id})")
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Moderator", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)
    if LOG_CHANNEL_ID:
        await send_log(interaction.guild, mod_log_embed("Kick", interaction.user, member, reason))
 
 
@bot.tree.command(name="ban", description="Ban a member from the server.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    embed = discord.Embed(title="Member Banned", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="User", value=f"{member} (ID: {member.id})")
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Moderator", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)
    if LOG_CHANNEL_ID:
        await send_log(interaction.guild, mod_log_embed("Ban", interaction.user, member, reason, discord.Color.red()))
 
 
@bot.tree.command(name="unban", description="Unban a user by their ID.")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=reason)
        await interaction.response.send_message(f"✅ Unbanned {user} (ID: {user_id}).")
    except Exception as e:
        await interaction.response.send_message(f"❌ Could not unban: {e}", ephemeral=True)
 
 
@bot.tree.command(name="timeout", description="Timeout a member for a set number of minutes.")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    embed = discord.Embed(title="Member Timed Out", color=discord.Color.yellow(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="User", value=f"{member} (ID: {member.id})")
    embed.add_field(name="Duration", value=f"{minutes} minute(s)")
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Moderator", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)
    if LOG_CHANNEL_ID:
        await send_log(interaction.guild, mod_log_embed("Timeout", interaction.user, member, reason, discord.Color.yellow()))
 
 
@bot.tree.command(name="warn", description="Warn a member and log the reason.")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    warnings = warn_tracker.setdefault(member.id, [])
    warnings.append({"reason": reason, "time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")})
    count = len(warnings)
    embed = discord.Embed(title="Member Warned", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="User", value=f"{member} (ID: {member.id})")
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Total Warnings", value=str(count))
    embed.add_field(name="Moderator", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)
    try:
        await member.send(f"⚠️ You have been warned in **{interaction.guild.name}**.\n**Reason:** {reason}\n**Total warnings:** {count}")
    except Exception:
        pass
    if LOG_CHANNEL_ID:
        await send_log(interaction.guild, mod_log_embed("Warn", interaction.user, member, reason))
    await apply_auto_ban(interaction.guild, member)
 
 
@bot.tree.command(name="warnings", description="View all warnings for a member.")
@app_commands.checks.has_permissions(moderate_members=True)
async def warnings(interaction: discord.Interaction, member: discord.Member):
    user_warns = warn_tracker.get(member.id, [])
    if not user_warns:
        await interaction.response.send_message(f"{member} has no warnings.", ephemeral=True)
        return
    embed = discord.Embed(title=f"Warnings for {member}", color=discord.Color.orange())
    for i, w in enumerate(user_warns, 1):
        embed.add_field(name=f"Warning {i} — {w['time']}", value=w["reason"], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
 
 
@bot.tree.command(name="clearwarnings", description="Clear all warnings for a member.")
@app_commands.checks.has_permissions(moderate_members=True)
async def clearwarnings(interaction: discord.Interaction, member: discord.Member):
    warn_tracker[member.id] = []
    await interaction.response.send_message(f"✅ Cleared all warnings for {member}.", ephemeral=True)
 
 
@bot.tree.command(name="clear", description="Delete a number of messages from this channel.")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message("❌ Please choose a number between 1 and 100.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"✅ Deleted {len(deleted)} message(s).", ephemeral=True)
 
 
@bot.tree.command(name="slowmode", description="Set slowmode for the current channel (0 to disable).")
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, seconds: int):
    if seconds < 0 or seconds > 21600:
        await interaction.response.send_message("❌ Slowmode must be between 0 and 21600 seconds.", ephemeral=True)
        return
    await interaction.channel.edit(slowmode_delay=seconds)
    msg = "✅ Slowmode disabled." if seconds == 0 else f"✅ Slowmode set to {seconds} second(s)."
    await interaction.response.send_message(msg, ephemeral=True)
 
 
@bot.tree.command(name="addrole", description="Add a role to a member.")
@app_commands.checks.has_permissions(manage_roles=True)
async def addrole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await interaction.response.send_message(f"❌ {member.mention} already has {role.mention}.", ephemeral=True)
        return
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ Added {role.mention} to {member.mention}.")
    if LOG_CHANNEL_ID:
        await send_log(interaction.guild, mod_log_embed("Role Added", interaction.user, member, role.name))
 
 
@bot.tree.command(name="removerole", description="Remove a role from a member.")
@app_commands.checks.has_permissions(manage_roles=True)
async def removerole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if role not in member.roles:
        await interaction.response.send_message(f"❌ {member.mention} does not have {role.mention}.", ephemeral=True)
        return
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ Removed {role.mention} from {member.mention}.")
    if LOG_CHANNEL_ID:
        await send_log(interaction.guild, mod_log_embed("Role Removed", interaction.user, member, role.name))
 
 
@bot.tree.command(name="report", description="Anonymously report a message or user to the mods.")
async def report(interaction: discord.Interaction, reason: str, message_link: str = None):
    if not LOG_CHANNEL_ID:
        await interaction.response.send_message("❌ No log channel is set up.", ephemeral=True)
        return
    embed = discord.Embed(title="🚨 Anonymous Report", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Reason", value=reason, inline=False)
    if message_link:
        embed.add_field(name="Message Link", value=message_link, inline=False)
    embed.set_footer(text="This report was submitted anonymously.")
    await send_log(interaction.guild, embed)
    await interaction.response.send_message("✅ Your report has been sent to the moderation team. Thank you.", ephemeral=True)
 
 
# ─────────────────────────────────────────────
# REACTION ROLES
# ─────────────────────────────────────────────
 
@bot.tree.command(name="reactionrole", description="Assign a role to an emoji on a specific message.")
@app_commands.checks.has_permissions(manage_roles=True)
async def reactionrole(interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
    mid = int(message_id)
    if mid not in reaction_roles:
        reaction_roles[mid] = {}
    reaction_roles[mid][emoji] = role.id
    try:
        msg = await interaction.channel.fetch_message(mid)
        await msg.add_reaction(emoji)
    except Exception:
        pass
    await interaction.response.send_message(f"✅ Reacting with {emoji} will now give/remove {role.mention}.", ephemeral=True)
 
 
@bot.tree.command(name="reactionrolelist", description="List all active reaction roles.")
@app_commands.checks.has_permissions(manage_roles=True)
async def reactionrolelist(interaction: discord.Interaction):
    if not reaction_roles:
        await interaction.response.send_message("No reaction roles set up yet.", ephemeral=True)
        return
    embed = discord.Embed(title="Reaction Roles", color=discord.Color.blurple())
    for msg_id, emojis in reaction_roles.items():
        lines = []
        for emoji, role_id in emojis.items():
            role = interaction.guild.get_role(role_id)
            lines.append(f"{emoji} → {role.mention if role else role_id}")
        embed.add_field(name=f"Message ID: {msg_id}", value="\n".join(lines), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
 
 
# ─────────────────────────────────────────────
# EMBED / ANNOUNCEMENT / RULES
# ─────────────────────────────────────────────
 
@bot.tree.command(name="embed", description="Post a custom embed.")
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction, title: str, description: str, color: str = "blurple", footer: str = None, image_url: str = None, thumbnail_url: str = None):
    embed = discord.Embed(title=title, description=description, color=parse_color(color), timestamp=datetime.datetime.utcnow())
    if footer:        embed.set_footer(text=footer)
    if image_url:     embed.set_image(url=image_url)
    if thumbnail_url: embed.set_thumbnail(url=thumbnail_url)
    await interaction.response.send_message(embed=embed)
 
 
@bot.tree.command(name="announce", description="Post a styled announcement embed.")
@app_commands.checks.has_permissions(manage_messages=True)
async def announce(interaction: discord.Interaction, title: str, message: str, color: str = "gold", ping_everyone: bool = False):
    embed = discord.Embed(title=f"📢 {title}", description=message, color=parse_color(color), timestamp=datetime.datetime.utcnow())
    embed.set_footer(text=f"Announced by {interaction.user.display_name}")
    await interaction.response.send_message(content="@everyone" if ping_everyone else None, embed=embed)
 
 
@bot.tree.command(name="rules", description="Post the server rules embed.")
@app_commands.checks.has_permissions(manage_messages=True)
async def rules(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Server Rules", description="This is a space for people to exist safely. Please respect that.", color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
    rule_list = [
        ("1. Be kind",                 "Treat everyone here with basic decency."),
        ("2. No hate speech or slurs", "This includes slurs of any kind — racial, homophobic, transphobic, ableist, or otherwise."),
        ("3. Keep it clean",           "No NSFW content outside of designated channels."),
        ("4. No threats or doxxing",   "Threatening anyone or sharing personal information without consent is an immediate ban."),
        ("5. No spam or flooding",     "Do not spam messages, emojis, or links."),
        ("6. No advertising",          "Do not advertise other servers without mod approval."),
        ("7. Use the right channels",  "Keep conversations in relevant channels. The vent channel is for people who are struggling."),
        ("8. Listen to moderators",    "Mod decisions are final. If you have a concern, bring it up calmly and privately."),
    ]
    for name, value in rule_list:
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text="Breaking these rules may result in a warning, timeout, kick, or ban.")
    await interaction.response.send_message(embed=embed)
 
 
# ─────────────────────────────────────────────
# INFO COMMANDS
# ─────────────────────────────────────────────
 
@bot.tree.command(name="userinfo", description="Show info about a user.")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    roles  = [r.mention for r in member.roles if r.name != "@everyone"]
    embed  = discord.Embed(title=f"User Info — {member}", color=member.color, timestamp=datetime.datetime.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID",             value=member.id,                                 inline=True)
    embed.add_field(name="Nickname",       value=member.nick or "None",                     inline=True)
    embed.add_field(name="Bot",            value="Yes" if member.bot else "No",             inline=True)
    embed.add_field(name="Account Created",value=member.created_at.strftime("%Y-%m-%d"),    inline=True)
    embed.add_field(name="Joined Server",  value=member.joined_at.strftime("%Y-%m-%d"),     inline=True)
    embed.add_field(name="Warnings",       value=str(len(warn_tracker.get(member.id, []))), inline=True)
    bday = birthday_store.get(member.id)
    embed.add_field(name="Birthday", value=f"{bday['month']}/{bday['day']}" if bday else "Not set", inline=True)
    embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if roles else "None", inline=False)
    await interaction.response.send_message(embed=embed)
 
 
@bot.tree.command(name="serverinfo", description="Show info about this server.")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Server Info — {guild.name}", color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="ID",       value=guild.id,                              inline=True)
    embed.add_field(name="Owner",    value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Members",  value=guild.member_count,                    inline=True)
    embed.add_field(name="Channels", value=len(guild.channels),                   inline=True)
    embed.add_field(name="Roles",    value=len(guild.roles),                      inline=True)
    embed.add_field(name="Created",  value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    await interaction.response.send_message(embed=embed)
 
 
# ─────────────────────────────────────────────
# FUN / ENGAGEMENT COMMANDS
# ─────────────────────────────────────────────
 
@bot.tree.command(name="ask", description="Ask Dei a question directly, anywhere.")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    await asyncio.sleep(random.uniform(0.5, 1.2))
    reply = get_dei_response(question)
    embed = discord.Embed(description=reply, color=discord.Color.blurple())
    embed.set_footer(text=f"Asked by {interaction.user.display_name}")
    await interaction.followup.send(embed=embed)
 
 
@bot.tree.command(name="lore", description="Get a random lore fact about Vaelun and the Cenzha.")
async def lore(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 From the Archives of Vaelun", description=random.choice(LORE_FACTS), color=discord.Color.gold())
    embed.set_footer(text="— Dei Talvyrvei")
    await interaction.response.send_message(embed=embed)
 
 
@bot.tree.command(name="8ball", description="Ask Dei the magic 8ball a question.")
async def eightball(interaction: discord.Interaction, question: str):
    embed = discord.Embed(color=discord.Color.blurple())
    embed.add_field(name="🔮 Question", value=question,                           inline=False)
    embed.add_field(name="Answer",      value=random.choice(EIGHTBALL_RESPONSES), inline=False)
    await interaction.response.send_message(embed=embed)
 
 
@bot.tree.command(name="poll", description="Create a poll. Leave options blank for a yes/no poll.")
async def poll(interaction: discord.Interaction, question: str, option1: str = None, option2: str = None, option3: str = None, option4: str = None):
    options = [o for o in [option1, option2, option3, option4] if o]
    embed   = discord.Embed(title="📊 " + question, color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
    embed.set_footer(text=f"Poll by {interaction.user.display_name}")
    if not options:
        embed.description = "React with ✅ for Yes or ❌ for No."
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
    else:
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        embed.description = "\n".join(f"{number_emojis[i]} {opt}" for i, opt in enumerate(options))
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(options)):
            await msg.add_reaction(number_emojis[i])
 
 
@bot.tree.command(name="birthday", description="Register your birthday so Dei can celebrate you.")
async def birthday(interaction: discord.Interaction, month: int, day: int):
    if not (1 <= month <= 12) or not (1 <= day <= 31):
        await interaction.response.send_message("❌ That does not look like a valid date.", ephemeral=True)
        return
    birthday_store[interaction.user.id] = {"month": month, "day": day}
    await interaction.response.send_message(f"✅ Birthday saved as {month}/{day}. I will remember.", ephemeral=True)
 
 
@bot.tree.command(name="remindme", description="Set a reminder. Dei will DM you when the time is up.")
async def remindme(interaction: discord.Interaction, minutes: int, reminder: str):
    if minutes < 1 or minutes > 10080:
        await interaction.response.send_message("❌ Please choose between 1 and 10080 minutes.", ephemeral=True)
        return
    await interaction.response.send_message(f"✅ I will remind you in {minutes} minute(s).", ephemeral=True)
 
    async def send_reminder():
        await asyncio.sleep(minutes * 60)
        try:
            embed = discord.Embed(title="⏰ Reminder", description=reminder, color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
            embed.set_footer(text=f"You asked me to remind you {minutes} minute(s) ago.")
            await interaction.user.send(embed=embed)
        except Exception:
            pass
 
    asyncio.create_task(send_reminder())
 
 
# ─────────────────────────────────────────────
# LOG SETTINGS
# ─────────────────────────────────────────────
 
# Which log types are enabled (all on by default)
LOG_SETTINGS = {
    "member_join":     True,
    "member_leave":    True,
    "message_delete":  True,
    "message_edit":    True,
    "member_ban":      True,
    "member_unban":    True,
    "nickname_change": True,
    "role_update":     True,
    "channel_create":  True,
    "channel_delete":  True,
    "mod_actions":     True,
    "compromised":     True,
}
 
LOG_LABELS = {
    "member_join":     "👋 Member Join",
    "member_leave":    "🚪 Member Leave",
    "message_delete":  "🗑️ Message Deleted",
    "message_edit":    "✏️ Message Edited",
    "member_ban":      "🔨 Member Banned",
    "member_unban":    "✅ Member Unbanned",
    "nickname_change": "📝 Nickname Changed",
    "role_update":     "🎭 Role Updated",
    "channel_create":  "📁 Channel Created",
    "channel_delete":  "❌ Channel Deleted",
    "mod_actions":     "⚠️ Mod Actions (warn/kick/ban/etc)",
    "compromised":     "🚨 Compromised Account",
}
 
 
class LogSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(LogSettingsSelect())
 
 
class LogSettingsSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=LOG_LABELS[key],
                value=key,
                default=LOG_SETTINGS[key],
                description="Currently " + ("enabled" if LOG_SETTINGS[key] else "disabled"),
            )
            for key in LOG_SETTINGS
        ]
        super().__init__(
            placeholder="Toggle log types on/off...",
            min_values=0,
            max_values=len(options),
            options=options,
        )
 
    async def callback(self, interaction: discord.Interaction):
        # Whatever is selected = enabled, everything else = disabled
        for key in LOG_SETTINGS:
            LOG_SETTINGS[key] = key in self.values
 
        enabled  = [LOG_LABELS[k] for k, v in LOG_SETTINGS.items() if v]
        disabled = [LOG_LABELS[k] for k, v in LOG_SETTINGS.items() if not v]
 
        embed = discord.Embed(
            title="Log Settings Updated",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="✅ Enabled",
            value="\n".join(enabled) if enabled else "None",
            inline=True
        )
        embed.add_field(
            name="❌ Disabled",
            value="\n".join(disabled) if disabled else "None",
            inline=True
        )
        embed.set_footer(text="Select again to change. Reselect all to re-enable everything.")
        await interaction.response.edit_message(embed=embed, view=LogSettingsView())
 
 
@bot.tree.command(name="logsettings", description="Toggle which events get logged in the log channel.")
@app_commands.checks.has_permissions(administrator=True)
async def logsettings(interaction: discord.Interaction):
    enabled  = [LOG_LABELS[k] for k, v in LOG_SETTINGS.items() if v]
    disabled = [LOG_LABELS[k] for k, v in LOG_SETTINGS.items() if not v]
 
    embed = discord.Embed(
        title="⚙️ Log Settings",
        description="Use the menu below to toggle which events Dei logs. Select the ones you want **enabled** and hit confirm.",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="✅ Currently Enabled",
        value="\n".join(enabled) if enabled else "None",
        inline=True
    )
    embed.add_field(
        name="❌ Currently Disabled",
        value="\n".join(disabled) if disabled else "None",
        inline=True
    )
    await interaction.response.send_message(embed=embed, view=LogSettingsView(), ephemeral=True)
 
 
# ─────────────────────────────────────────────
# HELP COMMAND
# ─────────────────────────────────────────────
 
@bot.tree.command(name="help", description="Show all of Dei's available commands.")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⊹ Dei Talvyrvei — Command List",
        description="Here is everything I can do. Commands marked 🔒 require moderator or admin permissions.",
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow()
    )
 
    embed.add_field(name="─── 💬 Conversation ───", value="\u200b", inline=False)
    embed.add_field(name="`/ask` [question]",        value="Ask Dei anything, anywhere.", inline=True)
    embed.add_field(name="`/lore`",                  value="Get a random Vaelun lore fact.", inline=True)
    embed.add_field(name="`/8ball` [question]",      value="Ask Dei the magic 8ball.", inline=True)
 
    embed.add_field(name="─── 🌿 Wellness ───", value="\u200b", inline=False)
    embed.add_field(name="`/grounding`",             value="Dei walks you through a grounding exercise. Great for anxiety or overwhelm.", inline=False)
 
    embed.add_field(name="─── 🎉 Fun ───", value="\u200b", inline=False)
    embed.add_field(name="`/poll` [question]",       value="Create a yes/no or multi-option poll.", inline=True)
    embed.add_field(name="`/birthday` [month] [day]",value="Register your birthday.", inline=True)
    embed.add_field(name="`/remindme` [min] [text]", value="Set a personal DM reminder.", inline=True)
 
    embed.add_field(name="─── ℹ️ Info ───", value="\u200b", inline=False)
    embed.add_field(name="`/userinfo` [@user]",      value="View info about a user.", inline=True)
    embed.add_field(name="`/serverinfo`",            value="View info about this server.", inline=True)
 
    embed.add_field(name="─── 🔒 Moderation ───", value="\u200b", inline=False)
    embed.add_field(name="`/warn` [@user] [reason]",    value="Warn a member.", inline=True)
    embed.add_field(name="`/warnings` [@user]",         value="View a member's warnings.", inline=True)
    embed.add_field(name="`/clearwarnings` [@user]",    value="Clear a member's warnings.", inline=True)
    embed.add_field(name="`/timeout` [@user] [min]",    value="Timeout a member.", inline=True)
    embed.add_field(name="`/kick` [@user] [reason]",    value="Kick a member.", inline=True)
    embed.add_field(name="`/ban` [@user] [reason]",     value="Ban a member.", inline=True)
    embed.add_field(name="`/unban` [user_id]",          value="Unban a user by ID.", inline=True)
    embed.add_field(name="`/clear` [amount]",           value="Bulk delete messages (max 100).", inline=True)
    embed.add_field(name="`/slowmode` [seconds]",       value="Set channel slowmode.", inline=True)
    embed.add_field(name="`/addrole` [@user] [role]",   value="Add a role to a member.", inline=True)
    embed.add_field(name="`/removerole` [@user] [role]",value="Remove a role from a member.", inline=True)
    embed.add_field(name="`/dm` [@user] [message]",     value="DM a member as the bot.", inline=True)
    embed.add_field(name="`/report` [reason]",          value="Anonymously report to mods.", inline=True)
 
    embed.add_field(name="─── 📢 Announcements ───", value="\u200b", inline=False)
    embed.add_field(name="`/embed` [title] [desc]",     value="Post a custom embed.", inline=True)
    embed.add_field(name="`/announce` [title] [msg]",   value="Post a styled announcement.", inline=True)
    embed.add_field(name="`/rules`",                    value="Post the server rules embed.", inline=True)
 
    embed.add_field(name="─── 🎭 Roles ───", value="\u200b", inline=False)
    embed.add_field(name="`/reactionrole` [msg_id] [emoji] [role]", value="Link an emoji to a role on a message.", inline=True)
    embed.add_field(name="`/reactionrolelist`",         value="View all active reaction roles.", inline=True)
 
    embed.add_field(name="─── 🔒 Admin Config ───", value="\u200b", inline=False)
    embed.add_field(name="`/setlog` [#channel]",        value="Set the mod log channel.", inline=True)
    embed.add_field(name="`/setwelcome` [#channel]",    value="Set the welcome channel.", inline=True)
    embed.add_field(name="`/setbirthday` [#channel]",   value="Set the birthday channel.", inline=True)
    embed.add_field(name="`/setvent` [#channel]",       value="Toggle a vent channel.", inline=True)
    embed.add_field(name="`/setactive` [#channel]",     value="Toggle an active channel.", inline=True)
    embed.add_field(name="`/channels`",                 value="View all channel settings.", inline=True)
    embed.add_field(name="`/logsettings`",              value="Toggle which events get logged with a dropdown menu.", inline=True)
 
    embed.set_footer(text="Dei Talvyrvei · Type a message in an active channel to talk to me directly.")
    await interaction.response.send_message(embed=embed, ephemeral=True)
 
 
# ─────────────────────────────────────────────
# GROUNDING COMMAND
# ─────────────────────────────────────────────
 
GROUNDING_EXERCISES = [
    {
        "name": "5-4-3-2-1",
        "description": (
            "This one grounds you in what is real and present. Take your time with each step.\n\n"
            "**5 —** Look around. Name five things you can *see*.\n"
            "**4 —** Notice four things you can *touch*. Feel their texture.\n"
            "**3 —** Listen. Name three things you can *hear*.\n"
            "**2 —** Find two things you can *smell*. Or think of two scents you like.\n"
            "**1 —** Notice one thing you can *taste*.\n\n"
            "*Breathe through each one. You do not have to rush.*"
        ),
    },
    {
        "name": "Box Breathing",
        "description": (
            "Your breath is always with you. This is one of the most reliable ways to slow everything down.\n\n"
            "**Inhale** slowly for 4 counts.\n"
            "**Hold** for 4 counts.\n"
            "**Exhale** slowly for 4 counts.\n"
            "**Hold** for 4 counts.\n\n"
            "Repeat this four times. Or more, if you need it.\n\n"
            "*I have used this myself. It works even when it feels like it will not.*"
        ),
    },
    {
        "name": "Cold Water",
        "description": (
            "Sometimes the body needs something physical to interrupt the spiral.\n\n"
            "If you can, go to a sink and run cold water over your hands or wrists.\n"
            "Feel the temperature. Focus on just that sensation.\n\n"
            "If you cannot do that right now, hold something cold if it is nearby.\n"
            "A cup. A window. Anything.\n\n"
            "*You do not have to think. Just feel the cold. That is enough for right now.*"
        ),
    },
    {
        "name": "Name Your Surroundings",
        "description": (
            "Look around the space you are in right now.\n\n"
            "Pick one object. Say its name, out loud if you can, or in your head.\n"
            "Then pick another. And another.\n\n"
            "Keep going until you feel the noise inside get a little quieter.\n\n"
            "*This room is real. You are in it. That is something solid to stand on.*"
        ),
    },
    {
        "name": "Safe Place Visualization",
        "description": (
            "Close your eyes if you are comfortable doing that.\n\n"
            "Picture a place where you feel safe. It can be real or imagined.\n"
            "Notice the details: what does it look like? What does it smell like?\n"
            "Is it warm or cool? Is it quiet or does it have sounds you love?\n\n"
            "Stay there for a moment. You can visit this place whenever you need to.\n\n"
            "*On Vaelun, I used to go to the edge of the Veil and just watch the light. "
            "Wherever yours is, it belongs to you.*"
        ),
    },
    {
        "name": "Progressive Muscle Relaxation",
        "description": (
            "Your body holds tension without you realizing it. This helps release it.\n\n"
            "Start with your hands — clench them into fists as tight as you can.\n"
            "Hold for five seconds. Then let go completely.\n\n"
            "Move up to your arms. Tense them. Hold. Release.\n"
            "Then your shoulders. Your face. Your stomach. Your legs. Your feet.\n\n"
            "With each release, notice the difference.\n\n"
            "*The body knows how to let go. Sometimes it just needs reminding.*"
        ),
    },
]
 
 
@bot.tree.command(name="grounding", description="Dei walks you through a grounding exercise.")
async def grounding(interaction: discord.Interaction):
    exercise = random.choice(GROUNDING_EXERCISES)
 
    embed = discord.Embed(
        title=f"🌿 Grounding — {exercise['name']}",
        description=exercise["description"],
        color=discord.Color.from_rgb(168, 191, 240),
    )
    embed.set_footer(text="Take your time. There is no rush. You are safe right now.")
    await interaction.response.send_message(embed=embed)
 
 
# ─────────────────────────────────────────────
# ERROR HANDLER
# ─────────────────────────────────────────────
 
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)
 
 
bot.run(DISCORD_TOKEN)
