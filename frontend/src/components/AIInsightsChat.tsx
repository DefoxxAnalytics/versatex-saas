import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Loader2,
  Send,
  User,
  Sparkles,
  StopCircle,
  Trash2,
  AlertCircle,
} from "lucide-react";
import { useRef, useEffect } from "react";
import { Streamdown } from "streamdown";
import { useAIChatStream, type ChatMessage } from "@/hooks/useAIInsights";
import { useOrganization } from "@/contexts/OrganizationContext";

const SUGGESTED_PROMPTS = [
  "What are the top cost savings opportunities?",
  "Which suppliers have the highest risk concentration?",
  "Show me spending anomalies from last quarter",
  "What categories should we consolidate?",
  "Analyze our supplier diversity metrics",
  "What's our maverick spend percentage?",
];

interface AIInsightsChatProps {
  className?: string;
  height?: string | number;
}

export function AIInsightsChat({
  className,
  height = "calc(100vh - 200px)",
}: AIInsightsChatProps) {
  const { activeOrganization } = useOrganization();
  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    cancelStream,
    clearMessages,
  } = useAIChatStream();

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const inputRef = useRef<string>("");

  const displayMessages = messages;

  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector(
      "[data-radix-scroll-area-viewport]"
    ) as HTMLDivElement;

    if (viewport) {
      requestAnimationFrame(() => {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: "smooth",
        });
      });
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const content = inputRef.current.trim();
    if (!content || isStreaming) return;

    sendMessage(content, {
      organization_id: activeOrganization?.id,
    });

    inputRef.current = "";
    if (textareaRef.current) {
      textareaRef.current.value = "";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSuggestedPrompt = (prompt: string) => {
    sendMessage(prompt, {
      organization_id: activeOrganization?.id,
    });
  };

  return (
    <Card className={cn("flex flex-col", className)} style={{ height }}>
      <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between pb-4 border-b">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary/10">
            <Sparkles className="h-5 w-5 text-primary" />
          </div>
          <div>
            <CardTitle className="text-lg">AI Procurement Assistant</CardTitle>
            <p className="text-sm text-muted-foreground">
              Ask questions about your procurement data
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <Badge variant="secondary" className="animate-pulse">
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              Thinking...
            </Badge>
          )}
          {displayMessages.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearMessages}
              disabled={isStreaming}
              className="text-muted-foreground hover:text-foreground"
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
        <div ref={scrollAreaRef} className="flex-1 overflow-hidden">
          {displayMessages.length === 0 ? (
            <div className="flex h-full flex-col p-6">
              <div className="flex flex-1 flex-col items-center justify-center gap-6 text-muted-foreground">
                <div className="flex flex-col items-center gap-3">
                  <Sparkles className="h-16 w-16 opacity-20" />
                  <p className="text-lg font-medium">
                    Start a conversation about your procurement data
                  </p>
                  <p className="text-sm text-center max-w-md">
                    Ask about spending patterns, supplier performance, cost
                    optimization opportunities, and more.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full">
                  {SUGGESTED_PROMPTS.map((prompt, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestedPrompt(prompt)}
                      disabled={isStreaming}
                      className="text-left rounded-lg border border-border bg-card px-4 py-3 text-sm transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <ScrollArea className="h-full">
              <div className="flex flex-col space-y-4 p-6">
                {displayMessages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}

                {isStreaming &&
                  !displayMessages.some((m) => m.isStreaming) && (
                    <div className="flex items-start gap-3">
                      <div className="h-8 w-8 shrink-0 mt-1 rounded-full bg-primary/10 flex items-center justify-center">
                        <Sparkles className="h-4 w-4 text-primary" />
                      </div>
                      <div className="rounded-lg bg-muted px-4 py-2.5">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      </div>
                    </div>
                  )}
              </div>
            </ScrollArea>
          )}
        </div>

        {error && (
          <div className="px-6 py-3 border-t bg-destructive/10">
            <div className="flex items-center gap-2 text-destructive text-sm">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="flex gap-3 p-4 border-t bg-background/50"
        >
          <Textarea
            ref={textareaRef}
            onChange={(e) => {
              inputRef.current = e.target.value;
            }}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your procurement data..."
            className="flex-1 max-h-32 resize-none min-h-11"
            rows={1}
            disabled={isStreaming}
          />
          {isStreaming ? (
            <Button
              type="button"
              size="icon"
              variant="destructive"
              onClick={cancelStream}
              className="shrink-0 h-11 w-11"
            >
              <StopCircle className="h-5 w-5" />
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon"
              className="shrink-0 h-11 w-11"
            >
              <Send className="h-5 w-5" />
            </Button>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3",
        isUser ? "justify-end items-start" : "justify-start items-start"
      )}
    >
      {!isUser && (
        <div className="h-8 w-8 shrink-0 mt-1 rounded-full bg-primary/10 flex items-center justify-center">
          <Sparkles className="h-4 w-4 text-primary" />
        </div>
      )}

      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-2.5",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <Streamdown>{message.content}</Streamdown>
            {message.isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse" />
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="h-8 w-8 shrink-0 mt-1 rounded-full bg-secondary flex items-center justify-center">
          <User className="h-4 w-4 text-secondary-foreground" />
        </div>
      )}
    </div>
  );
}
