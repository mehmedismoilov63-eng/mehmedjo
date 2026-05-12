# 👻 GHOST — Windows Voice Assistant

## Texnik Topshiriq (TZ) v1.0

- **Loyiha nomi:** GHOST — Windows Voice Assistant
- **Versiya:** 1.0.0 (Draft)
- **Platforma:** Windows 10 / 11
- **Tillar:** O'zbek tili, Rus tili
- **Foydalanuvchilar:** Bir necha kishi, ovoz bilan farqlash
- **Internet rejimi:** Online + Offline (hybrid)

---

## LOYIHA HAQIDA

GHOST bu Windows da ishlaydigan ovozli shaxsiy yordamchi. Apple Siri kabi ekran pastida chiqadi, lekin API larsiz — faqat Python kutubxonalari bilan ishlaydi. O'zbek va Rus tillarini qo'llab-quvvatlaydi, to'liq offline rejimda ham ishlaydi.

### Muammo
Windows uchun o'zbek tilida, offline ishlaydigan, noutbukni to'liq boshqara oladigan yordamchi yo'q. GHOST shu bo'shliqni to'ldiradi.

### Asosiy xususiyatlar

- Siri uslubida ekran pastida animatsion panel
- O'zbek va Rus tillarida ovoz qabul qilish va javob berish
- Ovoz orqali foydalanuvchilarni farqlash (Voice Profile)
- To'liq offline ishlash
- Noutbukning barcha funksiyalarini boshqarish
- Telegram integratsiyasi
- Ob-havo, tarjimon, matematika, media modullari
- System Tray da fon rejimida ishlash
---

## TEXNIK TALABLAR

### Tizim talablari

- **OS:** Windows 10/11 (64-bit)
- **CPU:** Intel i3 minimum, i5 tavsiya
- **RAM:** 4 GB minimum, 8 GB tavsiya
- **Disk:** 2 GB minimum, 5 GB tavsiya
- **Mikrofon:** har qanday, shovqin filtrli tavsiya
- **Internet:** ixtiyoriy (offline ishlaydi)
- **Python:** 3.11+

### Dasturlash muhiti

- **Asosiy til:** Python 3.11+
- **GUI:** PyQt6
- **Packaging:** PyInstaller (.exe)

### Kutubxonalar

#### STT (Offline)
- `faster-whisper` — asosiy, aniq
- `vosk` — zaxira, engil
- `SpeechRecognition` — mikrofon wrapper
- `pvporcupine` — wake word "Hey Ghost"
- `pyaudio` — mikrofon stream

