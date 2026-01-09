import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "../lib/utils";
import { User, Sparkles } from "lucide-react";

export interface MessageMetadata {
    usage?: {
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
    };
    trust?: number;
    sources?: string[];
}

interface ChatMessageProps {
    role: "user" | "assistant";
    content: string;
    metadata?: MessageMetadata;
}

export function ChatMessage({ role, content }: ChatMessageProps) {
    const isUser = role === "user";

    return (
        <div
            className={cn(
                "flex w-full gap-4 py-6 transition-colors",
                "bg-transparent" // Always transparent to match ChatGPT flow
            )}
        >
            <div className="flex-shrink-0 flex flex-col items-center">
                <div
                    className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center shadow-sm",
                        isUser
                            ? "bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                            : "bg-gradient-to-br from-blue-600 to-indigo-600 text-white"
                    )}
                >
                    {isUser ? <User className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
                </div>
            </div>

            <div className="flex-1 min-w-0 space-y-1">
                <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">
                    {isUser ? "You" : "GeneGPT"}
                </p>
                <div className="prose prose-sm max-w-none text-gray-800 dark:text-gray-200 leading-relaxed dark:prose-invert prose-a:text-blue-400 prose-a:font-normal prose-a:no-underline hover:prose-a:underline">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                </div>

                {!isUser && (
                    <div className="mt-6 pt-3 border-t border-gray-200 dark:border-[#333]">
                        <p className="text-[11px] text-gray-500 italic">
                            This system provides educational information. A healthcare professional can help apply this to your personal situation.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
