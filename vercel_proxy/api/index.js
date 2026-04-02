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
    const { query } = req.body;
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

    // 1. 임베딩 생성 (gemini-embedding-001)
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
        topK: 3,
        includeMetadata: true,
      }),
    });

    if (!pineconeRes.ok) {
      const errText = await pineconeRes.text();
      throw new Error(`Pinecone 검색 API 에러: ${errText}`);
    }
    
    const pineconeData = await pineconeRes.json();
    const contexts = pineconeData.matches.map(m => m.metadata.text).join('\n\n');

    // 3. Gemini 답변 요청 (스트리밍)
    const prompt = `당신은 인공지능 연구원 윤치현님의 비서입니다. 
제공된 컨텍스트를 바탕으로 사용자의 질문에 친절하게 답변하세요. 
모르는 내용이라면 지어내지 말고 모른다고 답변하세요.
반드시 한국어로 답변하세요.

컨텍스트: ${contexts}

질문: ${query}
답변:`;

    const chatRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key=${GOOGLE_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: prompt }] }],
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
