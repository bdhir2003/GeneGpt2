import { Evidence, AnswerJson } from "../lib/api";
import { ExternalLink, Database, Activity, FileText, Info } from "lucide-react";
import { cn } from "../lib/utils";

interface EvidencePanelProps {
    answerJson: AnswerJson | null;
}

export function EvidencePanel({ answerJson }: EvidencePanelProps) {
    if (!answerJson) {
        return (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 p-8 text-center bg-gray-50/50 rounded-xl border border-gray-100 dark:bg-gray-800/20 dark:border-gray-800">
                <Activity className="w-12 h-12 mb-4 opacity-30" />
                <p className="text-sm font-medium">Evidence Context</p>
                <p className="text-xs mt-2 opacity-60">
                    Ask a question to see real-time data from OMIM, NCBI, ClinVar, and PubMed.
                </p>
            </div>
        );
    }

    const { evidence, gene, disease_focus } = answerJson;
    const omim = evidence?.omim || {};
    const ncbi = evidence?.ncbi || {};
    const clinvar = evidence?.clinvar || {};
    const pubmed = evidence?.pubmed || {};

    return (
        <div className="space-y-6 h-full p-4 overflow-y-auto custom-scrollbar text-white">

            {/* Evidence Source Indicator */}
            <div className="flex items-center justify-between text-xs text-gray-400 mb-2 px-1">
                <span className="uppercase tracking-wider font-semibold">Live Data Sources</span>
                <span className="uppercase tracking-wider font-semibold">JSON Parcel: {Boolean(gene || disease_focus || omim || clinvar || pubmed).toString()}</span>
            </div>

            {/* Gene Header */}
            {(gene?.symbol || gene?.omim_id) && (
                <div className="p-4 rounded-xl bg-[#1A1A1A] border border-[#303030] shadow-sm group hover:border-[#404040] transition-colors">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="p-1.5 bg-blue-500/10 rounded-lg">
                            <Database className="w-4 h-4 text-blue-400" />
                        </div>
                        <h3 className="font-semibold text-white text-sm tracking-tight">Gene Target</h3>
                    </div>
                    <div className="space-y-2 text-sm bg-[#111] p-3 rounded-lg border border-[#252525]">
                        {gene.symbol && (
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-gray-400">Symbol</span>
                                <span className="font-mono font-bold text-white tracking-wide bg-blue-500/20 px-2 py-0.5 rounded text-blue-200 border border-blue-500/20">{gene.symbol}</span>
                            </div>
                        )}
                        {gene.omim_id && (
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-gray-500">OMIM ID</span>
                                <span className="font-mono text-white">{gene.omim_id}</span>
                            </div>
                        )}
                        {gene.ncbi_gene_id && (
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-gray-500">NCBI ID</span>
                                <span className="font-mono text-white">{gene.ncbi_gene_id}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Disease Focus */}
            {disease_focus?.used && (
                <div className="p-4 rounded-xl bg-[#1A1A1A] border border-[#303030] shadow-sm">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="p-1.5 bg-emerald-500/10 rounded-lg">
                            <Activity className="w-4 h-4 text-emerald-400" />
                        </div>
                        <h3 className="font-semibold text-white text-sm">Disease Associations</h3>
                    </div>
                    <p className="text-xs text-gray-400 mb-3 px-1">
                        Total phenotypes: <span className="text-white font-mono">{disease_focus.total_phenotypes}</span>
                    </p>
                    <ul className="space-y-2">
                        {disease_focus.top_diseases?.slice(0, 3).map((d, i) => (
                            <li key={i} className="text-sm bg-[#111] p-2.5 rounded border border-[#252525] text-white border-l-4 border-l-emerald-500 leading-snug">
                                {d.replace(/[{}]/g, "")}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* OMIM */}
            {omim.used && (
                <div className="rounded-xl border border-[#303030] overflow-hidden bg-[#1A1A1A]">
                    <div className="bg-[#212121] px-4 py-2.5 border-b border-[#303030] flex justify-between items-center">
                        <span className="font-medium text-sm flex items-center gap-2 text-white">
                            <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]"></span> OMIM
                        </span>
                        {omim.link && (
                            <a
                                href={omim.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-gray-400 hover:text-white transition-colors"
                                title="Open OMIM"
                            >
                                <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                        )}
                    </div>
                    <div className="p-4 text-sm space-y-3">
                        <div>
                            <span className="text-gray-500 text-xs uppercase tracking-wider font-semibold block mb-1">Inheritance</span>
                            <p className="text-white leading-relaxed bg-[#111] p-2 rounded border border-[#252525]">{omim.inheritance || "Not specified"}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* ClinVar */}
            {clinvar.used && (
                <div className="rounded-xl border border-[#303030] overflow-hidden bg-[#1A1A1A]">
                    <div className="bg-[#212121] px-4 py-2.5 border-b border-[#303030] flex justify-between items-center">
                        <span className="font-medium text-sm flex items-center gap-2 text-white">
                            <span className="w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.4)]"></span> ClinVar
                        </span>
                        {clinvar.link && (
                            <a
                                href={clinvar.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-gray-400 hover:text-white transition-colors"
                                title="Open ClinVar"
                            >
                                <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                        )}
                    </div>
                    <div className="p-4 text-sm space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-[#111] p-2 rounded border border-[#252525]">
                                <span className="text-gray-500 text-[10px] uppercase font-bold block mb-0.5">Significance</span>
                                <p className="font-medium text-white">{clinvar.clinical_significance || "N/A"}</p>
                            </div>
                            <div className="bg-[#111] p-2 rounded border border-[#252525]">
                                <span className="text-gray-500 text-[10px] uppercase font-bold block mb-0.5">Accession</span>
                                <p className="font-mono text-xs text-purple-300">{clinvar.accession || "N/A"}</p>
                            </div>
                        </div>
                        <div>
                            <span className="text-gray-500 text-xs uppercase font-bold block mb-1">Condition</span>
                            <p className="text-white leading-snug">{clinvar.condition || "N/A"}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* PubMed */}
            {pubmed.used && pubmed.papers && pubmed.papers.length > 0 && (
                <div className="rounded-xl border border-[#303030] overflow-hidden bg-[#1A1A1A]">
                    <div className="bg-[#212121] px-4 py-2.5 border-b border-[#303030] flex justify-between items-center">
                        <span className="font-medium text-sm flex items-center gap-2 text-white">
                            <span className="w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.4)]"></span> PubMed
                        </span>
                        <span className="text-xs text-gray-500 font-medium">{pubmed.papers.length} papers</span>
                    </div>
                    <div className="divide-y divide-[#252525]">
                        {pubmed.papers.slice(0, 3).map((paper: any, i: number) => (
                            <div key={i} className="p-3 hover:bg-[#202020] transition-colors group">
                                <a
                                    href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs font-medium !text-sky-400 hover:!text-sky-300 hover:underline leading-relaxed block mb-1.5"
                                >
                                    {paper.title}
                                </a>
                                <div className="flex items-center justify-between text-[10px] text-gray-400 group-hover:text-gray-300">
                                    <span className="truncate max-w-[200px]">{paper.journal}</span>
                                    <span className="font-mono">{paper.year}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

