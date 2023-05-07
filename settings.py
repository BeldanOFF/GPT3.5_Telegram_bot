import os
import dotenv

dotenv.load_dotenv('.env')
BOT_API_KEY = os.environ['BOT_API_KEY']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']