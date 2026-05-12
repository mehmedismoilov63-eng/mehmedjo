"""
Intent Parser - keyword-based matching
Rus va o'zbek tilida ishonchli ishlaydi.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from rapidfuzz import fuzz

from config import Config

logger = logging.getLogger(__name__)

INTENTS = {

    # ══════════════════════════════════════════════════════
    # OVOZ
    # ══════════════════════════════════════════════════════
    "system.volume_up": {
        "keywords": [
            "ovozni oshir", "ovoz oshir", "balandroq", "ovoz baland", "baland qil",
            "громче", "увеличь громкость", "сделай громче", "прибавь громкость", "погромче",
        ],
        "params": {"amount": 10},
    },
    "system.volume_down": {
        "keywords": [
            "ovozni kamaytir", "ovoz kamaytir", "pastroq", "past qil",
            "тише", "уменьши громкость", "сделай тише", "убавь громкость", "потише",
        ],
        "params": {"amount": 10},
    },
    "system.volume_mute": {
        "keywords": [
            "ovozni o'chir", "jim qil", "mute",
            "выключи звук", "без звука", "заглуши", "отключи звук",
        ],
        "params": {},
    },
    "system.volume_set": {
        "keywords": [
            "ovozni qil", "ovoz darajasi",
            "громкость поставь", "установи громкость", "громкость на",
        ],
        "params": {"level": 50},
    },

    # ══════════════════════════════════════════════════════
    # YORQINLIK
    # ══════════════════════════════════════════════════════
    "system.brightness_up": {
        "keywords": [
            "yorqinroq", "yorqinlikni oshir", "ekran yorqin",
            "ярче", "увеличь яркость", "сделай ярче", "яркость вверх",
        ],
        "params": {"amount": 10},
    },
    "system.brightness_down": {
        "keywords": [
            "qorong'iroq", "yorqinlikni kamaytir",
            "темнее", "уменьши яркость", "сделай темнее", "яркость вниз",
        ],
        "params": {"amount": 10},
    },

    # ══════════════════════════════════════════════════════
    # QUVVAT
    # ══════════════════════════════════════════════════════
    "system.shutdown": {
        "keywords": [
            "kompyuterni o'chir", "o'chirish", "shutdown",
            "выключи компьютер", "выключить", "завершить работу",
        ],
        "params": {},
    },
    "system.sleep": {
        "keywords": [
            "uxlat", "uyqu rejimi", "sleep",
            "спящий режим", "усыпи", "в сон", "режим сна",
        ],
        "params": {},
    },
    "system.restart": {
        "keywords": [
            "qayta yukla", "qayta ishga tushir", "restart", "reboot",
            "перезагрузи", "перезапусти", "перезагрузка",
        ],
        "params": {},
    },
    "system.lock": {
        "keywords": [
            "qulf", "ekranni qulflash", "lock",
            "заблокируй", "заблокировать экран", "блокировка",
        ],
        "params": {},
    },
    "system.unlock": {
        "keywords": [
            "qulfni och", "ekranni och", "unlock",
            "разблокируй", "разблокировать экран", "открой экран",
        ],
        "params": {"pin": None},
    },
    "system.set_pin": {
        "keywords": [
            "pin saqlash", "unlock pin qo'yish",
            "сохрани пин", "установи пин для разблокировки",
        ],
        "params": {"pin": None},
        "text_extract": True,
    },
    "system.cancel_shutdown": {
        "keywords": [
            "bekor qil", "o'chirishni bekor qil",
            "отмени выключение", "отменить выключение", "отмена",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # SKRINSHOT
    # ══════════════════════════════════════════════════════
    "system.screenshot": {
        "keywords": [
            "skrinshot", "ekran rasm", "rasmga ol", "screenshot",
            "скриншот", "снимок экрана", "сделай скриншот",
        ],
        "params": {},
    },
    "system.screenshot_window": {
        "keywords": [
            "oyna skrinshot", "faol oyna rasmi", "aktiv oyna",
            "скриншот окна", "снимок активного окна", "скриншот активного",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # ILOVALAR
    # ══════════════════════════════════════════════════════
    "app.open": {
        "keywords": [
            "och", "ishga tushir", "yoq",
            "открой", "открыть", "запусти", "запустить", "включи",
        ],
        "app_extract": True,
        "params": {"app_name": None},
    },
    "app.close": {
        "keywords": [
            "yop", "yopib qo'y", "tugat",
            "закрой", "закрыть", "завершить", "выключи",
        ],
        "app_extract": True,
        "params": {"app_name": None},
    },
    "app.switch": {
        "keywords": [
            "o'tish", "almashtir",
            "переключись на", "перейди в", "открой окно",
        ],
        "app_extract": True,
        "params": {"app_name": None},
    },
    "app.running_list": {
        "keywords": [
            "qaysi ilovalar ishlayapti", "ochiq ilovalar",
            "какие программы запущены", "список запущенных", "что открыто",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # VAQT VA SANA
    # ══════════════════════════════════════════════════════
    "system.time": {
        "keywords": [
            "soat necha", "vaqt", "hozir soat",
            "который час", "сколько времени", "время",
        ],
        "params": {},
    },
    "system.date": {
        "keywords": [
            "bugun qaysi kun", "sana", "bugun necha",
            "какой сегодня день", "какое число", "дата", "сегодня",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # TIZIM MA'LUMOTI
    # ══════════════════════════════════════════════════════
    "system.battery": {
        "keywords": [
            "batareya", "zaryad",
            "батарея", "заряд", "сколько заряда",
        ],
        "params": {},
    },
    "system.info": {
        "keywords": [
            "tizim", "kompyuter haqida", "system info",
            "информация о системе", "характеристики", "процессор", "оперативная",
        ],
        "params": {},
    },
    "system.disk": {
        "keywords": [
            "disk", "xotira", "bo'sh joy",
            "диск", "место на диске", "свободное место", "память",
        ],
        "params": {},
    },
    "system.network": {
        "keywords": [
            "internet", "tarmoq", "wifi", "ip manzil",
            "сеть", "интернет", "вай-фай", "ip адрес", "скорость интернета",
        ],
        "params": {},
    },
    "system.processes": {
        "keywords": [
            "jarayonlar", "ko'p xotira ishlatayotgan",
            "процессы", "что грузит", "нагрузка", "топ процессов",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # MEDIA
    # ══════════════════════════════════════════════════════
    "media.play_pause": {
        "keywords": [
            "play", "pause", "to'xtat", "davom ettir",
            "плей", "пауза", "воспроизвести", "остановить",
        ],
        "params": {},
    },
    "media.next": {
        "keywords": [
            "keyingi", "next", "keyingi qo'shiq",
            "следующий", "следующий трек", "дальше",
        ],
        "params": {},
    },
    "media.prev": {
        "keywords": [
            "oldingi", "previous", "oldingi qo'shiq",
            "предыдущий", "предыдущий трек", "назад",
        ],
        "params": {},
    },
    # ══════════════════════════════════════════════════════
    # OYNA BOSHQARUVI
    # ══════════════════════════════════════════════════════
    "window.minimize": {
        "keywords": [
            "kichraytir", "minimize",
            "свернуть", "сверни",
        ],
        "params": {},
    },
    "window.maximize": {
        "keywords": [
            "kattalashtir", "maximize",
            "развернуть", "разверни",
        ],
        "params": {},
    },
    "window.close": {
        "keywords": [
            "oynani yop", "close window",
            "закрой окно", "закрыть окно",
        ],
        "params": {},
    },
    "window.switch": {
        "keywords": [
            "oynalar orasida", "alt tab",
            "переключить окна", "alt tab",
        ],
        "params": {},
    },
    "window.desktop": {
        "keywords": [
            "ish stoliga", "desktop ko'rsat",
            "рабочий стол", "показать рабочий стол", "свернуть все",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # CLIPBOARD
    # ══════════════════════════════════════════════════════
    "clipboard.copy": {
        "keywords": [
            "nusxala", "copy", "ctrl c",
            "скопируй", "копировать", "ctrl c",
        ],
        "params": {},
    },
    "clipboard.paste": {
        "keywords": [
            "joylashtir", "paste", "ctrl v",
            "вставь", "вставить", "ctrl v",
        ],
        "params": {},
    },
    "clipboard.select_all": {
        "keywords": [
            "hammasini tanlash", "select all",
            "выдели всё", "выбрать всё", "ctrl a",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # INTERNET VA BRAUZER
    # ══════════════════════════════════════════════════════
    "browser.search": {
        "keywords": [
            "qidir", "izla", "search",
            "найди", "поищи", "загугли", "гугл", "google",
        ],
        "params": {"query": None},
    },
    "browser.open_url": {
        "keywords": [
            "saytga o't", "ochib ber",
            "открой сайт", "перейди на", "зайди на",
        ],
        "params": {"url": None},
    },
    "youtube.play": {
        "keywords": [
            "youtube", "ютуб", "qo'shiq qo'y", "musiqa qo'y",
            "включи на ютубе", "найди на ютубе", "поставь песню", "включи музыку",
        ],
        "params": {"query": None},
    },

    # ══════════════════════════════════════════════════════
    # OB-HAVO
    # ══════════════════════════════════════════════════════
    "weather.get": {
        "keywords": [
            "havo", "ob-havo", "harorat", "weather",
            "погода", "температура", "какая погода", "прогноз",
        ],
        "params": {"location": "Tashkent"},
    },

    # ══════════════════════════════════════════════════════
    # HISOBLASH
    # ══════════════════════════════════════════════════════
    "calculator.calculate": {
        "keywords": [
            "hisobla", "calculate",
            "посчитай", "вычисли", "сколько будет",
        ],
        "params": {"expression": None},
    },

    # ══════════════════════════════════════════════════════
    # TARJIMA
    # ══════════════════════════════════════════════════════
    "translator.translate": {
        "keywords": [
            "tarjima", "translate",
            "переведи", "перевести",
        ],
        "params": {"text": None, "target_lang": None},
    },

    # ══════════════════════════════════════════════════════
    # FAYL BOSHQARUVI
    # ══════════════════════════════════════════════════════
    "files.open_downloads": {
        "keywords": [
            "yuklamalar", "downloads",
            "загрузки", "открой загрузки", "папка загрузок",
        ],
        "params": {},
    },
    "files.open_documents": {
        "keywords": [
            "hujjatlar", "documents",
            "документы", "открой документы", "папка документов",
        ],
        "params": {},
    },
    "files.open_desktop": {
        "keywords": [
            "ish stoli papkasi", "desktop papka",
            "открой рабочий стол", "папка рабочего стола",
        ],
        "params": {},
    },
    "files.open_path": {
        "keywords": [
            "papkani och", "faylni och",
            "открой папку", "открой файл", "проводник",
        ],
        "params": {"path": None},
    },

    # ══════════════════════════════════════════════════════
    # ESLATMA VA TAYMER
    # ══════════════════════════════════════════════════════
    "timer.set": {
        "keywords": [
            "taymer", "timer", "vaqt belgilash",
            "таймер", "поставь таймер", "через минут", "через секунд",
        ],
        "params": {"seconds": 60},
    },
    "reminder.set": {
        "keywords": [
            "eslatma", "eslatib qo'y",
            "напомни", "напоминание", "поставь напоминание",
        ],
        "params": {"text": None},
    },

    # ══════════════════════════════════════════════════════
    # KLAVIATURA YORLIQLARI
    # ══════════════════════════════════════════════════════
    "keyboard.undo": {
        "keywords": [
            "bekor qil", "undo", "ctrl z",
            "отмени", "отменить", "ctrl z",
        ],
        "params": {},
    },
    "keyboard.redo": {
        "keywords": [
            "qaytarish", "redo", "ctrl y",
            "повтори", "повторить", "ctrl y",
        ],
        "params": {},
    },
    "keyboard.save": {
        "keywords": [
            "saqlash", "save", "ctrl s",
            "сохрани", "сохранить", "ctrl s",
        ],
        "params": {},
    },
    "keyboard.new_tab": {
        "keywords": [
            "yangi tab", "new tab",
            "новая вкладка", "открой вкладку", "ctrl t",
        ],
        "params": {},
    },
    "keyboard.close_tab": {
        "keywords": [
            "tabni yop", "close tab",
            "закрой вкладку", "ctrl w",
        ],
        "params": {},
    },
    "keyboard.refresh": {
        "keywords": [
            "yangilash", "refresh", "reload",
            "обнови", "обновить страницу", "f5",
        ],
        "params": {},
    },
    "keyboard.fullscreen": {
        "keywords": [
            "to'liq ekran", "fullscreen",
            "полный экран", "f11",
        ],
        "params": {},
    },
    "keyboard.zoom_in": {
        "keywords": [
            "kattalashtir", "zoom in",
            "увеличь масштаб", "приблизь", "ctrl plus",
        ],
        "params": {},
    },
    "keyboard.zoom_out": {
        "keywords": [
            "kichraytir masshtab", "zoom out",
            "уменьши масштаб", "отдали", "ctrl minus",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # MOUSE BOSHQARUVI
    # ══════════════════════════════════════════════════════
    "mouse.scroll_up": {
        "keywords": [
            "yuqoriga aylantir", "scroll up",
            "прокрути вверх", "листай вверх", "скролл вверх",
        ],
        "params": {"amount": 3},
    },
    "mouse.scroll_down": {
        "keywords": [
            "pastga aylantir", "scroll down",
            "прокрути вниз", "листай вниз", "скролл вниз",
        ],
        "params": {"amount": 3},
    },
    "mouse.click": {
        "keywords": [
            "bosish", "click",
            "кликни", "нажми", "щёлкни",
        ],
        "params": {},
    },
    "mouse.double_click": {
        "keywords": [
            "ikki marta bosish", "double click",
            "двойной клик", "дважды нажми",
        ],
        "params": {},
    },
    "mouse.right_click": {
        "keywords": [
            "o'ng tugma", "right click",
            "правая кнопка", "правый клик", "контекстное меню",
        ],
        "params": {},
    },
    "mouse.center": {
        "keywords": [
            "sichqonchani markazga", "mouse center",
            "мышь в центр", "курсор в центр",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # MATN KIRITISH
    # ══════════════════════════════════════════════════════
    "keyboard.type": {
        "keywords": [
            "yoz", "type", "kiritish",
            "напиши", "введи", "напечатай",
        ],
        "params": {"text": None},
        "text_extract": True,
    },
    "keyboard.enter": {
        "keywords": [
            "enter bosish", "enter tugmasi",
            "нажми клавишу enter", "клавиша enter", "нажать enter",
        ],
        "params": {},
    },
    "keyboard.escape": {
        "keywords": [
            "escape bosish", "esc tugmasi",
            "нажми клавишу escape", "клавиша escape", "нажать escape",
        ],
        "params": {},
    },
    "keyboard.delete": {
        "keywords": [
            "o'chirish", "delete",
            "удали", "удалить", "нажми delete",
        ],
        "params": {},
    },
    "keyboard.print_screen": {
        "keywords": [
            "print screen", "prtsc",
            "принтскрин", "нажми print screen",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # TIZIM TOZALASH VA OPTIMALLASHTIRISH
    # ══════════════════════════════════════════════════════
    "system.empty_trash": {
        "keywords": [
            "savatchani tozala", "trash tozala",
            "очисти корзину", "очистить корзину", "удали из корзины",
        ],
        "params": {},
    },
    "system.kill_process": {
        "keywords": [
            "jarayonni o'chir", "kill process",
            "убей процесс", "завершить процесс", "принудительно закрыть",
        ],
        "params": {"process_name": None},
        "text_extract": True,
    },
    "system.clear_clipboard": {
        "keywords": [
            "clipboard tozala", "bufer tozala",
            "очисти буфер обмена", "очистить буфер",
        ],
        "params": {},
    },
    "system.uptime": {
        "keywords": [
            "kompyuter qancha vaqt ishlayapti", "uptime",
            "сколько работает компьютер", "время работы", "аптайм",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # MAXSUS SAYTLAR
    # ══════════════════════════════════════════════════════
    "web.open_github": {
        "keywords": [
            "github", "гитхаб",
        ],
        "params": {},
    },
    "web.open_gmail": {
        "keywords": [
            "gmail", "почта", "электронная почта", "email",
        ],
        "params": {},
    },
    "web.open_maps": {
        "keywords": [
            "xarita", "maps", "google maps",
            "карты", "гугл карты", "открой карту",
        ],
        "params": {},
    },
    "web.open_translate": {
        "keywords": [
            "google tarjima", "google translate",
            "гугл переводчик", "открой переводчик",
        ],
        "params": {},
    },
    "web.open_news": {
        "keywords": [
            "yangiliklar", "news",
            "новости", "открой новости",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # TELEGRAM ORQALI MAXSUS
    # ══════════════════════════════════════════════════════
    "telegram.send_screenshot": {
        "keywords": [
            "telegramga skrinshot yuborish", "skrinshot yuborish",
            "отправь скриншот в телеграм", "скриншот в телеграм",
        ],
        "params": {},
    },
    "telegram.send_sysinfo": {
        "keywords": [
            "telegramga tizim ma'lumoti", "tizim yuborish",
            "отправь инфо в телеграм", "системная информация в телеграм",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # OVOZLI YOZUV
    # ══════════════════════════════════════════════════════
    "voice.repeat": {
        "keywords": [
            "qayta ayt", "takrorla", "oxirgini takrorla",
            "повтори последнее", "скажи ещё раз", "повтори снова",
        ],
        "params": {},
    },
    "voice.stop": {
        "keywords": [
            "gapirma", "jim bo'l", "to'xta",
            "замолчи", "стоп", "хватит говорить",
        ],
        "params": {},
    },

    # ══════════════════════════════════════════════════════
    # YANGI PROFESSIONAL FUNKSIYALAR
    # ══════════════════════════════════════════════════════

    # Clipboard
    "clipboard.read": {
        "keywords": [
            "clipboard ni o'qi", "nusxalangan nima",
            "что в буфере", "прочитай буфер", "что скопировано",
        ],
        "params": {},
    },

    # Internet tezligi
    "network.speed_test": {
        "keywords": [
            "internet tezligi", "speed test",
            "скорость интернета", "проверь скорость", "спидтест",
        ],
        "params": {},
    },
    "network.check": {
        "keywords": [
            "internet bormi", "internet tekshir",
            "есть ли интернет", "проверь интернет", "пинг",
        ],
        "params": {},
    },

    # Parol generatori
    "security.gen_password": {
        "keywords": [
            "parol yaratish", "yangi parol",
            "сгенерируй пароль", "создай пароль", "новый пароль",
        ],
        "params": {"length": 16},
    },

    # Bildirishnoma
    "system.notify": {
        "keywords": [
            "bildirishnoma", "xabar ko'rsat",
            "покажи уведомление", "отправь уведомление", "напомни сейчас",
        ],
        "params": {"text": None},
        "text_extract": True,
    },

    # Diktofon
    "recorder.start": {
        "keywords": [
            "yozishni boshlash", "diktofon yoq",
            "начни запись", "включи диктофон", "запись голоса",
        ],
        "params": {"seconds": 30},
    },
    "recorder.stop": {
        "keywords": [
            "yozishni to'xtatish", "diktofon o'chir",
            "останови запись", "выключи диктофон", "стоп запись",
        ],
        "params": {},
    },

    # Rejimlar
    "mode.work": {
        "keywords": [
            "ish rejimi", "ishga tayyorla",
            "рабочий режим", "режим работы", "включи рабочий режим",
        ],
        "params": {},
    },
    "mode.rest": {
        "keywords": [
            "dam olish rejimi", "tungi rejim",
            "режим отдыха", "ночной режим", "включи ночной режим",
        ],
        "params": {},
    },
    "mode.presentation": {
        "keywords": [
            "prezentatsiya rejimi",
            "режим презентации", "включи презентацию",
        ],
        "params": {},
    },

    # Fayl qidirish
    "files.search": {
        "keywords": [
            "fayl qidir", "fayl topish",
            "найди файл", "поищи файл", "где файл",
        ],
        "params": {"query": None},
        "text_extract": True,
    },

    # Tizim hisoboti
    "system.full_report": {
        "keywords": [
            "to'liq hisobot", "tizim hisoboti",
            "полный отчёт", "системный отчёт", "полная информация о системе",
        ],
        "params": {},
    },

    # Ekran yozuvi
    "screen.record": {
        "keywords": [
            "ekranni yozish", "screen record",
            "запись экрана", "записать экран", "скринкаст",
        ],
        "params": {"seconds": 30},
    },

    # Aqlli hisoblash
    "calculator.smart": {
        "keywords": [
            "foiz hisobla", "foizini hisoblash",
            "посчитай процент", "сколько процентов", "вычисли процент",
        ],
        "params": {"expression": None},
        "text_extract": True,
    },
}

# ── Ilova nomlari ──────────────────────────────────────────────────────────
APP_NAMES: Dict[str, str] = {
    "chrome": "chrome", "хром": "chrome", "google chrome": "chrome",
    "firefox": "firefox", "фаерфокс": "firefox",
    "edge": "edge", "эдж": "edge",
    "opera": "opera", "опера": "opera",
    "yandex": "yandex", "яндекс": "yandex",
    "telegram": "telegram", "телеграм": "telegram", "телеграмм": "telegram",
    "whatsapp": "whatsapp", "ватсап": "whatsapp",
    "discord": "discord", "дискорд": "discord",
    "skype": "skype", "скайп": "skype",
    "zoom": "zoom", "зум": "zoom",
    "spotify": "spotify", "спотифай": "spotify",
    "vlc": "vlc",
    "word": "word", "ворд": "word",
    "excel": "excel", "эксель": "excel",
    "powerpoint": "powerpoint",
    "notepad": "notepad", "блокнот": "notepad",
    "calculator": "calculator", "калькулятор": "calculator",
    "paint": "paint", "пейнт": "paint",
    "explorer": "explorer", "проводник": "explorer",
    "task manager": "task manager", "диспетчер задач": "task manager",
    "cmd": "cmd", "командная строка": "cmd",
    "powershell": "powershell",
    "vs code": "vs code", "visual studio code": "vs code",
    "youtube": "youtube", "ютуб": "youtube",
    "steam": "steam", "стим": "steam",
    "obs": "obs", "obs studio": "obs",
    "photoshop": "photoshop", "фотошоп": "photoshop",
    "figma": "figma",
    "postman": "postman",
    "pycharm": "pycharm",
}

OPEN_TRIGGERS = {
    "och", "ishga tushir", "yoq", "ni och",
    "оч", "ишга тушир",
    "открой", "открыть", "запусти", "запустить", "включи", "включить",
}
CLOSE_TRIGGERS = {
    "yop", "yopib qo'y", "tugat", "ni yop",
    "ёп", "тугат",
    "закрой", "закрыть", "завершить", "выключи", "выключить",
}


class IntentParser:
    def __init__(self, config: Config):
        self.config = config

    def parse(self, text: str, language: str = None) -> Optional[Dict[str, Any]]:
        text_clean = re.sub(r"[.,!?;:\"']", "", text.lower().strip())

        best_intent = None
        best_score = 0
        best_params = {}

        for intent_name, intent_data in INTENTS.items():
            score, params = self._match(text_clean, intent_name, intent_data)
            if score > best_score:
                best_score = score
                best_intent = intent_name
                best_params = params

        if best_score >= 50:
            logger.info(f"Intent: {best_intent} (score={best_score:.0f}) | '{text}'")
            return {
                "intent": best_intent,
                "action": best_intent,
                "confidence": best_score / 100.0,
                "parameters": best_params,
            }

        logger.warning(f"Intent topilmadi: '{text}' (max={best_score:.0f})")
        return None

    def _match(self, text: str, intent_name: str, intent_data: dict) -> tuple:
        keywords: List[str] = intent_data["keywords"]
        params = dict(intent_data.get("params", {}))
        best = 0

        for kw in keywords:
            if kw in text:
                best = max(best, 95)
                break
            r = fuzz.partial_ratio(kw, text)
            t = fuzz.token_set_ratio(kw, text)
            best = max(best, r, t)

        if best >= 50 and intent_data.get("app_extract"):
            app = self._extract_app(text, intent_name)
            if app:
                params["app_name"] = app
            else:
                best = 0

        if best >= 50 and intent_name == "calculator.calculate":
            params["expression"] = self._extract_expr(text)

        if best >= 50 and intent_name in ("browser.search", "youtube.play"):
            params["query"] = self._extract_query(text)

        if best >= 50 and intent_name == "timer.set":
            params["seconds"] = self._extract_seconds(text)

        if best >= 50 and intent_data.get("text_extract"):
            params["text"] = self._extract_tail(text, intent_data["keywords"])

        return best, params

    def _extract_tail(self, text: str, keywords: list) -> str:
        cleaned = text
        for kw in sorted(keywords, key=len, reverse=True):
            cleaned = cleaned.replace(kw, "").strip()
        return cleaned.strip()

    def _extract_app(self, text: str, intent_name: str) -> Optional[str]:
        triggers = OPEN_TRIGGERS if intent_name in ("app.open", "app.switch") else CLOSE_TRIGGERS
        cleaned = text
        for t in sorted(triggers, key=len, reverse=True):
            cleaned = cleaned.replace(t, " ")
        cleaned = cleaned.strip()

        for alias, name in APP_NAMES.items():
            if alias in cleaned or alias in text:
                return name

        best_alias, best_score = None, 0
        for alias in APP_NAMES:
            s = fuzz.partial_ratio(alias, cleaned)
            if s > best_score and s >= 70:
                best_score, best_alias = s, alias
        if best_alias:
            return APP_NAMES[best_alias]

        words = [w for w in cleaned.split() if len(w) > 2]
        return words[0] if words else None

    def _extract_expr(self, text: str) -> Optional[str]:
        m = re.search(r"[\d\s\+\-\*\/\(\)\.]+", text)
        return m.group().strip() if m else None

    def _extract_query(self, text: str) -> str:
        for kw in ["qidir", "изла", "найди", "поищи", "загугли", "гугл",
                   "search", "youtube", "ютуб", "qo'shiq qo'y", "включи музыку"]:
            text = text.replace(kw, "").strip()
        return text.strip()

    def _extract_seconds(self, text: str) -> int:
        m = re.search(r"(\d+)\s*(минут|секунд|дақиқа|soniya|minut)", text)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if "минут" in unit or "minut" in unit or "дақиқа" in unit:
                return n * 60
            return n
        m = re.search(r"\d+", text)
        return int(m.group()) * 60 if m else 60
