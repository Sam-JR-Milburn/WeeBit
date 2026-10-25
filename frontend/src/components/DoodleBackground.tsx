"use client";

import React, { useState, useEffect, useRef } from "react";

const DOODLE_GLYPHS = ["😝", "😆", "😵‍💫", "😋", "👾", "🤖"];

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
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const updateGrid = () => {
            const width = container.clientWidth;
            const height = container.clientHeight;

            // X and Y divisors determining spacing density (e.g., one emoji every ~100px)
            const divisorX = 160;
            const divisorY = 160;

            const cols = Math.max(2, Math.floor(width / divisorX));
            const rows = Math.max(2, Math.floor(height / divisorY)) + 1;

            const items: Tile[] = [];

            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    const glyph = DOODLE_GLYPHS[(r + c) % DOODLE_GLYPHS.length];
                    const rotation = ((r * 37 + c * 19) % 40) - 20;

                    // Hexagonal staggering: offset every alternating row by 50% of divisorX
                    const isEvenRow = r % 2 === 0;
                    const xOffset = isEvenRow ? 0 : divisorX / 2;

                    // Calculate precise percentage placement based on render dimensions
                    const leftPercent = ((c * divisorX + xOffset) / width) * 100;
                    const topPercent = ((r * divisorY) / Math.max(height, 200)) * 100;

                    items.push({
                        id: `${r}-${c}`,
                        glyph,
                        top: `${topPercent}%`,
                        left: `${leftPercent}%`,
                        transform: `rotate(${rotation}deg) scale(2.0)`,
                    });
                }
            }
            setTiles(items);
        };

        // Initial calculation on mount
        updateGrid();

        // Re-calculate dynamically if the viewport or container size changes
        const resizeObserver = new ResizeObserver(() => {
            updateGrid();
        });

        resizeObserver.observe(container);

        return () => {
            resizeObserver.disconnect();
        };
    }, []);

    return (
        <div ref={containerRef} className="relative flex-1 w-full bg-[#141414] overflow-y-auto flex flex-col">

            <div className="absolute inset-0 pointer-events-none min-h-full z-0 overflow-hidden">
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