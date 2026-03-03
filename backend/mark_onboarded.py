"""Mark existing brands as onboarding_completed to restore dashboard access."""
from dotenv import load_dotenv
load_dotenv()
from app.database import _get_engine
from sqlalchemy import text

engine = _get_engine()
with engine.connect() as conn:
    result = conn.execute(text(
        "UPDATE brands SET onboarding_completed = TRUE WHERE onboarding_completed IS NULL OR onboarding_completed = FALSE"
    ))
    conn.commit()
    print(f"Updated {result.rowcount} brand(s) - dashboard access restored.")
