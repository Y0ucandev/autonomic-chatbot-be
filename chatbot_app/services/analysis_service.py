import openai
from chatbot_app.startup import AI_API_KEY

client_ai = openai.AsyncOpenAI(api_key=AI_API_KEY)


async def analyze_sentiment(messages: list[str]) -> int:
    if len(messages) < 3:
        raise ValueError("There must be at least 3 messages to analyze.")

    prompt = (
        "Based on the following user messages, rate the user's mood on a scale from 0 (very negative) "
        "to 10 (very positive). Only respond with a single integer number:\n\n"
        + "\n".join(messages)
        + "\n\nMood score:"
    )

    response = client_ai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that analyzes user sentiment.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=1,
        stop=["\n"],
    )
    response = await response
    return int(response.choices[0].message.content.strip())
