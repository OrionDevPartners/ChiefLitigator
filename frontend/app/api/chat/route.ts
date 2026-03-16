import { convertToModelMessages, streamText, UIMessage } from 'ai'

export const maxDuration = 30

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json()

  const result = streamText({
    model: 'openai/gpt-4o-mini',
    system: `You are Cyphergy, an expert AI legal assistant. You help attorneys and legal professionals with:
- Drafting motions, briefs, contracts, and other legal documents
- Researching case law, statutes, and regulations
- Checking deadlines, statutes of limitations, and procedural requirements
- Analyzing legal issues and providing strategic advice

Always be precise, cite your sources when relevant, and clearly distinguish between legal information and legal advice. Format longer responses with clear headings and structure. Be concise and professional.`,
    messages: await convertToModelMessages(messages),
    abortSignal: req.signal,
  })

  return result.toUIMessageStreamResponse()
}
