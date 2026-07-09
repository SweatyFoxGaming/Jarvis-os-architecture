class JarvisQA:
    """Core Q&A patterns for natural conversation"""
    
    RESPONSES = {
        "greeting": [
            "Hello! JARVIS here. What can I do for you today?",
            "Good to see you. How can I assist?",
        ],
        "status": [
            "All systems are running smoothly. Executive architecture is fully active.",
            "I'm operating at peak performance. Ready for whatever you need.",
        ],
        "time": lambda: f"The current time is {datetime.now().strftime('%I:%M %p')}.",
        "thanks": [
            "You're very welcome.",
            "Always happy to help.",
        ],
    }
