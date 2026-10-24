"use client";

import React from "react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

interface AnalyticsChartProps {
    redirects: Record<string, number>;
}

export default function AnalyticsChart({ redirects }: AnalyticsChartProps) {
    // Transform data
    const chartData = Object.entries(redirects || {})
        .map(([date, count]) => ({
            date,
            redirects: count,
        }))
        .sort((a, b) => a.date.localeCompare(b.date));

    return (
        <div className="w-full pt-4 border-t border-slate-800 flex flex-col gap-3">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold block">
                Daily Redirect History
            </span>

            {chartData.length > 0 ? (
                <div className="w-full h-64 bg-[#112c5a]/20 border border-white/10 rounded-xl p-3">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#223a66" opacity={0.4} />
                            <XAxis
                                dataKey="date"
                                stroke="#94a3b8"
                                fontSize={11}
                                tickLine={false}
                                axisLine={{ stroke: '#223a66' }}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={11}
                                tickLine={false}
                                axisLine={{ stroke: '#223a66' }}
                                allowDecimals={false}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#112c5a',
                                    border: '1px solid #ffffff',
                                    borderRadius: '0.75rem',
                                    color: '#ffffff',
                                    fontSize: '12px',
                                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
                                }}
                                itemStyle={{ color: '#34d399', fontWeight: 'bold' }}
                                labelStyle={{ color: '#cbd5e1', marginBottom: '4px', fontWeight: '600' }}
                            />
                            <Line
                                type="monotone"
                                dataKey="redirects"
                                stroke="#34d399"
                                strokeWidth={3}
                                dot={{ fill: '#34d399', strokeWidth: 2, r: 4 }}
                                activeDot={{ r: 6, fill: '#ffffff', stroke: '#34d399', strokeWidth: 2 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            ) : (
                <div className="w-full h-28 flex items-center justify-center bg-[#112c5a]/20 border border-dashed border-white/10 rounded-xl text-slate-400 text-xs font-mono">
                    No redirect activity recorded for this date window.
                </div>
            )}
        </div>
    );
}