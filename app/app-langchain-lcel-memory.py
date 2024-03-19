from operator import itemgetter

from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import Runnable, RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig
from langchain.memory import ConversationBufferMemory

from chainlit.types import ThreadDict
import chainlit as cl

from message_logger import (
    setup_file_logger,
    LogMessage, 
    StudentLogMessage,
    MentorLogMessage
)

from reflection_prompts import (
    initial_messages,
    mentor_message
)

from textwrap import dedent
from datetime import datetime
import random

SESSION_ID = "FJISMZ3242"

role = 'student'
provider = 'unknown'
platform_id = 'Moodle'
courseid = 'Stat-101'


def setup_runnable():
    memory = cl.user_session.get("memory")
    model = AzureChatOpenAI(temperature = 0.4,
                            streaming=True,
                            openai_api_version="2024-02-15-preview",
                            azure_deployment="gpt-4-32k",
                            )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", mentor_message),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ]
    )

    runnable = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        )
        | prompt
        | model
        | StrOutputParser()
    )
    cl.user_session.set("runnable", runnable)


@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    # print(f"User: {current_user}")
    user = current_user
    if user:
        # Access metadata
        role = user.metadata.get('role')
        provider = user.metadata.get('provider')
        platform_id = user.metadata.get('platform-id')
        courseid = user.metadata.get('courseid')
        print(f"User: {user} \n Role: {role} \n Provider: {provider} \n Platform ID: {platform_id} \n Course ID: {courseid}")

@cl.on_chat_start
async def on_chat_start():
    user = cl.user_session.get("user")
    # chat_profile = cl.user_session.get("chat_profile")
    # await cl.Message(
    #     content=f"starting chat with {user.identifier} using the {chat_profile} chat profile"
    # ).send()

    timestamp = datetime.now().isoformat().replace(":", "-")    #strftime("%Y%m%d%H%M%S")
    logger = setup_file_logger(name=user.identifier, 
                               filename=f"logs/{timestamp}-{user.identifier}.log", 
                               log_format=True
                               )
    logger.debug(f"Chat started by user {user.identifier}")
    # logger.debug(f"Chat started by user {SESSION_ID}")

    cl.user_session.set("memory", ConversationBufferMemory(return_messages=True))
    cl.user_session.set("logger", logger)

    setup_runnable()

    #TODO: We can either add a message from a list of pre-defined messages or we
    #can use a generated message. This works, but results in
    #`load_memory_variables` and `AzureChatOpenAI` being shown in the UI.
    
    initial_message = dedent(' '.join(random.choice(initial_messages).split()))
    msg = cl.Message(content=initial_message, disable_feedback=True)
    await msg.send()

    # runnable = cl.user_session.get("runnable")
    memory = cl.user_session.get("memory")
    logger = cl.user_session.get("logger")

    # inputs = {"question": "Start the conversation. Tell the user about yourself, ask them about their day and the topic of their current lecture."}
    # # runnable.invoke(inputs)

    # res = cl.Message(content="")
    # async for chunk in runnable.astream( # pyright: ignore
    #     inputs,
    #     config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler(stream_final_answer=True)]),
    # ):
    #     await res.stream_token(chunk)

    # await res.send()
    memory.chat_memory.add_ai_message(initial_message) # pyright: ignore
    mentor_log_message = MentorLogMessage( # pyright: ignore
        message=initial_message
        )
    logger.info(mentor_log_message.json()) 



@cl.on_message
async def on_message(message: cl.Message):
    memory = cl.user_session.get("memory")
    runnable = cl.user_session.get("runnable")
    logger = cl.user_session.get("logger")

    res = cl.Message(content="")

    async for chunk in runnable.astream( # pyright: ignore
        {"question": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await res.stream_token(chunk)

    await res.send()

    memory.chat_memory.add_user_message(message.content) # pyright: ignore
    memory.chat_memory.add_ai_message(res.content) # pyright: ignore

    # print(memory.chat_memory)  # pyright: ignore

    student_log_message = StudentLogMessage( # pyright: ignore
        message=message.content # pyright: ignore
    )
    logger.info(student_log_message.json()) # pyright: ignore


    mentor_log_message = MentorLogMessage( # pyright: ignore
        message=res.content
        )
    logger.info(mentor_log_message.json()) # pyright: ignore


@cl.on_chat_end
def end():
    logger = cl.user_session.get("logger")
    user = current_user
    print(f"Goodbye {SESSION_ID}")
    logger.debug(f"Chat ended by user {user.identifier}")


@cl.password_auth_callback
def auth():
    return cl.User(identifier="test")