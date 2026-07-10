/// <reference path="../pb_data/types.d.ts" />

// Recreates public.albums. Writes stay backend-only (FastAPI's
// admin-authenticated PocketBase client performs all upserts); reads are
// public, matching the original "Public read access to albums" policy.
migrate((app) => {
  const collection = new Collection({
    type: "base",
    name: "albums",
    listRule: "",
    viewRule: "",
    createRule: null,
    updateRule: null,
    deleteRule: null,
    fields: [
      { type: "text", name: "title", required: true, max: 500 },
      { type: "text", name: "artist", required: true, max: 500 },
      { type: "text", name: "spotify_id", required: false, max: 200 },
      { type: "text", name: "discogs_id", required: false, max: 200 },
      { type: "text", name: "genre", required: false, max: 200 },
      { type: "text", name: "mood", required: false, max: 200 },
      { type: "number", name: "release_year", required: false },
      { type: "url", name: "cover_url", required: false },
      { type: "url", name: "spotify_preview_url", required: false },
      { type: "url", name: "spotify_url", required: false },
    ],
    indexes: [
      "CREATE UNIQUE INDEX idx_albums_spotify_id ON albums (spotify_id) WHERE spotify_id != ''",
      "CREATE UNIQUE INDEX idx_albums_title_artist_unique ON albums (lower(trim(title)), lower(trim(artist)))",
    ],
  })

  app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("albums")
  app.delete(collection)
})
