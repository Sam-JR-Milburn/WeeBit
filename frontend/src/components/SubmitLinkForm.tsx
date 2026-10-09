"use client";

import { useState } from "react";
import { LinkApi } from "@/lib/api";
import {linkSubmissionSchema} from "@/lib/schemas";

export default function SubmitLinkForm() {
    const [submitUrl, setSubmitUrl] = useState<string>("");
    const [shortUrl, setShortUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [copied, setCopied] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // Submit and retrieve a shortcode.
    const handleSubmit =
        async (e: React.SubmitEvent<HTMLFormElement>) => {
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
            const data = await LinkApi.createLink({ url: parsedUrl });
            const redirectUrl = LinkApi.buildShareableUrl(data.short_ref_code);
            setShortUrl(redirectUrl);
        } catch(err: unknown) {
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
    }

    return (
        <div className={"w-full max-w-lg min-h-[25vh] min-w-[20vw] bg-[#112c5a] rounded-xl p-6 sm:p-8 shadow-2xl flex flex-col justify-between"}>

            <div className="space-y-1.5 text-white">
                <h3 className="text-xl font-bold tracking-tight">Submit URL</h3>
                <p className="text-sm">
                    Submit a link, return a wee-bit.
                </p>
            </div>

            {/* Input Section */}
            <form onSubmit={handleSubmit} className={"w-full"}>
                <div className={"w-full h-12 bg-[#141414] border border-[#ffffff] focus-within:border-[#ffffff] rounded-lg p-1.5 flex items-center justify-between transition gap-2"}>
                    <input
                        type={"text"}
                        required
                        value={submitUrl}
                        onChange={(e) => setSubmitUrl(e.target.value)}
                        placeholder={"https://en.wikipedia.org/wiki/The_Dark_Side_of_the_Moon"}
                        className={"flex-1 bg-transparent text-slate-100 text-sm pl-3 pr-2 outline-none truncate"}
                        />
                    <button
                        type="submit"
                        disabled={loading}
                        className={"h-full w-20 bg-[#112c5a] hover:bg-[#1d4c9c] disabled:bg-[#141414] text-white font-medium text-xs rounded-md transition shrink-0 flex items-center justify-center"}
                    >
                        Submit
                    </button>
                </div>
            </form>

            {/* Link Copy + Error Section */}
            <div className={"h-12 w-full flex items-center"}>
                {error && (
                    <div className={"w-full h-12 bg-[#141414] border border-[#ffffff] rounded-lg px-4 flex items-center text-[#b30800] text-xs"}>
                        {error}
                    </div>
                )}

                {shortUrl && !error && (
                    <div className={'w-full h-12 bg-[#141414] border border-[#ffffff] rounded-lg p-1.5 flex items-center justify-between transition gap-2'}>
                        <span className="flex-1 font-mono text-sm text-emerald-400 pl-3 pr-2 truncate">
                            {shortUrl}
                        </span>
                        <button
                            type="button"
                            onClick={handleCopy}
                            className="h-full w-20 bg-[#112c5a] hover:bg-[#1d4c9c] text-slate-200 font-medium text-xs rounded-md transition shrink-0 flex items-center justify-center"
                        >
                            {copied ? "Copied!" : "Copy"}
                        </button>
                    </div>
                )}

                {/* Invisible if !error && !shortUrl */}
            </div>

        </div>
    )
}