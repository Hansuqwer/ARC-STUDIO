"""Trivial LangChain LCEL chain fixture.

Simple prompt | LLM chain for testing export functionality.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence

# Define prompt template
prompt = ChatPromptTemplate.from_messages(
    [("system", "You are a helpful assistant."), ("user", "{input}")]
)

# Define output parser
output_parser = StrOutputParser()

# Create simple chain using LCEL pipe operator
simple_chain = prompt | output_parser

# Alternative: explicit RunnableSequence
explicit_chain = RunnableSequence(prompt, output_parser)
