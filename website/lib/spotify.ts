export function spotifyEmbed(value: string): string | null {
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      url.hostname !== "open.spotify.com" ||
      url.username ||
      url.password ||
      url.port
    )
      return null;
    const match = url.pathname.match(
      /^\/(?:intl-[a-z]{2}\/)?(playlist|album|track)\/([a-zA-Z0-9]{22})\/?$/,
    );
    return match
      ? `https://open.spotify.com/embed/${match[1]}/${match[2]}?utm_source=generator&theme=0`
      : null;
  } catch {
    return null;
  }
}
