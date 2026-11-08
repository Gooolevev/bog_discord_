import { test } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { SpotifyPlayer } from "../components/spotify-player";

test("configured Spotify renders the real player immediately with autoplay permission", () => {
  const html = renderToStaticMarkup(createElement(SpotifyPlayer, {
    initialUrl: "https://open.spotify.com/track/0123456789012345678901?si=example",
  }));
  assert.match(html, /<iframe/);
  assert.match(html, /src="https:\/\/open.spotify.com\/embed\/track\/0123456789012345678901/);
  assert.match(html, /allow="[^"]*encrypted-media/);
  assert.match(html, /href="https:\/\/open.spotify.com\/track\/0123456789012345678901"/);
  assert.match(html, /allow="autoplay;/);
  assert.doesNotMatch(html, /Загрузить Spotify-плеер/);
});

test("missing or invalid Spotify configuration keeps the link form without a fake track", () => {
  for (const initialUrl of ["", "javascript:alert(1)", "https://untrusted.example/track/0123456789012345678901"]) {
    const html = renderToStaticMarkup(createElement(SpotifyPlayer, { initialUrl }));
    assert.doesNotMatch(html, /<iframe/);
    assert.match(html, /id="spotify-url"/);
  }
});
