import { test } from "node:test";
import assert from "node:assert/strict";
import {
  canManage,
  createState,
  verifyState,
  isSameOrigin,
  validateSettings,
  validId,
} from "../lib/security";
import { spotifyEmbed } from "../lib/spotify";
test("OAuth state: signature, cookie binding and expiry", () => {
  const secret = "test-only-secret-with-more-than-32-characters";
  const state = createState(secret, 1000);
  assert.equal(verifyState(state, state, secret, 2000), true);
  assert.equal(
    verifyState(state, createState(secret, 1000), secret, 2000),
    false,
  );
  assert.equal(verifyState(state, state, "different", 2000), false);
  assert.equal(verifyState(state, state, secret, 601001), false);
  assert.equal(verifyState(state, state, secret, 999), false);
  assert.equal(verifyState("", "", secret), false);
});
test("Discord permissions use BigInt and do not trust malformed values", () => {
  const guild = { id: "123456789012345678", name: "test", icon: null };
  assert.equal(canManage({ ...guild, permissions: "32" }), true);
  assert.equal(
    canManage({ ...guild, permissions: String((2n ** 52n) | 8n) }),
    true,
  );
  assert.equal(canManage({ ...guild, owner: true }), true);
  assert.equal(canManage({ ...guild, permissions: "1024" }), false);
  assert.equal(canManage({ ...guild, permissions: "not-an-int" }), false);
  assert.equal(canManage({ ...guild, permissions: "-1" }), false);
});
test("state changes require the configured origin", () => {
  assert.equal(
    isSameOrigin("http://localhost:3000", "http://localhost:3000"),
    true,
  );
  assert.equal(
    isSameOrigin("https://evil.example", "http://localhost:3000"),
    false,
  );
  assert.equal(isSameOrigin(null, "http://localhost:3000"), false);
  assert.equal(
    isSameOrigin("http://localhost:3001", "http://localhost:3000"),
    false,
  );
});
test("settings reject foreign types, disabled channel and unknown keys", () => {
  const value = {
    monitor_enabled: true,
    monitor_channel_id: "123456789012345678",
    poll_minutes: 60,
  };
  assert.equal(validateSettings(value), true);
  for (const invalid of [
    { ...value, poll_minutes: 0 },
    { ...value, poll_minutes: 1441 },
    { ...value, poll_minutes: true },
    { ...value, monitor_channel_id: "0" },
    { ...value, extra: true },
    { ...value, monitor_enabled: "false" },
    null,
  ])
    assert.equal(validateSettings(invalid), false);
  assert.equal(
    validateSettings({
      ...value,
      monitor_enabled: false,
      monitor_channel_id: "0",
    }),
    true,
  );
  assert.equal(validId("0"), false);
  assert.equal(validId("00000000000000000"), false);
  assert.equal(validId("99999999999999999999"), false);
});
test("Spotify: construct safe embeds without arbitrary URLs or HTML", () => {
  assert.equal(
    spotifyEmbed(
      "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=example",
    ),
    "https://open.spotify.com/embed/playlist/37i9dQZF1DXcBWIGoYBM5M?utm_source=generator&theme=0",
  );
  assert.ok(
    spotifyEmbed(
      "https://open.spotify.com/intl-ru/track/0123456789012345678901",
    ),
  );
  for (const url of [
    "javascript:alert(1)",
    "https://open.spotify.com.evil.example/playlist/37i9dQZF1DXcBWIGoYBM5M",
    "http://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
    "https://evil@open.spotify.com/track/0123456789012345678901",
    "https://open.spotify.com/embed/track/0123456789012345678901",
    "<iframe/>",
    "https://open.spotify.com/artist/0123456789012345678901",
  ])
    assert.equal(spotifyEmbed(url), null);
});
