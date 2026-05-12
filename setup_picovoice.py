"""
PicoVoice Setup Guide
Helps get free API key for wake word detection
"""

import webbrowser
import os

def main():
    print("🔑 PicoVoice API Key Setup")
    print("=" * 50)
    print()
    print("📋 PicoVoice - bu bepul wake word detection xizmati")
    print("🌐 https://console.picovoice.ai/")
    print()
    print("📝 Qadamlar:")
    print("1. Yuqoridagi linkga o'ting")
    print("2. Hisob yarating (Email + Password)")
    print("3. Yangi project yarating:")
    print("   - Project nomi: GHOST Assistant")
    print("   - Platform: Windows")
    print("4. Access Key nusxa oling")
    print("5. .env fayliga qo'ying")
    print()
    
    # Open browser
    try:
        webbrowser.open("https://console.picovoice.ai/")
        print("🌐 Brauzer ochildi...")
    except:
        print("❌ Brauzer ochib bo'lmadi")
        print("🔗 Qo'lda linkni oching: https://console.picovoice.ai/")
    
    print()
    print("🔑 Key olingach, .env faylini tahrirlang:")
    print("PICOVOICE_ACCESS_KEY=sizning_access_key_ingiz")
    print()
    
    # Check if .env exists
    if os.path.exists('.env'):
        print("✅ .env fayl mavjud")
        with open('.env', 'r') as f:
            content = f.read()
            if 'PICOVOICE_ACCESS_KEY=your_picovoice_access_key_here' in content:
                print("⚠️  Hali ham access key kiritilmagan")
            else:
                print("✅ Access key kiritilgan")
    else:
        print("⚠️  .env fayl mavjud emas")
    
    print()
    print("🚀 Key olingach, qaytadan 'python main_simple.py' ni ishga tushiring!")

if __name__ == "__main__":
    main()
