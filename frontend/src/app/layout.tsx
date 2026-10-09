import "./globals.css"
import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "WeeBit",
    description: "Deterministic URL shortener",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
        <body
            style={{backgroundColor: "#141414"}}
            className="antialiased">
        {children}
        </body>
        </html>
    );
}