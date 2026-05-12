from config import Config
from core.intent_parser import IntentParser
c = Config()
p = IntentParser(c)
tests = [
    ("включи на ютубе Imagine Dragons", "youtube.play"),
    ("поставь песню Coldplay", "youtube.play"),
    ("какая погода", "weather.get"),
    ("открой ютуб", "browser.open_url"),
    ("открой гугл", "browser.open_url"),
    ("зайди на github.com", "browser.open_url"),
    ("загугли рецепт плова", "browser.search"),
    ("открой телеграм", "app.open"),
    ("громче", "system.volume_up"),
    ("который час", "system.time"),
    ("какое сегодня число", "system.date"),
    ("заряд батареи", "system.battery"),
    ("следующий трек", "media.next"),
    ("свернуть", "window.minimize"),
    ("скриншот", "system.screenshot"),
]
ok = 0
for text, expected in tests:
    r = p.parse(text)
    got = r["action"] if r else "None"
    status = "OK  " if got == expected else "FAIL"
    if got == expected: ok += 1
    print(f"{status} [{text}] -> {got}")
print(f"\n{ok}/{len(tests)} passed")
