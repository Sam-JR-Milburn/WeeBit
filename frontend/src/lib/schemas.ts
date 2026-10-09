import { z } from "zod";

// Ensure that 'google.com' will result in 'https://google.com'.
export const linkSubmissionSchema = z.object({
    url: z
        .string()
        .trim()
        .min(1, "URL can't be empty")
        .transform((val) => (/^https?:\/\//i.test(val) ? val : `https://${val}`))
        .pipe(z.url("Please enter a valid URL.")),
});

export type LinkSubmissionInput = z.infer<typeof linkSubmissionSchema>;