export interface LinkResponse {
    short_ref_code: string;
    normalised_url: string;
}
export interface CreateLinkPayload {
    url: string;
}

export const getBaseUrl = (): string => {
    if (typeof window !== 'undefined') { // Client-side fallback
        return process.env.NEXT_PUBLIC_SITE_URL || window.location.origin;
    }
    return process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3080";
}

/**
 * Object literal namespace for calling.
 */
export const LinkApi = {
    /**
     * Turn a URL into a Wee Bit.
     * @param payload the URL interface
     */
    async createLink(payload: CreateLinkPayload): Promise<LinkResponse> {
        const response = await fetch("/api/link", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || "Failed to create link.");
        }
        return response.json();
    },

    /**
     * Construct the redirection URL.
     */
    buildShareableUrl(ShortRefCode: string): string {
        const baseUrl: string = getBaseUrl().replace(/\/$/, ""); // Strip trailing slashes, if any
        return `${baseUrl}/${ShortRefCode}`;
    }
}
