from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from openai import OpenAI
import os
from .models import SystemInstruction, Conversation, Message


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
    
    return render(request, 'script/prompts.html', context)


def get_llm_response(conversation):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    client = OpenAI(api_key=api_key)
    
    openai_messages = []
    
    system_instructions = SystemInstruction.objects.filter(is_active=True)
    if system_instructions.exists():
        combined = "\n\n".join([inst.instruction for inst in system_instructions])
        openai_messages.append({"role": "system", "content": combined})
    
    for msg in conversation.messages.all():
        if msg.role in ['user', 'assistant']:
            openai_messages.append({"role": msg.role, "content": msg.content})
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=openai_messages,
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content


def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    message.delete()
    return redirect('script:prompts')
