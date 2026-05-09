export interface Paper {
  id: string;
  n: number;
  title: string;
  authors: string;
  year: number | null;
  venue: string;
  claim: string;
}

export interface ResearchResult {
  session_id: string;
  papers_used: number;
  depth_reached: number;
  answer_paragraphs: string[];
  mechanism: string;
  intuition: string;
  limitations: string;
  open_questions: string;
  follow_up_questions: string[];
  papers: Paper[];
}

export interface ConversationMessage {
  role: "user" | "assistant";
  query?: string;
  result?: ResearchResult | null;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  depthReached: number;
  papersUsed: number;
  messages: ConversationMessage[];
  sessionId?: string;
}