#### TTS
- `edge-tts` — Microsoft ovozi, online (o'zbek/rus bor)
- `pyttsx3` — offline zaxira
- `pygame` — audio playback

#### NLP
- `rapidfuzz` — noto'g'ri talaffuzda ham tushunadi

#### Tizim boshqaruvi
- `pycaw` — ovoz balandligi
- `screen-brightness-control` — yorqinlik
- `pyautogui` — mouse, keyboard, screenshot
- `psutil` — process monitoring
- `pygetwindow` — oyna boshqaruv
- `winreg` — WiFi, Bluetooth
- `comtypes` — Windows COM

#### Telegram va Web
- `python-telegram-bot`
- `APScheduler` — rejalashtirish
- `googlesearch-python`
- `requests`

#### Qo'shimcha
- `deep-translator` — tarjimon
- `librosa` — ovoz profili
- `scikit-learn` — foydalanuvchi farqlash (ML)
---

## ARXITEKTURA

### Tizim qatlamlari

#### INPUT qatlami
- **Wake Word Engine** — "Hey Ghost" ni aniqlaydi
- **Listener (STT)** — ovozni matnga o'giradi
- **Voice Profiler** — kim gapirganini aniqlaydi

#### CORE qatlami
- **Intent Parser** — buyruqni tushunadi
- **Action Dispatcher** — to'g'ri modulga yo'naltiradi
- **Context Manager** — oldingi 3 buyruqni eslab qoladi

#### OUTPUT qatlami
- **Action Modules** — vazifani bajaradi
- **Response Builder** — javob matni yaratadi
- **Speaker (TTS)** — matni ovozga o'giradi

#### UI qatlami
- **Ghost GUI** — Siri uslubida animatsion panel
- **System Tray** — fon rejimi ikonkasi

### Fayl strukturasi

```
ghost/
├── main.py
├── config.py
├── requirements.txt
├── setup.py
│
├── core/
│   ├── assistant.py
│   ├── wake_word.py
│   ├── listener.py
│   ├── speaker.py
│   ├── intent_parser.py
│   ├── context_manager.py
│   └── voice_profiler.py
│
├── modules/
│   ├── system/
│   │   ├── volume.py
│   │   ├── brightness.py
│   │   ├── wifi.py
│   │   ├── bluetooth.py
│   │   ├── power.py
│   │   ├── screenshot.py
│   │   ├── clipboard.py
│   │   └── processes.py
│   ├── web/
│   │   ├── google_search.py
│   │   ├── youtube.py
│   │   └── browser.py
│   ├── communication/
│   │   ├── telegram_handler.py
│   │   └── scheduler.py
│   ├── productivity/
│   │   ├── notes.py
│   │   ├── reminders.py
│   │   ├── calculator.py
│   │   ├── translator.py
│   │   └── file_manager.py
│   └── media/
│       ├── player.py
│       └── weather.py
│
├── gui/
│   ├── ghost_window.py
│   ├── animations.py
│   └── tray_icon.py
│
├── data/
│   ├── intents_uz.json
│   ├── intents_ru.json
│   ├── voice_profiles/
│   ├── reminders.json
│   └── telegram_contacts.json
│
└── logs/
    └── ghost.log
```
---

## FUNKSIONAL TALABLAR

### 4.1 Wake Word

- **So'z:** "Hey Ghost" yoki "Ghost" (sozlanadi)
- **Har doim fon rejimida tinglab turadi**
- **Reaktsiya vaqti:** 500ms dan kam
- **Kutubxona:** pvporcupine, 100% offline

### 4.2 STT

- **Asosiy:** faster-whisper (offline)
- **Zaxira:** vosk (offline)
- **O'zbek aniqligi:** 85%+
- **Rus aniqligi:** 90%+
- **Timeout:** 5 soniya

### 4.3 TTS

- **Online:** edge-tts (Microsoft, o'zbek va rus ovozi bor)
- **Offline:** pyttsx3
- **Ovoz tezligi va jinsi sozlanadi**

### 4.4 Voice Profiler

- **Texnologiya:** librosa + scikit-learn (MFCC + GMM)
- **Ro'yxatdan o'tish:** 10 soniya ovoz namunasi
- **Aniqlik:** 90%+
- **Maksimum foydalanuvchi:** 10 ta
- **Har bir profilda:** ism, til, Telegram ID, sozlamalar

### 4.5 NLP Parser

- **rapidfuzz orqali noto'g'ri talaffuzni tuzatadi** (80%+ o'xshashlik)
- **Oldingi 3 buyruqni kontekst sifatida saqlaydi**
- **Ko'p qadamli buyruqlar ishlaydi**
- **Noaniq buyruqda aniqlashtiruvchi savol beradi**

### 4.6 Tizim boshqaruvi

#### Ovoz:
- "ovozni oshir / kamayt" — Volume ±10% (pycaw)
- "ovozni o'chir" — Mute toggle (pycaw)

#### Ekran:
- "ekranni yorqin qil / kamayt" — Brightness ±10%
- "ekranni o'chir" — Monitor off

#### Tizim:
- "skrinshot ol" — Desktop ga saqlaydi
- "kompyuterni o'chir" — 30s ogohlantirish bilan
- "uxlat" — Sleep mode
- "qayta yuklat" — Restart
- "WiFi yoq / o'chir" — toggle
- "Bluetooth yoq / o'chir" — toggle

#### Ilovalar:
- "[ilova] och" — ishga tushiradi
- "[ilova] yop" — yopadi
- "nusxa ol / joylash" — clipboard

### 4.7 Fayl tizimi

- "[fayl] ni qidir" — topib yo'lini aytadi
- "[fayl] ni och" — standart dasturda ochadi
- "[fayl] ni [joy] ga ko'chir" — ko'chiradi
- "[fayl] ni o'chir" — tasdiqlash so'rab o'chiradi
- "[papka] papka yarat" — yangi papka
- "so'nggi fayllarni ko'rsat" — oxirgi 5 ta

### 4.8 Telegram

- **Kontaktga xabar yuborish**
- **Guruhga / kanalga yuborish**
- **Rejalashtirilgan bir martalik xabar:** "Ertaga 9:00 da Akbarga yoz: meeting bor"
- **Kunlik takroriy xabar:** "Har kuni 8:00 da guruhga yoz: Xayrli tong"
- **Telegramdan GHOST ni boshqarish**
- "Telegramda yangi xabar bormi" — oxirgi xabarlarni o'qiydi

### 4.9 Qo'shimcha modullar

#### Ob-havo:
- **API:** Open-Meteo (bepul)
- "Bugun havo qanday", "Ertaka yomg'ir bo'ladimi"
- Harorat, namlik, shamol, yog'ingarchilik

#### Tarjimon:
- **deep-translator kutubxonasi**
- O'zbek ↔ Rus ↔ Ingliz
- "[so'z] ni inglizchaga tarjima qil"

#### Matematika:
- **Python eval** (xavfsiz sandbox)
- "Ikki yuz o'ttiz beshni yettiga bo'l"
- Qo'shish, ayirish, ko'paytirish, bo'lish, foiz, daraja

#### Media:
- "Musiqa ijro et / to'xtat / davom et / keyingi / oldingi"
- YouTube brauzerda ochadi

## GUI — INTERFEYS

### Asosiy panel (Siri uslubi)

#### Joylashuv
- Ekran pastida, markazda, taskbar ustida

#### O'lcham
- 600px kenglik, 120px balandlik (kengayadi)

#### Fon
- Qoramtir shaffof, #1A1A2E, 85% opacity

#### Chegara
- Yuqori qirrasi binafsha gradient

#### Animatsiya
- Pastdan silliq chiqish, 300ms ease-in-out
- **Assistent chaqirilganda:** markazda shaffof, yorug'likdan iborat shar shaklidagi element paydo bo'ladi ("GHOST ASSISTANT" yozuvi bilan), tungi shahar neon chiroqlari fonida

#### Mikrofon indikator
- Tinglaganda audio waveform animatsiyasi

#### Kirish matni
- Tanilgan ovoz real-time ko'rinadi

#### Javob matni
- GHOST javobi matn + ovozda

#### Yopilish
- Javobdan keyin 3 soniyada silliq yashirinadi

### System Tray

#### Fon rejimida ishlaganda
- Hech qanday oyna yo'q

#### Ikonka
- Ghost belgi (PNG)

#### O'ng klik
- Sozlamalar, Foydalanuvchi almashtirish, Chiqish

#### Holat
- Yashil (faol), sariq (tinglamoqda), qizil (xato)

### Sozlamalar oynasi

#### Wake word o'zgartirish
- Sozlamalar oynasidan wake word o'zgartirish mumkin

#### Foydalanuvchi qo'shish, o'chirish, ovoz qayta yozish
- Foydalanuvchi qo'shish, o'chirish, ovoz qayta yozish mumkin

#### Telegram token va kontaktlar
- Telegram token va kontaktlar sozlamalari

#### TTS ovoz va tezligi
- TTS ovoz va tezligi sozlamalari

#### Til tanlash
- Til tanlash sozlamalari

#### Windows Startup da avtoyoqish
- Windows Startup da avtoyoqish sozlamalari

---

## XAVFSIZLIK

- **Telegram token:** .env fayl + python-dotenv (config.py ga yozilmaydi)
- **Xavfli buyruqlarda tasdiq so'raladi** (o'chirish, shutdown)
- **Fayl o'chirishda:** "Haqiqatan o'chirasizmi?"
- **Shutdown:** 30 soniya ogohlantirish, "bekor qil" buyrug'i ishlaydi
- **Noma'lum ovozda:** faqat cheklangan buyruqlar
- **Logda shaxsiy ma'lumot saqlanmaydi**
- **Matematika eval:** faqat raqam va operator qabul qiladi

---

## ROADMAP — 8 HAFTA

| Hafta | Vazifa | Natija |
|-------|--------|--------|
| 1-hafta | STT + TTS + Wake Word | ovozni eshitadi, javob beradi |
| 2-hafta | NLP Parser + System Control | tizim buyruqlari ishlaydi |
| 3-hafta | Fayl tizimi + Ilovalar | fayllar va ilovalar boshqariladi |
| 4-hafta | Telegram + Scheduler | xabar va eslatmalar ishlaydi |
| 5-hafta | GUI — Siri uslubida animatsion panel | interfeys tayyor |
| 6-hafta | Voice Profiler | ko'p foydalanuvchi farqlanadi |
| 7-hafta | Ob-havo, tarjimon, matematika, media | barcha modullar tayyor |
| 8-hafta | Test + Optimallashtirish + PyInstaller | barcha testlar o'tgan, .exe tayyor |

---

## BUYRUQLAR RO'YXATI

### Tizim:
- ovozni oshir / kamayt / o'chir
- ekranni yorqin qil / kamayt / o'chir
- skrinshot ol
- kompyuterni o'chir / uxlat / qayta yuklat
- WiFi / Bluetooth yoq / o'chir
- nusxa ol / joylash

### Ilovalar va fayllar:
- [ilova] och / yop
- [fayl] ni qidir / och / ko'chir / o'chir
- [papka] papka yarat
- so'nggi fayllarni ko'rsat

### Telegram:
- [ism] ga [matn] yubor
- [guruh] ga [matn] yoz
- soat [vaqt] da [ism] ga yoz: [matn]
- har kuni soat [vaqt] da yoz: [matn]
- telegramda yangi xabar bormi

### Qo'shimcha:
- bugun havo qanday
- [so'z] ni [til] ga tarjima qil
- [hisob] ni hisobla
- musiqa ijro et / to'xtat / keyingi

---

## KPI MEZONLARI

- **STT aniqligi (o'zbek):** 85%+
- **STT aniqligi (rus):** 90%+
- **Wake word aniqligi:** 95%+
- **Reaktsiya vaqti:** 500ms dan kam
- **Ovoz farqlash aniqligi:** 90%+
- **Tizim buyruq muvaffaqiyati:** 98%+
- **Offline ishlash:** barcha asosiy funksiyalar
- **RAM (fon rejim):** 200 MB dan kam
- **CPU (fon rejim):** 3% dan kam

---

## QABUL QILISH SHARTLARI

Loyiha quyidagi shartlar bajarilganda qabul qilinadi:

- Barcha funksional talablar to'liq ishlaydi
- KPI mezonlari bajarilgan
- Offline rejimda asosiy funksiyalar ishlaydi
- Kamida 2 foydalanuvchi ovozi to'g'ri farqlanadi
- Telegram integratsiyasi 7 funksiyada ishlaydi
- GUI Siri uslubida silliq animatsiya bilan ishlaydi
- requirements.txt va README.md to'liq yozilgan
- Standalone .exe fayl tayyor (PyInstaller)
- Loglash tizimi ishlaydi
- Sozlamalar oynasidan barcha parametrlar o'zgartiriladi

---

## ATAMALAR

- **STT** — Speech-to-Text, ovozni matnga o'girish
- **TTS** — Text-to-Speech, matni ovozga o'girish
- **NLP** — Natural Language Processing, tabiiy tilni qayta ishlash
- **Wake Word** — assistentni faollashtiruvchi kalit so'z
- **Intent** — buyruqning ma'nosi va maqsadi
- **MFCC** — Mel-Frequency Cepstral Coefficients, ovoz tahlili
- **GMM** — Gaussian Mixture Model, ovoz profili ML modeli
- **Fuzzy matching** — noto'liq mos kelishda ham natija topish
- **Thread** — parallel ishlaydigan dastur jarayoni
- **PyInstaller** — Python ni standalone .exe ga aylantiruvchi

---

**GHOST TZ v1.0 — 2025**
