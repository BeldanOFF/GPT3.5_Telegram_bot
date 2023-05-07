import openai

openai.api_key = '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'

def update(message, role, content):
    message.append({"role":role, "content":content})
    return message

def get_response(messages):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        massages=messages
    )
    return response['choices'][0]

messages=[
    {"role": "user", "content": "Привет GPT, меня зовут Данила."},
    {"role": "assistant", "content": "Привет, Данила, чем я могу помочь?"},
]

while True:
    print(messages)
    user_input = input()
    get_response(user_input)
    print(get_response())