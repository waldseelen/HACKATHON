/* ── Code Watermark Background ──────────────────────────── */
import { WATERMARK_LINES } from '@/lib/utils';

export function CodeWatermark() {
    // Generate a repeating pattern of code lines
    const lines: string[] = [];
    for (let i = 0; i < 60; i++) {
        const idx = i % WATERMARK_LINES.length;
        const indent = '  '.repeat(Math.floor(Math.random() * 4));
        lines.push(`${indent}${WATERMARK_LINES[idx]}`);
    }

    return (
        <div className="watermark-bg" aria-hidden="true">
            {lines.join('\n')}
        </div>
    );
}
