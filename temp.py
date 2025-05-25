from dotenv import load_dotenv
load_dotenv()

# 🔍 DEBUG: Check how private key is stored in .env
with open(".env") as f:
    for line in f:
        if "FIREBASE_PRIVATE_KEY" in line:
            print(">>> FROM FILE:", repr(line))

# continue with firebase_config = { ... } here
