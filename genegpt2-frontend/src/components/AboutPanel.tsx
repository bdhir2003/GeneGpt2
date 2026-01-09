import React from "react";
import { X, Activity, Brain, Database, ShieldCheck, Scale, Lock, FileJson, ArrowDown, GitBranch, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

const INTRO_TEXT = `GeneGPT is an educational genetics AI that helps people understand genes, variants, and genetic reports using real scientific databases (ClinVar, OMIM, PubMed, GeneReviews, gnomAD).`;

const WHY_BUILT_TEXT = `Genetic results are often confusing, emotionally heavy, and hard to interpret. GeneGPT exists to reduce confusion and anxiety by translating complex science into understandable explanations.`;

const WHAT_SOLVES_TEXT = `It interprets genetic terms, connects trusted evidence to answers, avoids alarmism, and helps users prepare for real conversations with their healthcare providers.`;

const JSON_SYSTEM_TEXT = `GeneGPT uses a strict JSON (JavaScript Object Notation) architecture. By passing structured data objects—Question JSON, Evidence JSON, and Answer JSON—between layers, the system ensures that every claim in the final answer can be traced back to a specific database field. This makes the system transparent, auditable, and modular.`;

const MEMORY_PRIVACY_PART1 = `Short-term memory maintains context for your current conversation.`;
const MEMORY_PRIVACY_PART2 = `Long-term memory is opt-in only and strictly controlled.`;
const MEMORY_PRIVACY_PART3 = `Privacy is central to the design: sensitive health data is not auto-stored, and you can clear your memory at any time.`;

const PIPELINE_STEPS_DATA = [
    { number: "01", title: "Input Processing", text: "The system identifies the intent (gene, variant, disease, or general question) and injects context for follow-up questions." },
    { number: "02", title: "Data Structuring", text: "The question is converted into a structured JSON format to ensure precise database queries." },
    { number: "03", title: "Live Retrieval", text: "Real-time queries are sent to scientific sources like ClinVar and PubMed. No static training data is relied upon for facts." },
    { number: "04", title: "Synthesis", text: "The Reasoning Layer analyzes the retrieved evidence for conflicts, relevance, and clinical significance." },
    { number: "05", title: "Transparency", text: "The Final Answer JSON delivered to the UI contains every source used, allowing for full auditability." },
];

interface AboutPanelProps {
    onClose: () => void;
}

export function AboutPanel({ onClose }: AboutPanelProps) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-in fade-in duration-200">
            <div className="bg-[#0f0f0f] w-full max-w-5xl h-[92vh] rounded-2xl border border-[#303030] shadow-2xl flex flex-col overflow-hidden relative">

                {/* Header */}
                <div className="flex-none flex items-center justify-between px-8 py-6 border-b border-[#2a2a2a] bg-[#0f0f0f]/95 backdrop-blur absolute top-0 w-full z-10">
                    <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-3">
                        <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-blue-900/20">G</span>
                        About GeneGPT
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-[#252525] rounded-full text-gray-400 hover:text-white transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto px-8 pt-28 pb-12 custom-scrollbar space-y-20">

                    {/* SECTION 1 & 2: What & Why */}
                    <section className="max-w-3xl mx-auto text-center space-y-8">
                        <div>
                            <h3 className="text-3xl font-bold text-white mb-4 tracking-tight">Understanding Genetics, Simplified</h3>
                            <p className="text-lg text-gray-300 leading-relaxed font-light">
                                {INTRO_TEXT}
                            </p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-left mt-8">
                            <div className="bg-[#1a1a1a] p-6 rounded-2xl border border-[#2a2a2a]">
                                <h4 className="text-blue-400 font-semibold mb-2 flex items-center gap-2">
                                    <Activity className="w-4 h-4" /> Why it was built
                                </h4>
                                <p className="text-sm text-gray-400 leading-relaxed">
                                    {WHY_BUILT_TEXT}
                                </p>
                            </div>
                            <div className="bg-[#1a1a1a] p-6 rounded-2xl border border-[#2a2a2a]">
                                <h4 className="text-emerald-400 font-semibold mb-2 flex items-center gap-2">
                                    <ShieldCheck className="w-4 h-4" /> What it solves
                                </h4>
                                <p className="text-sm text-gray-400 leading-relaxed">
                                    {WHAT_SOLVES_TEXT}
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* SECTION 4 & 5: Architecture Diagram & Pipeline */}
                    <section className="max-w-4xl mx-auto">
                        <div className="text-center mb-10">
                            <h3 className="text-xl font-bold text-white mb-2">How GeneGPT Works</h3>
                            <p className="text-gray-500 text-sm">A transparent look at the internal pipeline</p>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
                            {/* Diagram */}
                            <div className="bg-[#161616] p-8 rounded-2xl border border-[#2a2a2a] flex flex-col items-center space-y-3 relative overflow-hidden">
                                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-600" />

                                <DiagramBox label="User Question" icon={<Activity className="w-4 h-4 text-blue-400" />} />
                                <Arrow />
                                <DiagramBox label="Intent Classifier" icon={<GitBranch className="w-4 h-4 text-purple-400" />} />
                                <Arrow />
                                <DiagramBox label="Structured JSON Parser" icon={<FileJson className="w-4 h-4 text-amber-400" />} />
                                <Arrow />
                                <div className="w-full text-center py-2 relative">
                                    <div className="absolute inset-x-0 top-1/2 h-px bg-[#333] -z-10" />
                                    <span className="bg-[#161616] px-3 text-[10px] text-gray-500 uppercase tracking-widest font-semibold">Evidence Fetch Layer</span>
                                </div>
                                <div className="grid grid-cols-2 gap-2 w-full max-w-[280px]">
                                    <SourceBadge name="OMIM" color="text-amber-500 bg-amber-500/10" />
                                    <SourceBadge name="ClinVar" color="text-blue-500 bg-blue-500/10" />
                                    <SourceBadge name="PubMed" color="text-sky-500 bg-sky-500/10" />
                                    <SourceBadge name="gnomAD" color="text-green-500 bg-green-500/10" />
                                </div>
                                <Arrow />
                                <DiagramBox label="Reasoning Layer" icon={<Brain className="w-4 h-4 text-rose-400" />} subtitle="Synthesis & Conflicts" />
                                <Arrow />
                                <DiagramBox label="Final Answer JSON" icon={<FileJson className="w-4 h-4 text-teal-400" />} />
                                <Arrow />
                                <div className="w-full bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg p-4 border border-[#333] text-center shadow-lg">
                                    <div className="font-semibold text-white text-sm">UI Rendering</div>
                                    <div className="text-[10px] text-gray-400 mt-1 flex justify-center gap-2">
                                        <span>Answer</span> • <span>Evidence</span> • <span>Meters</span>
                                    </div>
                                </div>
                            </div>

                            {/* Step Explanation */}
                            <div className="space-y-6 pt-2">
                                <h4 className="font-semibold text-white flex items-center gap-2 text-sm uppercase tracking-wider">
                                    <Layers className="w-4 h-4 text-gray-400" /> Pipeline Steps
                                </h4>
                                <ol className="space-y-4 relative border-l border-[#333] ml-2">
                                    {PIPELINE_STEPS_DATA.map((step) => (
                                        <Step key={step.number} number={step.number} title={step.title} text={step.text} />
                                    ))}
                                </ol>
                            </div>
                        </div>
                    </section>

                    {/* SECTION 6 & 7: JSON & Memory */}
                    <section className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                        <div className="space-y-4">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <FileJson className="w-5 h-5 text-amber-500" />
                                How the JSON System Works
                            </h3>
                            <p className="text-sm text-gray-400 leading-relaxed">
                                {JSON_SYSTEM_TEXT}
                            </p>
                        </div>
                        <div className="space-y-4">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <Lock className="w-5 h-5 text-rose-500" />
                                Memory System & Privacy
                            </h3>
                            <p className="text-sm text-gray-400 leading-relaxed">
                                <strong>{MEMORY_PRIVACY_PART1}</strong>
                                <br /><strong>{MEMORY_PRIVACY_PART2}</strong>
                                <br />{MEMORY_PRIVACY_PART3}
                            </p>
                        </div>
                    </section>

                    {/* SECTION 8: Meters */}
                    <section className="bg-[#161616] rounded-2xl border border-[#2a2a2a] p-8 max-w-4xl mx-auto">
                        <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                            <Scale className="w-5 h-5 text-teal-400" />
                            Understanding the Meters
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            <div className="space-y-2">
                                <div className="text-xs font-bold text-blue-400 uppercase tracking-wider">Evidence Trust</div>
                                <p className="text-sm text-gray-300">Shows how strong the backing scientific support is.</p>
                                <p className="text-xs text-gray-500">Based on source quality (Guidelines {'>'} Case Studies).</p>
                            </div>
                            <div className="space-y-2">
                                <div className="text-xs font-bold text-teal-400 uppercase tracking-wider">Scientific Consensus</div>
                                <p className="text-sm text-gray-300">Shows how stable and agreed-upon the science is.</p>
                                <p className="text-xs text-gray-500">Low scores mean emerging science, not errors.</p>
                            </div>
                            <div className="space-y-2">
                                <div className="text-xs font-bold text-purple-400 uppercase tracking-wider">Token Usage</div>
                                <p className="text-sm text-gray-300">Shows how much context/data was processed.</p>
                                <p className="text-xs text-gray-500">More tokens = comprehensive analysis.</p>
                            </div>
                        </div>
                    </section>

                    {/* SECTION 10: When to use */}
                    <section className="max-w-3xl mx-auto space-y-6">
                        <h3 className="text-lg font-bold text-white text-center">When to use GeneGPT</h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="bg-[#1a1a1a] p-5 rounded-xl border border-[#333] flex flex-col gap-3">
                                <div className="flex items-center gap-2 text-green-400 font-medium"><div className="w-5 h-5 bg-green-500/10 rounded-full flex items-center justify-center text-xs">✓</div> Recommended</div>
                                <ul className="space-y-2 text-sm text-gray-400 ml-7">
                                    <li>Learning genetics & terminology</li>
                                    <li>Understanding complex reports</li>
                                    <li>Preparing for doctor visits</li>
                                </ul>
                            </div>
                            <div className="bg-[#1a1a1a] p-5 rounded-xl border border-[#333] flex flex-col gap-3">
                                <div className="flex items-center gap-2 text-red-400 font-medium"><div className="w-5 h-5 bg-red-500/10 rounded-full flex items-center justify-center text-xs">✕</div> Not For</div>
                                <ul className="space-y-2 text-sm text-gray-400 ml-7">
                                    <li>Medical diagnosis</li>
                                    <li>Treatment decisions</li>
                                    <li>Emergency health advice</li>
                                </ul>
                            </div>
                        </div>
                    </section>

                    {/* SECTION 11: Footer */}
                    <div className="text-center pt-8 border-t border-[#2a2a2a] max-w-2xl mx-auto">
                        <p className="text-sm text-gray-500 font-medium">
                            GeneGPT is an educational support tool designed to foster understanding, not replace healthcare professionals.
                        </p>
                    </div>

                </div>
            </div>
        </div>
    );
}

