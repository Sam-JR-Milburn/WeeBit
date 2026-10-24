import "./globals.css"
import type { Metadata } from "next";
import Header from "@/components/Header";
import DoodleBackground from "@/components/DoodleBackground";

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
            <div className={"h-screen w-screen flex flex-col overflow-hidden text-slate-100"}>
                <Header />
                <DoodleBackground>
                    {children}
                </DoodleBackground>
            </div>
        </body>
        </html>
    );
}