export default async function handler(req, res) {
  // CORS 처리
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'OPTIONS, POST');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    const { query, history = [] } = req.body;
    if (!query) {
      return res.status(400).json({ error: 'Missing query' });
    }

    const GOOGLE_API_KEY = process.env.GOOGLE_API_KEY?.trim();
    const PINECONE_API_KEY = process.env.PINECONE_API_KEY?.trim();
    let PINECONE_HOST = process.env.PINECONE_HOST?.trim();

    if (!GOOGLE_API_KEY || !PINECONE_API_KEY || !PINECONE_HOST) {
      return res.status(500).json({ error: 'Server configuration error: Missing API Keys or Host' });
    }

    PINECONE_HOST = PINECONE_HOST.replace(/^https?:\/\//, "").replace(/\/$/, "");

    // 1. 임베딩 생성 (gemini-embedding-001) - 사용자의 현재 질문에 대한 임베딩만 검색용으로 생성
    const embedRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key=${GOOGLE_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "models/gemini-embedding-001",
          content: { parts: [{ text: query }] },
        }),
      }
    );

    if (!embedRes.ok) {
      const errText = await embedRes.text();
      throw new Error(`Google 임베딩 API 에러: ${errText}`);
    }
    
    const embedData = await embedRes.json();
    const queryEmbedding = embedData.embedding.values;

    // 2. Pinecone 검색
    const pineconeRes = await fetch(`https://${PINECONE_HOST}/query`, {
      method: "POST",
      headers: {
        "Api-Key": PINECONE_API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        vector: queryEmbedding,
        topK: 15,
        includeMetadata: true,
      }),
    });

    if (!pineconeRes.ok) {
      const errText = await pineconeRes.text();
      throw new Error(`Pinecone 검색 API 에러: ${errText}`);
    }
    
    const pineconeData = await pineconeRes.json();
    const contexts = pineconeData.matches.map(m => m.metadata.text).join('\\n\\n');

    // 3. Gemini 답변 요청 (스트리밍 + 대화 기록 추가)
    const prompt = `당신은 인공지능 연구원 윤치현(Chihyeon Yun)님의 똑똑하고 정중한 AI 개인 비서입니다.

[대화 및 답변 지침]
1. **윤치현 관련 질문 (프로젝트, 학업, 논문, 커리어 등)**:
   - 제공된 [컨텍스트(Context)]의 정보에 기반하여 사실에 기반해 정확하게 답변하세요.
   - 만약 질문이 윤치현님에 관한 것이지만 컨텍스트에 명시적으로 언급되지 않은 정보라면, 억지로 지어내지 말고 정중하게 "해당 내용은 제가 가진 정보(포트폴리오) 내에서는 찾기 어렵습니다."라고 답변하세요.
2. **윤치현 및 포트폴리오와 무관한 일반 질문 (일반 상식, 코딩 질문, 일상 대화 등)**:
   - 컨텍스트에 얽매이지 않고, 대화 전체 맥락을 고려하여 인공지능 비서로서 친절하고 정확하게 일반 지식으로 답변하세요.
3. **대화 맥락 유지**:
   - 이전 대화 기록(history)을 항상 참고하여 맥락이 자연스럽게 이어지도록 하세요. (예: "방금 말한 거 다시 설명해줘", "그 연구에 대해 더 자세히 말해줘" 등)
4. **언어 및 어조**:
   - 질문을 받은 언어(기본적으로 한국어 또는 영어)에 맞추어 정중하게 높임말로 자연스럽게 답변하세요.

[컨텍스트 시작]
${contexts}
[컨텍스트 끝]

질문: ${query}
답변:`;

    // 대화 내역(History)을 Gemini 형식에 맞게 구성
    const contents = [];
    for (const msg of history) {
      contents.push({
        role: msg.role === 'user' ? 'user' : 'model',
        parts: [{ text: msg.text }]
      });
    }
    // 현재 질문과 컨텍스트를 마지막 user 요청으로 추가
    contents.push({ role: "user", parts: [{ text: prompt }] });

    const chatRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:streamGenerateContent?alt=sse&key=${GOOGLE_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: contents,
          generationConfig: { temperature: 0.1 },
        }),
      }
    );

    if (!chatRes.ok) {
      const errText = await chatRes.text();
      throw new Error(`Google Chat API 에러: ${errText}`);
    }

    // 스트리밍 응답 전달
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const reader = chatRes.body.getReader();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      res.write(value);
    }
    res.end();

  } catch (error) {
    console.error("Handler error:", error);
    // Vercel에서 fetch failed 시 자세한 정보가 숨겨질 수 있으므로 스택 트레이스 또는 명시적 메시지 반환
    res.status(500).json({ error: error.message, stack: error.stack });
  }
}
