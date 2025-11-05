from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import SystemInstruction, Conversation, Message
from .agent import DescriptionAgent
import os


def prompts_view(request):
    conversation = Conversation.objects.filter(is_active=True).first()
    if not conversation:
        conversation = Conversation.objects.create(name="New Session")
    
    if request.method == 'POST':
        user_prompt = request.POST.get('prompt', '').strip()
        
        if user_prompt:
            try:
                Message.objects.create(conversation=conversation, role='user', content=user_prompt)
                assistant_response = get_llm_response(conversation)
                Message.objects.create(conversation=conversation, role='assistant', content=assistant_response)
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
    
    context = {
        'conversation': conversation,
        'conversation_messages': conversation.messages.all(),
    }
    
    return render(request, 'description/prompts.html', context)


def get_llm_response(conversation):
    """
    Process conversation using the DescriptionAgent following proper AI agent patterns
    """
    import os as os_module
    
    # Get API key
    api_key = os_module.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    # Initialize the agent
    agent = DescriptionAgent(
        api_key=api_key,
        model="gpt-4o",
        temperature=0.7,
        max_tokens=1000
    )
    
    # Load any additional system instructions from database
    system_instructions = SystemInstruction.objects.filter(is_active=True)
    if system_instructions.exists():
        instructions = [inst.instruction for inst in system_instructions]
        agent.set_additional_instructions(instructions)
    
    # Load conversation history into agent memory
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in conversation.messages.all()
        if msg.role in ['user', 'assistant']
    ]
    agent.load_memory(conversation_history)
    
    # Get the last user message
    last_user_message = conversation.messages.filter(role='user').last()
    if not last_user_message:
        raise ValueError("No user message found in conversation")
    
    # Run the agent (it will handle adding to memory internally)
    # Since we already loaded memory, we need to remove the last message first
    # to avoid duplication when agent.run() adds it again
    if agent.memory and agent.memory[-1]["role"] == "user":
        user_input = agent.memory.pop()["content"]
    else:
        user_input = last_user_message.content
    
    response = agent.run(user_input)
    
    return response


def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    message.delete()
    return redirect('description:prompts')

