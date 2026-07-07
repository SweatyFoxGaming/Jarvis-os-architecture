import pyttsx3
import speech_recognition as sr
import threading

class VoiceInterface:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            # Professional/Calm voice setting
            voices = self.engine.getProperty('voices')
            self.engine.setProperty('voice', voices[0].id)
            self.engine.setProperty('rate', 150)
        except Exception as e:
            print(f"Voice engine initialization failed: {e}")
            self.engine = None

    def speak(self, text):
        if not self.engine: return
        print(f"[Voice] JARVIS: {text}")

        def _speak():
            self.engine.say(text)
            self.engine.runAndWait()

        threading.Thread(target=_speak).start()

    def listen(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("[Voice] Listening...")
            audio = recognizer.listen(source)
            try:
                text = recognizer.recognize_google(audio)
                print(f"[Voice] You: {text}")
                return text
            except:
                return None

if __name__ == "__main__":
    vi = VoiceInterface()
    vi.speak("Voice interface initialized.")
