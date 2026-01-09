"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Menu, Sparkles, Activity, X, Plus, Globe, Mic, AudioLines, SquarePen } from "lucide-react";
import { sendMessage, AnswerJson } from "@/lib/api";
import { ChatMessage, MessageMetadata } from "@/components/ChatMessage";
import { EvidencePanel } from "@/components/EvidencePanel";
import { AnswerMetrics } from "@/components/AnswerMetrics"; // New import
import { AboutPanel } from "@/components/AboutPanel"; // New import
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  metadata?: MessageMetadata;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentEvidence, setCurrentEvidence] = useState<AnswerJson | null>(null);
  const [currentMetrics, setCurrentMetrics] = useState<{ usage?: any; trust?: number; certainty?: number } | null>(null); // New state
  const [showEvidence, setShowEvidence] = useState(true); // Default open on desktop
  const [showSidebar, setShowSidebar] = useState(true);
  const [showAbout, setShowAbout] = useState(false); // New state for About page
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Responsive init
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setShowEvidence(false);
        if (window.innerWidth < 768) setShowSidebar(false);
      }
    }
    // Run once on mount
    handleResize();
  }, []);

  // Helper to format evidence JSON into Markdown (replicating app_web.py logic)
  const formatEvidenceMarkdown = (json: AnswerJson): string => {
    let md = "";
    const { gene, disease_focus, evidence } = json;
    const { pubmed, clinvar } = evidence || {};

    // 1. Gene IDs
    if (gene?.symbol || gene?.omim_id || gene?.ncbi_gene_id) {
      md += "\n\n#### 🧾 Gene IDs used\n";
      if (gene.symbol) md += `**Gene symbol:** \`${gene.symbol}\`\n\n`;
      if (gene.omim_id || gene.ncbi_gene_id) md += "**Database IDs:**\n";
      if (gene.omim_id) md += `- OMIM: [\`${gene.omim_id}\`](https://www.omim.org/entry/${gene.omim_id}) \n`;
      if (gene.ncbi_gene_id) md += `- NCBI Gene ID: [\`${gene.ncbi_gene_id}\`](https://www.ncbi.nlm.nih.gov/gene/${gene.ncbi_gene_id}) \n`;
    }

    // 2. Disease Summary
    if (disease_focus?.used) {
      md += "\n#### 🦠 Disease summary (from OMIM)\n";
      const total = disease_focus.total_phenotypes;
      if (total) md += `**Total OMIM phenotypes:** ${total}\n\n`;

      if (disease_focus.top_diseases?.length > 0) {
        md += "**Top associated diseases:**\n";
        disease_focus.top_diseases.forEach((d: string) => {
          md += `- ${d.replace(/[{}]/g, "")}\n`;
        });
      }
    }

    // 3. PubMed Papers
    if (pubmed?.papers?.length > 0) {
      md += "\n#### 📄 PubMed papers used\n";
      pubmed.papers.slice(0, 5).forEach((p: any, i: number) => {
        const url = `https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/`;
        const header = `${i + 1}. [${p.title}](${url})`;
        md += `${header}\n`;

        let meta = [];
        if (p.pmid) meta.push(`PMID: \`${p.pmid}\``);
        if (p.year) meta.push(p.year);
        if (p.journal) meta.push(p.journal);

        if (meta.length > 0) {
          md += `<small>${meta.join(" • ")}</small>\n\n`;
        }
      });
    }

    // 4. ClinVar
    if (clinvar?.used) {
      md += "\n#### 🧬 ClinVar variant summary\n";
      md += `- **Accession:** \`${clinvar.accession || "not available"}\`\n`;
      md += `- **Clinical significance:** ${clinvar.clinical_significance || "not classified"}\n`;
      md += `- **Condition:** ${clinvar.condition || "not specified"}\n`;
      if (clinvar.link) md += `\n[Open full ClinVar record](${clinvar.link})\n`;
    }

    return md;
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    try {
      const data = await sendMessage(userMsg);

      // Append formatted evidence to the answer
      const evidenceMarkdown = formatEvidenceMarkdown(data.answer_json);
      const fullContent = data.answer + "\n" + evidenceMarkdown;

      setMessages((prev) => [...prev, {
        role: "assistant",
        content: fullContent,
        metadata: {
          usage: data.usage,
          trust: data.trust,
          sources: data.sources
        }
      }]);
      setCurrentEvidence(data.answer_json);
      setCurrentMetrics({ usage: data.usage, trust: data.trust, certainty: data.certainty }); // Set metrics
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `**Error:** ${err.message || "Something went wrong."}`,
        },
      ]);
      setCurrentMetrics(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    // FULL SCREEN WRAPPER
    <div className="flex h-screen bg-[#212121] text-gray-100 font-sans overflow-hidden">

      {/* 1. SIDEBAR (Left) */}
      <div
        className={cn(
          "flex-none flex-col bg-[#171717] transition-all duration-300 ease-in-out border-r border-[#303030]",
          showSidebar ? "w-[260px] flex" : "w-0 hidden overflow-hidden"
        )}
      >
        <div className="p-3">
          <button onClick={() => {
            setMessages([]);
            setCurrentEvidence(null);
            setCurrentMetrics(null); // Clear metrics
          }} className="w-full flex items-center justify-between px-3 py-3 text-sm text-gray-200 hover:bg-[#212121] rounded-lg transition-colors group">
            <span className="flex items-center gap-3 font-medium">
              <span className="bg-white text-black rounded-full p-1"><Sparkles className="w-3.5 h-3.5" /></span>
              New chat
            </span>
            <SquarePen className="w-4 h-4 opacity-0 group-hover:opacity-100 text-gray-400" />
          </button>
        </div>

        <div className="flex-1 px-3 py-2 overflow-y-auto custom-scrollbar">

          {/* New Metrics Section */}
          {currentMetrics && (
            <div className="px-3 mb-4">
              <AnswerMetrics usage={currentMetrics.usage} trust={currentMetrics.trust} certainty={currentMetrics.certainty} />
            </div>
          )}

          {!currentEvidence ? (
            <>
              <div className="text-xs font-semibold text-gray-500 mb-3 px-3 uppercase tracking-wider">History</div>
              <div className="text-sm text-gray-400 italic px-3 py-2">
                No active search data.
              </div>
            </>
          ) : (
            <div className="space-y-4">
              <div className="px-3">
                <div className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <Activity className="w-3 h-3" />
                  Raw Response JSON
                </div>
                <div className="bg-[#111] rounded-lg border border-[#303030] p-3 overflow-x-auto">
                  <pre className="text-[10px] text-green-400 font-mono leading-relaxed whitespace-pre-wrap break-all">
                    {JSON.stringify(currentEvidence, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="p-3 border-t border-[#303030]">
          <button
            onClick={() => setShowAbout(true)}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-gray-400 hover:text-white hover:bg-[#212121] rounded-lg transition-colors mb-2 group"
          >
            <span className="w-8 h-8 rounded-lg bg-[#252525] flex items-center justify-center text-gray-400 border border-[#333] group-hover:border-gray-500 transition-colors">?</span>
            About GeneGPT
          </button>

          <div className="flex items-center gap-3 px-2 py-2 hover:bg-[#212121] rounded-lg cursor-pointer transition-colors">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-500 to-emerald-700 flex items-center justify-center text-xs font-bold text-white shadow-sm">BD</div>
            <div className="text-sm font-medium">Bobby Dhir</div>
          </div>
        </div>
      </div>

      {/* 2. MAIN CHAT AREA (Center) */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#212121] relative">

        {/* Header */}
        <header className="flex-none h-14 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            {!showSidebar && (
              <button onClick={() => setShowSidebar(true)} className="p-2 hover:bg-[#2f2f2f] rounded-lg text-gray-400 transition-colors">
                <Menu className="w-5 h-5" />
              </button>
            )}
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl text-gray-200 cursor-pointer hover:bg-[#2f2f2f] transition-colors">
              <span className="text-lg font-semibold">GeneGPT 5.2</span>
              <span className="text-gray-500 text-xs font-medium bg-[#2f2f2f] px-1.5 py-0.5 rounded">v2</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              title="Toggle Live Evidence"
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border",
                showEvidence
                  ? "bg-white text-black border-transparent shadow-md"
                  : "bg-transparent text-gray-400 border-[#333] hover:text-gray-200 hover:border-gray-500"
              )}
            >
              <Activity className="w-4 h-4" />
              <span className="hidden sm:inline">
                {showEvidence ? "Hide verification data" : "Show verification data ▸"}
              </span>
            </button>
          </div>
        </header>

        {/* Scrollable Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto custom-scrollbar px-4"
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center pb-20">
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mb-6 shadow-xl shadow-white/5 animate-in fade-in zoom-in duration-500">
                <Sparkles className="w-8 h-8 text-black" />
              </div>
              <h1 className="text-2xl font-semibold text-white">What can I help with?</h1>
            </div>
          ) : (
            <div className="w-full max-w-3xl mx-auto pt-4 pb-8">
              {messages.map((m, i) => (
                <ChatMessage key={i} role={m.role} content={m.content} metadata={m.metadata} />
              ))}
              {isLoading && (
                <div className="ml-12 mt-2">
                  <div className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-pulse" />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="flex-none p-4 pb-6 w-full flex justify-center bg-gradient-to-t from-[#212121] to-[#212121]/0">
          <div className="w-full max-w-3xl relative">
            <div className="relative flex flex-col bg-[#2F2F2F] rounded-xl shadow-lg ring-1 ring-white/10 focus-within:ring-white/20 transition-all duration-200 overflow-hidden group">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message GeneGPT..."
                className="w-full bg-transparent border-none focus:ring-0 resize-none max-h-52 min-h-[52px] text-[16px] px-4 py-3 !text-white placeholder-gray-400 scrollbar-hide outline-none leading-relaxed hidden-scrollbar"
                style={{ color: '#ffffff' }}
                rows={1}
              />

            </div>
            <p className="text-[11px] text-center mt-3 text-gray-500 font-medium select-none">
              GeneGPT can make mistakes. Verify important genomic findings.
            </p>
          </div>
        </div>
      </div>

      {/* 3. RIGHTS EVIDENCE PANEL (Flex-none, Collapsible) */}
      <div
        className={cn(
          "flex-none bg-[#000000] border-l border-[#303030] transition-all duration-300 ease-in-out overflow-hidden flex flex-col",
          showEvidence ? "w-[400px]" : "w-0"
        )}
      >
        <div className="flex-none p-4 border-b border-[#303030] flex items-center justify-between bg-[#0C0C0C]">
          <span className="font-semibold text-sm text-gray-300 flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" />
            Verification Data
          </span>
          <button
            onClick={() => setShowEvidence(false)}
            className="p-1 hover:bg-[#1f1f1f] rounded text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar bg-[#0C0C0C]">
          <EvidencePanel answerJson={currentEvidence} />
        </div>
      </div>

      {showAbout && <AboutPanel onClose={() => setShowAbout(false)} />}

    </div>
  );
}
