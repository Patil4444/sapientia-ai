from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
import os

load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
if not api_key:
    raise SystemExit("Set ANTHROPIC_API_KEY in .env or environment")

llm = ChatAnthropic(model="claude-sonnet-4-6", api_key=api_key)
response = llm.invoke([HumanMessage(content="Say: Claude is connected.")])
print(response.content)
