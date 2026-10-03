from authlib.integrations.flask_client import OAuth
from supabase import create_client
from app.config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
oauth = OAuth()