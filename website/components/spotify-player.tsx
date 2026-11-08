"use client";
import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { ArrowUpRight, Music2, Disc3, Link2 } from "lucide-react";
import { spotifyEmbed } from "@/lib/spotify";
import { Button } from "@/components/ui/button";
type SpotifyController = {
  addListener(event: "ready", callback: () => void): void;
  play(): void;
  destroy(): void;
};
type SpotifyApi = {
  createController(
    element: HTMLElement,
    options: { url: string; width: string; height: number },
    callback: (controller: SpotifyController) => void,
  ): void;
};
let spotifyApi: Promise<SpotifyApi> | null = null;
function loadSpotifyApi(): Promise<SpotifyApi> {
  if (spotifyApi) return spotifyApi;
  spotifyApi = new Promise<SpotifyApi>((resolve, reject) => {
    const script = document.createElement("script");
    const spotifyWindow = window as Window & {
      onSpotifyIframeApiReady?: (api: SpotifyApi) => void;
    };
    const timeout = window.setTimeout(fail, 15000);
    function fail() {
      window.clearTimeout(timeout);
      script.remove();
      spotifyApi = null;
      reject(new Error("Spotify API unavailable"));
    }
    spotifyWindow.onSpotifyIframeApiReady = (api) => {
      window.clearTimeout(timeout);
      resolve(api);
    };
    script.src = "https://open.spotify.com/embed/iframe-api/v1";
    script.async = true;
    script.onerror = fail;
    document.head.append(script);
  });
  return spotifyApi;
}
function SpotifyEmbed({ source }: { source: string }) {
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let cancelled = false;
    let controller: SpotifyController | undefined;
    let placeholder: HTMLDivElement | undefined;
    const original = container.current?.querySelector("iframe");
    loadSpotifyApi().then((api) => {
      if (cancelled || !container.current) return;
      placeholder = document.createElement("div");
      container.current.append(placeholder);
      api.createController(placeholder, {
        url: source.split("?")[0].replace("/embed/", "/") + "?theme=0",
        width: "100%",
        height: 352,
      }, (created) => {
        if (cancelled) {
          created.destroy();
          return;
        }
        controller = created;
        original?.remove();
        created.addListener("ready", () => {
          if (!cancelled) created.play();
        });
      });
    }).catch(() => {
      // The ordinary Embed remains usable when the optional API cannot load.
      placeholder?.remove();
      console.warn("Spotify autoplay API unavailable; use the player controls.");
    });
    return () => {
      cancelled = true;
      controller?.destroy();
      placeholder?.remove();
    };
  }, [source]);
  return (
    <div ref={container}>
      <iframe
        title="Spotify — выбранная музыка"
        src={source}
        width="100%"
        height="352"
        loading="eager"
        allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
        allowFullScreen
      />
    </div>
  );
}
export function SpotifyPlayer({ initialUrl = "" }: { initialUrl?: string }) {
  const [value, setValue] = useState(initialUrl);
  const [source, setSource] = useState<string | null>(() =>
    spotifyEmbed(initialUrl),
  );
  const [error, setError] = useState("");
  function open(event: React.FormEvent) {
    event.preventDefault();
    const embed = spotifyEmbed(value);
    if (!embed) {
      setError("Нужна ссылка open.spotify.com на трек, альбом или плейлист.");
      return;
    }
    setSource(embed);
    setError("");
  }
  return (
    <div className="music-player">
      <div className="music-player-top">
        <span>
          <Music2 size={15} /> SOUNDTRACK TO YOUR SERVER
        </span>
        <span className="spotify-wordmark">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="12" />
            <g
              fill="none"
              stroke="#10201a"
              strokeWidth="1.5"
              strokeLinecap="round"
            >
              <path d="M5 9c5-2 10-1 14 1M6 12c4-1.5 8-1 12 1M7 15c3-1 6-.7 9 1" />
            </g>
          </svg>
          Spotify
        </span>
      </div>
      {source ? (
        <div className="spotify-frame">
          <SpotifyEmbed key={source} source={source} />
          <p className="spotify-play-hint">Если музыка не началась автоматически, нажмите ▶ в плеере.</p>
          <a
            className="text-link"
            href={source.split("?")[0].replace("/embed/", "/")}
            target="_blank"
            rel="noopener noreferrer"
          >
            Открыть в Spotify <ArrowUpRight size={14} />
          </a>
        </div>
      ) : (
        <>
          <div className="record-stage">
            <Image
              src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/orbit-art.svg`}
              width={240}
              height={240}
              className="record-cover"
              alt="Абстрактная обложка с пересекающимися орбитами"
            />
            <div className="vinyl" aria-hidden="true">
              <div className="vinyl-label">
                <Disc3 size={32} />
              </div>
            </div>
            <span className="record-caption">СВОЙ РИТМ. СВОЯ КОМПАНИЯ.</span>
          </div>
          <div className="music-caption">
            <div>
              <h3>
                Хорошая компания.
                <br />И подходящий саундтрек.
              </h3>
              <p>Вставьте ссылку — остальное за Spotify.</p>
            </div>
            <button
              className="round-play"
              type="submit"
              form="spotify-link-form"
              aria-label="Загрузить Spotify-плеер"
            >
              <ArrowUpRight size={19} />
            </button>
          </div>
        </>
      )}
      <form id="spotify-link-form" onSubmit={open} className="spotify-form">
        <label className="sr-only" htmlFor="spotify-url">
          Ссылка Spotify
        </label>
        <div className="spotify-input">
          <Link2 size={16} />
          <input
            id="spotify-url"
            type="url"
            placeholder="Ссылка на ваш Spotify-плейлист"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            required
            autoComplete="off"
          />
          <Button
            type="submit"
            size="icon"
            aria-label="Открыть музыку в Spotify-проигрывателе"
          >
            <ArrowUpRight size={18} />
          </Button>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </form>
      <p className="spotify-note">
        Spotify может ограничить трек превью. Полную версию можно открыть по
        ссылке выше.
      </p>
    </div>
  );
}
