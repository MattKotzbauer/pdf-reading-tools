
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
  tools=[{"type": "file_search"}], 
  model="gpt-4-turbo",
)

pdf_filename = sys.argv[1]
    # e.g. "love.pdf"
prompts_filename = sys.argv[2]
    # e.g. "text_prompts.txt"

vector_store = client.beta.vector_stores.create(name="Biomedical PDF")

# upload pdf
file_paths = ["./" + pdf_filename]
file_streams = [open(path, "rb") for path in file_paths]

file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
  vector_store_id=vector_store.id, files=file_streams
)

# print(file_batch.status)
# print(file_batch.file_counts)

assistant = client.beta.assistants.update(
  assistant_id=assistant.id,
  tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)

message_file = client.files.create(
  file = open("./" + pdf_filename, "rb"), purpose = "assistants"
)

thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": "Summarize the content of the biomedical PDF",
      "attachments": [
        { "file_id": message_file.id, "tools": [{"type": "file_search"}] }
      ],
    }
  ]
)

print(thread.tool_resources.file_search)
 
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id, assistant_id=assistant.id
)

time.sleep(10)

messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
print(messages)


message_content = messages[0].content[0].text
annotations = message_content.annotations
citations = []
for index, annotation in enumerate(annotations):
    message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
    if file_citation := getattr(annotation, "file_citation", None):
        cited_file = client.files.retrieve(file_citation.file_id)
        citations.append(f"[{index}] {cited_file.filename}")

print(message_content.value)
print("\n".join(citations))
