import FingerprintJS from '@fingerprintjs/fingerprintjs';

/**
 * Load/initialise Fingerprint JS once - promise function to grab it.
 */
let fpPromise: Promise<any> | null = null;
async function getFingerprintJSId(): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    try {
        if (!fpPromise) {
            fpPromise = FingerprintJS.load();
        }
        const fp = await fpPromise;
        const result = await fp.get();

        // Encode a FingerprintJS hash, unique to a visitor.
        const msgBuffer = new TextEncoder().encode(result.visitorId);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch (error) {
        console.warn("Failed to generate browser fingerprint:", error);
        return null;
    }
}



/**
 *      LINKS
 */

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

export const LinksApi = {
    /**
     * Turn a URL into a Wee Bit.
     * @param payload the URL interface
     */
    async createLink(payload: CreateLinkPayload): Promise<LinkResponse> {
        const headers: Record<string, string> = {
            "Content-Type": "application/json",
        }

        const visitorId = await getFingerprintJSId();
        if (visitorId) {
            headers["X-Visitor-Id"] = visitorId;
        }

        const response = await fetch("/api/links", {
            method: "POST",
            headers: headers,
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

/**
 *      ANALYTICS
 */

export interface GetLinkAnalyticsPayload {
    short_ref_code: string;
    from_date?: string | null;
    to_date?: string | null;
}

export interface LinkAnalyticsResponse {
    short_ref_code: string;
    normalised_url: string;
    from_date?: string | null;
    to_date: string;
    creates: Record<string, number>,
    redirects: Record<string, number>,
    unique_visitors: Record<string, number>,
}

export const AnalyticsApi = {
    /**
     * Get the analytics for a Wee Bit.
     * @param payload the short reference code, from date and to date.
     */
    async getAnalytics(payload: GetLinkAnalyticsPayload): Promise<LinkAnalyticsResponse>{
        const headers: Record<string, string> = {
            "Content-Type": "application/json",
        }

        const visitorId = await getFingerprintJSId();
        if (visitorId) {
            headers["X-Visitor-Id"] = visitorId;
        }

        // Add to/from dates if applicable.
        const params = new URLSearchParams();
        if (payload.from_date) params.append("from_date", payload.from_date);
        if (payload.to_date) params.append("to_date", payload.to_date);
        const params_string = params.toString() ? `?${params.toString()}` : "";

        const response = await fetch(`/api/analytics/${payload.short_ref_code}${params_string}`, {
            method: "GET",
            headers: headers,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Failed to fetch analytics. (Status): ${response.status}, ${response.statusText}`);
        }

        return response.json();
    }
}



/**
 * Object Literal Namespace for API calls
 */
export const api = {
    Links: LinksApi,
    Analytics: AnalyticsApi,
}