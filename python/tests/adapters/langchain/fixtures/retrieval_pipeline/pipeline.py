"""Retrieval pipeline fixture.

RAG-style pipeline with retriever + LLM for testing export functionality.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


# Define retriever (mock for testing)
class MockRetriever:
    def invoke(self, query):
        return ["doc1", "doc2"]


retriever = MockRetriever()

# Define prompt template for RAG
rag_prompt = ChatPromptTemplate.from_template(
    "Context: {context}\n\nQuestion: {question}\n\nAnswer:"
)

# Define output parser
parser = StrOutputParser()

# Create RAG chain using LCEL
rag_chain = {"context": retriever, "question": RunnablePassthrough()} | rag_prompt | parser

# Alternative: multi-step chain
retrieval_step = retriever
prompt_step = rag_prompt
output_step = parser

multi_step_chain = retrieval_step | prompt_step | output_step
