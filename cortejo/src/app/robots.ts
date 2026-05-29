import type { MetadataRoute } from "next";

const SITE = "https://maracatu.org";

// /compartilhar/* is explicitly disallowed: shared conversations are private
// by design (you only see them if someone shares the link with you). We do
// not want search engines indexing them, both for privacy of the sharing
// user and to avoid stale chat snapshots polluting search results.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/"],
        disallow: ["/api/", "/chat/", "/compartilhar/", "/auth/"],
      },
    ],
    sitemap: `${SITE}/sitemap.xml`,
    host: SITE,
  };
}
