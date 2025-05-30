import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import io

load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Set page config
st.set_page_config(
    page_title="Chat with PDF using Gemini", 
    page_icon=":book:", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Get text from PDF files
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Split text into chunks
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

# Create vector store from text chunks
def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

# Conversational chain
def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
    provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """

    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)

    return chain

# Handle user input and question answering
def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_question)

    chain = get_conversational_chain()
    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    actual_response = response["output_text"]

    # Show the response
    st.write(f"Response:", actual_response)
    create_download_link(actual_response, "response.txt")

# Create a download link for the text
def create_download_link(text, filename):
    buffer = io.BytesIO()
    buffer.write(text.encode())
    buffer.seek(0)

    return st.download_button(
        label="Download Response Text",
        data=buffer,
        file_name=filename,
        mime="text/plain"
    )

# Main function
def main():
    st.title("Chat with PDF using Gemini 💁")

    st.markdown("""
    **Instructions:**
    - Upload your PDF documents using the **Upload PDF Files** section in the sidebar.
    - Ask a question about the content of the PDFs after processing.
    - The AI will process the PDF content and give a detailed answer to your query.
    """)

    # Input form
    user_question = st.text_input("Ask a Question from the PDF Files", key="question_input")

    if user_question:
        st.spinner("Processing your question...")  # Show spinner
        user_input(user_question)

    with st.sidebar:
        st.title("Menu:")
        st.markdown("""
        **Upload PDF Files:**
        - Please upload one or more PDF files that you want to chat about.
        - Click on **Submit & Process** to start processing the files.
        """)
        pdf_docs = st.file_uploader("Upload PDF Files", accept_multiple_files=True)

        if st.button("Submit & Process"):
            if pdf_docs:
                with st.spinner("Processing files... Please wait."):
                    raw_text = get_pdf_text(pdf_docs)
                    text_chunks = get_text_chunks(raw_text)
                    get_vector_store(text_chunks)
                    st.success("Files processed successfully!")
            else:
                st.warning("Please upload at least one PDF file before processing.")

if __name__ == "__main__":
    main()
