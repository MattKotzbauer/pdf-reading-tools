"""
Generates answers considering PDF (argv[1]) for each prompt listed in prompts file (argv[2])

Usage: 
python pdfInterrogator.py <pdf_name> <prompts_file_name>
"""

from openai import OpenAI
import time
import sys

if len(sys.argv) != 3: 
    print("Usage: python pdfInterrogator.py <pdf_filename> <prompts_filename>")
    sys.exit(1)

client = OpenAI()

# init assistant
assistant = client.beta.assistants.create(
  name="pdf reader",
  # instructions="Use the uploaded file to provide answer. Do not answer if you couldn't find any context in the knowledge base, just say I don't know",
  instructions="Use the uploaded file to provide answer. If you can't find a text match within excerpts, use the location specified in parentheses after them. If asked to put something in the form of a Beamer presentation, use the \\begin{frame} and \\end{frame} commands to begin and end slides, and the \\frametitle{} command to title the slide",
  tools=[{"type": "code_interpreter"}], 
  model="gpt-4-turbo",
)

pdf_filename = sys.argv[1]
    # e.g. "love.pdf"
prompts_filename = sys.argv[2]
    # e.g. "text_prompts.txt"

# upload pdf
with open(pdf_filename, "rb") as f:
    file = client.files.create(file=f, purpose='assistants')

# create thread (thing the assistant lives on)
thread = client.beta.threads.create()

def read_prompts(filename):
    with open(filename, "r") as file:
        content = file.read().strip()
    return content.split("\n\n")

prompts = read_prompts(prompts_filename) 

answers = [[] for _ in prompts]

def answer_prompt(i, prompt):
    # query thread with message
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt,
        file_ids=[file.id]
    )

    # create run (activation of thread)
    run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
    )

    # poll for completion
    while True:
        updated_run = client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread.id)
        if updated_run.status == 'completed':
            break
        elif updated_run.status in ['failed', 'cancelled']:
            print("Run could not be completed:", updated_run.status)
            exit()
        time.sleep(1)  # sleep before next status check

    # print message
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    for msg in messages.data:
        for content in msg.content:
            if hasattr(content, 'text'):
                answers[i].append(content.text.value)
                break

for i, prompt in enumerate(prompts):
    answer_prompt(i, prompt)

filtered_answers = [ans[0] for ans in answers]

with open("text_answers.txt", "w") as file:
    file.write("\n------------\n".join(filtered_answers))

# print(filtered_answers)

