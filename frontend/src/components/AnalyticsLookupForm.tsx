"use client";

import React, { useState } from "react";
import { api, type LinkAnalyticsResponse } from "@/lib/api";
import AnalyticsChart from "@/components/AnalyticsChart";

export default function AnalyticsLookupForm() {
    const [shortRefCode, setShortRefCode] = useState<string>("");
    const [fromDate, setFromDate] = useState<string>("");
    const [toDate, setToDate] = useState<string>("");

    const [analyticsData, setAnalyticsData] = useState<LinkAnalyticsResponse | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const handleLookup = async (e: React.SubmitEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError(null);
        setAnalyticsData(null);

        let trimmedCode = shortRefCode.trim();
        if (!trimmedCode) {
            setError("Please enter a short reference code to inspect.");
            return;
        }

        // Transform if beginning with HOSTNAME/{short_ref_code}
        const FRONTEND_HOST = process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3080";
        const API_HOST = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

        if (trimmedCode.startsWith(FRONTEND_HOST)) {
            trimmedCode = trimmedCode.substring(FRONTEND_HOST.length);
        } else if (trimmedCode.startsWith(API_HOST)) {
            trimmedCode = trimmedCode.substring(API_HOST.length);
        }

        setLoading(true);

        try {
            const data = await api.Analytics.getAnalytics({
                short_ref_code: trimmedCode,
                from_date: fromDate ? fromDate : null,
                to_date: toDate ? toDate : null,
            });
            setAnalyticsData(data);
        } catch (err: unknown) {
            setError((err as Error).message || "Failed to fetch analytics for this code.");
        } finally {
            setLoading(false);
        }
    };

    // Calculate metrics from the response.
    const sumMetrics = (record: Record<string, number> = {}) => {
        return Object.values(record).reduce((acc, val) => acc + val, 0);
    };

    return (
        <div className="w-full max-w-3xl bg-[#112c5a] rounded-2xl p-8 sm:p-10 shadow-2xl flex flex-col gap-6 text-white">

            <div className="space-y-2">
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">WeeBit Analytics</h2>
                <p className="text-slate-300 text-sm sm:text-base">
                    Analytics on link usage, unique visitors, creation/recreation.
                </p>
            </div>

            <form onSubmit={handleLookup} className="w-full flex flex-col gap-4">
                <div className="w-full h-14 sm:h-16 bg-[#141414] border border-[#ffffff] focus-within:border-white rounded-xl p-2 flex items-center justify-between transition gap-3 shadow-inner">
                    <input
                        type="text"
                        required
                        value={shortRefCode}
                        onChange={(e) => setShortRefCode(e.target.value)}
                        placeholder="1dSgEp3"
                        className="flex-1 bg-transparent text-slate-100 text-base sm:text-lg pl-4 pr-2 outline-none truncate font-mono"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="h-full w-28 sm:w-32 bg-[#112c5a] hover:bg-[#1d4c9c] disabled:bg-[#141414] text-white font-semibold text-sm rounded-lg transition shrink-0 flex items-center justify-center shadow-md cursor-pointer"
                    >
                        {loading ? "Searching..." : "Inspect"}
                    </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
                    <div className="flex flex-col gap-1">
                        <label className="text-slate-300 font-medium">From Date (Optional)</label>
                        <input
                            type="date"
                            value={fromDate}
                            onChange={(e) => setFromDate(e.target.value)}
                            className="bg-[#141414] border border-white/40 focus:border-white rounded-lg px-3 py-2.5 text-slate-100 outline-none"
                        />
                    </div>
                    <div className="flex flex-col gap-1">
                        <label className="text-slate-300 font-medium">To Date (Optional)</label>
                        <input
                            type="date"
                            value={toDate}
                            onChange={(e) => setToDate(e.target.value)}
                            className="bg-[#141414] border border-white/40 focus:border-white rounded-lg px-3 py-2.5 text-slate-100 outline-none"
                        />
                    </div>
                </div>
            </form>

            <div className="w-full">
                {error && (
                    <div className="w-full min-h-[3.5rem] bg-[#141414] border border-[#ffffff] rounded-xl px-4 py-3 flex items-center text-[#b30800] text-sm font-medium">
                        {error}
                    </div>
                )}

                {analyticsData && !error && (
                    <div className="w-full bg-[#141414] border border-[#ffffff] rounded-xl p-6 flex flex-col gap-5 text-slate-200 transition">

                        {/* WeeBit + Url Section */}
                        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                            <div>
                                <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold block">Wee Bit</span>
                                <span className="text-emerald-400 font-bold text-lg block">{analyticsData.short_ref_code}</span>
                            </div>

                            <div className="w-full sm:w-64 text-left sm:text-right">
                                <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold block mb-1">RESOLVED URL</span>

                                <div className="overflow-hidden relative w-full group">
                                    <div className="truncate group-hover:overflow-visible group-hover:text-clip">
                                        <span
                                            className="font-mono text-emerald-400 font-bold text-lg whitespace-nowrap marquee-animation"
                                            style={{
                                                '--scroll-duration': `${Math.max(analyticsData.normalised_url.length * 0.08, 4)}s`
                                            } as React.CSSProperties}
                                        >
                                            {analyticsData.normalised_url}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <AnalyticsChart redirects={analyticsData.redirects} />

                        {/* Metrics */}
                        <div className="grid grid-cols-3 gap-3">
                            <div className="bg-[#112c5a]/40 border border-white/10 rounded-lg p-3 text-center">
                                <span className="text-xs text-slate-400 block mb-1">Total Redirects</span>
                                <span className="text-xl sm:text-2xl font-bold text-white">
                                    {sumMetrics(analyticsData.redirects)}
                                </span>
                            </div>
                            <div className="bg-[#112c5a]/40 border border-white/10 rounded-lg p-3 text-center">
                                <span className="text-xs text-slate-400 block mb-1">Unique Visitors</span>
                                <span className="text-xl sm:text-2xl font-bold text-white">
                                    {sumMetrics(analyticsData.unique_visitors)}
                                </span>
                            </div>
                            <div className="bg-[#112c5a]/40 border border-white/10 rounded-lg p-3 text-center">
                                <span className="text-xs text-slate-400 block mb-1">Total Creations</span>
                                <span className="text-xl sm:text-2xl font-bold text-white">
                                    {sumMetrics(analyticsData.creates)}
                                </span>
                            </div>
                        </div>

                    </div>
                )}

                {!analyticsData && !error && (
                    <div className="w-full h-16 bg-[#141414]/40 border border-dashed border-white/20 rounded-xl px-4 flex items-center justify-center text-slate-400 text-xs sm:text-sm">
                        Detailed statistics and metrics will load here once searched.
                    </div>
                )}
            </div>

        </div>
    );
}