// Subcomponents for the diagram
function DiagramBox({ label, icon, subtitle }: { label: string, icon: React.ReactNode, subtitle?: string }) {
    return (
        <div className="w-full bg-[#202020] p-3 rounded-lg border border-[#333] text-center shadow-sm flex flex-col items-center gap-1 group hover:border-[#444] transition-colors">
            <div className="opacity-80 group-hover:opacity-100 transition-opacity">{icon}</div>
            <div className="text-xs font-semibold text-gray-200">{label}</div>
            {subtitle && <div className="text-[10px] text-gray-500">{subtitle}</div>}
        </div>
    )
}

function Arrow() {
    return (
        <ArrowDown className="w-4 h-4 text-gray-600 my-1 flex-shrink-0" />
    )
}

function SourceBadge({ name, color }: { name: string, color: string }) {
    return (
        <div className={cn("text-[10px] font-medium px-2 py-1 rounded text-center border border-white/5", color)}>
            {name}
        </div>
    )
}

function Step({ number, title, text }: { number: string, title: string, text: string }) {
    return (
        <li className="ml-6 relative">
            <span className="absolute -left-[33px] top-0 flex items-center justify-center w-6 h-6 bg-[#222] rounded-full text-[10px] font-bold text-gray-500 border border-[#333]">
                {number}
            </span>
            <h5 className="text-sm font-semibold text-gray-200 mb-1">{title}</h5>
            <p className="text-sm text-gray-500 leading-relaxed font-light">{text}</p>
        </li>
    )
}
