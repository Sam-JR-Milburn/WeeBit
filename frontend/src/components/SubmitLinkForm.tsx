"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { linkSubmissionSchema } from "@/lib/schemas";

export default function SubmitLinkForm() {
    const [submitUrl, setSubmitUrl] = useState<string>("");
    const [shortUrl, setShortUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [copied, setCopied] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // Submit and retrieve a shortcode.
    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError(null);
        setCopied(false);

        // Preprocess
        const validationResult = linkSubmissionSchema.safeParse({ url: submitUrl });
        if (!validationResult.success) {
            try {
                setError(validationResult.error.issues[0].message);
            } catch {
                setError("Failed to parse URL");
            }
            return;
        }
        const parsedUrl = validationResult.data.url;
        setLoading(true);

        try {
            const data = await api.Links.createLink({ url: parsedUrl });
            const redirectUrl = api.Links.buildShareableUrl(data.short_ref_code);
            setShortUrl(redirectUrl);
        } catch (err: unknown) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    // Copy to clipboard
    const handleCopy = async () => {
        if (!shortUrl) return;
        await navigator.clipboard.writeText(shortUrl);
        setCopied(true);
        setTimeout(() => setCopied(false), 3000);
    };

    return (
        <div className="w-full max-w-3xl bg-[#112c5a] rounded-2xl p-8 sm:p-10 shadow-2xl flex flex-col gap-6 text-white">

            <div className="space-y-2">
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Submit URL</h2>
                <p className="text-slate-300 text-sm sm:text-base">
                    Submit a link, return a wee-bit.
                </p>
            </div>

            {/* Input Section */}
            <form onSubmit={handleSubmit} className="w-full">
                <div className="w-full h-14 sm:h-16 bg-[#141414] border border-[#ffffff] focus-within:border-white rounded-xl p-2 flex items-center justify-between transition gap-3 shadow-inner">
                    <input
                        type="text"
                        required
                        value={submitUrl}
                        onChange={(e) => setSubmitUrl(e.target.value)}
                        placeholder="https://en.wikipedia.org/wiki/The_Dark_Side_of_the_Moon"
                        className="flex-1 bg-transparent text-slate-100 text-base sm:text-lg pl-4 pr-2 outline-none truncate font-mono"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="h-full w-28 sm:w-32 bg-[#112c5a] hover:bg-[#1d4c9c] disabled:bg-[#141414] text-white font-semibold text-sm rounded-lg transition shrink-0 flex items-center justify-center shadow-md cursor-pointer"
                    >
                        {loading ? "Submitting..." : "Submit"}
                    </button>
                </div>
            </form>

            {/* Link Copy + Error Section */}
            <div className="w-full">
                {error && (
                    <div className="w-full min-h-[3.5rem] bg-[#141414] border border-[#ffffff] rounded-xl px-4 py-3 flex items-center text-[#b30800] text-sm font-medium">
                        {error}
                    </div>
                )}

                {shortUrl && !error && (
                    <div className="w-full h-14 sm:h-16 bg-[#141414] border border-[#ffffff] rounded-xl p-2 flex items-center justify-between transition gap-3 shadow-inner">
                        <span className="flex-1 font-mono text-base sm:text-lg text-emerald-400 pl-4 pr-2 truncate font-bold">
                            {shortUrl}
                        </span>
                        <button
                            type="button"
                            onClick={handleCopy}
                            className="h-full w-28 sm:w-32 bg-[#112c5a] hover:bg-[#1d4c9c] text-slate-200 font-semibold text-sm rounded-lg transition shrink-0 flex items-center justify-center shadow-md cursor-pointer"
                        >
                            {copied ? "Copied!" : "Copy"}
                        </button>
                    </div>
                )}

                {!shortUrl && !error && (
                    <div className="w-full h-16 bg-[#141414]/40 border border-dashed border-white/20 rounded-xl px-4 flex items-center justify-center text-slate-400 text-xs sm:text-sm">
                        Your short link will appear here once submitted.
                    </div>
                )}
            </div>

        </div>
    );
}