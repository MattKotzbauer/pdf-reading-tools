from openai import OpenAI
 
client = OpenAI()
 
assistant = client.beta.assistants.create(
  name="Biomedical PDF Reader",
  instructions="Consult the attached biomedical PDF to answer prompts",
  model="gpt-4o",
  tools=[{"type": "file_search"}],
)

vector_store = client.beta.vector_stores.create(name="PDF Vector Store")
 
file_paths = ["./love.pdf"]
file_streams = [open(path, "rb") for path in file_paths]
 
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
  vector_store_id=vector_store.id, files=file_streams
)
 
assistant = client.beta.assistants.update(
  assistant_id=assistant.id,
  tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)

message_file = client.files.create(
  file=open("./love.pdf", "rb"), purpose="assistants"
)
 
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": "Summarize the main ideas of the paper",
      "attachments": [
        { "file_id": message_file.id, "tools": [{"type": "file_search"}] }
      ],
    }
  ]
)
 
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id, assistant_id=assistant.id
)

messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

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







