# Vercel Serverless Proxy for RAG Chatbot

This directory contains the code to deploy a secure, serverless proxy for your RAG Chatbot using Vercel.
By deploying this, your API keys remain hidden and visitors from anywhere can talk to your chatbot without being blocked.

## How to Deploy to Vercel

1. **Install Vercel CLI (if not already installed):**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   Navigate into this `vercel_proxy` directory and run:
   ```bash
   vercel
   ```
   * Follow the prompts. Say "Y" to set up and deploy.
   * Do not link to an existing project (create a new one).

3. **Set Environment Variables:**
   Go to your Vercel Dashboard (https://vercel.com) -> Select your new project -> **Settings** -> **Environment Variables**.
   Add the following 3 variables:
   - `GOOGLE_API_KEY`: Your Google AI Studio API Key (AIza...)
   - `PINECONE_API_KEY`: Your Pinecone API Key (pcsk_...)
   - `PINECONE_HOST`: Your Pinecone Index Host (e.g., my-index-xxxx.svc.us-east-1.pinecone.io)

4. **Redeploy to apply variables:**
   Go back to the terminal and run:
   ```bash
   vercel --prod
   ```

5. **Connect your Frontend:**
   Copy the `.vercel.app` URL that Vercel gives you.
   In your `index.html` file, find the `WORKER_URL` variable and paste your Vercel URL with `/api` at the end:
   ```javascript
   const WORKER_URL = "https://your-vercel-project-name.vercel.app/api";
   ```