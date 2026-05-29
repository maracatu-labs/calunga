import type { MetadataRoute } from "next";
import { fetchFeed } from "@/lib/actions";

const SITE = "https://maracatu.org";

// Indexed pages: landing, feed list, individual feed items. Shared
// conversations (/share/*) and the authenticated chat area
// (/chat/*) are intentionally excluded — they are private surfaces.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const baseEntries: MetadataRoute.Sitemap = [
    {
      url: `${SITE}/`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${SITE}/feed`,
      lastModified: now,
      changeFrequency: "hourly",
      priority: 0.8,
    },
  ];

  // Pull a reasonable slice of the feed for sitemap. Search engines fetch
  // sitemap.xml infrequently, so a large slice is acceptable.
  try {
    const data = await fetchFeed({ limit: 200 });
    for (const evento of data.eventos) {
      baseEntries.push({
        url: `${SITE}/feed/${evento.id}`,
        lastModified: new Date(evento.updated_at || evento.created_at),
        changeFrequency: "monthly",
        priority: 0.5,
      });
    }
  } catch {
    // Backend offline: serve the static base entries only. Better to have
    // a partial sitemap than none.
  }

  return baseEntries;
}
