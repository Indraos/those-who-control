# Privacy

This exhibition features some intimate data, and we want to be clear how we are trying to make sure that it is not used in ways that you do not like. First off, **We will delete all collected data after the event concludes**. In particular, we don't access volumes you uploaded data is stored. 

## The Data the Installation Colects

### Past: The Rewriting of Memory
- **Images**: Original photos and AI-edited versions generated during your interaction. These are processed on `modal.run` and the OpenAI
- **Storage**: Temporarily stored on an AWS EC2 instance for the duration of the installation
- **Processing**: Images processed locally on the server; no external API calls for this module

### Present: The Conversation That Changes You
- **Conversation Data**: Text of your conversation with the AI system
- **Context Information**: Any personal context you provide in configuration files
- **API Usage**: Conversations processed through **OpenAI's GPT-5 API**
- **Storage**: Conversation history maintained in memory during your session, not persisted to disk

### Future: Possible Selves
- **Images**: Pictures from a web cam are processed on the kiosk laptop

## Infrastructure & Third-Party Services

- **GPT-5** (present/): Chat completions for conversational AI
  - **Training**: According to OpenAI's [data usage policy](https://openai.com/policies/usage-policies), data sent to the API is **not used to train OpenAI's models** by default
  - **Retention**: OpenAI may retain API data for up to 30 days for abuse monitoring, then deletes it (unless you're in a zero retention program)

- **gpt-image-1** (future/): Image editing and generation
  - **Training**: According to OpenAI's [data usage policy](https://openai.com/policies/usage-policies), data sent to the API is **not used to train OpenAI's models** by default
  - **Retention**: OpenAI may retain API data for up to 30 days for abuse monitoring, then deletes it (unless you're in a zero retention program)

We do not use cookies and do not print informative logs that would go to `modal` (see their [privacy policy](https://modal.com/docs/guide/security)). We will terminate modal instances 1 hour after the event. All images on the kiosk will be permanently deleted. All console state for `/present` will be deleted. The only remnant will be printouts of `/future` which you can keep.

Participation is voluntary. You control whether physical copies are created.

## Forgetting

It is **not** about creating a permanent archive of your participation. We showcase how memory is malleable, it's for you to make memories.