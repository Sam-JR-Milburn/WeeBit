"use client";

import React, { useState, useEffect } from "react";

const DOODLE_GLYPHS = ["😝", "😆", "😵‍💫"];

// Totally vibecoded, but ehh.

interface Tile {
    id: string;
    glyph: string;
    top: string;
    left: string;
    transform: string;
}

interface DoodleBackgroundProps {
    children: React.ReactNode;
}

export default function DoodleBackground({ children }: DoodleBackgroundProps) {
    const [tiles, setTiles] = useState<Tile[]>([]);

    useEffect(() => {
        const items: Tile[] = [];
        const rows = 8;
        const cols = 12;

        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const glyph = DOODLE_GLYPHS[Math.floor(Math.random() * DOODLE_GLYPHS.length)];
                const topOffset = (Math.random() - 0.5) * 50;
                const leftOffset = (Math.random() - 0.5) * 50;
                const rotation = Math.random() * 60 - 30;
                //const scale = Math.random() * 0.4 + 0.8;

                items.push({
                    id: `${r}-${c}`,
                    glyph,
                    top: `${(r * (100 / rows)) + (topOffset / rows)}%`,
                    left: `${(c * (100 / cols)) + (leftOffset / cols)}%`,
                    transform: `rotate(${rotation}deg)`,
                });
            }
        }
        setTiles(items);
    }, []);

    return (
        <div className="relative flex-1 w-full bg-[#141414] overflow-hidden flex flex-col">

            <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
                {tiles.map((tile) => (
                    <span
                        key={tile.id}
                        style={{
                            fontFamily: "'NotoEmoji-Bold', sans-serif",
                            position: "absolute",
                            top: tile.top,
                            left: tile.left,
                            transform: tile.transform,
                            fontSize: "2.5rem",
                            color: "#112c5a",
                            opacity: 0.35,
                            userSelect: "none",
                        }}
                    >
                        {tile.glyph}
                    </span>
                ))}
            </div>

            {/* Foreground Content Layer */}
            <div className="relative z-10 w-full h-full flex flex-col flex-1">
                {children}
            </div>

        </div>
    );
}