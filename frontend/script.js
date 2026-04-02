import { GoogleGenerativeAIEmbeddings, GoogleGenerativeAI } from "@langchain/google-genai";
import { Pinecone } from "@pinecone-database/pinecone";
import { PineconeStore } from "@langchain/pinecone";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { RetrievalQAChain } from "langchain/chains";
import { PromptTemplate } from "@langchain/core/prompts";

// UI 요소 가져오기
const googleApiKeyInput = document.getElementById('googleApiKey');
const pineconeApiKeyInput = document.getElementById('pineconeApiKey');
const pineconeEnvInput = document.getElementById('pineconeEnv');
const pineconeIndexInput = document.getElementById('pineconeIndex');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const chatMessages = document.getElementById('chatMessages');

let retriever; // 벡터스토어 리트리버를 전역으로 관리

// API 키 및 Pinecone 설정 저장/로드
function saveSettings() {
    sessionStorage.setItem('google_api_key', googleApiKeyInput.value);
    sessionStorage.setItem('pinecone_api_key', pineconeApiKeyInput.value);
    sessionStorage.setItem('pinecone_environment', pineconeEnvInput.value);
    sessionStorage.setItem('pinecone_index_name', pineconeIndexInput.value);
    alert('API 키 및 Pinecone 설정이 저장되었습니다.');
}

function loadSettings() {
    googleApiKeyInput.value = sessionStorage.getItem('google_api_key') || '';
    pineconeApiKeyInput.value = sessionStorage.getItem('pinecone_api_key') || '';
    pineconeEnvInput.value = sessionStorage.getItem('pinecone_environment') || '';
    pineconeIndexInput.value = sessionStorage.getItem('pinecone_index_name') || '';
}

// 초기 로드 시 설정 불러오기
document.addEventListener('DOMContentLoaded', loadSettings);

// API 키 입력 필드 변경 시 설정 저장
googleApiKeyInput.addEventListener('change', saveSettings);
pineconeApiKeyInput.addEventListener('change', saveSettings);
pineconeEnvInput.addEventListener('change', saveSettings);
pineconeIndexInput.addEventListener('change', saveSettings);

// 채팅 메시지 추가 함수
function addMessage(sender, text, isStreaming = false) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message', sender === 'user' ? 'user' : 'ai');
    messageDiv.innerHTML = text; // HTML 렌더링을 위해 innerHTML 사용
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight; // 스크롤 하단으로 이동
    return messageDiv; // 스트리밍 업데이트를 위해 반환
}

// 로딩 인디케이터 표시/숨김
function showLoader() {
    const loaderDiv = document.createElement('div');
    loaderDiv.id = 'loader';
    loaderDiv.classList.add('loader');
    const aiMessageDiv = document.createElement('div');
    aiMessageDiv.classList.add('chat-message', 'ai');
    aiMessageDiv.textContent = '답변 생성 중...';
    aiMessageDiv.appendChild(loaderDiv);
    chatMessages.appendChild(aiMessageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideLoader() {
    const loader = document.getElementById('loader');
    if (loader) {
        loader.parentNode.remove(); // 로더를 포함하는 메시지 div 전체 삭제
    }
}


// RAG 체인 초기화 함수
async function initializeRAGChain() {
    const googleApiKey = sessionStorage.getItem('google_api_key');
    const pineconeApiKey = sessionStorage.getItem('pinecone_api_key');
    const pineconeEnvironment = sessionStorage.getItem('pinecone_environment');
    const pineconeIndexName = sessionStorage.getItem('pinecone_index_name');

    if (!googleApiKey || !pineconeApiKey || !pineconeEnvironment || !pineconeIndexName) {
        alert('Google AI Studio API Key 및 Pinecone 설정(API Key, Environment, Index Name)을 모두 입력해주세요.');
        return null;
    }

    try {
        // 1. 임베딩 모델 초기화
        const embeddings = new GoogleGenerativeAIEmbeddings({
            model: "models/gemini-embedding-001", // 텍스트 임베딩 모델
            apiKey: googleApiKey,
        });

        // 2. Pinecone 클라이언트 및 벡터스토어 초기화
        const pinecone = new Pinecone({
            apiKey: pineconeApiKey,
            environment: pineconeEnvironment,
        });

        const pineconeIndex = pinecone.Index(pineconeIndexName);

        const vectorStore = await PineconeStore.fromExistingIndex(
            embeddings,
            { pineconeIndex }
        );
        
        retriever = vectorStore.asRetriever(); // 리트리버 설정

        // 3. LLM (Gemini 2.5 Flash) 초기화
        const model = new GoogleGenerativeAI({
            model: "gemini-2.5-flash", // Gemini 2.5 Flash 모델
            apiKey: googleApiKey,
            temperature: 0.3,
            maxOutputTokens: 1024,
            streaming: true, // 스트리밍 활성화
        });

        // 4. Prompt Template 정의
        const qaTemplate = `다음 컨텍스트를 사용하여 질문에 답변하세요.
        컨텍스트: {context}
        질문: {question}
        답변:`;
        const qaPrompt = PromptTemplate.fromTemplate(qaTemplate);

        // 5. RAG 체인 생성 (RetrievalQAChain)
        const chain = RetrievalQAChain.fromLLM(
            model,
            retriever,
            {
                prompt: qaPrompt,
                returnSourceDocuments: false, // 소스 문서는 반환하지 않음 (선택 사항)
            }
        );
        console.log("RAG 체인 초기화 성공!");
        return chain;

    } catch (error) {
        console.error("RAG 체인 초기화 중 오류 발생:", error);
        alert("RAG 체인 초기화에 실패했습니다. API 키 또는 Pinecone 설정을 확인해주세요.");
        return null;
    }
}

// 메시지 전송 처리
sendButton.addEventListener('click', async () => {
    const query = userInput.value.trim();
    if (!query) return;

    addMessage('user', query);
    userInput.value = ''; // 입력 필드 초기화

    showLoader(); // 로딩 인디케이터 표시
    sendButton.disabled = true; // 버튼 비활성화
    userInput.disabled = true; // 입력 필드 비활성화

    try {
        const chain = await initializeRAGChain();
        if (!chain) {
            hideLoader();
            addMessage('ai', '챗봇을 초기화할 수 없습니다. 설정을 확인해주세요.');
            return;
        }

        // 스트리밍 응답 처리를 위한 임시 메시지 div
        const aiResponseDiv = addMessage('ai', '');
        let fullResponse = '';

        // LangChain 체인 호출
        const stream = await chain.stream({ query });

        for await (const chunk of stream) {
            fullResponse += chunk.response || chunk.text || ''; // chunk 구조에 따라 변경될 수 있음
            aiResponseDiv.innerHTML = fullResponse; // 스트리밍되는 내용으로 UI 업데이트
            chatMessages.scrollTop = chatMessages.scrollHeight; // 스크롤 하단으로 유지
        }
        
    } catch (error) {
        console.error("챗봇 응답 처리 중 오류 발생:", error);
        addMessage('ai', '죄송합니다. 질문에 답변하는 도중 오류가 발생했습니다.');
    } finally {
        hideLoader(); // 로딩 인디케이터 숨김
        sendButton.disabled = false; // 버튼 활성화
        userInput.disabled = false; // 입력 필드 활성화
        userInput.focus(); // 입력 필드 포커스
    }
});

// 엔터 키로 메시지 전송
userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendButton.click();
    }
});
