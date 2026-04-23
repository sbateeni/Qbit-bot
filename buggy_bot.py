# BUGGY BOT TEST SCRIPT
import time

def start_engine():
    print("Initializing Market Engine...")
    time.sleep(2)
    print("Error: Accessing undefined data source...")
    # المتعمد هنا هو استدعاء متغير غير موجود ليتوقف البوت
    result = undefined_variable_for_testing + 100
    print("Result:", result)

if __name__ == "__main__":
    start_engine()
