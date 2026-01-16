import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { Activity, Cpu, ShieldCheck, Scale, ChevronDown, ChevronUp } from "lucide-react";

interface UsageStats {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
}

interface AnswerMetricsProps {
    usage?: UsageStats;
    trust?: number;
    certainty?: number;
}

export function AnswerMetrics({ usage, trust, certainty }: AnswerMetricsProps) {
    const [isTrustOpen, setIsTrustOpen] = useState(false);

    if (!usage && typeof trust !== 'number' && typeof certainty !== 'number') return null;

    const getTrustColor = (score: number) => {
        if (score >= 0.7) return "bg-emerald-500 text-emerald-100";
        if (score >= 0.4) return "bg-yellow-500 text-yellow-100";
        return "bg-red-500 text-red-100";
    };

    const getTrustBarColor = (score: number) => {
        if (score >= 0.7) return "bg-emerald-500";
        if (score >= 0.4) return "bg-yellow-500";
        return "bg-red-500";
    };

    const getCertaintyColor = (score: number) => {
        if (score >= 0.85) return "bg-teal-500 text-teal-100";
        if (score >= 0.60) return "bg-blue-500 text-blue-100";
        return "bg-slate-500 text-slate-200";
    };

    const getCertaintyBarGradient = (score: number) => {
        if (score >= 0.85) return "bg-gradient-to-r from-blue-500 to-teal-500";
        if (score >= 0.60) return "bg-gradient-to-r from-blue-400 to-blue-600";
        return "bg-gradient-to-r from-slate-600 to-slate-400";
    };

    const trustPercent = trust ? Math.round(trust * 100) : 0;
    const certaintyPercent = certainty ? Math.round(certainty * 100) : 0;

    return (
        <div className="space-y-6 p-4 bg-[#111] rounded-xl border border-[#303030] mb-4 shadow-lg">

            {/* 1. TRUSTWORTHINESS METER */}
            {typeof trust === 'number' && (
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-white font-medium text-sm">
                            <ShieldCheck className="w-4 h-4 text-blue-400" />
                            Evidence Trust Level
                        </div>
                        <span className={cn(
                            "text-xs font-bold px-2 py-0.5 rounded-full",
                            getTrustColor(trust)
                        )}>
                            {trustPercent}%
                        </span>
                    </div>

                    <div
                        className="h-2 w-full bg-[#2a2a2a] rounded-full overflow-hidden relative group cursor-help"
                        title="Calculated from ClinVar, GeneReviews, OMIM, PubMed, gnomAD"
                    >
                        <div
                            className={cn("h-full transition-all duration-700 ease-out shadow-[0_0_10px_rgba(0,0,0,0.3)]", getTrustBarColor(trust))}
                            style={{ width: `${trustPercent}%` }}
                        />
                    </div>

                    {/* Trust Legend */}
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2">
                        <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> <span className="text-[10px] text-gray-400">High (70–100%)</span></div>
                        <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-yellow-500" /> <span className="text-[10px] text-gray-400">Mod (40–70%)</span></div>
                        <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-red-500" /> <span className="text-[10px] text-gray-400">Emerging (0–40%)</span></div>
                    </div>

                    <p className="text-[10px] text-gray-400 mt-1 italic leading-tight">
                        Red does not mean incorrect — it means scientific evidence is still emerging or limited.
                    </p>

                    {/* Expandable Calculation */}
                    <div className="pt-2 border-t border-[#222] mt-2">
                        <button
                            onClick={() => setIsTrustOpen(!isTrustOpen)}
                            className="flex items-center justify-between w-full text-[10px] font-semibold text-gray-400 hover:text-gray-200 transition-colors"
                        >
                            How this score is calculated
                            {isTrustOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                        {isTrustOpen && (
                            <div className="mt-2 space-y-2 animate-in fade-in slide-in-from-top-1 duration-200">
                                <ul className="space-y-1 text-[10px] text-gray-300 font-mono bg-[#161616] p-2 rounded border border-[#2a2a2a]">
                                    <li>Start at 100%</li>
                                    <li>−20% if only literature (PubMed) used</li>
                                    <li>−15% if no clinical guideline source</li>
                                    <li>−10% if variant is VUS</li>
                                    <li>−15% if rare gene or limited phenotypes</li>
                                    <li>−10% if conflicting sources detected</li>
                                </ul>
                                <p className="text-[10px] text-gray-400 italic leading-relaxed">
                                    This score reflects strength and diversity of scientific evidence, not importance or seriousness.
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Separator 1 */}
            {typeof trust === 'number' && (typeof certainty === 'number' || usage) && (
                <div className="h-px bg-[#303030]" />
            )}

            {/* 2. ANSWER CERTAINTY METER (Renamed to Scientific Consensus Level) */}
            {typeof certainty === 'number' && (
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-white font-medium text-sm">
                            <Scale className="w-4 h-4 text-teal-400" />
                            Scientific Consensus Level
                        </div>
                        <span className={cn(
                            "text-xs font-bold px-2 py-0.5 rounded-full",
                            getCertaintyColor(certainty)
                        )}>
                            {certaintyPercent}%
                        </span>
                    </div>

                    {/* Dotted background using radial gradient for dots */}
                    <div
                        className="h-2 w-full bg-[#2a2a2a] rounded-full overflow-hidden relative group cursor-help bg-[image:radial-gradient(#444_1px,transparent_1px)] bg-[size:3px_3px]"
                        title="Consensus level of scientific knowledge"
                    >
                        <div
                            className={cn("h-full transition-all duration-700 ease-out shadow-sm", getCertaintyBarGradient(certainty))}
                            style={{ width: `${certaintyPercent}%` }}
                        />
                    </div>

                    <div className="pt-3 border-t border-[#222] mt-1">
                        <p className="text-[10px] font-semibold text-gray-400 mb-1">How to read this</p>
                        <p className="text-[10px] text-gray-400 leading-relaxed">
                            This reflects how consistent and well-established current scientific knowledge is for this topic.
                            A lower score does not mean the answer is wrong — it means the evidence is still emerging, limited, or varies across studies.
                        </p>
                    </div>
                </div>
            )}

            {/* Separator 2 */}
            {typeof certainty === 'number' && usage && (
                <div className="h-px bg-[#303030]" />
            )}

            {/* 3. TOKEN USAGE METER */}
            {usage && (
                <div className="space-y-3">
                    <div className="flex items-center gap-2 text-white font-medium text-sm">
                        <Cpu className="w-4 h-4 text-purple-400" />
                        Token Usage
                    </div>

                    <div className="relative pt-1">
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Total Load</span>
                            <span className="text-xs font-bold text-white font-mono">{usage.total_tokens.toLocaleString()}</span>
                        </div>

                        {/* Progress Bar (Blue -> Purple Gradient) */}
                        <div className="h-2 w-full bg-[#2a2a2a] rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-700 ease-out"
                                style={{ width: '100%' }}
                            >
                                {/* We can visually split prompt/completion if we want, but gradient bar represents total load visually */}
                            </div>
                        </div>

                        <div className="flex justify-between items-center mt-2 text-[10px] text-gray-500 font-mono">
                            <div className="flex gap-1.5 ">
                                <span>Prompt: <span className="text-gray-300">{usage.prompt_tokens}</span></span>
                                <span className="text-gray-700">|</span>
                                <span>Compl: <span className="text-gray-300">{usage.completion_tokens}</span></span>
                            </div>
                        </div>
                    </div>

                    <div className="pt-3 border-t border-[#222] mt-1">
                        <p className="text-[10px] font-semibold text-gray-400 mb-1">How to read this</p>
                        <p className="text-[10px] text-gray-400 leading-relaxed">
                            This shows how much context the AI used to answer your question.
                            It includes your question, the answer, system instructions, memory, and any scientific sources retrieved.
                            Higher values mean more information was used, not that your question was long.
                        </p>
                    </div>
                </div>
            )}

        </div>
    );
}
