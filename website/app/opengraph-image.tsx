import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
export const alt = "Discord Bot — ваш сервер, только ближе";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export default async function Image() {
  const font = await readFile(
    join(process.cwd(), "public/fonts/manrope-og.ttf"),
  );
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "#101314",
        color: "#f0f2ef",
        padding: "65px 80px",
        fontFamily: "Manrope",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          fontSize: 36,
          fontWeight: 700,
          letterSpacing: -2,
          color: "#a5e4ce",
        }}
      >
        <svg
          width="46"
          height="46"
          viewBox="0 0 40 40"
          fill="none"
          style={{ marginRight: 12 }}
        >
          <ellipse
            cx="20"
            cy="20"
            rx="15"
            ry="7"
            transform="rotate(-42 20 20)"
            stroke="#a5e4ce"
            strokeWidth="2"
          />
          <ellipse
            cx="20"
            cy="20"
            rx="15"
            ry="7"
            transform="rotate(42 20 20)"
            stroke="#a5e4ce"
            strokeWidth="2"
          />
        </svg>
        Discord Bot
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          marginTop: 65,
          fontSize: 88,
          fontWeight: 600,
          lineHeight: 1.1,
          letterSpacing: -5,
        }}
      >
        <span>Ваш сервер.</span>
        <span style={{ color: "#a5e4ce" }}>Только ближе.</span>
      </div>
      <div
        style={{
          display: "flex",
          marginTop: 40,
          fontSize: 23,
          color: "#8e9a96",
        }}
      >
        Меньше суеты. Больше совместных дел.
      </div>
    </div>,
    {
      ...size,
      fonts: [{ name: "Manrope", data: font, style: "normal", weight: 600 }],
    },
  );
}
